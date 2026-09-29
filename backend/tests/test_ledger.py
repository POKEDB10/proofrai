import json
import tempfile
from pathlib import Path

from backend.core.ledger.database import (
    get_db,
    load_controls_snapshot,
    load_results_for_run,
    load_reviews_for_run,
    load_run,
    load_system_card,
    save_controls_snapshot,
    save_result,
    save_review,
    save_run,
    save_system_card,
)
from backend.core.ledger.export import export_evidence_json, export_report_html
from backend.core.models import CaseResult, Control


def test_sqlite_ledger_crud() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        conn = get_db(db_path)

        # 1. Save and load run
        save_run(
            conn=conn,
            run_id="run-01",
            provider="gemini",
            target_model="gemini-3.5-flash-lite",
            judge_model="gemini-3.5-flash",
            temperature=0.0,
            suite_version="v1",
            control_config_hash="abc123def456",
            controls_yaml="title: test",
            created_at="2026-09-29T10:00:00Z",
        )
        run_meta = load_run(conn, "run-01")
        assert run_meta is not None
        assert run_meta["id"] == "run-01"
        assert run_meta["provider"] == "gemini"
        assert run_meta["temperature"] == 0.0

        # 2. Controls snapshot
        ctrl = Control(
            id="CTL-01",
            title="Minimise protected and unneeded fields",
            risk="Demographic bias and protected attribute leakage",
            rationale="Reduces model reliance on non-job attributes.",
            enforcement_point="pre_model",
            params={"mask_fields": ["gender", "phone"]},
            references=["NIST AI RMF Map"],
            test_ids=["A-PII-01"],
            status="approved",
        )
        save_controls_snapshot(conn, "run-01", [ctrl])
        snaps = load_controls_snapshot(conn, "run-01")
        assert len(snaps) == 1
        assert snaps[0]["control_id"] == "CTL-01"
        assert snaps[0]["params"] == {"mask_fields": ["gender", "phone"]}
        assert snaps[0]["references"] == ["NIST AI RMF Map"]

        # 3. CaseResult
        res = CaseResult(
            case_id="A-PII-01",
            variant="controlled",
            output_text="Redacted summary",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="pass",
            verdict_source="deterministic",
            judge_reason=None,
            blocked_by=None,
        )
        save_result(conn, "run-01", res)
        results = load_results_for_run(conn, "run-01")
        assert len(results) == 1
        assert results[0].case_id == "A-PII-01"
        assert results[0].verdict == "pass"

        # 4. Review
        save_review(
            conn=conn,
            run_id="run-01",
            case_id="A-PII-01",
            decision="accept",
            comment="Verified masking",
            reviewer="lead-analyst",
            created_at="2026-09-29T10:05:00Z",
        )
        reviews = load_reviews_for_run(conn, "run-01")
        assert len(reviews) == 1
        assert reviews[0]["decision"] == "accept"
        assert reviews[0]["reviewer"] == "lead-analyst"

        # 5. System card
        save_system_card(
            conn=conn,
            run_id="run-01",
            title="HireAssist Recruiting Copilot",
            intended_use="Summarizing candidate applications and answering recruiter FAQ.",
            known_limits="Synthetic recruiting tasks only. Not certified for autonomous hiring.",
            confirmed_by="Recruiter Lead",
            confirmed_at="2026-09-29T10:10:00Z",
        )
        sc = load_system_card(conn, "run-01")
        assert sc is not None
        assert sc["title"] == "HireAssist Recruiting Copilot"
        assert sc["confirmed_by"] == "Recruiter Lead"

        conn.close()


def test_export_deterministic_double_run() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        conn = get_db(db_path)

        # Seed run
        save_run(
            conn=conn,
            run_id="run-det",
            provider="gemini",
            target_model="gemini-3.5-flash-lite",
            judge_model="gemini-3.5-flash",
            temperature=0.0,
            suite_version="v1",
            control_config_hash="det123456",
            controls_yaml="title: test",
            created_at="2026-09-29T10:00:00Z",
        )
        res1 = CaseResult(
            case_id="A-PII-01",
            variant="baseline",
            output_text="Baseline output",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="fail",
            verdict_source="deterministic",
        )
        res2 = CaseResult(
            case_id="A-PII-01",
            variant="controlled",
            output_text="Controlled output",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="pass",
            verdict_source="deterministic",
        )
        save_result(conn, "run-det", res1)
        save_result(conn, "run-det", res2)

        json_out_1 = Path(tmpdir) / "export1.json"
        json_out_2 = Path(tmpdir) / "export2.json"

        text1 = export_evidence_json(conn, "run-det", json_out_1)
        text2 = export_evidence_json(conn, "run-det", json_out_2)

        assert text1 == text2
        assert json_out_1.read_bytes() == json_out_2.read_bytes()

        # Check JSON parsing
        parsed = json.loads(text1)
        assert parsed["run_metadata"]["run_id"] == "run-det"
        assert len(parsed["results"]) == 2
        assert parsed["release_gate"]["label"] is not None

        # Check HTML report
        html_out = Path(tmpdir) / "report.html"
        html_text = export_report_html(conn, "run-det", html_out)
        assert html_out.is_file()

        # Verify all 8 sections in order
        sections = [
            "System card",
            "Controls with rationale and references",
            "Results by risk",
            "Over-blocked benign cases",
            "Unresolved failures",
            "Reviewer decisions",
            "Model and suite versions with hashes",
            "What this run does not show",
        ]
        pos = -1
        for sec in sections:
            sec_tag = f"<h2>{sec}</h2>"
            found_pos = html_text.find(sec_tag)
            assert found_pos != -1, f"Missing section header: {sec_tag}"
            assert found_pos > pos, f"Section out of order: {sec}"
            pos = found_pos

        # Check token usage in HTML
        assert "--font-sans" in html_text
        assert "--font-mono" in html_text
        assert "--ground" in html_text
        assert "--surface" in html_text
        assert "--ink" in html_text

        # Ensure no unrendered template tags
        assert "{{" not in html_text
        assert "}}" not in html_text
        assert "{%" not in html_text
        assert "%}" not in html_text

        conn.close()


def test_ledger_empty_queries() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "empty_test.db"
        conn = get_db(db_path)
        assert load_run(conn, "missing-run") is None
        assert load_results_for_run(conn, "missing-run") == []
        assert load_reviews_for_run(conn, "missing-run") == []
        assert load_controls_snapshot(conn, "missing-run") == []
        assert load_system_card(conn, "missing-run") is None
        conn.close()

