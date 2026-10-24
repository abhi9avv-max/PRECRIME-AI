"""Compact 12 scenario cases (6 development + 6 held-out).

Does NOT include ground truth.
"""
from .builder import make_case, make_rec

def build_all_scenarios() -> list:
    std_spec = {
        "rule_id": "R-100",
        "required_fields": ["user_name", "src_ip", "event_id"],
        "expected_destination": "siem_dashboard",
        "checkpoints": {
            "EG-1": {"event_id": "4625"},
            "COL-1": {"agent_id": "agent-01"},
            "PAR-1": {"required_fields": ["user_name", "src_ip", "event_id"]},
            "RUL-1": {
                "rule_id": "R-100",
                "rule_conditions": [
                    {"field": "event_id", "op": "eq", "value": "4625"},
                    {"field": "outcome", "op": "eq", "value": "failure"},
                ],
            },
            "ALT-1": {"rule_id": "R-100"},
            "DEL-1": {"destination": "siem_dashboard"},
        },
    }

    healthy_records = lambda prefix: [
        make_rec(f"{prefix}_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625", "source": "srv-01"}),
        make_rec(f"{prefix}_col", "collection", "COL-1", {"event_received": True, "agent_id": "agent-01"}),
        make_rec(f"{prefix}_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"user_name": "alice", "src_ip": "10.0.0.1", "event_id": "4625"}}),
        make_rec(f"{prefix}_rul", "rule_evaluation", "RUL-1", {"matched": True, "rule_id": "R-100", "decoded_fields": {"event_id": "4625", "outcome": "failure"}}),
        make_rec(f"{prefix}_alt", "alert_generation", "ALT-1", {"alert_found": True, "rule_id": "R-100"}),
        make_rec(f"{prefix}_del", "delivery_visibility", "DEL-1", {"alert_received": True, "destination": "siem_dashboard"}),
    ]

    scenarios = []

    # 1a (dev) collection failure
    c1a_init = [
        make_rec("1a_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625", "source": "host-01"}),
        make_rec("1a_col", "collection", "COL-1", {"event_received": False, "agent_status": "active", "agent_id": "agent-01"}),
        make_rec("1a_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("collection_failure.a", "collection_failure", "a", "development",
        "Collection agent dropped event", "Agent is active but event was dropped before collector receipt",
        std_spec, c1a_init, healthy_records("1a_fix")))

    # 1b (held-out) collection failure
    c1b_init = [
        make_rec("1b_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625", "source": "srv-win-02"}),
        make_rec("1b_col", "collection", "COL-1", {"event_received": False, "agent_status": "disconnected", "agent_id": "agent-win-02"}),
        make_rec("1b_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("collection_failure.b", "collection_failure", "b", "held-out",
        "Disconnected agent collection failure", "Collector unreachable from disconnected agent endpoint",
        std_spec, c1b_init, healthy_records("1b_fix")))

    # 2a (dev) parsing failure
    c2a_init = [
        make_rec("2a_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("2a_col", "collection", "COL-1", {"event_received": True, "agent_id": "agent-01"}),
        make_rec("2a_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"src_ip": "10.0.0.5", "event_id": "4625"}}),
        make_rec("2a_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("parsing_failure.a", "parsing_failure", "a", "development",
        "Missing user_name extracted field", "Log decoder skipped user_name field parsing",
        std_spec, c2a_init, healthy_records("2a_fix")))

    # 2b (held-out) parsing failure (unresolved retest)
    c2b_init = [
        make_rec("2b_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("2b_col", "collection", "COL-1", {"event_received": True, "agent_id": "agent-02"}),
        make_rec("2b_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"event_id": "4625", "user_name": ""}}),
        make_rec("2b_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    c2b_postfix = [
        make_rec("2b_fix_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("2b_fix_col", "collection", "COL-1", {"event_received": True, "agent_id": "agent-02"}),
        make_rec("2b_fix_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"event_id": "4625", "user_name": "svc_account"}}), # src_ip still missing!
        make_rec("2b_fix_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("parsing_failure.b", "parsing_failure", "b", "held-out",
        "Empty user_name and missing src_ip", "Parser partially failed extraction and fix was incomplete",
        std_spec, c2b_init, c2b_postfix))

    # 3a (dev) rule mismatch
    c3a_init = [
        make_rec("3a_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("3a_col", "collection", "COL-1", {"event_received": True}),
        make_rec("3a_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"user_name": "bob", "src_ip": "10.0.0.2", "event_id": "4625"}}),
        make_rec("3a_rul", "rule_evaluation", "RUL-1", {
            "matched": False, "rule_id": "R-100",
            "decoded_fields": {"event_id": "4625", "outcome": "failed"},
            "rule_conditions": [{"field": "event_id", "op": "eq", "value": "4625"}, {"field": "outcome", "op": "eq", "value": "failure"}],
        }),
        make_rec("3a_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("rule_mismatch.a", "rule_mismatch", "a", "development",
        "Outcome value mismatch in rule condition", "Rule expected 'failure' but event contained 'failed'",
        std_spec, c3a_init, healthy_records("3a_fix")))

    # 3b (held-out) rule mismatch
    spec_3b = {
        "rule_id": "R-200",
        "required_fields": ["status", "event_id"],
        "expected_destination": "siem_dashboard",
        "checkpoints": {
            "EG-1": {"event_id": "AUTH-01"},
            "COL-1": {"agent_id": "agent-03"},
            "PAR-1": {"required_fields": ["status", "event_id"]},
            "RUL-1": {
                "rule_id": "R-200",
                "rule_conditions": [{"field": "status", "op": "in", "value": ["failure", "denied"]}],
            },
            "ALT-1": {"rule_id": "R-200"},
            "DEL-1": {"destination": "siem_dashboard"},
        },
    }
    c3b_init = [
        make_rec("3b_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "AUTH-01"}),
        make_rec("3b_col", "collection", "COL-1", {"event_received": True}),
        make_rec("3b_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"status": "rejected", "event_id": "AUTH-01"}}),
        make_rec("3b_rul", "rule_evaluation", "RUL-1", {
            "matched": False, "rule_id": "R-200",
            "decoded_fields": {"status": "rejected", "event_id": "AUTH-01"},
            "rule_conditions": [{"field": "status", "op": "in", "value": ["failure", "denied"]}],
        }),
        make_rec("3b_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    c3b_postfix = [
        make_rec("3b_fix_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "AUTH-01"}),
        make_rec("3b_fix_col", "collection", "COL-1", {"event_received": True}),
        make_rec("3b_fix_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"status": "denied", "event_id": "AUTH-01"}}),
        make_rec("3b_fix_rul", "rule_evaluation", "RUL-1", {"matched": True, "rule_id": "R-200", "decoded_fields": {"status": "denied", "event_id": "AUTH-01"}}),
        make_rec("3b_fix_alt", "alert_generation", "ALT-1", {"alert_found": True, "rule_id": "R-200"}),
        make_rec("3b_fix_del", "delivery_visibility", "DEL-1", {"alert_received": True, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("rule_mismatch.b", "rule_mismatch", "b", "held-out",
        "Disallowed status set mismatch", "Observed status 'rejected' not in ['failure', 'denied']",
        spec_3b, c3b_init, c3b_postfix))

    # 4a (dev) delivery failure
    c4a_init = [
        make_rec("4a_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("4a_col", "collection", "COL-1", {"event_received": True}),
        make_rec("4a_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"user_name": "charlie", "src_ip": "10.0.0.3", "event_id": "4625"}}),
        make_rec("4a_rul", "rule_evaluation", "RUL-1", {"matched": True, "rule_id": "R-100", "decoded_fields": {"event_id": "4625", "outcome": "failure"}}),
        make_rec("4a_alt", "alert_generation", "ALT-1", {"alert_found": True, "rule_id": "R-100"}),
        make_rec("4a_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("delivery_failure.a", "delivery_failure", "a", "development",
        "Dashboard delivery dropped alert", "Pipeline triggered alert but delivery to dashboard failed",
        std_spec, c4a_init, healthy_records("4a_fix")))

    # 4b (held-out) delivery failure (post-fix unavailable -> undetermined)
    spec_4b = dict(std_spec)
    spec_4b["expected_destination"] = "soc_webhook"
    c4b_init = [
        make_rec("4b_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("4b_col", "collection", "COL-1", {"event_received": True}),
        make_rec("4b_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"user_name": "david", "src_ip": "10.0.0.4", "event_id": "4625"}}),
        make_rec("4b_rul", "rule_evaluation", "RUL-1", {"matched": True, "rule_id": "R-100", "decoded_fields": {"event_id": "4625", "outcome": "failure"}}),
        make_rec("4b_alt", "alert_generation", "ALT-1", {"alert_found": True, "rule_id": "R-100"}),
        make_rec("4b_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "soc_webhook"}),
    ]
    c4b_postfix = [
        make_rec("4b_fix_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("4b_fix_col", "collection", "COL-1", {"event_received": True}),
        make_rec("4b_fix_par", "parsing", "PAR-1", {"raw_event_present": True, "extracted_fields": {"user_name": "david", "src_ip": "10.0.0.4", "event_id": "4625"}}),
        make_rec("4b_fix_rul", "rule_evaluation", "RUL-1", {"matched": True, "rule_id": "R-100", "decoded_fields": {"event_id": "4625", "outcome": "failure"}}),
        make_rec("4b_fix_alt", "alert_generation", "ALT-1", {"alert_found": True, "rule_id": "R-100"}),
        make_rec("4b_fix_del", "delivery_visibility", "DEL-1", {"reason": "Webhook connection timeout"}, avail="UNAVAILABLE"),
    ]
    scenarios.append(make_case("delivery_failure.b", "delivery_failure", "b", "held-out",
        "Webhook delivery failure with unreachable retest", "Target webhook endpoint unreachable during retest check",
        spec_4b, c4b_init, c4b_postfix))

    # 5a (dev) healthy pipeline
    scenarios.append(make_case("healthy_pipeline.a", "healthy_pipeline", "a", "development",
        "Nominal healthy SIEM detection", "Baseline healthy pipeline with all stages fully verified",
        std_spec, healthy_records("5a_init"), []))

    # 5b (held-out) healthy pipeline
    scenarios.append(make_case("healthy_pipeline.b", "healthy_pipeline", "b", "held-out",
        "Nominal healthy pipeline variant", "Second baseline healthy pipeline scenario",
        std_spec, healthy_records("5b_init"), []))

    # 6a (dev) insufficient evidence
    c6a_init = [
        make_rec("6a_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("6a_col", "collection", "COL-1", {"reason": "Collector API unreachable", "forwarded": True}, avail="UNAVAILABLE"),
        make_rec("6a_del", "delivery_visibility", "DEL-1", {"alert_received": False, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("insufficient_evidence.a", "insufficient_evidence", "a", "development",
        "Gaps in collection telemetry", "Collector checkpoint is unavailable with unconfirmed middle stages",
        std_spec, c6a_init, []))

    # 6b (held-out) conflicting evidence
    c6b_init = [
        make_rec("6b_eg", "event_generation", "EG-1", {"event_found": True, "event_id": "4625"}),
        make_rec("6b_col_1", "collection", "COL-1", {"event_received": True, "forwarded": True, "reporter": "agent"}),
        make_rec("6b_col_2", "collection", "COL-1", {"event_received": False, "reporter": "receiver"}),
        make_rec("6b_del", "delivery_visibility", "DEL-1", {"alert_received": True, "destination": "siem_dashboard"}),
    ]
    scenarios.append(make_case("insufficient_evidence.b", "insufficient_evidence", "b", "held-out",
        "Contradictory collection checkpoint reports", "Disagreement between agent forwarded status and receiver log",
        std_spec, c6b_init, []))

    return scenarios

ALL_SCENARIOS = build_all_scenarios()
SCENARIOS_BY_ID = {s["id"]: s for s in ALL_SCENARIOS}
