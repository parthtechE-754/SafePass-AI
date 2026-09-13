"""
SafePass AI — Predictive Corridor Risk Intelligence for Indian Roads
Main FastAPI Application
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.data.blackspots import load_blackspot_data
from app.ml.risk_engine import RiskEngine

load_dotenv()

# ── App Init ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="SafePass AI",
    description="Predictive Corridor Risk Intelligence for Indian Roads",
    version="1.0.0",
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

# ── Global State ──────────────────────────────────────────────────────────
risk_engine = RiskEngine()


@app.on_event("startup")
async def startup_event():
    """Load models and data on startup."""
    print("🚀 SafePass AI starting up...")
    risk_engine.initialize()
    app.state.risk_engine = risk_engine
    app.state.blackspots = load_blackspot_data()
    print(f"✅ Loaded {len(app.state.blackspots)} blackspot records")
    print("✅ Risk engine initialized")


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


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "SafePass AI",
        "version": "1.0.0",
        "blackspots_loaded": len(getattr(app.state, "blackspots", [])),
    }
