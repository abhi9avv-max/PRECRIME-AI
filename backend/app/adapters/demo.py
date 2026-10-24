"""Synthetic demo telemetry adapter.

Loads fixture evidence for scenarios without network or credentials.
Every record is labelled SYNTHETIC. Never reads or exposes ground truth.
"""
from typing import Dict, Any, List
from app.scenarios.fixtures import SCENARIOS_BY_ID

def fetch_demo_evidence(scenario_id: str, is_retest: bool = False) -> List[Dict[str, Any]]:
    """Return synthetic evidence records for the specified scenario."""
    case = SCENARIOS_BY_ID.get(scenario_id)
    if not case:
        raise ValueError(f"Unknown scenario ID: {scenario_id}")

    records = case["postfix_evidence"] if is_retest else case["initial_evidence"]
    
    # Ensure source_label is explicitly SYNTHETIC
    results = []
    for r in records:
        rec_copy = dict(r)
        rec_copy["source_label"] = "SYNTHETIC"
        results.append(rec_copy)
    return results
