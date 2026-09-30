import json
import re
from pathlib import Path
from typing import Any

from backend.core.models import Control, ControlEvent, ToolCall

SENSITIVE_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    r"\bDOB-[A-Z0-9-]+\b",
    r"\bTEL-[A-Z0-9-]+\b",
    r"\bNAT-[A-Z0-9-]+\b",
    r"\bHEALTH-[A-Z0-9-]+\b",
    r"\bMARITAL-[A-Z0-9-]+\b",
    r"\bADDR-[A-Z0-9-]+\b",
    r"\bGENDER-[A-Z0-9-]+\b",
]

SENSITIVE_KEYS = [
    "date_of_birth",
    "gender",
    "marital_status",
    "nationality",
    "health_note",
    "home_address",
    "phone",
    "email",
]


class ScanOutputControl:
    def __init__(
        self,
        control: Control | None = None,
        data_dir: Path | str = "backend/data",
    ) -> None:
        self.control_id = control.id if control else "CTL-03"
        self.redact_mask = (
            control.params.get("redact_mask", "[REDACTED]")
            if control and control.params
            else "[REDACTED]"
        )
        self.sensitive_values: set[str] = set()
        self._load_candidate_sensitive_values(Path(data_dir))

    def _load_candidate_sensitive_values(self, data_dir: Path) -> None:
        cand_path = data_dir / "candidates.json"
        if not cand_path.is_file():
            from backend.core.paths import resolve_data_path
            cand_path = resolve_data_path("candidates.json")
        if not cand_path.is_file():
            return
        try:
            with open(cand_path, encoding="utf-8") as f:
                candidates = json.load(f)
                for cand in candidates:
                    for key in SENSITIVE_KEYS:
                        val = cand.get(key)
                        if val and isinstance(val, str) and len(val.strip()) > 2:
                            self.sensitive_values.add(val.strip())
        except (json.JSONDecodeError, OSError):
            pass

    def run_post_model(
        self,
        reply_text: str,
        tool_calls: list[ToolCall],
        context: dict[str, Any],
    ) -> tuple[str, list[ToolCall], ControlEvent]:
        modified_text = reply_text
        redactions: list[str] = []

        for val in sorted(self.sensitive_values, key=len, reverse=True):
            count = modified_text.count(val)
            if count > 0:
                modified_text = modified_text.replace(val, self.redact_mask)
                redactions.extend([val] * count)

        for pat in SENSITIVE_PATTERNS:
            matches = re.findall(pat, modified_text)
            for m in matches:
                if m != self.redact_mask:
                    count = modified_text.count(m)
                    if count > 0:
                        modified_text = modified_text.replace(m, self.redact_mask)
                        redactions.extend([m] * count)

        if not redactions:
            event = ControlEvent(
                control_id=self.control_id,
                stage="post_model",
                action="pass",
                detail="No sensitive personal data detected in output",
            )
            return reply_text, tool_calls, event

        if len(redactions) > 3:
            event = ControlEvent(
                control_id=self.control_id,
                stage="post_model",
                action="block",
                detail=(
                    f"Blocked output containing {len(redactions)} sensitive "
                    "personal value(s) exceeding threshold"
                ),
            )
            return (
                "Refusal: Output contained multiple sensitive candidate values and was blocked by policy.",
                [],
                event,
            )

        event = ControlEvent(
            control_id=self.control_id,
            stage="post_model",
            action="modify",
            detail=f"Redacted {len(redactions)} sensitive personal value(s) from output",
        )
        return modified_text, tool_calls, event
