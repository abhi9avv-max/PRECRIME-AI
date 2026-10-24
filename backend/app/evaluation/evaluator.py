"""Evaluation batch harness for running all 12 scenario cases against ground truth."""
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models import (
    Investigation,
    TestRun,
    EvidenceRecord,
    StageResult,
    Diagnosis,
    RemediationAction,
    AuditEvent,
    EvaluationResult,
)
from app.scenarios.fixtures import ALL_SCENARIOS
from app.evaluation.ground_truth import GROUND_TRUTH_CASES
from app.diagnostics.engine import diagnose
from app.diagnostics.recovery import evaluate_recovery
from app.diagnostics.stages import PipelineStage, STAGE_CHECKPOINTS
from app.redaction import redact_payload


def run_evaluation_batch(db: Session) -> Dict[str, Any]:
    """Execute a complete evaluation batch across all 12 cases and persist evaluation_results."""
    batch_id = str(uuid.uuid4())
    evaluated_at = datetime.now(timezone.utc).isoformat()
    results_records: List[EvaluationResult] = []

    for case in ALL_SCENARIOS:
        case_id = case["id"]
        gt = GROUND_TRUTH_CASES[case_id]
        split = case["split"]

        inv_id = f"eval-{batch_id[:8]}-{case_id}"
        inv = Investigation(
            id=inv_id,
            title=f"Evaluation Suite: {case['name']}",
            source_mode="DEMO",
            kind="EVALUATION",
            status="RUN_COMPLETED",
        )
        db.add(inv)

        # Record audit event
        audit_init = AuditEvent(
            id=str(uuid.uuid4()),
            investigation_id=inv_id,
            actor="evaluation-harness",
            action="INVESTIGATION_CREATED",
            details={"case_id": case_id, "batch_id": batch_id},
        )
        db.add(audit_init)

        # Run initial diagnosis
        run_id = f"run-{batch_id[:8]}-{case_id}-init"
        t0 = time.perf_counter()
        diag_res = diagnose(case["expectation_spec"], case["initial_evidence"])
        latency_ms = max(1, int((time.perf_counter() - t0) * 1000))

        initial_run = TestRun(
            id=run_id,
            investigation_id=inv_id,
            scenario_id=case_id,
            run_type="INITIAL",
            started_at=evaluated_at,
            finished_at=evaluated_at,
            status="COMPLETED",
        )
        db.add(initial_run)

        # Persist initial evidence records
        for r in case["initial_evidence"]:
            ev = EvidenceRecord(
                id=f"{run_id}-{r['id']}",
                run_id=run_id,
                stage=r["stage"],
                checkpoint_id=r["checkpoint_id"],
                source_label=r.get("source_label", "SYNTHETIC"),
                availability=r.get("availability", "AVAILABLE"),
                payload=redact_payload(r.get("payload", {})),
                observed_at=r.get("observed_at", evaluated_at),
                content_hash=r.get("content_hash", ""),
            )
            db.add(ev)

        # Persist stage results
        for sr in diag_res["stage_results"]:
            res_rec = StageResult(
                id=str(uuid.uuid4()),
                run_id=run_id,
                stage=sr["stage"],
                status=sr["status"],
                reason=sr["reason"],
                evidence_ids=sr["evidence_ids"],
            )
            db.add(res_rec)

        diag_data = diag_res["diagnosis"]
        diag = Diagnosis(
            id=str(uuid.uuid4()),
            run_id=run_id,
            outcome=diag_data["outcome"],
            failure_stage=diag_data["failure_stage"],
            reason=diag_data["reason"],
            confidence_label=diag_data["confidence_label"],
            evidence_refs=diag_data["evidence_refs"],
            limitations=diag_data["limitations"],
            latency_ms=latency_ms,
        )
        db.add(diag)

        # Retest evaluation if scenario has post-fix evidence and failed
        retest_result = "N/A"
        if case["postfix_evidence"] and diag_data["outcome"] == "FAILURE_LOCALIZED":
            retest_run_id = f"run-{batch_id[:8]}-{case_id}-retest"
            retest_diag = diagnose(case["expectation_spec"], case["postfix_evidence"])
            retest_obj = {
                "id": retest_run_id,
                "scenario_id": case_id,
                "parent_run_id": run_id,
                "run_type": "RETEST",
            }
            rec_eval = evaluate_recovery(
                original_run={"id": run_id, "scenario_id": case_id, "run_type": "INITIAL"},
                original_evidence=case["initial_evidence"],
                original_stage_results=diag_res["stage_results"],
                original_diagnosis=diag_data,
                retest_run=retest_obj,
                retest_evidence=case["postfix_evidence"],
                retest_stage_results=retest_diag["stage_results"],
            )
            retest_result = rec_eval["recovery_result"]

        # Checkpoint coverage count (out of 6 required checkpoints)
        available_ckpts = {
            r["checkpoint_id"]
            for r in case["initial_evidence"]
            if r.get("availability") == "AVAILABLE"
        }
        required_ckpts = set(STAGE_CHECKPOINTS.values())
        covered_count = len(available_ckpts.intersection(required_ckpts))

        # Metric truth evaluation
        is_evaluable = gt["evaluable"]
        is_insufficient = gt["insufficient_evidence"]

        # Correct localization: matched failure stage on failed evaluable cases
        correct_localization = (
            gt["expected_failure_stage"] is not None
            and diag_data["failure_stage"] == gt["expected_failure_stage"]
        )

        # False attribution: claimed failure when ground truth has no failure OR wrong failure stage
        false_attribution = False
        if diag_data["outcome"] == "FAILURE_LOCALIZED":
            if gt["expected_failure_stage"] is None:
                false_attribution = True
            elif diag_data["failure_stage"] != gt["expected_failure_stage"]:
                false_attribution = True

        eval_rec = EvaluationResult(
            id=str(uuid.uuid4()),
            batch_id=batch_id,
            case_id=case_id,
            run_id=run_id,
            evaluated_at=evaluated_at,
            split=split,
            outcome=diag_data["outcome"],
            failure_stage=diag_data["failure_stage"],
            is_evaluable=is_evaluable,
            is_insufficient=is_insufficient,
            retest_result=retest_result,
            correct_localization=correct_localization,
            false_attribution=false_attribution,
            latency_ms=latency_ms,
            checkpoints_available=covered_count,
            checkpoints_required=len(required_ckpts),
        )
        db.add(eval_rec)
        results_records.append(eval_rec)

    db.commit()
    return {"batch_id": batch_id, "evaluated_at": evaluated_at, "cases_evaluated": len(results_records)}
