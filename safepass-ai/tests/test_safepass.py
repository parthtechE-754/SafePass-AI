"""
SafePass AI — Comprehensive Production QA & Test Suite
Covers:
- System Health & Model Status
- HTTP HEAD / GET / POST method resilience
- Corridor Risk Index (CRI) ML Inference with SHAP Explainability
- Citizen Hazard NLP Classification
- Multi-Route Corridor Comparison Engine
- Blackspot GeoJSON & Proximity Search
- 24-Hour Temporal Risk Calculation
- Supabase & Resilient Cloud Storage Endpoints
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure safepass-ai is on sys.path
TEST_DIR = Path(__file__).resolve().parent
APP_DIR = TEST_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app, startup_event


@pytest.fixture(scope="session", autouse=True)
def init_app():
    """Trigger FastAPI startup event to initialize models and data."""
    import asyncio
    asyncio.run(startup_event())


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. System Health & Infrastructure ─────────────────────────────────────

def test_system_health(client):
    """Test health endpoint returns healthy status and models are loaded."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "SafePass AI"
    assert data["blackspots_loaded"] >= 20
    assert data["ml_cri_model"] is True
    assert data["nlp_hazard_model"] is True
    assert data["shap_explainability"] is True


def test_api_health_route(client):
    """Test /api/health route."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ml_models"]["cri_gradient_boosting"] is True


def test_head_requests_supported(client):
    """Verify HTTP HEAD requests succeed without 405 Method Not Allowed."""
    for path in ["/", "/health", "/favicon.ico", "/dashboard", "/model-card"]:
        response = client.head(path)
        assert response.status_code == 200, f"HEAD {path} failed with {response.status_code}"


def test_favicon_endpoint(client):
    """Verify SVG favicon endpoint returns valid SVG and 200 OK."""
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers.get("content-type", "")
    assert "<svg" in response.text


def test_model_card_html_and_raw(client):
    """Test MODEL_CARD endpoint in HTML and raw markdown formats."""
    resp_html = client.get("/model-card")
    assert resp_html.status_code == 200
    assert "MODEL_CARD" in resp_html.text or "SafePass" in resp_html.text

    resp_raw = client.get("/model-card?format=raw")
    assert resp_raw.status_code == 200
    assert "Corridor Risk Index" in resp_raw.text or "SafePass" in resp_raw.text


# ── 2. Task 1: ML CRI Risk Engine & SHAP Explainability ────────────────────

def test_predict_risk_post_valid(client):
    """Test CRI prediction with full valid input parameters."""
    payload = {
        "time_of_day": "night",
        "weather_severity": 2.0,
        "road_type": "ghat",
        "historical_accident_count": 8,
        "visibility_score": 4.0,
        "traffic_density": 7.0,
        "is_blackspot": 1
    }
    response = client.post("/predict-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert 0.0 <= data["cri_score"] <= 10.0
    assert data["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert data["risk_color"].startswith("#")
    assert len(data["top_factors"]) > 0
    # Check factor structure
    factor = data["top_factors"][0]
    assert "factor" in factor
    assert "title" in factor
    assert "percentage" in factor
    assert "icon" in factor
    assert factor["icon"] != ""
    assert "Time Of Day Day" not in factor["title"]


def test_predict_risk_empty_body_resilience(client):
    """Verify empty POST body does NOT crash with 500 JSONDecodeError."""
    response = client.post("/predict-risk", content="")
    assert response.status_code == 200
    data = response.json()
    assert "cri_score" in data
    assert 0.0 <= data["cri_score"] <= 10.0


def test_predict_risk_get_query_params(client):
    """Verify GET request with query params returns valid CRI prediction."""
    response = client.get("/predict-risk?time_of_day=day&weather_severity=0&road_type=highway")
    assert response.status_code == 200
    data = response.json()
    assert "cri_score" in data
    assert data["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]


def test_api_predict_risk_alias(client):
    """Test /api/predict-risk alias behaves identically."""
    response = client.post("/api/predict-risk", json={"time_of_day": "dawn", "road_type": "highway"})
    assert response.status_code == 200
    data = response.json()
    assert "cri_score" in data
    assert len(data["top_factors"]) > 0


# ── 3. Task 2: NLP Citizen Hazard Classifier ──────────────────────────────

def test_classify_hazard_waterlogging(client):
    """Test NLP classification of waterlogging report."""
    response = client.post("/classify-hazard", json={"text": "Severe waterlogging and flooded highway near underpass"})
    assert response.status_code == 200
    data = response.json()
    assert data["suggested_category"] in ["waterlogging", "pothole", "blackspot"]
    assert 1.0 <= data["suggested_severity"] <= 10.0
    assert 0.0 <= data["confidence"] <= 1.0


def test_classify_hazard_accident_fatal(client):
    """Test NLP classification of fatal crash with severity escalation."""
    response = client.post("/classify-hazard", json={"text": "Deadly multi-vehicle collision fatal rollover on bypass"})
    assert response.status_code == 200
    data = response.json()
    assert data["suggested_category"] in ["accident", "blackspot"]
    assert data["suggested_severity"] >= 8.0  # High severity boost for fatal keyword


def test_classify_hazard_empty_resilience(client):
    """Verify empty text or empty POST does NOT throw 500."""
    resp1 = client.post("/classify-hazard", json={})
    assert resp1.status_code == 200
    resp2 = client.post("/classify-hazard", content="")
    assert resp2.status_code == 200
    resp3 = client.get("/classify-hazard?text=foggy+stretch")
    assert resp3.status_code == 200
    assert "suggested_category" in resp3.json()


# ── 4. Corridor Route Comparison Engine ───────────────────────────────────

def test_route_comparison_nagpur_pune(client):
    """Test multi-route comparison between Nagpur and Pune."""
    payload = {
        "origin_lat": 21.1458,
        "origin_lng": 79.0882,
        "dest_lat": 18.5204,
        "dest_lng": 73.8567,
        "vehicle_type": "car"
    }
    response = client.post("/api/routes/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data
    assert len(data["routes"]) >= 1
    recommended = data.get("recommended")
    assert recommended is not None
    # Check first route details
    r = data["routes"][0]
    assert "name" in r
    assert "distance_km" in r
    assert "safety_score" in r
    assert "ml_cri" in r
    assert "top_factors" in r
    assert "route_points" in r
    assert len(r["route_points"]) > 0


def test_point_risk_endpoint(client):
    """Test single geographic point risk calculation."""
    payload = {"lat": 18.7421, "lng": 73.4025}  # Borghat
    response = client.post("/api/point-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "cri" in data
    assert "level" in data
    assert "components" in data


# ── 5. Blackspots & Temporal Risk ─────────────────────────────────────────

def test_blackspots_geojson(client):
    """Test GeoJSON blackspots retrieval."""
    response = client.get("/api/blackspots")
    assert response.status_code == 200
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) >= 20
    first_feat = geojson["features"][0]
    assert first_feat["geometry"]["type"] == "Point"
    assert "severity" in first_feat["properties"]


def test_blackspots_nearby(client):
    """Test finding blackspots near Pune-Mumbai Borghat."""
    response = client.get("/api/blackspots/nearby?lat=18.74&lng=73.40&radius=25")
    assert response.status_code == 200
    data = response.json()
    assert "blackspots" in data
    assert len(data["blackspots"]) >= 1
    assert "Borghat" in data["blackspots"][0]["name"] or data["blackspots"][0]["distance_km"] <= 25


def test_temporal_risk_curve(client):
    """Test 24-hour temporal risk curve computation."""
    response = client.get("/api/temporal-risk?origin_lat=21.14&origin_lng=79.08&dest_lat=18.52&dest_lng=73.85")
    assert response.status_code == 200
    data = response.json()
    assert "hourly_risk" in data
    assert len(data["hourly_risk"]) == 24
    assert "safest_hour" in data
    assert "riskiest_hour" in data


# ── 6. Cloud Storage & Telemetry Endpoints ────────────────────────────────

def test_supabase_status(client):
    """Test Supabase status reports storage mode."""
    response = client.get("/api/supabase/status")
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data


def test_save_and_get_trips(client):
    """Test saving a trip and retrieving it."""
    trip = {
        "origin_name": "Nagpur",
        "origin_lat": 21.1458,
        "origin_lng": 79.0882,
        "dest_name": "Pune",
        "dest_lat": 18.5204,
        "dest_lng": 73.8567,
        "corridor_name": "Samruddhi Mahamarg Corridor",
        "safety_score": 8.5,
        "avg_cri": 2.8,
        "distance_km": 680.0,
        "est_time_min": 520,
        "danger_zones": 1
    }
    post_resp = client.post("/api/trips", json=trip)
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    get_resp = client.get("/api/trips")
    assert get_resp.status_code == 200
    assert get_resp.json()["count"] >= 1


def test_report_and_get_hazards(client):
    """Test reporting a citizen hazard and fetching community hazards."""
    hazard = {
        "title": "Loose gravel on curve",
        "hazard_type": "blackspot",
        "severity": 6.5,
        "lat": 19.12,
        "lng": 74.55,
        "highway": "NH-60",
        "description": "Loose gravel scattered on hairpin turn"
    }
    post_resp = client.post("/api/hazards", json=hazard)
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    get_resp = client.get("/api/hazards")
    assert get_resp.status_code == 200
    assert get_resp.json()["count"] >= 1


def test_log_sos_telemetry(client):
    """Test logging an emergency SOS incident."""
    sos_payload = {
        "lat": 19.05,
        "lng": 73.10,
        "service": "1033",
        "notes": "Highway breakdown SOS test"
    }
    response = client.post("/api/sos", json=sos_payload)
    assert response.status_code == 200
    assert response.json()["success"] is True
