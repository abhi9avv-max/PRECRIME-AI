"""PRECRIME AI Backend Main FastAPI Application."""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.db import engine, Base, SessionLocal
from app.models import Scenario
from app.scenarios.fixtures import ALL_SCENARIOS
from app.evaluation.ground_truth import GROUND_TRUTH_CASES
from app.api.investigations import router as investigations_router
from app.api.runs import router as runs_router
from app.api.reviews import router as reviews_router
from app.api.scenarios import router as scenarios_router
from app.api.evaluation import router as evaluation_router
from app.api.integrations import router as integrations_router


def seed_scenarios(db):
    """Seed the 12 scenarios idempotently at startup. Seed NO fake investigations."""
    for case in ALL_SCENARIOS:
        existing = db.query(Scenario).filter(Scenario.id == case["id"]).first()
        gt = GROUND_TRUTH_CASES.get(case["id"])
        if not existing:
            sc = Scenario(
                id=case["id"],
                family=case["family"],
                variant=case["variant"],
                split=case["split"],
                name=case["name"],
                description=case["description"],
                expected_stages=case["expectation_spec"],
                ground_truth=gt,
            )
            db.add(sc)
        else:
            existing.family = case["family"]
            existing.variant = case["variant"]
            existing.split = case["split"]
            existing.name = case["name"]
            existing.description = case["description"]
            existing.expected_stages = case["expectation_spec"]
            existing.ground_truth = gt
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_scenarios(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="PRECRIME AI API",
    description="Evidence-based SIEM detection-failure investigator",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
origins = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request parameters",
            "details": jsonable_encoder(exc.errors()),
        },
    )


# Register API Routers
app.include_router(investigations_router)
app.include_router(runs_router)
app.include_router(reviews_router)
app.include_router(scenarios_router)
app.include_router(evaluation_router)
app.include_router(integrations_router)


@app.get("/api/health")
def health_check():
    persistence_mode = os.getenv("PERSISTENCE_MODE", "persistent")
    return {
        "status": "ok",
        "service": "precrime-ai-backend",
        "persistence_mode": persistence_mode,
        "ephemeral_warning": "Ephemeral storage: data resets on restart" if persistence_mode == "ephemeral" else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
