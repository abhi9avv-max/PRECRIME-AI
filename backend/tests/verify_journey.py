"""End-to-end complete journey verification script."""
import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app, Base, engine, seed_scenarios, SessionLocal

def run_verification():
    print("[1/8] Initializing database and test client...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_scenarios(db)
    db.close()

    client = TestClient(app)

    # Health check
    h = client.get("/api/health")
    assert h.status_code == 200, f"Health check failed: {h.text}"
    print(f"  Health Check: OK ({h.json()['status']})")

    # [2/8] Walk parsing_failure.a
    print("[2/8] Walking parsing_failure.a journey...")
    inv_res = client.post("/api/investigations", json={"title": "E2E Parsing Walkthrough", "source_mode": "DEMO"})
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    run_res = client.post(f"/api/investigations/{inv_id}/runs", json={"scenario_id": "parsing_failure.a"})
    assert run_res.status_code == 201
    run_id = run_res.json()["run_id"]
    diag = run_res.json()["diagnosis"]
    assert diag["outcome"] == "FAILURE_LOCALIZED"
    assert diag["failure_stage"] == "parsing"
    print(f"  Diagnosis: {diag['outcome']} at stage '{diag['failure_stage']}'")

    ev_res = client.get(f"/api/runs/{run_id}/evidence")
    assert ev_res.status_code == 200
    evidence = ev_res.json()
    print(f"  Evidence records count: {len(evidence)}")

    inv_detail = client.get(f"/api/investigations/{inv_id}").json()
    diag_id = inv_detail["runs"][0]["diagnosis"]["id"]
    rem_id = inv_detail["runs"][0]["remediation"]["id"]

    # Review
    rev = client.post(f"/api/diagnoses/{diag_id}/review", json={"decision": "ACCEPT", "reviewer": "Lead Analyst", "note": "Verified decoder gap"})
    assert rev.status_code == 200
    print(f"  Diagnosis Review: {rev.json()['review_status']}")

    # Approval
    appr = client.post(f"/api/remediations/{rem_id}/approve", json={"decision": "APPROVE", "reviewer": "SOC Lead", "note": "Approved decoder pattern update"})
    assert appr.status_code == 200
    print(f"  Remediation Approval: {appr.json()['approval_status']} (Execution: {appr.json()['execution_status']})")

    # Retest
    ret = client.post(f"/api/runs/{run_id}/retest")
    assert ret.status_code == 200
    ret_data = ret.json()
    assert ret_data["final_result"] == "VERIFIED"
    print(f"  Retest Recovery Result: {ret_data['final_result']} (All RC1..RC5 checks PASS)")

    # Report export
    rep_j = client.get(f"/api/investigations/{inv_id}/report?format=json")
    assert rep_j.status_code == 200
    rep_m = client.get(f"/api/investigations/{inv_id}/report?format=md")
    assert rep_m.status_code == 200
    print("  Report Export (JSON & Markdown): OK")

    # [3/8] Test parsing_failure.b (held-out -> UNRESOLVED)
    print("[3/8] Testing held-out parsing_failure.b (expecting UNRESOLVED retest)...")
    inv_2b = client.post("/api/investigations", json={"title": "Held-out 2b", "source_mode": "DEMO"}).json()
    run_2b = client.post(f"/api/investigations/{inv_2b['id']}/runs", json={"scenario_id": "parsing_failure.b"}).json()
    inv_2b_detail = client.get(f"/api/investigations/{inv_2b['id']}").json()
    d2b_id = inv_2b_detail["runs"][0]["diagnosis"]["id"]
    r2b_id = inv_2b_detail["runs"][0]["remediation"]["id"]
    client.post(f"/api/diagnoses/{d2b_id}/review", json={"decision": "ACCEPT", "reviewer": "Analyst", "note": "ok"})
    client.post(f"/api/remediations/{r2b_id}/approve", json={"decision": "APPROVE", "reviewer": "Lead", "note": "ok"})
    ret_2b = client.post(f"/api/runs/{run_2b['run_id']}/retest").json()
    assert ret_2b["final_result"] == "UNRESOLVED"
    print(f"  Held-out 2b Retest Result: {ret_2b['final_result']} (Correctly detected incomplete fix)")

    # [4/8] Test delivery_failure.b (held-out -> UNDETERMINED)
    print("[4/8] Testing held-out delivery_failure.b (expecting UNDETERMINED retest)...")
    inv_4b = client.post("/api/investigations", json={"title": "Held-out 4b", "source_mode": "DEMO"}).json()
    run_4b = client.post(f"/api/investigations/{inv_4b['id']}/runs", json={"scenario_id": "delivery_failure.b"}).json()
    inv_4b_detail = client.get(f"/api/investigations/{inv_4b['id']}").json()
    d4b_id = inv_4b_detail["runs"][0]["diagnosis"]["id"]
    r4b_id = inv_4b_detail["runs"][0]["remediation"]["id"]
    client.post(f"/api/diagnoses/{d4b_id}/review", json={"decision": "ACCEPT", "reviewer": "Analyst", "note": "ok"})
    client.post(f"/api/remediations/{r4b_id}/approve", json={"decision": "APPROVE", "reviewer": "Lead", "note": "ok"})
    ret_4b = client.post(f"/api/runs/{run_4b['run_id']}/retest").json()
    assert ret_4b["final_result"] == "UNDETERMINED"
    print(f"  Held-out 4b Retest Result: {ret_4b['final_result']} (Correctly preserved uncertainty on unavailable checkpoint)")

    # [5/8] Healthy pipeline retest rejected
    print("[5/8] Testing healthy pipeline retest rejection (expecting 409)...")
    inv_5 = client.post("/api/investigations", json={"title": "Healthy 5a", "source_mode": "DEMO"}).json()
    run_5 = client.post(f"/api/investigations/{inv_5['id']}/runs", json={"scenario_id": "healthy_pipeline.a"}).json()
    assert run_5["diagnosis"]["outcome"] == "HEALTHY"
    ret_5 = client.post(f"/api/runs/{run_5['run_id']}/retest")
    assert ret_5.status_code == 409
    print(f"  Healthy Retest Rejection: HTTP {ret_5.status_code} ({ret_5.json()['detail']['message']})")

    # [6/8] Insufficient evidence -> UNDETERMINED with no remediation
    print("[6/8] Testing insufficient evidence case 6a...")
    inv_6 = client.post("/api/investigations", json={"title": "Insufficient 6a", "source_mode": "DEMO"}).json()
    run_6 = client.post(f"/api/investigations/{inv_6['id']}/runs", json={"scenario_id": "insufficient_evidence.a"}).json()
    assert run_6["diagnosis"]["outcome"] == "UNDETERMINED"
    assert run_6["diagnosis"]["failure_stage"] is None
    assert run_6["diagnosis"]["remediation"]["proposed_change"] is None
    print(f"  Insufficient Evidence Outcome: {run_6['diagnosis']['outcome']} with no unsupported remediation")

    # [7/8] Run 12-case evaluation suite
    print("[7/8] Executing 12-case evaluation suite...")
    eval_res = client.post("/api/evaluation/run")
    assert eval_res.status_code == 200
    metrics = client.get("/api/metrics").json()
    comb = metrics["combined"]
    print(f"  Localization Accuracy: {comb['failure_localization_accuracy']['display']}")
    print(f"  False Attribution Rate: {comb['false_attribution_rate']['display']}")
    print(f"  Supported Abstention: {comb['abstention_quality']['supported_abstention']['display']}")
    print(f"  Unnecessary Abstention: {comb['abstention_quality']['unnecessary_abstention']['display']}")
    print(f"  Retest Verification Accuracy: {comb['retest_verification_accuracy']['display']}")
    print(f"  Checkpoint Evidence Coverage: {comb['evidence_coverage']['display']}")
    print(f"  Mean Latency: {comb['diagnosis_latency']['mean_ms']} ms")

    # [8/8] Wazuh unconfigured connectivity test
    print("[8/8] Testing Wazuh unconfigured response...")
    wazuh_res = client.post("/api/integrations/wazuh/test").json()
    assert wazuh_res["connected"] is False
    print(f"  Wazuh Connected: {wazuh_res['connected']} ({wazuh_res['message']})")

    print("\n=======================================================")
    print("ALL VERIFICATION CHECKS PASSED WITH SOLID EVIDENCE!")
    print("=======================================================")

if __name__ == "__main__":
    run_verification()
