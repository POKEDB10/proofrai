import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

import backend.app.routes as routes_module
from backend.app.main import app
from backend.core.ledger.database import (
    DEFAULT_LEDGER_PATH,
    get_db,
    load_run,
    save_result,
    save_run,
)
from backend.core.models import CaseResult
from backend.core.suite.loader import load_suite

client = TestClient(app)


def _ensure_seed_run() -> None:
    conn = get_db(DEFAULT_LEDGER_PATH)
    if not load_run(conn, "run-01"):
        cases = load_suite()
        save_run(
            conn=conn,
            run_id="run-01",
            provider="gemini",
            target_model="gemini-3.5-flash-lite",
            judge_model="gemini-3.5-flash",
            temperature=0.0,
            suite_version="v1",
            control_config_hash="seed123456",
            controls_yaml="title: seed",
            created_at="2026-09-29T10:00:00Z",
        )
        for c in cases:
            base_res = CaseResult(
                case_id=c.id,
                variant="baseline",
                output_text="Candidate evaluation text",
                tool_calls=[],
                events=[],
                checks=[],
                verdict="pass",
                verdict_source="deterministic",
            )
            ctrl_res = CaseResult(
                case_id=c.id,
                variant="controlled",
                output_text="Refusal text",
                tool_calls=[],
                events=[],
                checks=[],
                verdict="pass",
                verdict_source="deterministic",
            )
            save_result(conn, "run-01", base_res)
            save_result(conn, "run-01", ctrl_res)
    conn.close()


def test_get_controls_route() -> None:
    resp = client.get("/api/controls")
    assert resp.status_code == 200
    controls = resp.json()
    assert isinstance(controls, list)
    assert len(controls) == 6
    first = controls[0]
    assert "id" in first
    assert "title" in first
    assert "enforcement_point" in first
    assert "status" in first


def test_patch_control_route() -> None:
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    shutil.copyfile("backend/data/control_library.yaml", tmp_path)
    orig_path = routes_module.CONTROL_LIBRARY_PATH
    routes_module.CONTROL_LIBRARY_PATH = tmp_path

    try:
        resp = client.patch("/api/controls/CTL-01", json={"status": "approved"})
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["id"] == "CTL-01"
        assert updated["status"] == "approved"

        bad_resp = client.patch("/api/controls/CTL-01", json={"status": "enabled"})
        assert bad_resp.status_code == 400
        err = bad_resp.json()
        assert "detail" in err
        assert "Fix:" in err["detail"]

        not_found = client.patch("/api/controls/CTL-999", json={"status": "approved"})
        assert not_found.status_code == 404
        err = not_found.json()
        assert "detail" in err
        assert "Fix:" in err["detail"]
    finally:
        routes_module.CONTROL_LIBRARY_PATH = orig_path
        tmp_path.unlink(missing_ok=True)


def test_runs_lifecycle_routes() -> None:
    _ensure_seed_run()
    resp = client.get("/api/runs/run-01")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["id"] == "run-01"
    assert summary["status"] == "completed"
    assert "progress" in summary
    assert summary["progress"]["current"] == 30
    assert "counts" in summary
    assert summary["counts"]["total_cases"] == 30
    assert summary["counts"]["attack_total"] == 16
    assert summary["counts"]["benign_total"] == 14
    assert "release_gate" in summary
    assert summary["release_gate"]["label"] in (
        "Unresolved risk",
        "Review required",
        "Ready for further testing",
    )

    # 2. Non-existent run
    not_found = client.get("/api/runs/run-nonexistent")
    assert not_found.status_code == 404
    assert "Fix:" in not_found.json()["detail"]

    # 3. Invalid payload type triggers 422 with Fix instruction
    bad_type = client.post("/api/runs", json={"no_cache": "not_a_bool"})
    assert bad_type.status_code == 422
    assert "Fix:" in bad_type.json()["detail"]



def test_get_run_results_route() -> None:
    _ensure_seed_run()
    resp = client.get("/api/runs/run-01/results")
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) == 60
    sample = results[0]
    assert "case_id" in sample
    assert "variant" in sample
    assert "verdict" in sample
    assert "checks" in sample
    assert isinstance(sample["checks"], list)
    if sample["checks"]:
        assert "spans" in sample["checks"][0]


def test_post_run_review_and_export_route() -> None:
    _ensure_seed_run()
    review_data = {
        "case_id": "A-DISC-01",
        "decision": "needs_work",
        "comment": "Pending judge model evaluation in Phase 8",
        "reviewer": "test-analyst",
    }
    resp = client.post("/api/runs/run-01/reviews", json=review_data)
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["status"] == "saved"
    assert res_json["decision"] == "needs_work"

    bad_decision = client.post(
        "/api/runs/run-01/reviews",
        json={"case_id": "A-DISC-01", "decision": "invalid", "comment": "test"},
    )
    assert bad_decision.status_code == 400
    assert "Fix:" in bad_decision.json()["detail"]

    bad_case = client.post(
        "/api/runs/run-01/reviews",
        json={"case_id": "INVALID-CASE", "decision": "accept", "comment": "test"},
    )
    assert bad_case.status_code == 404
    assert "Fix:" in bad_case.json()["detail"]

    export_resp = client.get("/api/runs/run-01/export")
    assert export_resp.status_code == 200
    evidence = export_resp.json()
    assert "reviews" in evidence
    assert any(
        r["case_id"] == "A-DISC-01"
        and r["decision"] == "needs_work"
        and r["reviewer"] == "test-analyst"
        for r in evidence["reviews"]
    )


def test_get_run_report_route() -> None:
    _ensure_seed_run()
    resp = client.get("/api/runs/run-01/report")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html_text = resp.text
    assert "<!DOCTYPE html>" in html_text
    assert "ProofRAI Assurance Report" in html_text
    assert "What this run does not show" in html_text


def test_interview_and_card_routes() -> None:
    tmp_path = Path("backend/data/control_library_test_interview.yaml")
    shutil.copyfile("backend/data/control_library.yaml", tmp_path)
    tmp_card = Path("backend/data/card_test.json")
    tmp_interview = Path("backend/data/interview_test.json")

    orig_path = routes_module.CONTROL_LIBRARY_PATH
    orig_card = routes_module.CARD_FILE_PATH
    orig_interview = routes_module.INTERVIEW_FILE_PATH

    routes_module.CONTROL_LIBRARY_PATH = tmp_path
    routes_module.CARD_FILE_PATH = tmp_card
    routes_module.INTERVIEW_FILE_PATH = tmp_interview

    try:
        # 1. Post compliant interview answers
        interview_payload = {
            "tasks": ["summarise_applications"],
            "data_seen": ["contact_details", "work_history"],
            "decision_impact": "neither",
            "actions": ["none"],
            "human_oversight": "before_actions",
            "affected_parties": ["job_candidates", "recruiters"],
            "decision_significance": "significant",
            "known_limitations": "Model outputs require human recruiter validation.",
        }
        resp = client.post("/api/interview", json=interview_payload)
        assert resp.status_code == 200
        res_data = resp.json()
        assert res_data["status"] == "ok"
        assert len(res_data["conflicts"]) == 0
        assert "CTL-02" in res_data["proposed_controls"]
        assert "CTL-04" not in res_data["proposed_controls"]

        # 2. Trigger conflict: determination with no oversight
        conflict_payload = dict(interview_payload)
        conflict_payload["decision_impact"] = "determine"
        conflict_payload["human_oversight"] = "never"
        c_resp = client.post("/api/interview", json=conflict_payload)
        assert c_resp.status_code == 200
        c_data = c_resp.json()
        assert len(c_data["conflicts"]) >= 1
        assert any("outputs determine outcomes" in c["message"] for c in c_data["conflicts"])

        # 3. GET /api/card
        card_resp = client.get("/api/card")
        assert card_resp.status_code == 200
        card_data = card_resp.json()
        assert "title" in card_data
        assert "structured_fields" in card_data
        assert "intended_use" in card_data
        assert "known_limits" in card_data

        # 4. POST /api/card/confirm
        confirm_payload = {
            "confirmed_by": "Compliance Officer",
            "intended_use": "Verified intended use text for recruiting team.",
            "known_limits": "Verified constraints and boundaries.",
        }
        conf_resp = client.post("/api/card/confirm", json=confirm_payload)
        assert conf_resp.status_code == 200
        conf_data = conf_resp.json()
        assert conf_data["status"] == "confirmed"
        assert conf_data["confirmed_by"] == "Compliance Officer"
        assert conf_data["confirmed_at"] is not None
    finally:
        routes_module.CONTROL_LIBRARY_PATH = orig_path
        routes_module.CARD_FILE_PATH = orig_card
        routes_module.INTERVIEW_FILE_PATH = orig_interview
        tmp_path.unlink(missing_ok=True)
        tmp_card.unlink(missing_ok=True)
        tmp_interview.unlink(missing_ok=True)


def test_get_run_impact_route() -> None:
    _ensure_seed_run()
    resp = client.get("/api/runs/run-01/impact")
    assert resp.status_code == 200
    impacts = resp.json()
    assert isinstance(impacts, list)
    assert len(impacts) >= 1
    assert "control_id" in impacts[0]
    assert "attacks_mitigated" in impacts[0]
    assert "causal_chain" in impacts[0]


def test_get_run_recommendations_route() -> None:
    _ensure_seed_run()
    resp = client.get("/api/runs/run-01/recommendations")
    assert resp.status_code == 200
    recs = resp.json()
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert "vulnerability" in recs[0]
    assert "suggested_action" in recs[0]


def test_get_explain_route() -> None:
    resp = client.get("/api/explain")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 5
    assert "what_is_this" in items[0]
    assert "example" in items[0]


def test_post_suite_generate_route() -> None:
    resp = client.post("/api/suite/generate", json={"category": "prompt_injection", "evaluate_now": False})
    assert resp.status_code == 200
    data = resp.json()
    assert "cases" in data
    assert len(data["cases"]) >= 1
    assert data["cases"][0]["case"]["group"] == "attack"


def test_post_test_single_prompt_route() -> None:
    resp = client.post(
        "/api/test/prompt",
        json={"task": "chat", "message": "Can you summarize our interview stages?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "baseline" in data
    assert "controlled" in data
    assert data["baseline"]["variant"] == "baseline"
    assert data["controlled"]["variant"] == "controlled"


def test_session_isolation_and_management() -> None:
    sess_id = f"test-sess-{uuid.uuid4().hex[:8]}"
    headers = {"X-Session-ID": sess_id}

    # 1. New session starts fresh with 0 runs and draft card
    info_resp = client.get("/api/session/info", headers=headers)
    assert info_resp.status_code == 200
    info = info_resp.json()
    assert info["session_id"] == sess_id
    assert info["is_demo"] is False
    assert info["runs_count"] == 0
    assert info["card_status"] == "draft"

    # 2. Controls can be retrieved in this session
    ctl_resp = client.get("/api/controls", headers=headers)
    assert ctl_resp.status_code == 200
    assert len(ctl_resp.json()) >= 6

    # 3. Load demo benchmark data into this session
    demo_resp = client.post("/api/session/load-demo", headers=headers)
    assert demo_resp.status_code == 200

    info_after_demo = client.get("/api/session/info", headers=headers).json()
    assert info_after_demo["runs_count"] >= 1

    # 4. Reset this session back to clean draft state
    reset_resp = client.post("/api/session/reset", headers=headers)
    assert reset_resp.status_code == 200

    info_after_reset = client.get("/api/session/info", headers=headers).json()
    assert info_after_reset["runs_count"] == 0
    assert info_after_reset["card_status"] == "draft"




