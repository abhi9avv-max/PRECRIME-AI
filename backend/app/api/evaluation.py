"""API endpoints for the evaluation test suite and empirical metrics."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.evaluation.evaluator import run_evaluation_batch
from app.evaluation.metrics import get_latest_metrics

router = APIRouter(prefix="/api", tags=["evaluation"])


@router.post("/evaluation/run")
def trigger_evaluation_suite(db: Session = Depends(get_db)):
    """Executes all 12 scenario cases as a fresh evaluation batch and persists results."""
    batch_summary = run_evaluation_batch(db)
    metrics_summary = get_latest_metrics(db)
    return {
        "status": "COMPLETED",
        "batch_id": batch_summary["batch_id"],
        "evaluated_at": batch_summary["evaluated_at"],
        "cases_evaluated": batch_summary["cases_evaluated"],
        "metrics": metrics_summary,
    }


@router.get("/metrics")
def read_metrics(db: Session = Depends(get_db)):
    """Computes and returns metrics from the most recent persisted evaluation batch."""
    return get_latest_metrics(db)
