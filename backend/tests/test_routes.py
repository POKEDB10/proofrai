import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

import backend.app.routes as routes_module
from backend.app.main import app

client = TestClient(app)


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
        # 1. Successful patch
        resp = client.patch("/api/controls/CTL-01", json={"status": "approved"})
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["id"] == "CTL-01"
        assert updated["status"] == "approved"

        # 2. Invalid status
        bad_resp = client.patch("/api/controls/CTL-01", json={"status": "enabled"})
        assert bad_resp.status_code == 400
        err = bad_resp.json()
        assert "detail" in err
        assert "Fix:" in err["detail"]

        # 3. Non-existent control
        not_found = client.patch("/api/controls/CTL-999", json={"status": "approved"})
        assert not_found.status_code == 404
        err = not_found.json()
        assert "detail" in err
        assert "Fix:" in err["detail"]
    finally:
        routes_module.CONTROL_LIBRARY_PATH = orig_path
        tmp_path.unlink(missing_ok=True)


def test_runs_lifecycle_routes() -> None:
    # 1. Existing run summary
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


def test_get_run_results_route() -> None:
    resp = client.get("/api/runs/run-01/results")
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) == 60  # 30 baseline + 30 controlled
    sample = results[0]
    assert "case_id" in sample
    assert "variant" in sample
    assert "verdict" in sample
    assert "checks" in sample
    assert isinstance(sample["checks"], list)
    if sample["checks"]:
        assert "spans" in sample["checks"][0]


def test_post_run_review_and_export_route() -> None:
    # 1. Post review
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

    # 2. Invalid review decision
    bad_decision = client.post(
        "/api/runs/run-01/reviews",
        json={"case_id": "A-DISC-01", "decision": "invalid", "comment": "test"},
    )
    assert bad_decision.status_code == 400
    assert "Fix:" in bad_decision.json()["detail"]

    # 3. Invalid case id
    bad_case = client.post(
        "/api/runs/run-01/reviews",
        json={"case_id": "INVALID-CASE", "decision": "accept", "comment": "test"},
    )
    assert bad_case.status_code == 404
    assert "Fix:" in bad_case.json()["detail"]

    # 4. Verify review appears in export
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
    resp = client.get("/api/runs/run-01/report")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html_text = resp.text
    assert "<!DOCTYPE html>" in html_text
    assert "ProofRAI Assurance Report" in html_text
    assert "What this run does not show" in html_text
