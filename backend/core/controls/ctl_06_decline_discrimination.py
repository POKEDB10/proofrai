import re
from typing import Any

from backend.core.models import Control, ControlEvent

DISCRIMINATION_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "age",
        "filter_or_rank_by_age",
        re.compile(
            r"(?:filter\s+out|exclude|disqualify|remove).*(?:candidates\s+over\s+\d+|\b(?:over|under)\s+\d+\s+years?\s+old\b|\bage\b)|"
            r"(?:rank|prioritise|prefer).*(?:younger|older|\bage\b)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "gender",
        "filter_or_rank_by_gender",
        re.compile(
            r"(?:rank|prioritise|prefer)\s+(?:male|female|men|women)\s+(?:candidates\s+ahead|ahead|first)|"
            r"(?:filter|exclude|disqualify).*(?:male|female|men|women)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "nationality",
        "filter_or_exclude_by_nationality",
        re.compile(
            r"(?:only\s+evaluate.*local\s+citizenship|exclude.*foreign\s+nationals|filter.*by\s+nationality|"
            r"exclude.*non-citizens|disqualify.*foreigners)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "family_status",
        "filter_by_family_or_marital_status",
        re.compile(
            r"(?:filter\s+out|exclude|disqualify).*(?:young\s+children|marital|family\s+commitments|pregnant|maternity)|"
            r"(?:filter|rank).*by\s+(?:family|marital)\s+status",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "proxy_age",
        "proxy_age_by_graduation_year",
        re.compile(
            r"(?:graduation\s+years?.*(?:younger|adaptable|recent)|graduated\s+after\s+\d{4}.*younger|"
            r"rank\s+candidates\s+who\s+graduated\s+after\s+\d{4})",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "proxy_ethnicity",
        "proxy_ethnicity_by_name",
        re.compile(
            r"(?:infer.*(?:cultural|ethnic)\s+backgrounds|candidate\s+names.*infer|estimate\s+regional\s+representation|"
            r"infer.*cultural\s+background)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
]

DECLINE_MESSAGE = (
    "I cannot fulfill this request. Company policy and fair hiring standards prohibit "
    "filtering or ranking candidates based on age, gender, nationality, family status, "
    "or proxy demographic attributes. Candidate assessments must be grounded strictly "
    "in job-related qualifications and criteria."
)


class DeclineDiscriminationControl:
    def __init__(self, control: Control | None = None) -> None:
        self.control_id = control.id if control else "CTL-06"

    def run_pre_model(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any],
    ) -> tuple[list[dict[str, str]], ControlEvent]:
        user_texts: list[str] = []
        for msg in messages:
            if msg.get("role") == "user":
                user_texts.append(msg.get("content", ""))
        if context.get("message"):
            user_texts.append(str(context["message"]))

        combined_input = " ".join(user_texts)

        for category, pattern_name, pattern in DISCRIMINATION_PATTERNS:
            if pattern.search(combined_input):
                event = ControlEvent(
                    control_id=self.control_id,
                    stage="pre_model",
                    action="block",
                    detail=f"Blocked request attempting discriminatory filtering or proxy pattern: {pattern_name} ({category})",
                )
                context["blocked"] = True
                context["block_reply"] = DECLINE_MESSAGE
                return messages, event

        event = ControlEvent(
            control_id=self.control_id,
            stage="pre_model",
            action="pass",
            detail="No discriminatory filtering or proxy patterns detected in request",
        )
        return messages, event
