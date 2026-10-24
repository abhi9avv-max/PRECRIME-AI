"""Comprehensive integration tests for PRECRIME AI FastAPI endpoints and state machine."""
import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app, seed_scenarios
from app.models import Investigation, TestRun, AuditEvent, EvaluationResult
from app.evaluation.metrics import slice_metrics

# Use isolated in-memory or temporary SQLite database for tests
TEST_DB_URL = "sqlite:///./test_precrime.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_scenarios(db)
    db.close()
    yield
    test_engine.dispose()
    if os.path.exists("./test_precrime.db"):
        try:
            os.remove("./test_precrime.db")
        except Exception:
            pass


@pytest.fixture
def client():
    return TestClient(app)


def test_ground_truth_separation(client):
    """GET /api/scenarios and /api/runs/{id}/evidence must never expose ground truth."""
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 12
    for s in scenarios:
        assert "ground_truth" not in s
        assert "expected_outcome" not in s
        assert "expected_retest_class" not in s


def test_metrics_empty_state_not_zeros(client):
    """When no evaluation suite has been run, /api/metrics returns explicit empty state, not zeros."""
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["has_data"] is False
    assert data["metrics"] is None
    assert "No evaluation has been run yet" in data["message"]


def test_full_investigation_journey_and_state_machine(client):
    """End-to-end journey walking: create -> run -> review -> approve -> retest -> report."""
    # 1. Create investigation
    create_res = client.post("/api/investigations", json={"title": "Test Auth Investigation", "source_mode": "DEMO"})
    assert create_res.status_code == 201
    inv = create_res.json()
    inv_id = inv["id"]
    assert inv["status"] == "CREATED"

    # 2. Run scenario (parsing_failure.a)
    run_res = client.post(f"/api/investigations/{inv_id}/runs", json={"scenario_id": "parsing_failure.a"})
    assert run_res.status_code == 201
    run_data = run_res.json()
    run_id = run_data["run_id"]
    diag = run_data["diagnosis"]
    assert diag["outcome"] == "FAILURE_LOCALIZED"
    assert diag["failure_stage"] == "parsing"
    assert len(diag["evidence_refs"]) > 0

    # 3. Check evidence endpoint does not leak ground truth
    ev_res = client.get(f"/api/runs/{run_id}/evidence")
    assert ev_res.status_code == 200
    evidence = ev_res.json()
    assert len(evidence) >= 4
    for e in evidence:
        assert "ground_truth" not in e

    # Check investigation details
    inv_detail = client.get(f"/api/investigations/{inv_id}").json()
    assert inv_detail["status"] == "RUN_COMPLETED"
    diag_id = inv_detail["runs"][0]["diagnosis"]["id"]
    rem_id = inv_detail["runs"][0]["remediation"]["id"]

    # 4. State Machine 409 Checks:
    # (a) Approval before review ACCEPT -> 409
    app_fail = client.post(f"/api/remediations/{rem_id}/approve", json={"decision": "APPROVE", "reviewer": "Jane Doe"})
    assert app_fail.status_code == 409
    assert "cannot be approved without a recorded diagnosis ACCEPT" in app_fail.json()["detail"]["message"]

    # (b) Retest before approval -> 409
    ret_fail = client.post(f"/api/runs/{run_id}/retest")
    assert ret_fail.status_code == 409
    assert "Remediation must be APPROVED" in ret_fail.json()["detail"]["message"]

    # (c) Empty reviewer name -> 422
    rev_empty = client.post(f"/api/diagnoses/{diag_id}/review", json={"decision": "ACCEPT", "reviewer": "   "})
    assert rev_empty.status_code == 422

    # 5. Record Diagnosis Review
    rev_res = client.post(f"/api/diagnoses/{diag_id}/review", json={"decision": "ACCEPT", "reviewer": "Jane Doe", "note": "Verified parsing gap"})
    assert rev_res.status_code == 200
    assert rev_res.json()["review_status"] == "ACCEPT"

    # 6. Approve Remediation
    app_res = client.post(f"/api/remediations/{rem_id}/approve", json={"decision": "APPROVE", "reviewer": "Jane Doe", "note": "Approved decoder fix"})
    assert app_res.status_code == 200
    assert app_res.json()["approval_status"] == "APPROVED"
    assert app_res.json()["execution_status"] == "SIMULATED_APPLIED"

    # 7. Execute Retest
    retest_res = client.post(f"/api/runs/{run_id}/retest")
    assert retest_res.status_code == 200
    ret_data = retest_res.json()
    assert ret_data["final_result"] == "VERIFIED"
    assert ret_data["parent_run_id"] == run_id
    assert ret_data["retest_run_id"] != run_id

    # 8. Report Export (JSON and Markdown)
    rep_json = client.get(f"/api/investigations/{inv_id}/report?format=json")
    assert rep_json.status_code == 200
    j_data = rep_json.json()
    assert j_data["status"] == "RETEST_VERIFIED"
    assert len(j_data["runs"]) == 2
    assert j_data["retest_comparison"]["recovery_result"] == "VERIFIED"

    rep_md = client.get(f"/api/investigations/{inv_id}/report?format=md")
    assert rep_md.status_code == 200
    assert "# PRECRIME AI - Investigation Report" in rep_md.text
    assert "RC1" in rep_md.text


def test_healthy_scenario_retest_rejected(client):
    """Healthy pipelines require no remediation and retest returns 409."""
    inv = client.post("/api/investigations", json={"title": "Healthy Test", "source_mode": "DEMO"}).json()
    run = client.post(f"/api/investigations/{inv['id']}/runs", json={"scenario_id": "healthy_pipeline.a"}).json()
    assert run["diagnosis"]["outcome"] == "HEALTHY"

    ret_res = client.post(f"/api/runs/{run['run_id']}/retest")
    assert ret_res.status_code == 409
    assert "Healthy pipelines require no remediation or retest" in ret_res.json()["detail"]["message"]


def test_injected_adapter_exception_persists_error_run(client):
    """An exception during run execution persists an ERROR run and writes an audit event."""
    inv = client.post("/api/investigations", json={"title": "Exception Test", "source_mode": "DEMO"}).json()
    with patch("app.api.runs.fetch_demo_evidence", side_effect=RuntimeError("Simulated pipeline failure")):
        resp = client.post(f"/api/investigations/{inv['id']}/runs", json={"scenario_id": "parsing_failure.a"})
        assert resp.status_code == 500

    inv_detail = client.get(f"/api/investigations/{inv['id']}").json()
    assert inv_detail["status"] == "RUN_FAILED"
    assert len(inv_detail["runs"]) == 1
    assert inv_detail["runs"][0]["status"] == "ERROR"
    assert "Simulated pipeline failure" in inv_detail["runs"][0]["error"]
    actions = [a["action"] for a in inv_detail["audit_events"]]
    assert "RUN_FAILED" in actions


def test_evaluation_run_and_metrics_verification(client):
    """POST /api/evaluation/run executes all 12 cases and matches independently computed metrics."""
    eval_res = client.post("/api/evaluation/run")
    assert eval_res.status_code == 200
    res_data = eval_res.json()
    assert res_data["cases_evaluated"] == 12

    # Query metrics endpoint
    metrics_res = client.get("/api/metrics")
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["has_data"] is True
    comb = metrics["combined"]

    # Verify failure localization accuracy
    assert comb["failure_localization_accuracy"]["numerator"] == 8
    assert comb["failure_localization_accuracy"]["denominator"] == 8
    assert comb["failure_localization_accuracy"]["value"] == 100.0

    # Verify false attribution rate
    assert comb["false_attribution_rate"]["numerator"] == 0
    assert comb["false_attribution_rate"]["value"] == 0.0

    # Verify abstentions
    assert comb["abstention_quality"]["supported_abstention"]["numerator"] == 2
    assert comb["abstention_quality"]["supported_abstention"]["denominator"] == 2
    assert comb["abstention_quality"]["unnecessary_abstention"]["numerator"] == 0


def test_wazuh_integration_test(client):
    """Wazuh test returns connected=False with clear reason when unconfigured; handles mocked success."""
    # 1. Unconfigured
    with patch.dict(os.environ, {"WAZUH_API_URL": "", "WAZUH_API_USER": "", "WAZUH_API_PASSWORD": ""}, clear=True):
        resp = client.post("/api/integrations/wazuh/test")
        assert resp.status_code == 200
        assert resp.json()["connected"] is False
        assert "Missing environment variables" in resp.json()["message"]

    # 2. Mocked successful authentication
    with patch("app.adapters.wazuh.httpx.Client") as mock_client_cls:
        mock_instance = mock_client_cls.return_value.__enter__.return_value
        mock_instance.post.return_value.status_code = 200
        with patch.dict(os.environ, {
            "WAZUH_API_URL": "https://wazuh.mock.local:55000",
            "WAZUH_API_USER": "admin",
            "WAZUH_API_PASSWORD": "password123",
            "WAZUH_VERIFY_TLS": "true",
        }):
            resp = client.post("/api/integrations/wazuh/test")
            assert resp.status_code == 200
            assert resp.json()["connected"] is True
            assert "Successfully authenticated" in resp.json()["message"]
