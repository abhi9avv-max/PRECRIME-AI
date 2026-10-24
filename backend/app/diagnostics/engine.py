"""Deterministic SIEM Detection-Failure Diagnostic Engine.

Zero LLM calls, zero heuristics, zero hardcoded scenarios.
Analyzes generic expectation specs against evidence records strictly according
to pipeline prerequisite rules, cross-stage consistency, and evidence availability.
"""
from typing import Dict, Any, List, Optional, Tuple
from .stages import (
    PipelineStage,
    STAGE_ORDER,
    STAGE_CHECKPOINTS,
    StageStatus,
    DiagnosticOutcome,
    ConfidenceLabel,
    Availability,
)
from .remediation import generate_remediation


class StageEvaluation:
    def __init__(
        self,
        stage: PipelineStage,
        checkpoint_id: str,
        outcome: str,  # SATISFIED, VIOLATED, MISSING, CONFLICTING
        reason: str,
        evidence_ids: List[str],
        details: Dict[str, Any],
    ):
        self.stage = stage
        self.checkpoint_id = checkpoint_id
        self.outcome = outcome
        self.reason = reason
        self.evidence_ids = evidence_ids
        self.details = details


def evaluate_checkpoint(
    stage: PipelineStage,
    checkpoint_id: str,
    spec: Dict[str, Any],
    records: List[Dict[str, Any]],
) -> StageEvaluation:
    """Step 1: Evaluate raw stage outcome from checkpoint records."""
    if not records:
        return StageEvaluation(
            stage=stage,
            checkpoint_id=checkpoint_id,
            outcome="MISSING",
            reason=f"No evidence records found for checkpoint {checkpoint_id}.",
            evidence_ids=[],
            details={},
        )

    available_records = [r for r in records if r.get("availability") == Availability.AVAILABLE.value]
    evidence_ids = [r.get("id") for r in records if r.get("id")]

    if not available_records:
        reasons = [r.get("payload", {}).get("reason", "Unavailable") for r in records]
        return StageEvaluation(
            stage=stage,
            checkpoint_id=checkpoint_id,
            outcome="MISSING",
            reason=f"Checkpoint {checkpoint_id} unavailable: {'; '.join(reasons)}",
            evidence_ids=evidence_ids,
            details={"availability": "UNAVAILABLE"},
        )

    # Check for internal conflicts among multiple available records for the same checkpoint
    if len(available_records) > 1:
        # Check if observations contradict
        obs_set = set()
        for r in available_records:
            p = r.get("payload", {})
            if stage == PipelineStage.EVENT_GENERATION:
                obs_set.add(bool(p.get("event_found")))
            elif stage == PipelineStage.COLLECTION:
                # Key observation is receipt: event_received
                # Also if one reports forwarded=True but another says event_received=False
                val = p.get("event_received")
                if val is None and "forwarded" in p:
                    val = p.get("forwarded")
                obs_set.add(bool(val))
            elif stage == PipelineStage.PARSING:
                obs_set.add(bool(p.get("raw_event_present")))
            elif stage == PipelineStage.RULE_EVALUATION:
                obs_set.add(bool(p.get("matched")))
            elif stage == PipelineStage.ALERT_GENERATION:
                obs_set.add(bool(p.get("alert_found")))
            elif stage == PipelineStage.DELIVERY_VISIBILITY:
                obs_set.add(bool(p.get("alert_received")))

        if len(obs_set) > 1:
            return StageEvaluation(
                stage=stage,
                checkpoint_id=checkpoint_id,
                outcome="CONFLICTING",
                reason=f"Contradictory observations among {len(available_records)} available records for {checkpoint_id}.",
                evidence_ids=[r.get("id") for r in available_records if r.get("id")],
                details={},
            )

    # Use the primary available record
    primary = available_records[0]
    p = primary.get("payload", {})
    available_ids = [r.get("id") for r in available_records if r.get("id")]

    # Stage-specific logic
    if stage == PipelineStage.EVENT_GENERATION:
        found = p.get("event_found", False)
        if found:
            event_id = p.get("event_id")
            return StageEvaluation(
                stage, checkpoint_id, "SATISFIED",
                f"Source event confirmed generated (event_id: {event_id}).",
                available_ids,
                {"event_id": event_id, "source": p.get("source")},
            )
        return StageEvaluation(
            stage, checkpoint_id, "VIOLATED",
            "Event generation was not confirmed on source system.",
            available_ids,
            {"source": p.get("source")},
        )

    elif stage == PipelineStage.COLLECTION:
        received = p.get("event_received")
        if received is True:
            return StageEvaluation(
                stage, checkpoint_id, "SATISFIED",
                "Event successfully received by collector.",
                available_ids,
                {"agent_id": p.get("agent_id") or p.get("source")},
            )
        elif received is False:
            status = p.get("agent_status", "unknown")
            return StageEvaluation(
                stage, checkpoint_id, "VIOLATED",
                f"Collection checkpoint reached but event was not received (agent_status: {status}).",
                available_ids,
                {"agent_id": p.get("agent_id"), "agent_status": status, "source": p.get("source")},
            )
        else:
            return StageEvaluation(
                stage, checkpoint_id, "MISSING",
                "Collection status missing event_received indicator.",
                available_ids,
                {},
            )

    elif stage == PipelineStage.PARSING:
        raw_present = p.get("raw_event_present", False)
        if not raw_present:
            return StageEvaluation(
                stage, checkpoint_id, "MISSING",
                "Raw event not present in parser checkpoint.",
                available_ids,
                {},
            )
        extracted = p.get("extracted_fields", {})
        required = spec.get("required_fields") or spec.get("checkpoints", {}).get("PAR-1", {}).get("required_fields", [])
        
        missing_fields = []
        for req in required:
            val = extracted.get(req)
            if val is None or val == "":
                missing_fields.append(req)

        if missing_fields:
            return StageEvaluation(
                stage, checkpoint_id, "VIOLATED",
                f"Parser failed to extract required fields: {missing_fields}.",
                available_ids,
                {"missing_fields": missing_fields, "extracted_fields": extracted},
            )

        return StageEvaluation(
            stage, checkpoint_id, "SATISFIED",
            f"All required fields extracted successfully: {list(required)}.",
            available_ids,
            {"extracted_fields": extracted},
        )

    elif stage == PipelineStage.RULE_EVALUATION:
        decoded = p.get("decoded_fields")
        matched = p.get("matched")

        # Evaluate condition rules if present in spec or payload
        rule_spec = spec.get("checkpoints", {}).get("RUL-1", {})
        rule_id = spec.get("rule_id") or rule_spec.get("rule_id") or p.get("rule_id", "unknown")
        conditions = rule_spec.get("rule_conditions") or p.get("rule_conditions", [])

        if matched is False or (decoded and matched is not True):
            failed_desc = "rule condition not satisfied"
            field_name = None
            observed_val = None
            if conditions and decoded is not None:
                for cond in conditions:
                    f = cond.get("field")
                    op = cond.get("op")
                    val = cond.get("value")
                    actual = decoded.get(f)
                    cond_met = False
                    if op == "eq":
                        cond_met = (actual == val)
                    elif op == "in":
                        cond_met = (actual in val) if isinstance(val, (list, set, tuple)) else False
                    
                    if not cond_met:
                        failed_desc = f"{f} ({actual!r}) does not satisfy {op} {val!r}"
                        field_name = f
                        observed_val = actual
                        break

            return StageEvaluation(
                stage, checkpoint_id, "VIOLATED",
                f"Rule {rule_id} condition failed: {failed_desc}.",
                available_ids,
                {
                    "rule_id": rule_id,
                    "failed_condition": failed_desc,
                    "field_name": field_name,
                    "observed_value": observed_val,
                    "decoded_fields": decoded,
                },
            )
        elif matched is True:
            return StageEvaluation(
                stage, checkpoint_id, "SATISFIED",
                f"Rule {rule_id} matched successfully against decoded fields.",
                available_ids,
                {"rule_id": rule_id, "decoded_fields": decoded},
            )
        else:
            return StageEvaluation(
                stage, checkpoint_id, "MISSING",
                "Rule evaluation checkpoint missing decoded fields or match determination.",
                available_ids,
                {},
            )

    elif stage == PipelineStage.ALERT_GENERATION:
        alert_found = p.get("alert_found", False)
        rule_id = p.get("rule_id")
        expected_rule_id = spec.get("rule_id") or spec.get("checkpoints", {}).get("ALT-1", {}).get("rule_id")

        if alert_found:
            if expected_rule_id and rule_id and str(rule_id) != str(expected_rule_id):
                return StageEvaluation(
                    stage, checkpoint_id, "VIOLATED",
                    f"Alert found for rule {rule_id}, but expected rule {expected_rule_id}.",
                    available_ids,
                    {"rule_id": rule_id, "expected_rule_id": expected_rule_id},
                )
            return StageEvaluation(
                stage, checkpoint_id, "SATISFIED",
                f"Alert successfully generated for rule {rule_id or expected_rule_id}.",
                available_ids,
                {"rule_id": rule_id or expected_rule_id},
            )
        else:
            return StageEvaluation(
                stage, checkpoint_id, "VIOLATED",
                f"Alert was not generated for expected rule {expected_rule_id}.",
                available_ids,
                {"expected_rule_id": expected_rule_id},
            )

    elif stage == PipelineStage.DELIVERY_VISIBILITY:
        alert_received = p.get("alert_received")
        dest = p.get("destination") or spec.get("expected_destination") or "configured destination"
        if alert_received is True:
            return StageEvaluation(
                stage, checkpoint_id, "SATISFIED",
                f"Alert successfully received at destination {dest}.",
                available_ids,
                {"destination": dest},
            )
        elif alert_received is False:
            return StageEvaluation(
                stage, checkpoint_id, "VIOLATED",
                f"Alert was not received at destination {dest}.",
                available_ids,
                {"destination": dest},
            )
        else:
            return StageEvaluation(
                stage, checkpoint_id, "MISSING",
                f"Delivery checkpoint {checkpoint_id} could not be queried.",
                available_ids,
                {"destination": dest},
            )

    return StageEvaluation(stage, checkpoint_id, "MISSING", "Unknown checkpoint logic.", available_ids, {})


def diagnose(
    expectation_spec: Dict[str, Any],
    evidence_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Execute deterministic 4-step SIEM detection diagnosis.
    
    Returns:
        {
            "stage_results": [ {stage, status, reason, evidence_ids}, ... ],
            "diagnosis": {
                "outcome": FAILURE_LOCALIZED | HEALTHY | UNDETERMINED,
                "failure_stage": Optional[str],
                "reason": str,
                "confidence_label": str,
                "evidence_refs": List[str],
                "limitations": List[str],
                "remediation": Dict[str, Any],
            }
        }
    """
    # Group evidence records by checkpoint / stage
    by_stage: Dict[PipelineStage, List[Dict[str, Any]]] = {s: [] for s in STAGE_ORDER}
    for r in evidence_records:
        st_val = r.get("stage")
        for st in STAGE_ORDER:
            if st.value == st_val:
                by_stage[st].append(r)
                break

    # Step 1: Per-stage raw evaluations
    raw_evals: Dict[PipelineStage, StageEvaluation] = {}
    for stage in STAGE_ORDER:
        chk_id = STAGE_CHECKPOINTS[stage]
        st_records = by_stage[stage]
        raw_evals[stage] = evaluate_checkpoint(stage, chk_id, expectation_spec, st_records)

    # Step 2: Cross-stage consistency check
    # If stage k is SATISFIED while earlier stage j < k is VIOLATED, mark stage j CONFLICTING.
    for k_idx in range(len(STAGE_ORDER)):
        k_stage = STAGE_ORDER[k_idx]
        if raw_evals[k_stage].outcome == "SATISFIED":
            for j_idx in range(k_idx):
                j_stage = STAGE_ORDER[j_idx]
                if raw_evals[j_stage].outcome == "VIOLATED":
                    raw_evals[j_stage].outcome = "CONFLICTING"
                    raw_evals[j_stage].reason = (
                        f"Cross-stage conflict: downstream stage {k_stage.value} was satisfied, "
                        f"contradicting observed violation at {j_stage.value}."
                    )

    # Step 3: Assign statuses in pipeline order
    final_stage_results: List[Dict[str, Any]] = []
    failed_upstream_stage: Optional[PipelineStage] = None
    has_unconfirmed_prerequisite = False
    failure_stage: Optional[PipelineStage] = None

    for stage in STAGE_ORDER:
        evaluation = raw_evals[stage]
        st_name = stage.value

        if failed_upstream_stage is not None:
            # Rule a: any earlier stage FAIL -> NOT REACHED
            final_status = StageStatus.NOT_REACHED.value
            reason = f"Prerequisite stage {failed_upstream_stage.value} failed."
        elif evaluation.outcome in ("MISSING", "CONFLICTING"):
            # Rule b: MISSING or CONFLICTING -> UNKNOWN
            final_status = StageStatus.UNKNOWN.value
            reason = evaluation.reason
            has_unconfirmed_prerequisite = True
        elif evaluation.outcome == "SATISFIED":
            # Rule c: SATISFIED -> PASS
            final_status = StageStatus.PASS.value
            reason = evaluation.reason
        elif evaluation.outcome == "VIOLATED":
            # Rule d: VIOLATED -> FAIL only if ALL earlier stages are PASS; otherwise UNKNOWN
            if not has_unconfirmed_prerequisite and failed_upstream_stage is None:
                final_status = StageStatus.FAIL.value
                reason = evaluation.reason
                failed_upstream_stage = stage
                if failure_stage is None:
                    failure_stage = stage
            else:
                final_status = StageStatus.UNKNOWN.value
                reason = f"Violation observed at {st_name} but prerequisite stage unconfirmed; cannot be attributed."
                has_unconfirmed_prerequisite = True
        else:
            final_status = StageStatus.UNKNOWN.value
            reason = "Indeterminate stage status."
            has_unconfirmed_prerequisite = True

        final_stage_results.append({
            "stage": st_name,
            "status": final_status,
            "reason": reason,
            "evidence_ids": evaluation.evidence_ids,
        })

    # Step 4: Outcome determination
    fail_stages = [res for res in final_stage_results if res["status"] == StageStatus.FAIL.value]
    unknown_stages = [s for s in STAGE_ORDER if any(res["stage"] == s.value and res["status"] == StageStatus.UNKNOWN.value for res in final_stage_results)]
    not_reached_stages = [s for s in STAGE_ORDER if any(res["stage"] == s.value and res["status"] == StageStatus.NOT_REACHED.value for res in final_stage_results)]

    # Collect source labels to note synthetic data in limitations
    has_synthetic = any(r.get("source_label") == "SYNTHETIC" for r in evidence_records)
    limitations: List[str] = []
    if unknown_stages:
        limitations.append(f"Unconfirmed stages: {', '.join(s.value for s in unknown_stages)}.")
    if not_reached_stages:
        limitations.append(f"Not reached downstream stages: {', '.join(s.value for s in not_reached_stages)}.")
    if has_synthetic:
        limitations.append("Analysis evaluated on synthetic checkpoint telemetry.")

    if len(fail_stages) == 1:
        outcome = DiagnosticOutcome.FAILURE_LOCALIZED
        failed_stage_name = fail_stages[0]["stage"]
        failure_stage_enum = PipelineStage(failed_stage_name)
        diag_reason = (
            f"Earliest evidence-supported failure localized to stage '{failed_stage_name}': "
            f"{fail_stages[0]['reason']}"
        )
        conf_label = ConfidenceLabel.SUPPORTED_BY_EVIDENCE.value
        evidence_refs = fail_stages[0]["evidence_ids"]
    elif all(res["status"] == StageStatus.PASS.value for res in final_stage_results):
        outcome = DiagnosticOutcome.HEALTHY
        failure_stage_enum = None
        diag_reason = "All pipeline stages passed verification. Expected detection was delivered."
        conf_label = ConfidenceLabel.NO_FAILURE_FOUND.value
        evidence_refs = [eid for res in final_stage_results for eid in res["evidence_ids"]]
    else:
        outcome = DiagnosticOutcome.UNDETERMINED
        failure_stage_enum = None
        conf_label = ConfidenceLabel.UNDETERMINED.value
        missing_ckpts = [STAGE_CHECKPOINTS[s] for s in unknown_stages]
        diag_reason = (
            f"Diagnosis undetermined due to incomplete or conflicting evidence across stages: "
            f"[{', '.join(s.value for s in unknown_stages)}]. "
            f"Additional checkpoint evidence needed for: {missing_ckpts}."
        )
        evidence_refs = [eid for res in final_stage_results for eid in res["evidence_ids"]]

    # Stage details for remediation
    stage_details = {s.value: raw_evals[s].details for s in STAGE_ORDER}
    remediation_info = generate_remediation(
        outcome=outcome,
        failure_stage=failure_stage_enum,
        stage_details=stage_details,
        unknown_stages=unknown_stages,
    )

    diagnosis = {
        "outcome": outcome.value,
        "failure_stage": failure_stage_enum.value if failure_stage_enum else None,
        "reason": diag_reason,
        "confidence_label": conf_label,
        "evidence_refs": evidence_refs,
        "limitations": limitations,
        "remediation": remediation_info,
    }

    return {
        "stage_results": final_stage_results,
        "diagnosis": diagnosis,
    }
