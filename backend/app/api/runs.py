"""API endpoints for test runs, evidence retrieval, and retests."""
import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Investigation,
    TestRun,
    EvidenceRecord,
    StageResult,
    Diagnosis,
    RemediationAction,
    AuditEvent,
    Scenario,
)
from app.schemas import RunCreate
from app.adapters.demo import fetch_demo_evidence
from app.diagnostics.engine import diagnose
from app.diagnostics.recovery import evaluate_recovery
from app.redaction import redact_payload

router = APIRouter(prefix="/api", tags=["runs"])


@router.post("/investigations/{inv_id}/runs", status_code=201)
def create_run(inv_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == inv_id).first()
    if not inv:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"Investigation {inv_id} not found", "details": None},
        )

    scenario = db.query(Scenario).filter(Scenario.id == payload.scenario_id).first()
    if not scenario:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"Scenario {payload.scenario_id} not found", "details": None},
        )

    run_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # Create run record
    run = TestRun(
        id=run_id,
        investigation_id=inv.id,
        scenario_id=scenario.id,
        run_type="INITIAL",
        parent_run_id=None,
        started_at=now_iso,
        status="COMPLETED",
    )
    db.add(run)

    # Audit RUN_STARTED
    db.add(AuditEvent(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        actor="analyst",
        action="RUN_STARTED",
        timestamp=now_iso,
        details={"run_id": run_id, "scenario_id": scenario.id},
    ))
    db.flush()

    try:
        # Fetch evidence via adapter
        evidence_records = fetch_demo_evidence(scenario.id, is_retest=False)

        # Execute deterministic diagnostic engine
        t0 = time.perf_counter()
        engine_output = diagnose(scenario.expected_stages, evidence_records)
        latency_ms = max(1, int((time.perf_counter() - t0) * 1000))

        # Persist evidence records
        for r in evidence_records:
            ev = EvidenceRecord(
                id=f"{run_id}-{r['id']}",
                run_id=run_id,
                stage=r["stage"],
                checkpoint_id=r["checkpoint_id"],
                source_label=r.get("source_label", "SYNTHETIC"),
                availability=r.get("availability", "AVAILABLE"),
                payload=redact_payload(r.get("payload", {})),
                observed_at=r.get("observed_at", now_iso),
                content_hash=r.get("content_hash", ""),
            )
            db.add(ev)

        # Persist stage results
        for sr in engine_output["stage_results"]:
            db.add(StageResult(
                id=str(uuid.uuid4()),
                run_id=run_id,
                stage=sr["stage"],
                status=sr["status"],
                reason=sr["reason"],
                evidence_ids=sr["evidence_ids"],
            ))

        diag_data = engine_output["diagnosis"]
        diag = Diagnosis(
            id=str(uuid.uuid4()),
            run_id=run_id,
            outcome=diag_data["outcome"],
            failure_stage=diag_data["failure_stage"],
            reason=diag_data["reason"],
            confidence_label=diag_data["confidence_label"],
            evidence_refs=diag_data["evidence_refs"],
            limitations=diag_data["limitations"],
            created_at=now_iso,
            latency_ms=latency_ms,
        )
        db.add(diag)
        db.flush()

        # Audit DIAGNOSIS_SAVED
        db.add(AuditEvent(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            actor="system",
            action="DIAGNOSIS_SAVED",
            timestamp=now_iso,
            details={"diagnosis_id": diag.id, "outcome": diag.outcome, "failure_stage": diag.failure_stage},
        ))

        # Persist remediation action if localized failure
        remed_info = diag_data.get("remediation", {})
        if remed_info.get("proposed_change"):
            rem = RemediationAction(
                id=str(uuid.uuid4()),
                diagnosis_id=diag.id,
                proposed_change=remed_info["proposed_change"],
                approval_status="PENDING",
                execution_status="NOT_EXECUTED",
            )
            db.add(rem)
            db.add(AuditEvent(
                id=str(uuid.uuid4()),
                investigation_id=inv.id,
                actor="system",
                action="REMEDIATION_PROPOSED",
                timestamp=now_iso,
                details={"remediation_id": rem.id, "proposed_change": rem.proposed_change},
            ))

        finish_iso = datetime.now(timezone.utc).isoformat()
        run.finished_at = finish_iso
        inv.status = "RUN_COMPLETED"

        db.add(AuditEvent(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            actor="system",
            action="RUN_COMPLETED",
            timestamp=finish_iso,
            details={"run_id": run_id, "latency_ms": latency_ms},
        ))
        db.commit()

        return {
            "run_id": run_id,
            "investigation_id": inv.id,
            "status": "COMPLETED",
            "stage_results": engine_output["stage_results"],
            "diagnosis": diag_data,
        }

    except Exception as e:
        db.rollback()
        # Persist run failure with error status and audit event
        err_msg = str(e)
        run.status = "ERROR"
        run.error = err_msg
        run.finished_at = datetime.now(timezone.utc).isoformat()
        inv.status = "RUN_FAILED"
        db.add(run)
        db.add(AuditEvent(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            actor="system",
            action="RUN_FAILED",
            timestamp=run.finished_at,
            details={"run_id": run_id, "error": err_msg},
        ))
        db.commit()
        raise HTTPException(
            status_code=500,
            detail={"error": "RUN_EXECUTION_ERROR", "message": f"Execution failed: {err_msg}", "details": None},
        )


@router.get("/runs/{run_id}/evidence")
def get_run_evidence(run_id: str, db: Session = Depends(get_db)):
    evs = db.query(EvidenceRecord).filter(EvidenceRecord.run_id == run_id).all()
    if not evs:
        # Check if run exists
        r = db.query(TestRun).filter(TestRun.id == run_id).first()
        if not r:
            raise HTTPException(
                status_code=404,
                detail={"error": "NOT_FOUND", "message": f"Run {run_id} not found", "details": None},
            )
    return [
        {
            "id": e.id,
            "run_id": e.run_id,
            "stage": e.stage,
            "checkpoint_id": e.checkpoint_id,
            "source_label": e.source_label,
            "availability": e.availability,
            "payload": e.payload,
            "observed_at": e.observed_at,
            "content_hash": e.content_hash,
        }
        for e in evs
    ]


@router.post("/runs/{run_id}/retest")
def execute_retest(run_id: str, db: Session = Depends(get_db)):
    original_run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not original_run:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"Run {run_id} not found", "details": None},
        )

    inv = original_run.investigation
    diag = original_run.diagnosis

    if not diag:
        raise HTTPException(
            status_code=409,
            detail={"error": "STATE_CONFLICT", "message": "Original run has no diagnosis to retest.", "details": None},
        )

    # If healthy, retest returns 409
    if diag.outcome == "HEALTHY":
        raise HTTPException(
            status_code=409,
            detail={"error": "STATE_CONFLICT", "message": "Healthy pipelines require no remediation or retest.", "details": None},
        )

    # Remediation check
    rem = diag.remediation
    if not rem:
        raise HTTPException(
            status_code=409,
            detail={"error": "STATE_CONFLICT", "message": "Diagnosis has no remediation proposal.", "details": None},
        )

    if rem.approval_status != "APPROVED" or rem.execution_status != "SIMULATED_APPLIED":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "STATE_CONFLICT",
                "message": f"Remediation must be APPROVED and SIMULATED_APPLIED before retest. Current status: {rem.approval_status}/{rem.execution_status}.",
                "details": None,
            },
        )

    scenario = db.query(Scenario).filter(Scenario.id == original_run.scenario_id).first()
    now_iso = datetime.now(timezone.utc).isoformat()
    retest_run_id = str(uuid.uuid4())

    # Create new run (run_type RETEST, parent_run_id = original)
    retest_run = TestRun(
        id=retest_run_id,
        investigation_id=inv.id,
        scenario_id=scenario.id,
        run_type="RETEST",
        parent_run_id=original_run.id,
        started_at=now_iso,
        status="COMPLETED",
    )
    db.add(retest_run)

    db.add(AuditEvent(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        actor="analyst",
        action="RETEST_STARTED",
        timestamp=now_iso,
        details={"retest_run_id": retest_run_id, "parent_run_id": original_run.id},
    ))
    db.flush()

    # Load post-fix evidence records
    postfix_evidence = fetch_demo_evidence(scenario.id, is_retest=True)

    # Run diagnostic engine on post-fix bundle
    t0 = time.perf_counter()
    retest_engine_res = diagnose(scenario.expected_stages, postfix_evidence)
    latency_ms = max(1, int((time.perf_counter() - t0) * 1000))

    # Persist post-fix evidence
    for r in postfix_evidence:
        ev = EvidenceRecord(
            id=f"{retest_run_id}-{r['id']}",
            run_id=retest_run_id,
            stage=r["stage"],
            checkpoint_id=r["checkpoint_id"],
            source_label=r.get("source_label", "SYNTHETIC"),
            availability=r.get("availability", "AVAILABLE"),
            payload=redact_payload(r.get("payload", {})),
            observed_at=r.get("observed_at", now_iso),
            content_hash=r.get("content_hash", ""),
        )
        db.add(ev)

    # Persist retest stage results
    for sr in retest_engine_res["stage_results"]:
        db.add(StageResult(
            id=str(uuid.uuid4()),
            run_id=retest_run_id,
            stage=sr["stage"],
            status=sr["status"],
            reason=sr["reason"],
            evidence_ids=sr["evidence_ids"],
        ))

    retest_diag_data = retest_engine_res["diagnosis"]
    retest_diag = Diagnosis(
        id=str(uuid.uuid4()),
        run_id=retest_run_id,
        outcome=retest_diag_data["outcome"],
        failure_stage=retest_diag_data["failure_stage"],
        reason=retest_diag_data["reason"],
        confidence_label=retest_diag_data["confidence_label"],
        evidence_refs=retest_diag_data["evidence_refs"],
        limitations=retest_diag_data["limitations"],
        created_at=now_iso,
        latency_ms=latency_ms,
    )
    db.add(retest_diag)

    # Retrieve original evidence to evaluate RC1..RC5
    orig_ev = db.query(EvidenceRecord).filter(EvidenceRecord.run_id == original_run.id).all()
    orig_ev_dicts = [
        {"id": e.id, "checkpoint_id": e.checkpoint_id, "payload": e.payload, "content_hash": e.content_hash}
        for e in orig_ev
    ]
    orig_stages_data = [
        {"stage": sr.stage, "status": sr.status, "reason": sr.reason}
        for sr in original_run.stage_results
    ]
    orig_diag_dict = {
        "outcome": diag.outcome,
        "failure_stage": diag.failure_stage,
    }

    recovery_res = evaluate_recovery(
        original_run={"id": original_run.id, "scenario_id": original_run.scenario_id, "run_type": "INITIAL"},
        original_evidence=orig_ev_dicts,
        original_stage_results=orig_stages_data,
        original_diagnosis=orig_diag_dict,
        retest_run={"id": retest_run_id, "scenario_id": scenario.id, "parent_run_id": original_run.id, "run_type": "RETEST"},
        retest_evidence=postfix_evidence,
        retest_stage_results=retest_engine_res["stage_results"],
    )

    final_class = recovery_res["recovery_result"]
    inv.status = f"RETEST_{final_class}"
    retest_run.finished_at = datetime.now(timezone.utc).isoformat()

    db.add(AuditEvent(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        actor="system",
        action="RETEST_COMPLETED",
        timestamp=retest_run.finished_at,
        details={"retest_run_id": retest_run_id, "recovery_result": final_class},
    ))
    db.commit()

    return {
        "retest_run_id": retest_run_id,
        "parent_run_id": original_run.id,
        "investigation_id": inv.id,
        "status": "COMPLETED",
        "stage_results": retest_engine_res["stage_results"],
        "diagnosis": retest_diag_data,
        "recovery_checks": recovery_res["checks"],
        "final_result": final_class,
    }
