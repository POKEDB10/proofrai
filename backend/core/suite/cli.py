import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
repo_root = backend_dir.parent
for p in [str(backend_dir), str(repo_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.core.gate.evaluator import evaluate_release_gate
from backend.core.ledger.database import DEFAULT_LEDGER_PATH, get_db
from backend.core.ledger.export import export_evidence_json, export_report_html
from backend.core.suite.loader import load_suite
from backend.core.suite.runner import SuiteRunner


def print_summary_table(results_list: list, cases_list: list) -> None:
    cases_by_id = {c.id: c for c in cases_list}
    baseline_map = {r.case_id: r for r in results_list if r.variant == "baseline"}
    controlled_map = {r.case_id: r for r in results_list if r.variant == "controlled"}

    attack_cases = [c for c in cases_list if c.group == "attack"]
    benign_cases = [c for c in cases_list if c.group == "benign"]

    base_atk_pass = sum(1 for c in attack_cases if baseline_map.get(c.id) and baseline_map[c.id].verdict == "pass")
    ctrl_atk_pass = sum(1 for c in attack_cases if controlled_map.get(c.id) and controlled_map[c.id].verdict == "pass")

    base_ben_pass = sum(1 for c in benign_cases if baseline_map.get(c.id) and baseline_map[c.id].verdict == "pass")
    ctrl_ben_pass = sum(1 for c in benign_cases if controlled_map.get(c.id) and controlled_map[c.id].verdict == "pass")

    total_attack = len(attack_cases)
    total_benign = len(benign_cases)

    base_atk_pct = (base_atk_pass / total_attack * 100) if total_attack else 0.0
    ctrl_atk_pct = (ctrl_atk_pass / total_attack * 100) if total_attack else 0.0
    base_ben_pct = (base_ben_pass / total_benign * 100) if total_benign else 0.0
    ctrl_ben_pct = (ctrl_ben_pass / total_benign * 100) if total_benign else 0.0

    print("\n" + "=" * 62)
    print("                ProofRAI Suite Results Summary")
    print("=" * 62)
    print(f"{'Metric':<32} | {'Baseline':<12} | {'Controlled':<12}")
    print("-" * 62)
    print(
        f"{'Attack pass rate (harm prevented)':<32} | "
        f"{base_atk_pass}/{total_attack} ({base_atk_pct:.1f}%) | "
        f"{ctrl_atk_pass}/{total_attack} ({ctrl_atk_pct:.1f}%)"
    )
    print(
        f"{'Benign completion rate':<32} | "
        f"{base_ben_pass}/{total_benign} ({base_ben_pct:.1f}%) | "
        f"{ctrl_ben_pass}/{total_benign} ({ctrl_ben_pct:.1f}%)"
    )
    print("=" * 62)

    over_blocked = [
        r for r in results_list
        if r.variant == "controlled"
        and cases_by_id.get(r.case_id)
        and cases_by_id[r.case_id].group == "benign"
        and r.blocked_by
    ]
    print("\nOver-blocked benign cases:")
    if over_blocked:
        for ob in over_blocked:
            blockers = ", ".join(ob.blocked_by or [])
            print(f"- {ob.case_id}: blocked by [{blockers}]")
    else:
        print("None (0 over-blocked cases)")

    needs_review = [r for r in results_list if r.verdict == "needs_review"]
    needs_review_ctrl = [r for r in needs_review if r.variant == "controlled"]
    print("\nNeeds review cases (controlled variant):")
    if needs_review_ctrl:
        for nr in needs_review_ctrl:
            reason = nr.judge_reason or "ambiguous deterministic check"
            print(f"- {nr.case_id} ({cases_by_id[nr.case_id].risk}): {reason}")
    else:
        print("None")

    errors = [r for r in results_list if r.verdict == "error"]
    print("\nError cases:")
    if errors:
        for err in errors:
            print(f"- {err.case_id} [{err.variant}]: {err.judge_reason}")
    else:
        print("None (0 errors)")

    gate_label, gate_reasons = evaluate_release_gate(results_list, cases_list)
    print("\nRelease gate verdict:")
    print(f"[{gate_label}]")
    for reason in gate_reasons:
        print(f"  - {reason}")
    print("=" * 62 + "\n")


def parse_arg(flag: str, default: str) -> str:
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


def main() -> None:
    no_cache = "--no-cache" in sys.argv
    run_id = parse_arg("--run-id", "run-01")
    db_path = parse_arg("--db", str(DEFAULT_LEDGER_PATH))
    export_dir_str = parse_arg("--export-dir", "examples")

    suite_cases = load_suite()
    runner = SuiteRunner(db_path=db_path)
    results = runner.run_suite(suite_cases, run_id=run_id, no_cache=no_cache)
    print_summary_table(results, suite_cases)

    export_dir = Path(export_dir_str)
    export_dir.mkdir(parents=True, exist_ok=True)
    conn = get_db(db_path)
    evidence_path = export_dir / f"evidence_{run_id}.json"
    report_path = export_dir / "report.html"

    export_evidence_json(conn, run_id, evidence_path)
    export_report_html(conn, run_id, report_path)
    conn.close()

    print(f"Exported evidence JSON to: {evidence_path}")
    print(f"Exported report HTML to:   {report_path}\n")


if __name__ == "__main__":
    main()
