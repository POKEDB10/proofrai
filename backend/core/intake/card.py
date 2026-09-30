import json
from datetime import datetime, timezone
from pathlib import Path

from backend.core.intake.schema import InterviewAnswers, SystemCardData
from backend.core.llm.adapter import LLMAdapter
from backend.core.paths import resolve_data_path

CARD_FILE_PATH = resolve_data_path("card.json")

TASK_LABELS: dict[str, str] = {
    "summarise_applications": "Summarise applications",
    "answer_candidate_questions": "Answer candidate questions",
    "draft_screening_notes": "Draft screening notes",
    "send_messages": "Send messages",
}

DATA_LABELS: dict[str, str] = {
    "work_history": "Work history and experience",
    "skills_education": "Skills and qualifications",
    "contact_details": "Contact details",
    "protected_characteristics": "Protected characteristics",
}

ACTION_LABELS: dict[str, str] = {
    "none": "No autonomous actions",
    "advance_candidate": "Advance candidate",
    "send_rejection_email": "Send rejection email",
    "schedule_interview": "Schedule interview",
}

OVERSIGHT_LABELS: dict[str, str] = {
    "never": "Never",
    "before_actions": "Before actions",
    "always": "Always",
}

SIGNIFICANCE_LABELS: dict[str, str] = {
    "non_significant": "Non-significant (informational screening)",
    "significant": "Significant (affects employment opportunity)",
    "critical": "Critical (automated final hiring decision)",
}


def build_structured_fields(answers: InterviewAnswers) -> dict[str, str]:
    tasks_str = ", ".join(TASK_LABELS.get(t, t) for t in answers.tasks) or "None"
    data_str = ", ".join(DATA_LABELS.get(d, d) for d in answers.data_seen) or "None"
    actions_str = ", ".join(ACTION_LABELS.get(a, a) for a in answers.actions) or "None"
    oversight_str = OVERSIGHT_LABELS.get(answers.human_oversight, answers.human_oversight)
    significance_str = SIGNIFICANCE_LABELS.get(
        answers.decision_significance, answers.decision_significance
    )
    parties_str = ", ".join(p.replace("_", " ").capitalize() for p in answers.affected_parties) or "None"
    impact_str = (
        "Informs recruiters"
        if answers.decision_impact == "inform"
        else ("Determines outcomes" if answers.decision_impact == "determine" else "Neither")
    )

    return {
        "Assistant": "HireAssist",
        "Tasks performed": tasks_str,
        "Data processed": data_str,
        "Decision role": impact_str,
        "Permitted actions": actions_str,
        "Human oversight": oversight_str,
        "Affected parties": parties_str,
        "Decision significance": significance_str,
    }


def draft_card_paragraphs(
    answers: InterviewAnswers,
    adapter: LLMAdapter | None = None,
) -> tuple[str, str]:
    structured = build_structured_fields(answers)
    prompt = (
        "You are drafting the intended use and known limits sections of an AI system card.\n"
        "Draft two plain paragraphs based strictly on these system specifications:\n"
        f"- Tasks: {structured['Tasks performed']}\n"
        f"- Data: {structured['Data processed']}\n"
        f"- Decision role: {structured['Decision role']}\n"
        f"- Actions: {structured['Permitted actions']}\n"
        f"- Oversight: {structured['Human oversight']}\n"
        f"- Stated limits: {answers.known_limitations}\n\n"
        "Write in plain sentences without promotional words. Return a valid JSON object with exactly two keys:\n"
        "{\n"
        '  "intended_use": "one plain paragraph describing purpose and recruiter workflow",\n'
        '  "known_limits": "one plain paragraph describing operational constraints and verification requirements"\n'
        "}"
    )

    llm = adapter or LLMAdapter()
    try:
        messages = [
            {"role": "system", "content": "You draft factual system cards. Output JSON only."},
            {"role": "user", "content": prompt},
        ]
        completion = llm.complete(
            messages=messages,
            temperature=0.0,
        )
        text = completion.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        intended_use = str(data.get("intended_use", "")).strip()
        known_limits = str(data.get("known_limits", "")).strip()
        if intended_use and known_limits:
            return intended_use, known_limits
    except (json.JSONDecodeError, KeyError, RuntimeError, ValueError):
        pass

    # Deterministic fallback paragraphs derived strictly from interview specifications
    fallback_intended = (
        f"HireAssist is intended to assist recruiting teams by performing {structured['Tasks performed'].lower()}. "
        f"It processes candidate information including {structured['Data processed'].lower()} to provide summary "
        f"notes that inform human recruiters. Human oversight is maintained {structured['Human oversight'].lower()}."
    )
    fallback_limits = (
        f"{answers.known_limitations} "
        "The system does not make unilateral hiring commitments and cannot independently verify external credentials."
    )
    return fallback_intended, fallback_limits


def load_card_from_file(file_path: Path | str = CARD_FILE_PATH) -> SystemCardData:
    path = Path(file_path)
    if not path.is_file():
        default_answers = InterviewAnswers()
        structured = build_structured_fields(default_answers)
        intended, limits = draft_card_paragraphs(default_answers)
        card = SystemCardData(
            title="HireAssist Recruiting Assistant",
            structured_fields=structured,
            intended_use=intended,
            known_limits=limits,
            status="draft",
        )
        save_card_to_file(card, path)
        return card

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return SystemCardData.model_validate(data)


def save_card_to_file(
    card: SystemCardData,
    file_path: Path | str = CARD_FILE_PATH,
) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card.model_dump(), f, indent=2)


def confirm_card_in_file(
    confirmed_by: str,
    intended_use: str,
    known_limits: str,
    file_path: Path | str = CARD_FILE_PATH,
) -> SystemCardData:
    card = load_card_from_file(file_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    card.intended_use = intended_use.strip()
    card.known_limits = known_limits.strip()
    card.confirmed_by = confirmed_by.strip()
    card.confirmed_at = now_iso
    card.status = "confirmed"
    save_card_to_file(card, file_path)
    return card
