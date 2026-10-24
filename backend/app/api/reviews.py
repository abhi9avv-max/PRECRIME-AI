"""API endpoints for human review and remediation approval workflows."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Investigation,
    Diagnosis,
    RemediationAction,
    AuditEvent,
)
from app.schemas import DiagnosisReviewRequest, RemediationApproveRequest

router = APIRouter(prefix="/api", tags=["reviews"])


@router.post("/diagnoses/{diag_id}/review")
def review_diagnosis(diag_id: str, payload: DiagnosisReviewRequest, db: Session = Depends(get_db)):
    diag = db.query(Diagnosis).filter(Diagnosis.id == diag_id).first()
    if not diag:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"Diagnosis {diag_id} not found", "details": None},
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    diag.review_status = payload.decision
    diag.reviewed_by = payload.reviewer
    diag.reviewed_at = now_iso
    diag.review_note = payload.note

    inv = diag.run.investigation
    inv.status = "REVIEWED"

    db.add(AuditEvent(
        id=str(uuid.uuid4()),
        investigation_id=inv.id,
        actor=payload.reviewer,
        action="DIAGNOSIS_REVIEWED",
        timestamp=now_iso,
        details={"diagnosis_id": diag.id, "decision": payload.decision, "note": payload.note},
    ))
    db.commit()

    return {
        "diagnosis_id": diag.id,
        "review_status": diag.review_status,
        "reviewed_by": diag.reviewed_by,
        "reviewed_at": diag.reviewed_at,
        "review_note": diag.review_note,
    }


@router.post("/remediations/{rem_id}/approve")
def approve_remediation(rem_id: str, payload: RemediationApproveRequest, db: Session = Depends(get_db)):
    rem = db.query(RemediationAction).filter(RemediationAction.id == rem_id).first()
    if not rem:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"Remediation {rem_id} not found", "details": None},
        )

    diag = rem.diagnosis
    inv = diag.run.investigation

    # 409 unless diagnosis has a recorded ACCEPT
    if diag.review_status != "ACCEPT":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "STATE_CONFLICT",
                "message": f"Remediation cannot be approved without a recorded diagnosis ACCEPT. Current review status: {diag.review_status}.",
                "details": None,
            },
        )

    # If already rejected, rejection is final
    if rem.approval_status == "REJECTED":
        raise HTTPException(
            status_code=409,
            detail={"error": "STATE_CONFLICT", "message": "Remediation has already been rejected; rejection is final.", "details": None},
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    rem.approved_by = payload.reviewer
    rem.decided_at = now_iso
    rem.decision_note = payload.note

    if payload.decision == "APPROVE":
        rem.approval_status = "APPROVED"
        # Audit REMEDIATION_APPROVED
        db.add(AuditEvent(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            actor=payload.reviewer,
            action="REMEDIATION_APPROVED",
            timestamp=now_iso,
            details={"remediation_id": rem.id, "reviewer": payload.reviewer, "note": payload.note},
        ))

        # Immediately apply simulated execution
        rem.execution_status = "SIMULATED_APPLIED"
        sim_time = datetime.now(timezone.utc).isoformat()
        db.add(AuditEvent(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            actor="system",
            action="REMEDIATION_SIMULATED_APPLIED",
            timestamp=sim_time,
            details={"remediation_id": rem.id, "simulated": True},
        ))
        inv.status = "REMEDIATION_APPROVED"

    else:
        rem.approval_status = "REJECTED"
        rem.execution_status = "NOT_EXECUTED"
        db.add(AuditEvent(
            id=str(uuid.uuid4()),
            investigation_id=inv.id,
            actor=payload.reviewer,
            action="REMEDIATION_REJECTED",
            timestamp=now_iso,
            details={"remediation_id": rem.id, "reviewer": payload.reviewer, "note": payload.note},
        ))
        inv.status = "REMEDIATION_REJECTED"

    db.commit()

    return {
        "remediation_id": rem.id,
        "approval_status": rem.approval_status,
        "execution_status": rem.execution_status,
        "approved_by": rem.approved_by,
        "decided_at": rem.decided_at,
        "decision_note": rem.decision_note,
    }
