"""Deterministic recovery verification and retest evaluation.

RC1: new run id, same scenario, RETEST linked to original parent.
RC2: original evidence hashes unchanged.
RC3: the originally failed stage is now PASS.
RC4: every later stage is now PASS.
RC5: expected alert SATISFIED at DEL-1.

Classification:
- VERIFIED: All RC1..RC5 checks pass.
- UNRESOLVED: Any check definitely fails.
- UNDETERMINED: No definite failure, but at least one check is non-evaluable (missing/unavailable evidence).
"""
import hashlib
import json
from typing import Dict, Any, List, Optional
from .stages import PipelineStage, STAGE_ORDER, StageStatus

def canonical_hash(payload: Any) -> str:
    """Compute sha256 of canonical JSON payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def evaluate_recovery(
    original_run: Dict[str, Any],
    original_evidence: List[Dict[str, Any]],
    original_stage_results: List[Dict[str, Any]],
    original_diagnosis: Dict[str, Any],
    retest_run: Dict[str, Any],
    retest_evidence: List[Dict[str, Any]],
    retest_stage_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluate RC1..RC5 checks from evidence records and stage results."""
    checks = []

    # RC1: New run id, same scenario, RETEST linked to original parent
    rc1_pass = (
        retest_run.get("id") != original_run.get("id")
        and retest_run.get("scenario_id") == original_run.get("scenario_id")
        and retest_run.get("parent_run_id") == original_run.get("id")
        and retest_run.get("run_type") == "RETEST"
    )
    checks.append({
        "id": "RC1",
        "name": "Retest lineage link",
        "description": "Retest is a new run with distinct ID linked to parent and matching scenario.",
        "status": "PASS" if rc1_pass else "FAIL",
        "detail": f"Parent={retest_run.get('parent_run_id')}, RunType={retest_run.get('run_type')}",
    })

    # RC2: Original evidence hashes unchanged
    rc2_status = "PASS"
    rc2_detail = "All original evidence records maintained exact content hashes."
    for rec in original_evidence:
        stored_hash = rec.get("content_hash")
        computed_hash = canonical_hash(rec.get("payload", {}))
        if stored_hash and computed_hash != stored_hash:
            rc2_status = "FAIL"
            rc2_detail = f"Record {rec.get('id')} content hash mismatch: {stored_hash} vs {computed_hash}."
            break
    checks.append({
        "id": "RC2",
        "name": "Original evidence immutability",
        "description": "Original evidence content hashes remain completely unmodified.",
        "status": rc2_status,
        "detail": rc2_detail,
    })

    # Find the stage that originally failed
    orig_fail_stage = original_diagnosis.get("failure_stage")
    retest_stages_by_name = {sr["stage"]: sr for sr in retest_stage_results}

    if not orig_fail_stage:
        # Original run was not a failure
        rc3_status = "NOT_EVALUABLE"
        rc3_detail = "Original diagnosis had no localized failure stage."
        rc4_status = "NOT_EVALUABLE"
        rc4_detail = "Original diagnosis had no failure stage to measure downstream stages against."
    else:
        # RC3: The originally failed stage is now PASS
        orig_res = retest_stages_by_name.get(orig_fail_stage, {})
        retest_orig_status = orig_res.get("status")
        if retest_orig_status == StageStatus.PASS.value:
            rc3_status = "PASS"
            rc3_detail = f"Stage '{orig_fail_stage}' status transitioned to PASS."
        elif retest_orig_status == StageStatus.FAIL.value:
            rc3_status = "FAIL"
            rc3_detail = f"Stage '{orig_fail_stage}' is still failing: {orig_res.get('reason')}."
        else:
            rc3_status = "NOT_EVALUABLE"
            rc3_detail = f"Stage '{orig_fail_stage}' status is {retest_orig_status}."

        # RC4: Every later stage PASS
        try:
            fail_idx = [s.value for s in STAGE_ORDER].index(orig_fail_stage)
            later_stages = STAGE_ORDER[fail_idx + 1:]
            later_results = [retest_stages_by_name.get(s.value, {}) for s in later_stages]
            if not later_stages:
                rc4_status = "PASS"
                rc4_detail = "Failed stage was final stage; no downstream stages."
            elif all(r.get("status") == StageStatus.PASS.value for r in later_results):
                rc4_status = "PASS"
                rc4_detail = f"All {len(later_stages)} downstream stages are PASS."
            elif any(r.get("status") == StageStatus.FAIL.value for r in later_results):
                rc4_status = "FAIL"
                failed_downstream = [r.get("stage") for r in later_results if r.get("status") == StageStatus.FAIL.value]
                rc4_detail = f"Downstream stages failed: {failed_downstream}."
            else:
                rc4_status = "NOT_EVALUABLE"
                rc4_detail = "One or more downstream stages are UNKNOWN or NOT REACHED."
        except ValueError:
            rc4_status = "NOT_EVALUABLE"
            rc4_detail = "Could not determine stage order index."

    checks.append({
        "id": "RC3",
        "name": "Remediated stage recovery",
        "description": "Originally failed stage evaluates to PASS in the retest.",
        "status": rc3_status,
        "detail": rc3_detail,
    })

    checks.append({
        "id": "RC4",
        "name": "Downstream pipeline integrity",
        "description": "All stages downstream of the fix evaluate to PASS.",
        "status": rc4_status,
        "detail": rc4_detail,
    })

    # RC5: Expected alert SATISFIED at DEL-1
    del_res = retest_stages_by_name.get(PipelineStage.DELIVERY_VISIBILITY.value, {})
    del_status = del_res.get("status")
    if del_status == StageStatus.PASS.value:
        rc5_status = "PASS"
        rc5_detail = "Alert received at destination checkpoint DEL-1."
    elif del_status == StageStatus.FAIL.value:
        rc5_status = "FAIL"
        rc5_detail = f"DEL-1 check failed: {del_res.get('reason')}."
    else:
        rc5_status = "NOT_EVALUABLE"
        rc5_detail = f"DEL-1 status is {del_status}."

    checks.append({
        "id": "RC5",
        "name": "End-to-end alert delivery",
        "description": "Delivery visibility checkpoint confirms alert reception.",
        "status": rc5_status,
        "detail": rc5_detail,
    })

    # Final result classification
    if any(c["status"] == "FAIL" for c in checks):
        recovery_result = "UNRESOLVED"
    elif any(c["status"] == "NOT_EVALUABLE" for c in checks):
        recovery_result = "UNDETERMINED"
    elif all(c["status"] == "PASS" for c in checks):
        recovery_result = "VERIFIED"
    else:
        recovery_result = "UNDETERMINED"

    return {
        "checks": checks,
        "recovery_result": recovery_result,
    }
