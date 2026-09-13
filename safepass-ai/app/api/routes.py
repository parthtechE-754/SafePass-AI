"""
SafePass AI — API Routes
All REST endpoints for route risk computation, blackspot data, and weather.
"""

import os
import math
import httpx
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Query, HTTPException
from pydantic import BaseModel

from app.data.blackspots import get_blackspots_geojson, get_nearby_blackspots
from app.ml.risk_engine import RiskEngine
from app.services.supabase_client import supabase_service

router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────

class RouteRiskRequest(BaseModel):
    """Request body for route risk computation."""
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    travel_hour: Optional[int] = None  # 0-23, None = now
    travel_month: Optional[int] = None
    vehicle_type: Optional[str] = "car"  # car, two_wheeler, truck


class PointRiskRequest(BaseModel):
    """Request body for single-point risk."""
    lat: float
    lng: float
    travel_hour: Optional[int] = None


class SaveTripRequest(BaseModel):
    """Trip record to store in Supabase."""
    origin_name: str
    origin_lat: float
    origin_lng: float
    dest_name: str
    dest_lat: float
    dest_lng: float
    corridor_name: str
    safety_score: float
    avg_cri: float
    distance_km: float
    est_time_min: int
    danger_zones: int = 0
    weather: Optional[dict] = None
    user_id: Optional[str] = "driver_anon"


class ReportHazardRequest(BaseModel):
    """Citizen highway hazard report."""
    title: str
    hazard_type: str = "blackspot"
    severity: float = 5.0
    lat: float
    lng: float
    highway: Optional[str] = "National Highway"
    description: Optional[str] = ""
    reported_by: Optional[str] = "Citizen Reporter"


class LogSosRequest(BaseModel):
    """Emergency SOS telemetry."""
    lat: float
    lng: float
    service: str = "112"
    notes: Optional[str] = "Emergency call from SafePass Maps"


# ── System Health Endpoint ───────────────────────────────────────────────

@router.get("/health")
async def api_health(request: Request):
    """Return health status of SafePass AI."""
    spots_count = len(getattr(request.app.state, "blackspots", []))
    return {
        "status": "healthy",
        "service": "SafePass AI",
        "version": "1.0.0",
        "blackspots_loaded": spots_count,
        "database": supabase_service.get_status()["mode"],
    }


# ── Blackspot Endpoints ──────────────────────────────────────────────────

@router.get("/blackspots")
async def get_blackspots():
    """Return all blackspots as GeoJSON."""
    return get_blackspots_geojson()


@router.get("/blackspots/nearby")
async def get_nearby(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: float = Query(10.0, description="Radius in km"),
):
    """Find blackspots near a point."""
    spots = get_nearby_blackspots(lat, lng, radius)
    return {"count": len(spots), "blackspots": spots}


# ── Weather Endpoint ─────────────────────────────────────────────────────

@router.get("/weather")
async def get_weather(
    lat: float = Query(...),
    lng: float = Query(...),
):
    """Fetch real-time live weather using Open-Meteo (100% Free, zero key required) or OpenWeatherMap."""
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "")

    # 1. If user provided an OpenWeatherMap key, try that first
    if api_key and api_key != "your_owm_key_here":
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": lat, "lon": lng, "appid": api_key, "units": "metric"},
                    timeout=4.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "temperature_c": round(data["main"]["temp"], 1),
                        "humidity": data["main"]["humidity"],
                        "wind_kmh": round(data["wind"]["speed"] * 3.6, 1),
                        "visibility_km": round(data.get("visibility", 10000) / 1000, 1),
                        "rain_mm": data.get("rain", {}).get("1h", 0),
                        "weather_main": data["weather"][0]["main"],
                        "weather_desc": data["weather"][0]["description"],
                        "icon": data["weather"][0]["icon"],
                        "source": "openweathermap",
                    }
        except Exception:
            pass

    # 2. Connect 100% Free Live Open-Meteo Satellite & Meteorological API
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lng}&current="
            f"temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&timezone=auto"
        )
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json().get("current", {})
                w_code = data.get("weather_code", 0)

                # WMO weather code descriptions
                w_desc = "Clear sky"
                w_main = "Clear"
                w_icon = "01d"

                if w_code in (1, 2, 3):
                    w_main, w_desc, w_icon = "Clouds", "Partly cloudy", "02d"
                elif w_code in (45, 48):
                    w_main, w_desc, w_icon = "Fog", "Dense highway fog", "50d"
                elif w_code in (51, 53, 55, 56, 57):
                    w_main, w_desc, w_icon = "Drizzle", "Light drizzle", "09d"
                elif w_code in (61, 63, 65, 80, 81, 82):
                    w_main, w_desc, w_icon = "Rain", "Moderate rainfall", "10d"
                elif w_code in (95, 96, 99):
                    w_main, w_desc, w_icon = "Thunderstorm", "Severe thunderstorm", "11d"

                rain_amount = data.get("rain") or data.get("precipitation") or 0.0

                return {
                    "temperature_c": round(data.get("temperature_2m", 28.0), 1),
                    "humidity": data.get("relative_humidity_2m", 65),
                    "wind_kmh": round(data.get("wind_speed_10m", 12.0), 1),
                    "visibility_km": 3.0 if w_code in (45, 48) else (5.0 if rain_amount > 5 else 10.0),
                    "rain_mm": round(rain_amount, 1),
                    "weather_main": w_main,
                    "weather_desc": w_desc,
                    "icon": w_icon,
                    "source": "open-meteo-live",
                }
    except Exception:
        pass

    # 3. Fallback simulation if network drops
    return _simulate_weather(lat, lng)


def _simulate_weather(lat: float, lng: float) -> dict:
    """Simulate realistic weather for demo purposes."""
    import random
    now = datetime.now()
    is_monsoon = now.month in (6, 7, 8, 9)
    is_winter = now.month in (11, 12, 1, 2)

    if is_monsoon:
        rain = random.choice([0, 5, 12, 25, 40, 60])
        visibility = random.choice([2, 4, 6, 8, 10])
        temp = random.randint(24, 32)
    elif is_winter:
        rain = 0
        visibility = random.choice([0.3, 0.5, 1, 3, 8, 10])
        temp = random.randint(8, 20)
    else:
        rain = random.choice([0, 0, 0, 2, 5])
        visibility = random.choice([6, 8, 10, 10])
        temp = random.randint(28, 42)

    weather_states = {
        0: ("Clear", "clear sky", "01d"),
        (1, 5): ("Drizzle", "light drizzle", "09d"),
        (5, 20): ("Rain", "moderate rain", "10d"),
        (20, 50): ("Rain", "heavy rain", "10d"),
        (50, 100): ("Thunderstorm", "heavy thunderstorm", "11d"),
    }

    main, desc, icon = "Clear", "clear sky", "01d"
    if rain > 50:
        main, desc, icon = "Thunderstorm", "heavy thunderstorm", "11d"
    elif rain > 20:
        main, desc, icon = "Rain", "heavy rain", "10d"
    elif rain > 5:
        main, desc, icon = "Rain", "moderate rain", "10d"
    elif rain > 0:
        main, desc, icon = "Drizzle", "light drizzle", "09d"
    elif visibility < 1:
        main, desc, icon = "Fog", "dense fog", "50d"

    return {
        "temperature_c": temp,
        "humidity": random.randint(40, 95),
        "wind_kmh": round(random.uniform(5, 35), 1),
        "visibility_km": visibility,
        "rain_mm": rain,
        "weather_main": main,
        "weather_desc": desc,
        "icon": icon,
        "source": "simulated",
    }


# ── Route Risk Computation ───────────────────────────────────────────────

@router.post("/route/risk")
async def compute_route_risk(request: Request, body: RouteRiskRequest):
    """
    Compute Corridor Risk Index for a route.
    Generates sample points along the straight-line path and scores each.
    """
    risk_engine: RiskEngine = request.app.state.risk_engine

    # Generate interpolated points along the route
    route_points = _interpolate_route(
        body.origin_lat, body.origin_lng,
        body.dest_lat, body.dest_lng,
        num_segments=20,
    )

    # Determine travel time
    now = datetime.now()
    if body.travel_hour is not None:
        now = now.replace(hour=body.travel_hour, minute=0)
    if body.travel_month is not None:
        now = now.replace(month=body.travel_month)

    # Get weather for midpoint
    mid_idx = len(route_points) // 2
    mid_lat, mid_lng = route_points[mid_idx]
    weather = await get_weather(lat=mid_lat, lng=mid_lng)

    # Compute risk for each segment
    result = risk_engine.compute_route_risk(
        route_points=route_points,
        weather_data=weather,
        travel_time=now,
    )

    # Add route metadata
    distance_km = _haversine_distance(
        body.origin_lat, body.origin_lng,
        body.dest_lat, body.dest_lng,
    )

    result["distance_km"] = round(distance_km, 1)
    result["weather"] = weather
    result["vehicle_type"] = body.vehicle_type
    result["travel_time"] = now.isoformat()
    result["route_points"] = [{"lat": p[0], "lng": p[1]} for p in route_points]

    # Safety score (inverted CRI, 0-10 where 10 = safest)
    result["safety_score"] = round(10 - result["avg_cri"], 1)

    return result


@router.post("/point/risk")
async def compute_point_risk(request: Request, body: PointRiskRequest):
    """Compute risk for a single point."""
    risk_engine: RiskEngine = request.app.state.risk_engine

    now = datetime.now()
    if body.travel_hour is not None:
        now = now.replace(hour=body.travel_hour)

    weather = await get_weather(lat=body.lat, lng=body.lng)

    result = risk_engine.compute_corridor_risk_index(
        lat=body.lat,
        lng=body.lng,
        weather=weather,
        travel_time=now,
    )
    result["weather"] = weather
    return result


# ── Compare Routes ───────────────────────────────────────────────────────

async def _fetch_osrm_routes(lat1: float, lng1: float, lat2: float, lng2: float):
    """Attempt to fetch real driving road geometry from OSRM."""
    url = f"https://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson&alternatives=true&steps=true"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    results = []
                    names = [
                        "Recommended Safe Corridor",
                        "Express Highway Corridor",
                        "Alternative Secondary Route"
                    ]
                    for idx, r in enumerate(data["routes"][:3]):
                        coords = r["geometry"]["coordinates"]  # [lng, lat]
                        # Downsample points for smooth rendering
                        step = max(1, len(coords) // 35)
                        sampled = coords[::step]
                        if sampled[-1] != coords[-1]:
                            sampled.append(coords[-1])
                        pts = [(round(c[1], 5), round(c[0], 5)) for c in sampled]
                        dist_km = round(r.get("distance", 0) / 1000, 1)
                        dur_min = round(r.get("duration", 0) / 60)

                        steps_text = []
                        for leg in r.get("legs", []):
                            for s in leg.get("steps", []):
                                name = s.get("name") or "Corridor Segment"
                                man = s.get("maneuver", {}).get("type", "proceed")
                                steps_text.append(f"{man.title()} onto {name}")

                        name_label = names[idx] if idx < len(names) else f"Route Variant {idx+1}"
                        results.append((name_label, pts, dist_km, dur_min, steps_text[:8]))
                    return results
    except Exception:
        pass
    return None


@router.post("/routes/compare")
async def compare_routes(request: Request, body: RouteRiskRequest):
    """
    Compare multiple route options between origin and destination.
    Uses real OSRM road geometry if available, supplemented with intelligent corridor alternatives.
    """
    risk_engine: RiskEngine = request.app.state.risk_engine

    now = datetime.now()
    if body.travel_hour is not None:
        now = now.replace(hour=body.travel_hour)

    routes = []

    # Try fetching real OSRM routes first
    osrm_data = await _fetch_osrm_routes(body.origin_lat, body.origin_lng, body.dest_lat, body.dest_lng)

    mid_point = (body.origin_lat + body.dest_lat) / 2, (body.origin_lng + body.dest_lng) / 2
    weather = await get_weather(lat=mid_point[0], lng=mid_point[1])

    if osrm_data and len(osrm_data) > 0:
        for name, points, dist_km, est_time_min, steps in osrm_data:
            result = risk_engine.compute_route_risk(points, weather, now)
            routes.append({
                "name": name,
                "avg_cri": result["avg_cri"],
                "max_cri": result["max_cri"],
                "safety_score": round(10 - result["avg_cri"], 1),
                "danger_zones": result["danger_zones"],
                "distance_km": dist_km,
                "est_time_min": est_time_min,
                "overall_level": result["overall_level"],
                "segments": result["segments"],
                "steps": steps,
                "route_points": [{"lat": p[0], "lng": p[1]} for p in points],
            })

    # If fewer than 3 route options (or OSRM failed/throttled), supplement with corridor variants
    if len(routes) < 3:
        existing_names = {r["name"] for r in routes}

        direct_points = _interpolate_route(
            body.origin_lat, body.origin_lng,
            body.dest_lat, body.dest_lng, 18
        )

        mid_lat_n = (body.origin_lat + body.dest_lat) / 2 + 0.09
        mid_lng_n = (body.origin_lng + body.dest_lng) / 2
        north_points = (
            _interpolate_route(body.origin_lat, body.origin_lng, mid_lat_n, mid_lng_n, 9) +
            _interpolate_route(mid_lat_n, mid_lng_n, body.dest_lat, body.dest_lng, 9)
        )

        mid_lat_s = (body.origin_lat + body.dest_lat) / 2 - 0.07
        mid_lng_s = (body.origin_lng + body.dest_lng) / 2 + 0.05
        south_points = (
            _interpolate_route(body.origin_lat, body.origin_lng, mid_lat_s, mid_lng_s, 9) +
            _interpolate_route(mid_lat_s, mid_lng_s, body.dest_lat, body.dest_lng, 9)
        )

        supplemental_candidates = [
            ("Recommended Safe Corridor", direct_points),
            ("Northern Bypass Highway", north_points),
            ("Southern Express Corridor", south_points),
        ]

        for name, points in supplemental_candidates:
            if len(routes) >= 3:
                break
            if name in existing_names:
                continue

            result = risk_engine.compute_route_risk(points, weather, now)
            dist = sum(
                _haversine_distance(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
                for i in range(len(points) - 1)
            )
            est_time_min = round(dist / 65 * 60)

            routes.append({
                "name": name,
                "avg_cri": result["avg_cri"],
                "max_cri": result["max_cri"],
                "safety_score": round(10 - result["avg_cri"], 1),
                "danger_zones": result["danger_zones"],
                "distance_km": round(dist, 1),
                "est_time_min": est_time_min,
                "overall_level": result["overall_level"],
                "segments": result["segments"],
                "steps": [
                    f"Start corridor drive on {name}",
                    "Pass through automated highway surveillance checkpoint",
                    "Maintain lane discipline through monitored sector",
                    "Arrive safely at destination"
                ],
                "route_points": [{"lat": p[0], "lng": p[1]} for p in points],
            })
            existing_names.add(name)

    # Sort by safety score (highest safety first)
    routes.sort(key=lambda r: r["safety_score"], reverse=True)

    return {
        "routes": routes,
        "weather": weather,
        "recommended": routes[0]["name"],
        "recommendation_reason": f"Top safety rating ({routes[0]['safety_score']}/10) with lowest corridor risk exposure.",
    }


@router.get("/nearest-hazard")
async def get_nearest_hazard(
    request: Request,
    lat: float = Query(..., description="Current user latitude"),
    lng: float = Query(..., description="Current user longitude"),
    radius: float = Query(35.0, description="Max lookup radius in km"),
):
    """Find the single closest accident blackspot or road hazard to user live GPS position."""
    spots = get_nearby_blackspots(lat, lng, radius)
    if not spots:
        return {
            "has_hazard": False,
            "message": "Corridor clear — no critical blackspots within 35 km."
        }

    # Sort by distance
    spots.sort(key=lambda s: s.get("distance_km", 999))
    closest = spots[0]
    dist = round(closest.get("distance_km", 0), 1)

    if dist <= 2.0:
        urgency = "CRITICAL"
        msg = f"DANGER: Approaching {closest['name']} in {dist} km! High crash history ({closest.get('annual_fatalities', 20)} fatalities). Reduce speed to {closest.get('speed_limit', 50)} km/h immediately."
    elif dist <= 6.0:
        urgency = "WARNING"
        factors = ", ".join(closest.get("risk_factors", [])[:2]).replace("_", " ")
        msg = f"CAUTION: {closest['name']} ahead in {dist} km on {closest.get('highway', 'Highway')}. Watch for {factors}."
    else:
        urgency = "ADVISORY"
        msg = f"Approaching {closest['name']} in {dist} km. Safe highway corridor zone."

    return {
        "has_hazard": True,
        "hazard": closest,
        "distance_km": dist,
        "urgency": urgency,
        "advisory": msg,
    }


# ── Temporal Risk Profile ────────────────────────────────────────────────

@router.get("/temporal-risk")
async def get_temporal_risk(
    request: Request,
    origin_lat: float = Query(...),
    origin_lng: float = Query(...),
    dest_lat: float = Query(...),
    dest_lng: float = Query(...),
):
    """Get hourly risk profile for a route — 'When should I travel?'"""
    risk_engine: RiskEngine = request.app.state.risk_engine

    points = _interpolate_route(origin_lat, origin_lng, dest_lat, dest_lng, 10)
    profile = risk_engine._compute_hourly_risk_profile(points)

    safest_hour = min(profile, key=profile.get)
    riskiest_hour = max(profile, key=profile.get)

    return {
        "hourly_risk": profile,
        "safest_hour": safest_hour,
        "safest_risk": profile[safest_hour],
        "riskiest_hour": riskiest_hour,
        "riskiest_risk": profile[riskiest_hour],
        "recommendation": f"Travel at {safest_hour}:00 for the lowest risk ({profile[safest_hour]}/10). Avoid {riskiest_hour}:00 ({profile[riskiest_hour]}/10).",
    }


# ── Utility Functions ────────────────────────────────────────────────────

def _interpolate_route(
    lat1: float, lng1: float, lat2: float, lng2: float, num_segments: int
) -> list[tuple[float, float]]:
    """Generate evenly spaced points along a path, preserving exact start and end coordinates."""
    points = []
    import random
    for i in range(num_segments + 1):
        t = i / num_segments
        lat = lat1 + t * (lat2 - lat1)
        lng = lng1 + t * (lng2 - lng1)
        # Add slight natural variation to simulate road curves for intermediate points only
        if 0 < i < num_segments:
            lat += random.uniform(-0.004, 0.004)
            lng += random.uniform(-0.004, 0.004)
        points.append((round(lat, 6), round(lng, 6)))
    return points


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Supabase Cloud Integration Endpoints ─────────────────────────────────

@router.get("/supabase/status")
async def get_supabase_status():
    """Returns Supabase connection status and active storage mode."""
    return supabase_service.get_status()


@router.post("/supabase/trips")
async def save_trip(body: SaveTripRequest):
    """Save user corridor trip to Supabase database."""
    result = await supabase_service.save_trip(body.model_dump())
    return result


@router.get("/supabase/trips")
async def get_trips(limit: int = Query(15, ge=1, le=50)):
    """Retrieve saved corridor trips."""
    trips = await supabase_service.get_recent_trips(limit=limit)
    return {"trips": trips, "count": len(trips)}


@router.post("/supabase/hazards")
async def report_hazard(body: ReportHazardRequest):
    """Submit a citizen or driver hazard report to Supabase."""
    result = await supabase_service.report_hazard(body.model_dump())
    return result


@router.get("/supabase/hazards")
async def get_hazards(limit: int = Query(50, ge=1, le=100)):
    """Fetch recent community hazard reports."""
    hazards = await supabase_service.get_community_hazards(limit=limit)
    return {"hazards": hazards, "count": len(hazards)}


@router.post("/supabase/sos")
async def log_sos(body: LogSosRequest):
    """Log an emergency SOS incident with live GPS telemetry."""
    result = await supabase_service.log_sos_incident(body.model_dump())
    return result

