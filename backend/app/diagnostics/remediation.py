"""Deterministic remediation generation and evidence guidance."""
from typing import Dict, Any, List, Optional
from .stages import PipelineStage, DiagnosticOutcome

def generate_remediation(
    outcome: DiagnosticOutcome,
    failure_stage: Optional[PipelineStage],
    stage_details: Dict[str, Any],
    unknown_stages: List[PipelineStage],
) -> Dict[str, Any]:
    """Generate simulated remediation or next evidence requirements."""
    if outcome != DiagnosticOutcome.FAILURE_LOCALIZED or not failure_stage:
        # No remediation for healthy or undetermined states
        needed_evidence = []
        for stage in unknown_stages:
            needed_evidence.append(f"Checkpoint evidence for {stage.value} to confirm stage integrity")
        if not unknown_stages and outcome == DiagnosticOutcome.HEALTHY:
            needed_evidence = ["No additional evidence required; all checkpoints verified."]
        return {
            "proposed_change": None,
            "simulated_label": "SIMULATED: no real system is modified",
            "evidence_to_collect_next": needed_evidence,
        }

    details = stage_details.get(failure_stage.value, {})
    proposed_change = ""

    if failure_stage == PipelineStage.EVENT_GENERATION:
        source = details.get("source", "designated host")
        proposed_change = (
            f"SIMULATED: no real system is modified. "
            f"Verify event logging audit policy and audit daemon status on {source}."
        )
    elif failure_stage == PipelineStage.COLLECTION:
        agent_id = details.get("agent_id") or details.get("source", "target agent/source")
        proposed_change = (
            f"SIMULATED: no real system is modified. "
            f"Restore log forwarding and restart agent connection for source: {agent_id}."
        )
    elif failure_stage == PipelineStage.PARSING:
        missing_fields = details.get("missing_fields", [])
        fields_str = ", ".join(missing_fields) if missing_fields else "required fields"
        proposed_change = (
            f"SIMULATED: no real system is modified. "
            f"Update the decoder pattern to extract missing fields: [{fields_str}]."
        )
    elif failure_stage == PipelineStage.RULE_EVALUATION:
        condition_info = details.get("failed_condition", "rule condition")
        observed_val = details.get("observed_value")
        field_name = details.get("field_name")
        rule_id = details.get("rule_id", "specified rule")
        if field_name and observed_val is not None:
            proposed_change = (
                f"SIMULATED: no real system is modified. "
                f"In rule {rule_id}, align condition on '{field_name}' to account for observed value '{observed_val}'."
            )
        else:
            proposed_change = (
                f"SIMULATED: no real system is modified. "
                f"In rule {rule_id}, align condition ({condition_info}) with observed telemetry."
            )
    elif failure_stage == PipelineStage.ALERT_GENERATION:
        rule_id = details.get("rule_id", "triggered rule")
        proposed_change = (
            f"SIMULATED: no real system is modified. "
            f"Verify alert threshold and notification engine queue for rule: {rule_id}."
        )
    elif failure_stage == PipelineStage.DELIVERY_VISIBILITY:
        dest = details.get("destination", "configured SIEM destination/webhook")
        proposed_change = (
            f"SIMULATED: no real system is modified. "
            f"Restore webhook or API delivery forwarding to destination: {dest}."
        )

    return {
        "proposed_change": proposed_change,
        "simulated_label": "SIMULATED: no real system is modified",
        "evidence_to_collect_next": [],
    }
