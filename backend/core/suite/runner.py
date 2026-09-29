import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from backend.app.settings import get_settings
from backend.core.checks.evaluators import (
    canary_absent,
    field_values_absent,
    output_mentions_any,
    refusal_marker,
    tool_not_executed,
    tool_queued,
)
from backend.core.controls.loader import load_control_library
from backend.core.controls.pipeline import ControlPipeline
from backend.core.ledger.database import (
    DEFAULT_LEDGER_PATH,
    get_db,
    load_results_for_run,
    load_run,
    save_controls_snapshot,
    save_result,
    save_run,
)
from backend.core.models import (
    Case,
    CaseResult,
    CheckResult,
    CheckSpec,
    Control,
    ControlEvent,
    ToolCall,
    Verdict,
    VerdictSource,
)
from backend.core.target.assistant import HireAssist, TargetExecution


def evaluate_check(
    check_spec: CheckSpec,
    output_text: str,
    tool_calls: list[ToolCall],
) -> CheckResult:
    name = check_spec.name
    args = check_spec.args or {}

    if name == "canary_absent":
        return canary_absent(value=args.get("value", ""), text=output_text)
    if name == "field_values_absent":
        return field_values_absent(
            fields=args.get("fields", []),
            candidate_ids=args.get("candidate_ids", []),
            text=output_text,
        )
    if name == "tool_not_executed":
        return tool_not_executed(
            name=args.get("name", ""), tool_calls=tool_calls
        )
    if name == "tool_queued":
        return tool_queued(name=args.get("name", ""), tool_calls=tool_calls)
    if name == "output_mentions_any":
        return output_mentions_any(
            keywords=args.get("keywords", []), text=output_text
        )
    if name == "refusal_marker":
        return refusal_marker(text=output_text)

    return CheckResult(
        name=name,
        passed=False,
        detail=f"Unknown check evaluator '{name}'",
        spans=[],
    )


def execute_case_variant(
    case: Case,
    assistant: HireAssist,
    no_cache: bool = False,
) -> tuple[TargetExecution | None, str | None]:
    task = case.task
    user_input = case.input

    try:
        if task in ("summarize", "summarize_candidate"):
            candidate_id = (
                user_input.get("candidate_id", "")
                if isinstance(user_input, dict)
                else str(user_input)
            )
            return assistant.summarize_candidate(candidate_id, no_cache=no_cache), None

        if task in ("faq", "answer_faq"):
            question = (
                user_input.get("question", "")
                if isinstance(user_input, dict)
                else str(user_input)
            )
            return assistant.answer_faq(question, no_cache=no_cache), None

        if task in ("draft", "draft_screening_notes"):
            if isinstance(user_input, dict):
                candidate_id = user_input.get("candidate_id", "")
                job_id = user_input.get("job_id", "")
            else:
                candidate_id = str(user_input)
                job_id = "job-01"
            return (
                assistant.draft_screening_notes(
                    candidate_id=candidate_id, job_id=job_id, no_cache=no_cache
                ),
                None,
            )

        if task in ("chat", "recruiter_chat"):
            if isinstance(user_input, dict):
                message = user_input.get("message", "")
                candidate_id = user_input.get("candidate_id")
            else:
                message = str(user_input)
                candidate_id = None

            context: dict[str, Any] = {"task": "recruiter_chat", "message": message}
            full_prompt = message
            if candidate_id:
                record = assistant.tools.get_candidate_record(candidate_id)
                context["candidate_id"] = candidate_id
                context["candidate_record"] = record
                full_prompt = (
                    f"{message}\nCandidate Profile Record: "
                    f"{json.dumps(record, ensure_ascii=False)}"
                )

            return assistant._execute_turn(full_prompt, context, no_cache=no_cache), None

        return None, f"Unknown task '{task}'"
    except (RuntimeError, ValueError, KeyError, OSError, TypeError) as exc:
        return None, str(exc)


def determine_verdict(
    case: Case,
    checks: list[CheckResult],
    events: list[ControlEvent],
    error_msg: str | None = None,
) -> tuple[Verdict, VerdictSource, str | None, list[str] | None]:
    if error_msg is not None:
        return "error", "deterministic", f"Execution error: {error_msg}", None

    if case.judge == "pending":
        return "needs_review", "judge", "Judge evaluation pending", None

    has_ambiguity = any("ambiguous" in c.detail for c in checks)
    if has_ambiguity:
        return "needs_review", "deterministic", "Ambiguous check result", None

    all_passed = all(c.passed for c in checks)
    verdict: Verdict = "pass" if all_passed else "fail"

    blocked_by: list[str] | None = None
    if case.group == "benign" and verdict == "fail":
        modifying_controls = [
            e.control_id for e in events if e.action in ("block", "modify")
        ]
        if modifying_controls:
            blocked_by = modifying_controls

    return verdict, "deterministic", None, blocked_by


class SuiteRunner:
    def __init__(
        self,
        controls: list[Control] | None = None,
        db_path: Path | str = DEFAULT_LEDGER_PATH,
        runs_dir: Path | str | None = None,
    ) -> None:
        if runs_dir is not None:
            self.db_path = Path(runs_dir) / "ledger.db"
        else:
            self.db_path = Path(db_path)

        all_controls = controls or load_control_library()
        implemented_ids = {"CTL-01", "CTL-02", "CTL-03", "CTL-05"}
        self.approved_controls: list[Control] = []
        for c in all_controls:
            if c.id in implemented_ids:
                c_copy = c.model_copy()
                c_copy.status = "approved"
                self.approved_controls.append(c_copy)
            else:
                self.approved_controls.append(c.model_copy())

    def run_suite(
        self,
        cases: list[Case],
        run_id: str = "run-01",
        no_cache: bool = False,
        run_file_name: str | None = None,
    ) -> list[CaseResult]:
        if run_file_name is not None and run_id == "run-01":
            run_id = Path(run_file_name).stem

        conn = get_db(self.db_path)
        existing_run = load_run(conn, run_id)
        settings = get_settings()

        controls_data = [c.model_dump() for c in self.approved_controls]
        controls_yaml = yaml.dump(controls_data, sort_keys=True)
        control_config_hash = hashlib.sha256(controls_yaml.encode("utf-8")).hexdigest()[:12]
        created_at = datetime.now(timezone.utc).isoformat()

        if not existing_run:
            save_run(
                conn=conn,
                run_id=run_id,
                provider=settings.provider,
                target_model=settings.target_model,
                judge_model=settings.judge_model,
                temperature=0.0,
                suite_version="v1",
                control_config_hash=control_config_hash,
                controls_yaml=controls_yaml,
                created_at=created_at,
            )
            save_controls_snapshot(conn, run_id, self.approved_controls)

        db_results = load_results_for_run(conn, run_id)
        existing_results: dict[tuple[str, str], CaseResult] = {
            (r.case_id, r.variant): r for r in db_results
        }

        all_results: list[CaseResult] = []
        total_cases = len(cases)

        baseline_assistant = HireAssist()
        pipeline = ControlPipeline(self.approved_controls)
        controlled_assistant = HireAssist(hooks=pipeline)

        for idx, case in enumerate(cases, start=1):
            counter_str = f"[{idx}/{total_cases}] {case.id}"
            sys.stderr.write(f"\r{counter_str} running baseline...      ")
            sys.stderr.flush()

            # Baseline variant
            baseline_key = (case.id, "baseline")
            if (
                baseline_key in existing_results
                and existing_results[baseline_key].verdict != "error"
                and not no_cache
            ):
                base_result = existing_results[baseline_key]
            else:
                exec_res, err = execute_case_variant(
                    case, baseline_assistant, no_cache=no_cache
                )
                output_text = exec_res.output_text if exec_res else ""
                tool_calls = exec_res.tool_calls if exec_res else []
                events = exec_res.events if exec_res else []

                checks = [
                    evaluate_check(spec, output_text, tool_calls)
                    for spec in case.checks
                ]
                v, v_source, j_reason, blocked_by = determine_verdict(
                    case, checks, events, err
                )
                base_result = CaseResult(
                    case_id=case.id,
                    variant="baseline",
                    output_text=output_text,
                    tool_calls=tool_calls,
                    events=events,
                    checks=checks,
                    verdict=v,
                    verdict_source=v_source,
                    judge_reason=j_reason,
                    blocked_by=blocked_by,
                )
                save_result(conn, run_id, base_result)
                existing_results[baseline_key] = base_result

            all_results.append(base_result)

            # Controlled variant
            sys.stderr.write(f"\r{counter_str} running controlled...    ")
            sys.stderr.flush()

            pipeline.clear_events()
            controlled_key = (case.id, "controlled")
            if (
                controlled_key in existing_results
                and existing_results[controlled_key].verdict != "error"
                and not no_cache
            ):
                ctrl_result = existing_results[controlled_key]
            else:
                exec_res, err = execute_case_variant(
                    case, controlled_assistant, no_cache=no_cache
                )
                output_text = exec_res.output_text if exec_res else ""
                tool_calls = exec_res.tool_calls if exec_res else []
                events = exec_res.events if exec_res else []

                checks = [
                    evaluate_check(spec, output_text, tool_calls)
                    for spec in case.checks
                ]
                v, v_source, j_reason, blocked_by = determine_verdict(
                    case, checks, events, err
                )
                ctrl_result = CaseResult(
                    case_id=case.id,
                    variant="controlled",
                    output_text=output_text,
                    tool_calls=tool_calls,
                    events=events,
                    checks=checks,
                    verdict=v,
                    verdict_source=v_source,
                    judge_reason=j_reason,
                    blocked_by=blocked_by,
                )
                save_result(conn, run_id, ctrl_result)
                existing_results[controlled_key] = ctrl_result

            all_results.append(ctrl_result)

        sys.stderr.write(f"\rCompleted run of {total_cases} cases.             \n")
        sys.stderr.flush()
        conn.close()

        return all_results
