import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.core.gate.evaluator import evaluate_release_gate
from backend.core.ledger.database import (
    DEFAULT_LEDGER_PATH,
    get_db,
    load_results_for_run,
    load_run,
)
from backend.core.suite.loader import load_suite
from backend.core.suite.runner import SuiteRunner


@dataclass
class RunTracker:
    run_id: str
    status: str
    current_case: int
    total_cases: int
    current_case_id: str
    current_variant: str
    error_message: str | None = None


active_trackers: dict[str, RunTracker] = {}
tracker_lock = threading.Lock()


def execute_background_run(
    run_id: str,
    no_cache: bool = False,
    db_path: Path | str = DEFAULT_LEDGER_PATH,
) -> None:
    cases = load_suite()
    total_cases = len(cases)

    with tracker_lock:
        tracker = RunTracker(
            run_id=run_id,
            status="running",
            current_case=0,
            total_cases=total_cases,
            current_case_id=cases[0].id if cases else "",
            current_variant="baseline",
            error_message=None,
        )
        active_trackers[run_id] = tracker

    def on_progress(idx: int, total: int, case_id: str, variant: str) -> None:
        with tracker_lock:
            tracker.current_case = idx
            tracker.total_cases = total
            tracker.current_case_id = case_id
            tracker.current_variant = variant

    try:
        runner = SuiteRunner(db_path=db_path)
        runner.run_suite(
            cases=cases,
            run_id=run_id,
            no_cache=no_cache,
            progress_callback=on_progress,
        )
        with tracker_lock:
            tracker.status = "completed"
            tracker.current_case = total_cases
    except (RuntimeError, ValueError, KeyError, OSError, TypeError, TimeoutError) as exc:
        with tracker_lock:
            tracker.status = "failed"
            tracker.error_message = str(exc)


def get_run_summary(
    run_id: str,
    db_path: Path | str = DEFAULT_LEDGER_PATH,
) -> dict[str, Any] | None:
    with tracker_lock:
        tracker = active_trackers.get(run_id)

    conn = get_db(db_path)
    run_meta = load_run(conn, run_id)

    if not run_meta and not tracker:
        conn.close()
        return None

    cases = load_suite()
    total_cases = len(cases)
    results = load_results_for_run(conn, run_id)
    conn.close()

    cases_by_id = {c.id: c for c in cases}
    controlled_map = {r.case_id: r for r in results if r.variant == "controlled"}
    attack_cases = [c for c in cases if c.group == "attack"]
    benign_cases = [c for c in cases if c.group == "benign"]

    attack_passed = sum(
        1 for c in attack_cases
        if controlled_map.get(c.id) and controlled_map[c.id].verdict == "pass"
    )
    benign_completed = sum(
        1 for c in benign_cases
        if controlled_map.get(c.id) and controlled_map[c.id].verdict == "pass"
    )
    over_blocked = sum(
        1 for r in results
        if r.variant == "controlled"
        and r.blocked_by
        and cases_by_id.get(r.case_id)
        and cases_by_id[r.case_id].group == "benign"
    )
    needs_review = sum(
        1 for r in results
        if r.variant == "controlled" and r.verdict == "needs_review"
    )
    errors = sum(1 for r in results if r.verdict == "error")
    completed_cases = len({r.case_id for r in results})

    if tracker and tracker.status == "running":
        status = "running"
        current = tracker.current_case
        percent = round((current / total_cases) * 100.0, 1) if total_cases > 0 else 0.0
        gate_summary = None
    elif tracker and tracker.status == "failed":
        status = "failed"
        current = tracker.current_case
        percent = round((current / total_cases) * 100.0, 1) if total_cases > 0 else 0.0
        gate_summary = None
    else:
        status = "completed"
        current = total_cases
        percent = 100.0
        gate_label, gate_reasons = evaluate_release_gate(results, cases)
        gate_summary = {
            "label": gate_label,
            "reasons": gate_reasons,
        }

    counts = {
        "total_cases": total_cases,
        "completed_cases": completed_cases,
        "attack_total": len(attack_cases),
        "attack_passed": attack_passed,
        "benign_total": len(benign_cases),
        "benign_completed": benign_completed,
        "over_blocked": over_blocked,
        "needs_review": needs_review,
        "errors": errors,
    }

    progress = {
        "current": current,
        "total": total_cases,
        "percent": percent,
    }

    return {
        "id": run_id,
        "status": status,
        "progress": progress,
        "counts": counts,
        "release_gate": gate_summary,
    }
