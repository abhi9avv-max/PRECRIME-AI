"""API endpoint for listing available diagnostic scenarios (NO ground truth)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Scenario

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios(db: Session = Depends(get_db)):
    """Returns available scenarios with family, variant, split, and expectation specs.

    Guarantees no ground truth is exposed.
    """
    scenarios = db.query(Scenario).order_by(Scenario.id).all()
    return [
        {
            "id": s.id,
            "family": s.family,
            "variant": s.variant,
            "split": s.split,
            "name": s.name,
            "description": s.description,
            "expected_stages": s.expected_stages,
        }
        for s in scenarios
    ]
