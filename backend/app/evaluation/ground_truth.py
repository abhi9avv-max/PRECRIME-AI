"""Ground Truth definitions for evaluation harness.

This file is ONLY read by the evaluation harness and metrics calculation.
Neither GET /api/scenarios, nor the demo adapter, nor the diagnostic engine
imports or accesses this file.
"""
from typing import Dict, Any

GROUND_TRUTH_CASES: Dict[str, Dict[str, Any]] = {
    "collection_failure.a": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "collection",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "VERIFIED",
    },
    "collection_failure.b": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "collection",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "VERIFIED",
    },
    "parsing_failure.a": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "parsing",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "VERIFIED",
    },
    "parsing_failure.b": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "parsing",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "UNRESOLVED",
    },
    "rule_mismatch.a": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "rule_evaluation",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "VERIFIED",
    },
    "rule_mismatch.b": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "rule_evaluation",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "VERIFIED",
    },
    "delivery_failure.a": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "delivery_visibility",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "VERIFIED",
    },
    "delivery_failure.b": {
        "expected_outcome": "FAILURE_LOCALIZED",
        "expected_failure_stage": "delivery_visibility",
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "UNDETERMINED",
    },
    "healthy_pipeline.a": {
        "expected_outcome": "HEALTHY",
        "expected_failure_stage": None,
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "N/A",
    },
    "healthy_pipeline.b": {
        "expected_outcome": "HEALTHY",
        "expected_failure_stage": None,
        "evaluable": True,
        "insufficient_evidence": False,
        "expected_retest_class": "N/A",
    },
    "insufficient_evidence.a": {
        "expected_outcome": "UNDETERMINED",
        "expected_failure_stage": None,
        "evaluable": False,
        "insufficient_evidence": True,
        "expected_retest_class": "N/A",
    },
    "insufficient_evidence.b": {
        "expected_outcome": "UNDETERMINED",
        "expected_failure_stage": None,
        "evaluable": False,
        "insufficient_evidence": True,
        "expected_retest_class": "N/A",
    },
}
