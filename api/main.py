"""
SafePass AI — Standalone ML Model Inference Service
Exposes:
1. POST /predict-risk -> Real-time Corridor Risk Index (CRI) with SHAP explainability
2. POST /classify-hazard -> NLP text classification for citizen hazard reports
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project imports resolve
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
SAFEPASS_DIR = ROOT_DIR / "safepass-ai"

for p in [str(ROOT_DIR), str(SAFEPASS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.ml.service import ml_service
except ImportError:
    import importlib.util
    service_path = SAFEPASS_DIR / "app" / "ml" / "service.py"
    spec = importlib.util.spec_from_file_location("safepass_ml_service", str(service_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ml_service = module.ml_service


app = FastAPI(
    title="SafePass AI — ML Model Serving API",
    description="Machine Learning & Explainable AI services for Smart India Hackathon 2026 (Problem Statement R1-03)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Schemas ────────────────────────────────────────────

class PredictRiskRequest(BaseModel):
    time_of_day: str = Field("day", description="dawn | day | dusk | night | deep-night")
    weather_severity: int = Field(0, ge=0, le=4, description="0: Clear, 1: Drizzle, 2: Rain, 3: Fog, 4: Storm")
    road_type: str = Field("highway", description="highway | ghat | hairpin | urban")
    historical_accident_count: int = Field(5, ge=0, description="Accident count over past 3 years")
    visibility_score: float = Field(8.5, ge=0.0, le=10.0, description="Visibility distance in km (0.1 to 10.0)")
    traffic_density: float = Field(5.0, ge=0.0, le=10.0, description="Traffic congestion index (0 to 10)")
    is_blackspot: int = Field(0, ge=0, le=1, description="1 if segment is an official MoRTH blackspot, 0 otherwise")


class FactorExplanation(BaseModel):
    factor: str
    title: str
    percentage: float
    icon: str
    explanation: Optional[str] = None


class PredictRiskResponse(BaseModel):
    cri_score: float
    risk_level: str
    risk_color: str
    model: str
    r2_score: float
    top_factors: List[Dict[str, Any]]


class ClassifyHazardRequest(BaseModel):
    text: str = Field(..., description="Free-text hazard report description")


class ClassifyHazardResponse(BaseModel):
    suggested_category: str
    suggested_severity: float
    confidence: float
    model: str


# ── Endpoints ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "SafePass AI — ML Model API",
        "version": "2.0.0",
        "endpoints": {
            "predict_risk": "POST /predict-risk",
            "classify_hazard": "POST /classify-hazard",
            "health": "GET /health",
        },
        "model_status": {
            "cri_gradient_boosting": "loaded" if ml_service.cri_bundle else "fallback",
            "hazard_nlp_classifier": "loaded" if ml_service.hazard_bundle else "fallback",
            "shap_explainability": "active" if ml_service.shap_explainer else "feature_importances",
        }
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "cri_model_loaded": ml_service.cri_bundle is not None,
        "hazard_model_loaded": ml_service.hazard_bundle is not None,
        "shap_active": ml_service.shap_explainer is not None,
    }


@app.post("/predict-risk", response_model=PredictRiskResponse)
async def predict_risk(req: PredictRiskRequest):
    """
    Predict Corridor Risk Index (CRI) continuous score (0-10) using
    Gradient Boosting Regressor with SHAP feature attribution explainability.
    """
    result = ml_service.predict_risk(
        time_of_day=req.time_of_day,
        weather_severity=req.weather_severity,
        road_type=req.road_type,
        historical_accident_count=req.historical_accident_count,
        visibility_score=req.visibility_score,
        traffic_density=req.traffic_density,
        is_blackspot=req.is_blackspot,
    )
    return result


@app.post("/classify-hazard", response_model=ClassifyHazardResponse)
async def classify_hazard(req: ClassifyHazardRequest):
    """
    NLP classification of citizen hazard report text.
    Predicts category (pothole, waterlogging, fog, accident, blackspot) and severity (1-10).
    """
    result = ml_service.classify_hazard(text=req.text)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
