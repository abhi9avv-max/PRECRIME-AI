"""Unit tests for recovery checks (RC1..RC5) and retest verification."""
import pytest
from app.diagnostics.engine import diagnose
from app.diagnostics.recovery import evaluate_recovery
from app.scenarios.fixtures import SCENARIOS_BY_ID
from app.evaluation.ground_truth import GROUND_TRUTH_CASES


def test_recovery_all_retest_cases():
    """Verify that evaluate_recovery yields the exact expected ground truth retest class."""
    for case_id, gt in GROUND_TRUTH_CASES.items():
        expected_class = gt["expected_retest_class"]
        if expected_class == "N/A":
            continue

        case = SCENARIOS_BY_ID[case_id]
        orig_run = {"id": "run-orig-1", "scenario_id": case_id, "run_type": "INITIAL"}
        orig_diag_res = diagnose(case["expectation_spec"], case["initial_evidence"])

        retest_run = {
            "id": "run-retest-2",
            "scenario_id": case_id,
            "parent_run_id": "run-orig-1",
            "run_type": "RETEST",
        }
        retest_diag_res = diagnose(case["expectation_spec"], case["postfix_evidence"])

        rec_res = evaluate_recovery(
            original_run=orig_run,
            original_evidence=case["initial_evidence"],
            original_stage_results=orig_diag_res["stage_results"],
            original_diagnosis=orig_diag_res["diagnosis"],
            retest_run=retest_run,
            retest_evidence=case["postfix_evidence"],
            retest_stage_results=retest_diag_res["stage_results"],
        )

        assert rec_res["recovery_result"] == expected_class, (
            f"Case {case_id} recovery mismatch: expected {expected_class}, got {rec_res['recovery_result']}"
        )


def test_corrupted_postfix_flips_verified_to_unresolved():
    """Mutation test: corrupting post-fix evidence flips VERIFIED to UNRESOLVED."""
    case = SCENARIOS_BY_ID["parsing_failure.a"]
    orig_run = {"id": "run-1", "scenario_id": "parsing_failure.a", "run_type": "INITIAL"}
    orig_diag = diagnose(case["expectation_spec"], case["initial_evidence"])

    retest_run = {
        "id": "run-2",
        "scenario_id": "parsing_failure.a",
        "parent_run_id": "run-1",
        "run_type": "RETEST",
    }
    # Corrupt post-fix evidence by breaking delivery
    corrupted_postfix = []
    for rec in case["postfix_evidence"]:
        r = dict(rec)
        if r["checkpoint_id"] == "DEL-1":
            r = dict(r)
            r["payload"] = {"alert_received": False}
        corrupted_postfix.append(r)

    retest_diag = diagnose(case["expectation_spec"], corrupted_postfix)
    rec_res = evaluate_recovery(
        original_run=orig_run,
        original_evidence=case["initial_evidence"],
        original_stage_results=orig_diag["stage_results"],
        original_diagnosis=orig_diag["diagnosis"],
        retest_run=retest_run,
        retest_evidence=corrupted_postfix,
        retest_stage_results=retest_diag["stage_results"],
    )
    assert rec_res["recovery_result"] == "UNRESOLVED"
    failed_checks = [c["id"] for c in rec_res["checks"] if c["status"] == "FAIL"]
    assert "RC5" in failed_checks


def test_tampered_original_evidence_fails_rc2():
    """Tampering with original evidence causes RC2 to FAIL and yields UNRESOLVED."""
    case = SCENARIOS_BY_ID["parsing_failure.a"]
    orig_run = {"id": "run-1", "scenario_id": "parsing_failure.a", "run_type": "INITIAL"}
    orig_diag = diagnose(case["expectation_spec"], case["initial_evidence"])

    retest_run = {
        "id": "run-2",
        "scenario_id": "parsing_failure.a",
        "parent_run_id": "run-1",
        "run_type": "RETEST",
    }
    retest_diag = diagnose(case["expectation_spec"], case["postfix_evidence"])

    # Tamper with an original evidence record's payload without updating its content_hash
    tampered_orig = []
    for r in case["initial_evidence"]:
        tampered_r = dict(r)
        if tampered_r["checkpoint_id"] == "PAR-1":
            tampered_r["payload"] = {"tampered": True}
        tampered_orig.append(tampered_r)

    rec_res = evaluate_recovery(
        original_run=orig_run,
        original_evidence=tampered_orig,
        original_stage_results=orig_diag["stage_results"],
        original_diagnosis=orig_diag["diagnosis"],
        retest_run=retest_run,
        retest_evidence=case["postfix_evidence"],
        retest_stage_results=retest_diag["stage_results"],
    )
    assert rec_res["recovery_result"] == "UNRESOLVED"
    rc2 = next(c for c in rec_res["checks"] if c["id"] == "RC2")
    assert rc2["status"] == "FAIL"
