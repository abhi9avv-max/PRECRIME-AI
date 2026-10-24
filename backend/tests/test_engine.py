"""Unit tests for the deterministic diagnostic engine."""
import importlib
import inspect
import re
from pathlib import Path
import pytest

from app.diagnostics.engine import diagnose
from app.diagnostics.stages import PipelineStage, StageStatus, DiagnosticOutcome
from app.scenarios.fixtures import ALL_SCENARIOS, SCENARIOS_BY_ID
from app.evaluation.ground_truth import GROUND_TRUTH_CASES


def test_engine_static_purity():
    """Verify engine package imports nothing from evaluation/db/adapters/scenarios,

    and that no scenario IDs appear in engine source code.
    """
    engine_file = Path(__file__).resolve().parent.parent / "app" / "diagnostics" / "engine.py"
    source = engine_file.read_text(encoding="utf-8")

    forbidden = ["evaluation", "models", "db", "adapters", "scenarios"]
    for word in forbidden:
        assert f"app.{word}" not in source, f"Engine illegally references app.{word}"
        assert f"import {word}" not in source, f"Engine illegally imports {word}"

    # Verify no scenario IDs (e.g. collection_failure.a, 1a, etc.) are in engine.py
    for case_id in GROUND_TRUTH_CASES:
        assert case_id not in source, f"Engine source contains hardcoded scenario id: {case_id}"


def test_all_12_cases_deterministic_outcomes():
    """Test that all 12 scenario cases produce the exact expected ground truth outcomes."""
    for case in ALL_SCENARIOS:
        case_id = case["id"]
        gt = GROUND_TRUTH_CASES[case_id]

        result = diagnose(case["expectation_spec"], case["initial_evidence"])
        diag = result["diagnosis"]
        stage_results = {s["stage"]: s for s in result["stage_results"]}

        assert diag["outcome"] == gt["expected_outcome"], f"Case {case_id} outcome mismatch"
        assert diag["failure_stage"] == gt["expected_failure_stage"], f"Case {case_id} failure_stage mismatch"

        # Check evidence refs exist
        assert len(diag["evidence_refs"]) > 0 or diag["outcome"] == "HEALTHY"

        # For failures, verify downstream absence results in NOT REACHED, never FAIL
        if gt["expected_failure_stage"]:
            fail_idx = [s.value for s in PipelineStage].index(gt["expected_failure_stage"])
            for later_stage in list(PipelineStage)[fail_idx + 1:]:
                st_res = stage_results[later_stage.value]
                assert st_res["status"] == StageStatus.NOT_REACHED.value, (
                    f"Downstream stage {later_stage.value} should be NOT REACHED in {case_id}, got {st_res['status']}"
                )


def test_cross_stage_conflict_rule():
    """If stage k is SATISFIED while earlier stage j < k is VIOLATED, mark stage j CONFLICTING."""
    spec = {"rule_id": "R-100", "required_fields": ["user_name"]}
    records = [
        {"id": "r1", "stage": "event_generation", "checkpoint_id": "EG-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_found": True}},
        # Collection reports event NOT received (violated)
        {"id": "r2", "stage": "collection", "checkpoint_id": "COL-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_received": False}},
        # But alert delivery is satisfied!
        {"id": "r3", "stage": "delivery_visibility", "checkpoint_id": "DEL-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"alert_received": True}},
    ]
    res = diagnose(spec, records)
    stage_results = {s["stage"]: s for s in res["stage_results"]}
    assert stage_results["collection"]["status"] == StageStatus.UNKNOWN.value
    assert "conflict" in stage_results["collection"]["reason"].lower()
    assert res["diagnosis"]["outcome"] == DiagnosticOutcome.UNDETERMINED.value


def test_violation_behind_unconfirmed_prerequisite_is_downgraded():
    """A violation observed downstream when an upstream stage is UNKNOWN must be downgraded to UNKNOWN."""
    spec = {"rule_id": "R-100", "required_fields": ["user_name"]}
    records = [
        {"id": "r1", "stage": "event_generation", "checkpoint_id": "EG-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_found": True}},
        # Collection is unavailable -> UNKNOWN
        {"id": "r2", "stage": "collection", "checkpoint_id": "COL-1", "source_label": "SYNTHETIC", "availability": "UNAVAILABLE", "payload": {"reason": "timeout"}},
        # Delivery observed absence -> would be violated, but must be UNKNOWN
        {"id": "r3", "stage": "delivery_visibility", "checkpoint_id": "DEL-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"alert_received": False}},
    ]
    res = diagnose(spec, records)
    stage_results = {s["stage"]: s for s in res["stage_results"]}
    assert stage_results["delivery_visibility"]["status"] == StageStatus.UNKNOWN.value
    assert "prerequisite" in stage_results["delivery_visibility"]["reason"].lower()
    assert res["diagnosis"]["outcome"] == DiagnosticOutcome.UNDETERMINED.value


# Hand-built generalization tests not present in fixtures
def test_generalization_1_event_generation_failure():
    """Test localization to earliest stage (event_generation)."""
    spec = {"rule_id": "R-CUSTOM"}
    records = [
        {"id": "g1", "stage": "event_generation", "checkpoint_id": "EG-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_found": False, "source": "linux-auditd"}},
        {"id": "g2", "stage": "collection", "checkpoint_id": "COL-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_received": False}},
    ]
    res = diagnose(spec, records)
    assert res["diagnosis"]["outcome"] == DiagnosticOutcome.FAILURE_LOCALIZED.value
    assert res["diagnosis"]["failure_stage"] == "event_generation"
    assert res["stage_results"][1]["status"] == StageStatus.NOT_REACHED.value


def test_generalization_2_alert_generation_failure():
    """Test localization specifically at alert_generation with wrong rule id."""
    spec = {"rule_id": "R-300", "required_fields": ["cmd"]}
    records = [
        {"id": "g1", "stage": "event_generation", "checkpoint_id": "EG-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_found": True}},
        {"id": "g2", "stage": "collection", "checkpoint_id": "COL-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_received": True}},
        {"id": "g3", "stage": "parsing", "checkpoint_id": "PAR-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"raw_event_present": True, "extracted_fields": {"cmd": "whoami"}}},
        {"id": "g4", "stage": "rule_evaluation", "checkpoint_id": "RUL-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"matched": True, "decoded_fields": {"cmd": "whoami"}}},
        {"id": "g5", "stage": "alert_generation", "checkpoint_id": "ALT-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"alert_found": False}},
    ]
    res = diagnose(spec, records)
    assert res["diagnosis"]["outcome"] == DiagnosticOutcome.FAILURE_LOCALIZED.value
    assert res["diagnosis"]["failure_stage"] == "alert_generation"


def test_generalization_3_empty_string_field_violation():
    """Test parsing violation when field exists but is empty string."""
    spec = {"required_fields": ["ip_addr", "domain"]}
    records = [
        {"id": "g1", "stage": "event_generation", "checkpoint_id": "EG-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_found": True}},
        {"id": "g2", "stage": "collection", "checkpoint_id": "COL-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"event_received": True}},
        {"id": "g3", "stage": "parsing", "checkpoint_id": "PAR-1", "source_label": "SYNTHETIC", "availability": "AVAILABLE", "payload": {"raw_event_present": True, "extracted_fields": {"ip_addr": "192.168.1.1", "domain": ""}}},
    ]
    res = diagnose(spec, records)
    assert res["diagnosis"]["outcome"] == DiagnosticOutcome.FAILURE_LOCALIZED.value
    assert res["diagnosis"]["failure_stage"] == "parsing"
    assert "domain" in res["stage_results"][2]["reason"]


def test_generalization_4_fully_missing_telemetry():
    """Completely missing evidence returns UNDETERMINED with no root cause invented."""
    spec = {"rule_id": "R-NONE"}
    res = diagnose(spec, [])
    assert res["diagnosis"]["outcome"] == DiagnosticOutcome.UNDETERMINED.value
    assert res["diagnosis"]["failure_stage"] is None
    assert all(s["status"] == StageStatus.UNKNOWN.value for s in res["stage_results"])
