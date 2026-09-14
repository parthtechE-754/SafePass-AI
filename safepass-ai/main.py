"""
SafePass AI — Predictive Corridor Risk Intelligence for Indian Roads
Main FastAPI Application
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.data.blackspots import load_blackspot_data
from app.ml.risk_engine import RiskEngine
from app.ml.service import ml_service

load_dotenv()

# ── App Init ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="SafePass AI",
    description="Predictive Corridor Risk Intelligence for Indian Roads",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Files & Templates ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")

# ── API Routes ────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")
 
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="#EA580C"/><path d="M50 20 L50 60 M50 60 L70 45" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round"/><circle cx="50" cy="50" r="10" fill="#FFFFFF"/></svg>'
    return Response(content=svg_icon, media_type="image/svg+xml")


# ── Global State ──────────────────────────────────────────────────────────
risk_engine = RiskEngine()


@app.on_event("startup")
async def startup_event():
    """Load models and data on startup."""
    print("🚀 SafePass AI starting up...")
    risk_engine.initialize()
    app.state.risk_engine = risk_engine
    app.state.blackspots = load_blackspot_data()
    app.state.ml_service = ml_service
    print(f"✅ Loaded {len(app.state.blackspots)} blackspot records")
    print(f"✅ Loaded ML CRI Model: {'Active' if ml_service.cri_bundle else 'Fallback'}")
    print(f"✅ Loaded NLP Hazard Classifier: {'Active' if ml_service.hazard_bundle else 'Fallback'}")


# ── Direct Root ML Endpoints (Task 1 & Task 2) ───────────────────────────
@app.post("/predict-risk")
async def root_predict_risk(request: Request):
    """Direct root endpoint for Corridor Risk Index (CRI) ML prediction with SHAP."""
    body = await request.json()
    return ml_service.predict_risk(
        time_of_day=body.get("time_of_day", "day"),
        weather_severity=body.get("weather_severity", 0),
        road_type=body.get("road_type", "highway"),
        historical_accident_count=body.get("historical_accident_count", 5),
        visibility_score=body.get("visibility_score", 8.5),
        traffic_density=body.get("traffic_density", 5.0),
        is_blackspot=body.get("is_blackspot", 0),
    )


@app.post("/classify-hazard")
async def root_classify_hazard(request: Request):
    """Direct root endpoint for citizen hazard NLP classification."""
    body = await request.json()
    return ml_service.classify_hazard(text=body.get("text", ""))


# ── Page Routes ───────────────────────────────────────────────────────────
@app.get("/")
async def home(request: Request):
    """Main SafePass AI dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "mapbox_token": os.getenv("MAPBOX_ACCESS_TOKEN", ""),
        }
    )


@app.get("/dashboard")
async def dashboard(request: Request):
    """Admin dashboard with risk heatmap."""
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "mapbox_token": os.getenv("MAPBOX_ACCESS_TOKEN", ""),
        }
    )


@app.get("/model-card")
async def model_card(request: Request, format: str = "html"):
    """Serve MODEL_CARD specification with executive dark-theme viewer for SIH judges."""
    from fastapi.responses import PlainTextResponse
    card_content = ""
    for p in [Path(__file__).parent / "MODEL_CARD.md", Path(__file__).parent.parent / "MODEL_CARD.md"]:
        if p.exists():
            card_content = p.read_text(encoding="utf-8")
            break
    if not card_content:
        return PlainTextResponse("MODEL_CARD.md not found", status_code=404)
    if format == "raw":
        return PlainTextResponse(card_content, media_type="text/markdown")
    return templates.TemplateResponse(
        request=request,
        name="model_card.html",
        context={"markdown_content": card_content}
    )



@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "SafePass AI",
        "version": "2.0.0",
        "blackspots_loaded": len(getattr(app.state, "blackspots", [])),
        "ml_cri_model": ml_service.cri_bundle is not None,
        "nlp_hazard_model": ml_service.hazard_bundle is not None,
        "shap_explainability": ml_service.shap_explainer is not None,
    }
