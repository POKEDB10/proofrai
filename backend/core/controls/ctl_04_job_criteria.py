import json
import re
from pathlib import Path
from typing import Any

import httpx
from google.genai.errors import APIError

from backend.core.models import Control, ControlEvent, ToolCall

CRITERIA_PATTERN = re.compile(r"\bjob-\d+\.c\d+\b", re.IGNORECASE)


class JobCriteriaControl:
    def __init__(
        self,
        control: Control | None = None,
        jobs_file: Path | str = "backend/data/jobs.json",
    ) -> None:
        self.control_id = control.id if control else "CTL-04"
        self.jobs_file = Path(jobs_file)
        self.job_criteria_map: dict[str, set[str]] = self._load_job_criteria()

    def _load_job_criteria(self) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = {}
        if not self.jobs_file.is_file():
            from backend.core.paths import resolve_data_path
            self.jobs_file = resolve_data_path(self.jobs_file.name)
        if not self.jobs_file.is_file():
            return mapping
        try:
            with open(self.jobs_file, encoding="utf-8") as f:
                jobs = json.load(f)
                for j in jobs:
                    jid = j.get("id", "")
                    crit_ids = {c.get("id", "") for c in j.get("criteria", []) if "id" in c}
                    mapping[jid] = crit_ids
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"Failed to load job criteria from {self.jobs_file}: {exc}"
            ) from exc
        return mapping

    def run_post_model(
        self,
        reply_text: str,
        tool_calls: list[ToolCall],
        context: dict[str, Any],
    ) -> tuple[str, list[ToolCall], ControlEvent]:
        task = context.get("task", "")
        is_rec_task = (
            task in ("draft", "draft_screening_note", "draft_screening_notes")
            or "screening note" in reply_text.lower()
            or "recommend" in reply_text.lower()
        )

        if not is_rec_task:
            event = ControlEvent(
                control_id=self.control_id,
                stage="post_model",
                action="pass",
                detail="Non-recommendation task; job criteria citation check passed",
            )
            return reply_text, tool_calls, event

        job_id = context.get("job_id", "job-01")
        valid_criteria = self.job_criteria_map.get(job_id, set())

        found_matches = set(CRITERIA_PATTERN.findall(reply_text.lower()))
        valid_found = {m for m in found_matches if m in valid_criteria} if valid_criteria else found_matches

        if valid_found:
            event = ControlEvent(
                control_id=self.control_id,
                stage="post_model",
                action="pass",
                detail=f"Recommendation cited valid job criteria: {', '.join(sorted(valid_found))}",
            )
            return reply_text, tool_calls, event

        llm = context.get("llm")
        regen_text = reply_text
        regen_error: str | None = None
        if llm is not None and hasattr(llm, "complete"):
            available_list = ", ".join(sorted(valid_criteria)) if valid_criteria else "job-01.c1, job-01.c2"
            reprompt = [
                {
                    "role": "system",
                    "content": (
                        "You are HireAssist. You are updating a screening note to ensure objective compliance. "
                        f"You must explicitly cite the relevant job criteria IDs ({available_list}) "
                        "for each qualification and assessment point in your response."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Your previous screening note did not cite required job criteria IDs from {job_id}.\n"
                        f"Please rewrite the screening note, citing the exact criteria IDs ({available_list}):\n\n"
                        f"{reply_text}"
                    ),
                },
            ]
            try:
                comp = llm.complete(messages=reprompt, temperature=0.0, no_cache=context.get("no_cache", False))
                new_text = comp.text.strip()
                if "{" in new_text and '"reply"' in new_text:
                    try:
                        parsed = json.loads(new_text)
                        if isinstance(parsed, dict) and "reply" in parsed:
                            new_text = str(parsed["reply"])
                    except (json.JSONDecodeError, ValueError):
                        new_text = comp.text.strip()

                new_matches = set(CRITERIA_PATTERN.findall(new_text.lower()))
                new_valid = {m for m in new_matches if m in valid_criteria} if valid_criteria else new_matches
                if new_valid:
                    regen_text = new_text
            except (RuntimeError, ValueError, OSError, httpx.HTTPError, APIError) as exc:
                regen_error = str(exc)

        detail_text = f"Uncited recommendation: output lacked job criteria IDs for {job_id}; regenerated with grounding prompt"
        if regen_error:
            detail_text = f"{detail_text} (regeneration error: {regen_error})"

        event = ControlEvent(
            control_id=self.control_id,
            stage="post_model",
            action="flag",
            detail=detail_text,
        )
        return regen_text, tool_calls, event
