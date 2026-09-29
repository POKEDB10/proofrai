import copy
import re
from typing import Any

from backend.core.models import Control, ControlEvent

PROTECTED_FIELDS = [
    "date_of_birth",
    "gender",
    "marital_status",
    "nationality",
    "health_note",
    "home_address",
    "phone",
]


class MinimiseFieldsControl:
    def __init__(self, control: Control | None = None) -> None:
        self.control_id = control.id if control else "CTL-01"
        self.fields = PROTECTED_FIELDS
        if control and control.params and "fields_to_mask" in control.params:
            self.fields = control.params["fields_to_mask"]

    def run_pre_model(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any],
    ) -> tuple[list[dict[str, str]], ControlEvent]:
        masked_count = 0
        new_context = context

        if "candidate_record" in context and isinstance(
            context["candidate_record"], dict
        ):
            record_copy = copy.deepcopy(context["candidate_record"])
            for field in self.fields:
                if field in record_copy and record_copy[field] != "[MASKED]":
                    record_copy[field] = "[MASKED]"
                    masked_count += 1
            new_context["candidate_record"] = record_copy

        new_messages: list[dict[str, str]] = []
        for msg in messages:
            content = msg.get("content", "")
            modified_content = content
            for field in self.fields:
                pattern = rf'"{re.escape(field)}"\s*:\s*"([^"]*)"'
                matches = re.findall(pattern, modified_content)
                for val in matches:
                    if val != "[MASKED]":
                        masked_count += 1
                modified_content = re.sub(
                    pattern, f'"{field}": "[MASKED]"', modified_content
                )

            if "candidate_record" in context and isinstance(
                context["candidate_record"], dict
            ):
                orig_record = context["candidate_record"]
                for field in self.fields:
                    val = orig_record.get(field)
                    if (
                        val
                        and isinstance(val, str)
                        and val != "[MASKED]"
                        and val in modified_content
                    ):
                        modified_content = modified_content.replace(
                            val, "[MASKED]"
                        )

            new_messages.append({"role": msg["role"], "content": modified_content})

        if masked_count > 0:
            event = ControlEvent(
                control_id=self.control_id,
                stage="pre_model",
                action="modify",
                detail=f"Masked {masked_count} protected field(s) in candidate data",
            )
        else:
            event = ControlEvent(
                control_id=self.control_id,
                stage="pre_model",
                action="pass",
                detail="No protected fields found to mask",
            )

        return new_messages, event
