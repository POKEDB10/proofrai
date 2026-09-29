import tempfile
from pathlib import Path

import pytest

from backend.core.ledger.database import get_db, save_result
from backend.core.models import Case, CaseResult
from backend.core.suite.loader import load_suite
from backend.core.suite.runner import SuiteRunner


def test_suite_case_count_and_structure() -> None:
    cases = load_suite()
    assert len(cases) == 30

    attack_cases = [c for c in cases if c.group == "attack"]
    benign_cases = [c for c in cases if c.group == "benign"]

    assert len(attack_cases) == 16
    assert len(benign_cases) == 14

    # Verify critical attack cases
    critical_attack_prefixes = ("A-PII-", "A-INJ-", "A-LEAK-")
    critical_cases = [c for c in cases if c.critical]
    assert len(critical_cases) == 9
    for c in critical_cases:
        assert c.group == "attack"
        assert any(c.id.startswith(pfx) for pfx in critical_attack_prefixes)

    # Verify A-DISC and A-PROXY have judge: pending
    pending_prefixes = ("A-DISC-", "A-PROXY-")
    pending_cases = [c for c in cases if c.judge == "pending"]
    assert len(pending_cases) == 6
    for c in pending_cases:
        assert any(c.id.startswith(pfx) for pfx in pending_prefixes)


def test_malformed_suite_file_rejected() -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write("- id: INVALID-01\n  group: attack\n")
        temp_path = f.name

    try:
        with pytest.raises(ValueError) as excinfo:
            load_suite(temp_path)
        err_msg = str(excinfo.value)
        assert "Malformed suite file" in err_msg
        assert "Field" in err_msg
        assert "Fix:" in err_msg
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_runner_resumability() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        runner = SuiteRunner(db_path=db_path)

        mock_case = Case(
            id="B-TEST-01",
            group="benign",
            risk="Test risk",
            task="faq",
            input="Test question?",
            checks=[],
            judge=None,
            critical=False,
        )

        # Pre-seed result for baseline
        pre_seeded = CaseResult(
            case_id="B-TEST-01",
            variant="baseline",
            output_text="Pre-computed baseline reply",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="pass",
            verdict_source="deterministic",
        )
        conn = get_db(db_path)
        save_result(conn, "run-01", pre_seeded)
        conn.close()

        # Run with mock case
        results = runner.run_suite([mock_case], run_id="run-01")
        assert len(results) == 2

        base = next(r for r in results if r.variant == "baseline")
        assert base.output_text == "Pre-computed baseline reply"
