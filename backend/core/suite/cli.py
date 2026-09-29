import sys
from pathlib import Path

# Ensure backend package is on sys.path
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent
repo_root = backend_dir.parent
for p in [str(backend_dir), str(repo_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.core.suite.loader import load_suite
from backend.core.suite.runner import SuiteRunner


def print_summary_table(results_list: list, cases_list: list) -> None:
    cases_by_id = {c.id: c for c in cases_list}
    baseline_map = {r.case_id: r for r in results_list if r.variant == "baseline"}
    controlled_map = {r.case_id: r for r in results_list if r.variant == "controlled"}

    attack_cases = [c for c in cases_list if c.group == "attack"]
    benign_cases = [c for c in cases_list if c.group == "benign"]

    # Attack rates
    base_atk_pass = sum(1 for c in attack_cases if baseline_map.get(c.id) and baseline_map[c.id].verdict == "pass")
    ctrl_atk_pass = sum(1 for c in attack_cases if controlled_map.get(c.id) and controlled_map[c.id].verdict == "pass")

    # Benign completion rates
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

    # Over-blocked cases
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

    # Needs review cases
    needs_review = [r for r in results_list if r.verdict == "needs_review"]
    needs_review_ctrl = [r for r in needs_review if r.variant == "controlled"]
    print("\nNeeds review cases (controlled variant):")
    if needs_review_ctrl:
        for nr in needs_review_ctrl:
            reason = nr.judge_reason or "ambiguous deterministic check"
            print(f"- {nr.case_id} ({cases_by_id[nr.case_id].risk}): {reason}")
    else:
        print("None")

    # Error cases
    errors = [r for r in results_list if r.verdict == "error"]
    print("\nError cases:")
    if errors:
        for err in errors:
            print(f"- {err.case_id} [{err.variant}]: {err.judge_reason}")
    else:
        print("None (0 errors)")
    print("=" * 62 + "\n")


def main() -> None:
    no_cache = "--no-cache" in sys.argv
    suite_cases = load_suite()
    runner = SuiteRunner()
    results = runner.run_suite(suite_cases, no_cache=no_cache)
    print_summary_table(results, suite_cases)


if __name__ == "__main__":
    main()
