"""SQLAlchemy database models for PRECRIME AI."""
from datetime import datetime, timezone
import json
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from .db import Base


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    source_mode = Column(String, nullable=False, default="DEMO")  # DEMO | WAZUH
    kind = Column(String, nullable=False, default="ANALYST")      # ANALYST | EVALUATION
    status = Column(String, nullable=False, default="CREATED")
    # States: CREATED, RUN_COMPLETED, RUN_FAILED, REVIEWED, REMEDIATION_APPROVED, REMEDIATION_REJECTED, RETEST_VERIFIED, RETEST_UNRESOLVED, RETEST_UNDETERMINED
    created_at = Column(String, nullable=False, default=utc_now_iso)

    runs = relationship("TestRun", back_populates="investigation", cascade="all, delete-orphan", order_by="TestRun.started_at")
    audit_events = relationship("AuditEvent", back_populates="investigation", cascade="all, delete-orphan", order_by="AuditEvent.timestamp")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String, primary_key=True)  # e.g. "parsing_failure.a"
    family = Column(String, nullable=False)
    variant = Column(String, nullable=False)
    split = Column(String, nullable=False)  # development | held-out
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    expected_stages = Column(JSON, nullable=False)  # Expectation spec
    ground_truth = Column(JSON, nullable=True)     # Evaluator-only; never exposed via public scenarios API


class TestRun(Base):
    __test__ = False
    __tablename__ = "test_runs"

    id = Column(String, primary_key=True)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    run_type = Column(String, nullable=False, default="INITIAL")  # INITIAL | RETEST
    parent_run_id = Column(String, nullable=True)
    started_at = Column(String, nullable=False, default=utc_now_iso)
    finished_at = Column(String, nullable=True)
    status = Column(String, nullable=False, default="COMPLETED")  # COMPLETED | ERROR
    error = Column(Text, nullable=True)

    investigation = relationship("Investigation", back_populates="runs")
    evidence = relationship("EvidenceRecord", back_populates="run", cascade="all, delete-orphan")
    stage_results = relationship("StageResult", back_populates="run", cascade="all, delete-orphan")
    diagnosis = relationship("Diagnosis", back_populates="run", uselist=False, cascade="all, delete-orphan")


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("test_runs.id"), nullable=False)
    stage = Column(String, nullable=False)
    checkpoint_id = Column(String, nullable=False)
    source_label = Column(String, nullable=False)  # SYNTHETIC | WAZUH
    availability = Column(String, nullable=False)  # AVAILABLE | UNAVAILABLE
    payload = Column(JSON, nullable=False)
    observed_at = Column(String, nullable=False, default=utc_now_iso)
    content_hash = Column(String, nullable=False)

    run = relationship("TestRun", back_populates="evidence")


class StageResult(Base):
    __tablename__ = "stage_results"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("test_runs.id"), nullable=False)
    stage = Column(String, nullable=False)
    status = Column(String, nullable=False)  # PASS | FAIL | UNKNOWN | NOT REACHED
    reason = Column(Text, nullable=False)
    evidence_ids = Column(JSON, nullable=False, default=list)

    run = relationship("TestRun", back_populates="stage_results")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("test_runs.id"), nullable=False, unique=True)
    outcome = Column(String, nullable=False)  # FAILURE_LOCALIZED | HEALTHY | UNDETERMINED
    failure_stage = Column(String, nullable=True)
    reason = Column(Text, nullable=False)
    confidence_label = Column(String, nullable=False)
    evidence_refs = Column(JSON, nullable=False, default=list)
    limitations = Column(JSON, nullable=False, default=list)
    created_at = Column(String, nullable=False, default=utc_now_iso)
    latency_ms = Column(Integer, nullable=False, default=0)

    review_status = Column(String, nullable=True)  # ACCEPT | REJECT | None
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(String, nullable=True)
    review_note = Column(Text, nullable=True)

    run = relationship("TestRun", back_populates="diagnosis")
    remediation = relationship("RemediationAction", back_populates="diagnosis", uselist=False, cascade="all, delete-orphan")


class RemediationAction(Base):
    __tablename__ = "remediation_actions"

    id = Column(String, primary_key=True)
    diagnosis_id = Column(String, ForeignKey("diagnoses.id"), nullable=False, unique=True)
    proposed_change = Column(Text, nullable=True)
    approval_status = Column(String, nullable=False, default="PENDING")  # PENDING | APPROVED | REJECTED
    execution_status = Column(String, nullable=False, default="NOT_EXECUTED")  # NOT_EXECUTED | SIMULATED_APPLIED
    approved_by = Column(String, nullable=True)
    decided_at = Column(String, nullable=True)
    decision_note = Column(Text, nullable=True)

    diagnosis = relationship("Diagnosis", back_populates="remediation")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    investigation_id = Column(String, ForeignKey("investigations.id"), nullable=False)
    actor = Column(String, nullable=False, default="system")
    action = Column(String, nullable=False)
    timestamp = Column(String, nullable=False, default=utc_now_iso)
    details = Column(JSON, nullable=False, default=dict)

    investigation = relationship("Investigation", back_populates="audit_events")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=False)
    case_id = Column(String, nullable=False)
    run_id = Column(String, nullable=False)
    evaluated_at = Column(String, nullable=False, default=utc_now_iso)
    split = Column(String, nullable=False)  # development | held-out
    outcome = Column(String, nullable=False)
    failure_stage = Column(String, nullable=True)
    is_evaluable = Column(Boolean, nullable=False)
    is_insufficient = Column(Boolean, nullable=False)
    retest_result = Column(String, nullable=True)  # VERIFIED | UNRESOLVED | UNDETERMINED | N/A
    correct_localization = Column(Boolean, nullable=False)
    false_attribution = Column(Boolean, nullable=False)
    latency_ms = Column(Integer, nullable=False, default=0)
    checkpoints_available = Column(Integer, nullable=False, default=0)
    checkpoints_required = Column(Integer, nullable=False, default=6)
