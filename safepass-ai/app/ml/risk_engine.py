"""
SafePass AI — Corridor Risk Index (CRI) Engine
Computes per-segment risk scores by fusing:
  1. Historical accident blackspot proximity
  2. Weather hazard score (rain, fog, visibility)
  3. Road geometry risk (curves, gradient, highway type)
  4. Temporal risk pattern (hour, day, month)
  5. Infrastructure score (lighting, divider, shoulder)
"""

import math
import random
from datetime import datetime
from typing import Optional
from app.data.blackspots import INDIAN_BLACKSPOTS, get_nearby_blackspots


class RiskEngine:
    """Core engine for computing Corridor Risk Index (CRI) per road segment."""

    # ── CRI Weights (tuned for Indian roads) ─────────────────────────────
    WEIGHTS = {
        "accident_history": 0.35,
        "weather_hazard": 0.25,
        "road_geometry": 0.20,
        "temporal_risk": 0.12,
        "infrastructure": 0.08,
    }

    # ── Temporal risk profiles (based on MoRTH data patterns) ────────────
    # Higher = more dangerous. Normalized 0-10.
    HOURLY_RISK = {
        0: 6.5, 1: 5.8, 2: 5.2, 3: 4.5, 4: 4.0, 5: 4.5,
        6: 5.0, 7: 5.5, 8: 6.0, 9: 5.5, 10: 5.0, 11: 5.2,
        12: 5.5, 13: 5.8, 14: 6.0, 15: 6.5, 16: 7.0, 17: 7.8,
        18: 8.5, 19: 9.0, 20: 8.8, 21: 8.2, 22: 7.5, 23: 7.0,
    }

    # Monthly risk (monsoon = higher risk)
    MONTHLY_RISK = {
        1: 6.0, 2: 5.0, 3: 4.5, 4: 4.0, 5: 4.5, 6: 7.5,
        7: 9.0, 8: 8.5, 9: 7.8, 10: 6.5, 11: 5.5, 12: 6.5,
    }

    # Day of week risk (weekend = higher)
    DAY_RISK = {
        0: 6.5, 1: 5.5, 2: 5.0, 3: 5.0, 4: 5.5, 5: 6.5, 6: 7.5,
    }

    def __init__(self):
        self._initialized = False

    def initialize(self):
        """Initialize the risk engine (load models, pre-compute caches)."""
        self._initialized = True

    def compute_corridor_risk_index(
        self,
        lat: float,
        lng: float,
        weather: Optional[dict] = None,
        road_info: Optional[dict] = None,
        travel_time: Optional[datetime] = None,
    ) -> dict:
        """
        Compute Corridor Risk Index (CRI) for a point on the road.

        Returns:
            {
                "cri": float (0-10),
                "level": "LOW" | "MODERATE" | "HIGH" | "CRITICAL",
                "color": hex color,
                "components": {
                    "accident_history": float,
                    "weather_hazard": float,
                    "road_geometry": float,
                    "temporal_risk": float,
                    "infrastructure": float,
                },
                "risk_factors": [...],
                "recommendation": str,
            }
        """
        now = travel_time or datetime.now()

        # 1. Accident History Score
        accident_score, accident_factors = self._compute_accident_score(lat, lng)

        # 2. Weather Hazard Score
        weather_score, weather_factors = self._compute_weather_score(weather)

        # 3. Road Geometry Score
        road_score, road_factors = self._compute_road_score(road_info, lat, lng)

        # 4. Temporal Risk Score
        temporal_score, temporal_factors = self._compute_temporal_score(now)

        # 5. Infrastructure Score
        infra_score, infra_factors = self._compute_infrastructure_score(road_info)

        # ── Composite CRI ────────────────────────────────────────────────
        components = {
            "accident_history": round(accident_score, 2),
            "weather_hazard": round(weather_score, 2),
            "road_geometry": round(road_score, 2),
            "temporal_risk": round(temporal_score, 2),
            "infrastructure": round(infra_score, 2),
        }

        cri = sum(
            self.WEIGHTS[key] * components[key]
            for key in self.WEIGHTS
        )
        cri = round(min(max(cri, 0), 10), 2)

        # ── Risk Level & Color ───────────────────────────────────────────
        level, color = self._classify_risk(cri)

        # ── Collect all risk factors ─────────────────────────────────────
        all_factors = accident_factors + weather_factors + road_factors + temporal_factors + infra_factors

        # ── Generate recommendation ──────────────────────────────────────
        recommendation = self._generate_recommendation(cri, all_factors, weather)

        return {
            "cri": cri,
            "level": level,
            "color": color,
            "components": components,
            "risk_factors": all_factors[:5],  # Top 5
            "recommendation": recommendation,
            "lat": lat,
            "lng": lng,
        }

    def compute_route_risk(
        self,
        route_points: list[tuple[float, float]],
        weather_data: Optional[dict] = None,
        travel_time: Optional[datetime] = None,
    ) -> dict:
        """
        Compute CRI for every segment along a route.

        Args:
            route_points: List of (lat, lng) tuples along the route
            weather_data: Weather conditions
            travel_time: When the user plans to travel

        Returns:
            {
                "segments": [...],
                "avg_cri": float,
                "max_cri": float,
                "danger_zones": int,
                "overall_level": str,
                "safest_hour": int,
                "temporal_risk_profile": {...},
            }
        """
        segments = []
        for i, (lat, lng) in enumerate(route_points):
            seg_risk = self.compute_corridor_risk_index(
                lat=lat, lng=lng,
                weather=weather_data,
                travel_time=travel_time,
            )
            seg_risk["segment_index"] = i
            segments.append(seg_risk)

        cris = [s["cri"] for s in segments]
        avg_cri = round(sum(cris) / len(cris), 2) if cris else 0
        max_cri = round(max(cris), 2) if cris else 0
        danger_zones = sum(1 for c in cris if c >= 7.0)

        overall_level, _ = self._classify_risk(avg_cri)

        # Temporal risk profile (hourly)
        temporal_profile = self._compute_hourly_risk_profile(route_points)

        # Find safest hour
        safest_hour = min(temporal_profile, key=temporal_profile.get)

        return {
            "segments": segments,
            "avg_cri": avg_cri,
            "max_cri": max_cri,
            "danger_zones": danger_zones,
            "total_segments": len(segments),
            "overall_level": overall_level,
            "safest_hour": safest_hour,
            "temporal_risk_profile": temporal_profile,
        }

    # ── Component Scorers ─────────────────────────────────────────────────

    def _compute_accident_score(self, lat: float, lng: float) -> tuple[float, list[dict]]:
        """Score based on proximity to known accident blackspots."""
        nearby = get_nearby_blackspots(lat, lng, radius_km=10.0)
        factors = []

        if not nearby:
            # Add slight base risk (Indian roads inherently riskier)
            base_risk = 2.5 + random.uniform(-0.5, 0.5)
            return base_risk, [{"type": "info", "icon": "ℹ️", "text": "No known blackspots nearby"}]

        # Highest severity nearby blackspot dominates
        closest = nearby[0]
        distance = closest["distance_km"]

        # Distance decay: risk decreases with distance
        distance_factor = max(0, 1 - (distance / 10.0))
        score = closest["severity"] * distance_factor

        # Add smaller contributions from other nearby blackspots
        for spot in nearby[1:3]:
            d_factor = max(0, 1 - (spot["distance_km"] / 10.0))
            score += spot["severity"] * d_factor * 0.2

        score = min(score, 10.0)

        # Generate factors
        factors.append({
            "type": "danger",
            "icon": "⚠️",
            "text": f"Accident blackspot: {closest['name']} ({closest['distance_km']}km away)",
            "detail": closest["description"],
        })
        factors.append({
            "type": "stat",
            "icon": "📊",
            "text": f"{closest['annual_accidents']} accidents/year, {closest['annual_fatalities']} fatalities",
        })

        for rf in closest["risk_factors"][:3]:
            label = rf.replace("_", " ").title()
            factors.append({"type": "warning", "icon": "🔶", "text": label})

        return score, factors

    def _compute_weather_score(self, weather: Optional[dict]) -> tuple[float, list[dict]]:
        """Score based on weather conditions."""
        if not weather:
            return 3.0, [{"type": "info", "icon": "🌤️", "text": "Weather data unavailable – assuming moderate"}]

        score = 0.0
        factors = []

        # Rain intensity
        rain = weather.get("rain_mm", 0)
        if rain > 50:
            score += 9.0
            factors.append({"type": "danger", "icon": "🌧️", "text": f"Heavy rainfall: {rain}mm – high aquaplaning risk"})
        elif rain > 20:
            score += 7.0
            factors.append({"type": "warning", "icon": "🌧️", "text": f"Moderate rain: {rain}mm – reduced grip"})
        elif rain > 5:
            score += 4.5
            factors.append({"type": "caution", "icon": "🌦️", "text": f"Light rain: {rain}mm"})
        else:
            score += 1.0

        # Visibility
        visibility = weather.get("visibility_km", 10)
        if visibility < 0.2:
            score += 9.5
            factors.append({"type": "danger", "icon": "🌫️", "text": f"Dense fog: {visibility}km visibility – EXTREME danger"})
        elif visibility < 1:
            score += 7.0
            factors.append({"type": "warning", "icon": "🌫️", "text": f"Poor visibility: {visibility}km"})
        elif visibility < 5:
            score += 3.5
            factors.append({"type": "caution", "icon": "🌫️", "text": f"Reduced visibility: {visibility}km"})

        # Wind
        wind = weather.get("wind_kmh", 0)
        if wind > 60:
            score += 6.0
            factors.append({"type": "warning", "icon": "💨", "text": f"High winds: {wind} km/h"})
        elif wind > 30:
            score += 2.5

        # Temperature extremes
        temp = weather.get("temperature_c", 25)
        if temp > 45:
            score += 3.0
            factors.append({"type": "warning", "icon": "🌡️", "text": f"Extreme heat: {temp}°C – road surface degradation"})
        elif temp < 5:
            score += 4.0
            factors.append({"type": "warning", "icon": "❄️", "text": f"Cold conditions: {temp}°C – possible ice"})

        score = min(score / 2.0, 10.0)  # Normalize
        return score, factors

    def _compute_road_score(self, road_info: Optional[dict], lat: float, lng: float) -> tuple[float, list[dict]]:
        """Score based on road geometry and type."""
        factors = []

        if not road_info:
            # Infer from nearby blackspot data
            nearby = get_nearby_blackspots(lat, lng, radius_km=15.0)
            if nearby:
                closest = nearby[0]
                road_type = closest.get("road_type", "unknown")
                speed_limit = closest.get("speed_limit", 60)
            else:
                road_type = "unknown"
                speed_limit = 60
            road_info = {"road_type": road_type, "speed_limit": speed_limit}

        score = 0.0
        road_type = road_info.get("road_type", "unknown")

        # Road type base risk
        type_risk = {
            "expressway": 3.5,
            "national_highway": 5.5,
            "state_highway": 6.0,
            "district_road": 6.5,
            "village_road": 5.0,
            "ring_road": 4.5,
            "unknown": 5.0,
        }
        score = type_risk.get(road_type, 5.0)

        # Speed limit (higher = more risk)
        speed = road_info.get("speed_limit", 60)
        if speed >= 100:
            score += 1.5
            factors.append({"type": "warning", "icon": "🏎️", "text": f"High speed zone: {speed} km/h limit"})
        elif speed <= 40:
            factors.append({"type": "info", "icon": "🐌", "text": f"Low speed zone: {speed} km/h – likely ghat/curve section"})
            score += 1.0  # Ghats are dangerous despite low speed limits

        # Lanes
        lanes = road_info.get("lanes", 2)
        if lanes <= 2:
            score += 1.5
            factors.append({"type": "warning", "icon": "↔️", "text": "Narrow road: 2 lanes or less"})

        # Divider
        if not road_info.get("has_divider", True):
            score += 2.0
            factors.append({"type": "danger", "icon": "🚧", "text": "No central divider – head-on collision risk"})

        score = min(score, 10.0)
        return score, factors

    def _compute_temporal_score(self, dt: datetime) -> tuple[float, list[dict]]:
        """Score based on time of day, day of week, month."""
        factors = []

        hour_risk = self.HOURLY_RISK.get(dt.hour, 5.0)
        month_risk = self.MONTHLY_RISK.get(dt.month, 5.0)
        day_risk = self.DAY_RISK.get(dt.weekday(), 5.0)

        score = (hour_risk * 0.5 + month_risk * 0.3 + day_risk * 0.2)

        if dt.hour >= 18 or dt.hour <= 5:
            factors.append({"type": "warning", "icon": "🌙", "text": "Night driving – reduced visibility, fatigue risk"})
        if dt.month in (6, 7, 8, 9):
            factors.append({"type": "warning", "icon": "🌧️", "text": "Monsoon season – elevated weather risk"})
        if dt.weekday() in (5, 6):
            factors.append({"type": "caution", "icon": "📅", "text": "Weekend – higher traffic and risk"})

        return min(score, 10.0), factors

    def _compute_infrastructure_score(self, road_info: Optional[dict]) -> tuple[float, list[dict]]:
        """Score based on road infrastructure quality."""
        if not road_info:
            return 4.5, [{"type": "info", "icon": "🏗️", "text": "Infrastructure data unavailable"}]

        factors = []
        score = 3.0  # Base

        if not road_info.get("has_lighting", True):
            score += 2.5
            factors.append({"type": "warning", "icon": "💡", "text": "No street lighting"})

        if not road_info.get("has_shoulder", True):
            score += 1.5
            factors.append({"type": "warning", "icon": "🛤️", "text": "No road shoulder – breakdown danger"})

        if road_info.get("surface_quality", "good") == "poor":
            score += 2.0
            factors.append({"type": "warning", "icon": "🕳️", "text": "Poor road surface – pothole risk"})

        return min(score, 10.0), factors

    # ── Helpers ───────────────────────────────────────────────────────────

    def _classify_risk(self, cri: float) -> tuple[str, str]:
        """Classify CRI into risk level and color."""
        if cri >= 8.0:
            return "CRITICAL", "#DC2626"    # Red
        elif cri >= 6.0:
            return "HIGH", "#F97316"        # Orange
        elif cri >= 4.0:
            return "MODERATE", "#EAB308"    # Yellow
        else:
            return "LOW", "#22C55E"         # Green

    def _generate_recommendation(self, cri: float, factors: list, weather: Optional[dict]) -> str:
        """Generate actionable safety recommendation."""
        if cri >= 8.0:
            return "⛔ AVOID this route if possible. If you must travel, reduce speed to 40 km/h, keep headlights on, and maintain safe distance."
        elif cri >= 6.0:
            return "⚠️ CAUTION: Drive slowly, stay alert, and avoid overtaking. Consider an alternate route."
        elif cri >= 4.0:
            return "🟡 MODERATE RISK: Normal caution. Keep to speed limits and stay focused."
        else:
            return "✅ LOW RISK: Road conditions appear safe. Follow normal driving practices."

    def _compute_hourly_risk_profile(self, route_points: list[tuple[float, float]]) -> dict[int, float]:
        """Compute risk profile for each hour (0-23) for a route."""
        profile = {}
        for hour in range(24):
            dt = datetime.now().replace(hour=hour, minute=0)
            risks = []
            for lat, lng in route_points[:10]:  # Sample up to 10 points
                r = self.compute_corridor_risk_index(lat, lng, travel_time=dt)
                risks.append(r["cri"])
            profile[hour] = round(sum(risks) / len(risks), 2) if risks else 5.0
        return profile
