import json
import sys
from pathlib import Path
from typing import Any

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

DEFAULT_RUNS_DIR = Path("backend/data/runs")


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
        runs_dir: Path | str = DEFAULT_RUNS_DIR,
    ) -> None:
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

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
        run_file_name: str = "latest.jsonl",
        no_cache: bool = False,
    ) -> list[CaseResult]:
        run_path = self.runs_dir / run_file_name

        existing_results: dict[tuple[str, str], CaseResult] = {}
        if run_path.is_file():
            with open(run_path, encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        try:
                            parsed = CaseResult.model_validate_json(line_str)
                            existing_results[(parsed.case_id, parsed.variant)] = parsed
                        except (ValueError, TypeError, KeyError):
                            continue

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
                with open(run_path, "a", encoding="utf-8") as f:
                    f.write(base_result.model_dump_json() + "\n")
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
                with open(run_path, "a", encoding="utf-8") as f:
                    f.write(ctrl_result.model_dump_json() + "\n")
                existing_results[controlled_key] = ctrl_result

            all_results.append(ctrl_result)

        sys.stderr.write(f"\rCompleted run of {total_cases} cases.             \n")
        sys.stderr.flush()

        with open(run_path, "w", encoding="utf-8") as f:
            f.writelines(r.model_dump_json() + "\n" for r in all_results)

        return all_results
