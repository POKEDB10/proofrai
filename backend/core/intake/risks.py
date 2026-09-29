from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from backend.core.intake.schema import InterviewAnswers

RiskPredicate = Callable[[InterviewAnswers], bool]

RISK_DEFINITIONS: list[dict[str, Any]] = [
    {
        "control_id": "CTL-01",
        "risk": "Disclosure and bias from protected candidate attributes",
        "check": lambda a: bool({"protected_characteristics", "contact_details"} & set(a.data_seen)),
    },
    {
        "control_id": "CTL-02",
        "risk": "Prompt injection from candidate supplied resume text",
        "check": lambda a: "summarise_applications" in a.tasks
        or "answer_candidate_questions" in a.tasks
        or "work_history" in a.data_seen,
    },
    {
        "control_id": "CTL-03",
        "risk": "Sensitive candidate data leakage in generated responses",
        "check": lambda a: bool({"contact_details", "protected_characteristics"} & set(a.data_seen))
        or a.decision_impact != "neither",
    },
    {
        "control_id": "CTL-04",
        "risk": "Unauthorised or out of scope tool execution",
        "check": lambda a: any(act != "none" for act in a.actions),
    },
    {
        "control_id": "CTL-05",
        "risk": "Autonomous execution of high-impact recruiting actions",
        "check": lambda a: bool({"advance_candidate", "send_rejection_email"} & set(a.actions))
        or a.decision_significance in ("significant", "critical"),
    },
    {
        "control_id": "CTL-06",
        "risk": "Hallucination or ungrounded claims in assessment",
        "check": lambda a: "draft_screening_notes" in a.tasks or a.decision_impact in ("inform", "determine"),
    },
]


def map_risks_and_controls(answers: InterviewAnswers) -> tuple[list[str], list[str]]:
    risks: list[str] = []
    proposed_controls: list[str] = []

    for item in RISK_DEFINITIONS:
        predicate: RiskPredicate = item["check"]
        if predicate(answers):
            risks.append(item["risk"])
            proposed_controls.append(item["control_id"])

    return risks, proposed_controls


def sync_control_library_with_proposals(
    proposed_control_ids: list[str],
    library_path: Path | str = "backend/data/control_library.yaml",
) -> list[dict[str, Any]]:
    path = Path(library_path)
    if not path.is_file():
        return []

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        return []

    proposed_set = set(proposed_control_ids)
    for ctl in data:
        if isinstance(ctl, dict) and "id" in ctl:
            cid = ctl["id"]
            if cid in proposed_set:
                if ctl.get("status") == "rejected":
                    ctl["status"] = "proposed"
            else:
                ctl["status"] = "rejected"

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)

    return data
