"""API endpoints for investigations and audit reports."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.models import (
    Investigation,
    TestRun,
    Diagnosis,
    RemediationAction,
    AuditEvent,
    StageResult,
    EvidenceRecord,
)
from app.schemas import InvestigationCreate, ErrorResponse
from app.diagnostics.recovery import evaluate_recovery

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.post("", response_model=dict, status_code=201)
def create_investigation(payload: InvestigationCreate, db: Session = Depends(get_db)):
    inv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    inv = Investigation(
        id=inv_id,
        title=payload.title,
        source_mode=payload.source_mode,
        kind="ANALYST",
        status="CREATED",
        created_at=now,
    )
    db.add(inv)

    audit = AuditEvent(
        id=str(uuid.uuid4()),
        investigation_id=inv_id,
        actor="analyst",
        action="INVESTIGATION_CREATED",
        timestamp=now,
        details={"title": payload.title, "source_mode": payload.source_mode},
    )
    db.add(audit)
    db.commit()
    db.refresh(inv)

    return {
        "id": inv.id,
        "title": inv.title,
        "source_mode": inv.source_mode,
        "kind": inv.kind,
        "status": inv.status,
        "created_at": inv.created_at,
    }


@router.get("", response_model=list)
def list_investigations(db: Session = Depends(get_db)):
    # Return all investigations ordered by created_at desc (hide internal evaluation batch items from analyst list)
    invs = db.query(Investigation).filter(Investigation.kind == "ANALYST").order_by(desc(Investigation.created_at)).all()
    out = []
    for inv in invs:
        # Determine latest run summary
        latest_run = inv.runs[-1] if inv.runs else None
        diag = latest_run.diagnosis if latest_run else None
        out.append({
            "id": inv.id,
            "title": inv.title,
            "source_mode": inv.source_mode,
            "status": inv.status,
            "created_at": inv.created_at,
            "runs_count": len(inv.runs),
            "latest_outcome": diag.outcome if diag else None,
            "failure_stage": diag.failure_stage if diag else None,
        })
    return out


@router.get("/{id}")
def get_investigation(id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter(Investigation.id == id).first()
    if not inv:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"Investigation {id} not found", "details": None},
        )

    runs_data = []
    for r in inv.runs:
        diag_data = None
        remed_data = None
        if r.diagnosis:
            d = r.diagnosis
            diag_data = {
                "id": d.id,
                "run_id": d.run_id,
                "outcome": d.outcome,
                "failure_stage": d.failure_stage,
                "reason": d.reason,
                "confidence_label": d.confidence_label,
                "evidence_refs": d.evidence_refs,
                "limitations": d.limitations,
                "created_at": d.created_at,
                "latency_ms": d.latency_ms,
                "review_status": d.review_status,
                "reviewed_by": d.reviewed_by,
                "reviewed_at": d.reviewed_at,
                "review_note": d.review_note,
            }
            if d.remediation:
                rem = d.remediation
                remed_data = {
                    "id": rem.id,
                    "diagnosis_id": rem.diagnosis_id,
                    "proposed_change": rem.proposed_change,
                    "approval_status": rem.approval_status,
                    "execution_status": rem.execution_status,
                    "approved_by": rem.approved_by,
                    "decided_at": rem.decided_at,
                    "decision_note": rem.decision_note,
                }

        stages_data = [
            {
                "id": sr.id,
                "stage": sr.stage,
                "status": sr.status,
                "reason": sr.reason,
                "evidence_ids": sr.evidence_ids,
            }
            for sr in r.stage_results
        ]

        runs_data.append({
            "id": r.id,
            "investigation_id": r.investigation_id,
            "scenario_id": r.scenario_id,
            "run_type": r.run_type,
            "parent_run_id": r.parent_run_id,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
            "error": r.error,
            "stage_results": stages_data,
            "diagnosis": diag_data,
            "remediation": remed_data,
        })

    audit_data = [
        {
            "id": a.id,
            "actor": a.actor,
            "action": a.action,
            "timestamp": a.timestamp,
            "details": a.details,
        }
        for a in inv.audit_events
    ]

    return {
        "id": inv.id,
        "title": inv.title,
        "source_mode": inv.source_mode,
        "kind": inv.kind,
        "status": inv.status,
        "created_at": inv.created_at,
        "runs": runs_data,
        "audit_events": audit_data,
    }


@router.get("/{id}/report")
def export_investigation_report(
    id: str,
    format: str = Query(default="json", pattern="^(json|md)$"),
    db: Session = Depends(get_db),
):
    inv_data = get_investigation(id, db)
    runs = inv_data["runs"]
    audit = inv_data["audit_events"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Calculate retest comparison if both initial and retest runs exist
    retest_comparison = None
    initial_run = next((r for r in runs if r["run_type"] == "INITIAL"), None)
    retest_run = next((r for r in runs if r["run_type"] == "RETEST"), None)

    if initial_run and retest_run:
        orig_ev = db.query(EvidenceRecord).filter(EvidenceRecord.run_id == initial_run["id"]).all()
        ret_ev = db.query(EvidenceRecord).filter(EvidenceRecord.run_id == retest_run["id"]).all()
        rec_eval = evaluate_recovery(
            original_run=initial_run,
            original_evidence=[{"id": e.id, "content_hash": e.content_hash, "payload": e.payload} for e in orig_ev],
            original_stage_results=initial_run["stage_results"],
            original_diagnosis=initial_run["diagnosis"] or {},
            retest_run=retest_run,
            retest_evidence=[{"id": e.id, "content_hash": e.content_hash, "payload": e.payload} for e in ret_ev],
            retest_stage_results=retest_run["stage_results"],
        )
        retest_comparison = {
            "initial_run_id": initial_run["id"],
            "retest_run_id": retest_run["id"],
            "recovery_result": rec_eval["recovery_result"],
            "checks": rec_eval["checks"],
        }

    report = {
        "generated_at": now_iso,
        "investigation_id": inv_data["id"],
        "title": inv_data["title"],
        "source_mode": inv_data["source_mode"],
        "status": inv_data["status"],
        "runs": runs,
        "retest_comparison": retest_comparison,
        "audit_trail": audit,
    }

    if format == "json":
        return JSONResponse(content=report)

    # Markdown format
    md_lines = [
        f"# PRECRIME AI - Investigation Report",
        f"**Investigation ID**: `{inv_data['id']}`  ",
        f"**Title**: {inv_data['title']}  ",
        f"**Source Mode**: {inv_data['source_mode']}  ",
        f"**Status**: {inv_data['status']}  ",
        f"**Generated**: {now_iso}  ",
        "",
        "## Pipeline Trace Runs",
    ]
    for r in runs:
        md_lines.append(f"### Run `{r['id']}` ({r['run_type']}) - Status: {r['status']}")
        diag = r.get("diagnosis")
        if diag:
            md_lines.append(f"- **Outcome**: `{diag['outcome']}` (Confidence: {diag['confidence_label']})")
            if diag.get("failure_stage"):
                md_lines.append(f"- **Earliest Failure**: `{diag['failure_stage']}`")
            md_lines.append(f"- **Reason**: {diag['reason']}")
            if diag.get("evidence_refs"):
                md_lines.append(f"- **Evidence Refs**: {', '.join(diag['evidence_refs'])}")
            if diag.get("limitations"):
                md_lines.append(f"- **Limitations**: {'; '.join(diag['limitations'])}")
            if diag.get("review_status"):
                md_lines.append(f"- **Review**: {diag['review_status']} by {diag['reviewed_by']} ({diag['review_note']})")
            rem = r.get("remediation")
            if rem and rem.get("proposed_change"):
                md_lines.append(f"- **Remediation**: `{rem['approval_status']}` - {rem['proposed_change']}")

        md_lines.append("\n**Stage Results:**")
        for sr in r.get("stage_results", []):
            md_lines.append(f"- **{sr['stage']}**: `{sr['status']}` - {sr['reason']}")
        md_lines.append("")

    if retest_comparison:
        md_lines.append("## Verification & Recovery Checks")
        md_lines.append(f"**Overall Recovery Result**: `{retest_comparison['recovery_result']}`\n")
        for c in retest_comparison["checks"]:
            md_lines.append(f"- **[{c['status']}] {c['id']}: {c['name']}** - {c['description']} ({c['detail']})")
        md_lines.append("")

    md_lines.append("## Audit Trail")
    for a in audit:
        md_lines.append(f"- `{a['timestamp']}` | **{a['actor']}** -> `{a['action']}`")

    return PlainTextResponse(content="\n".join(md_lines), media_type="text/markdown")
