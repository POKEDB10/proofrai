from backend.core.intake.schema import Conflict, InterviewAnswers

NEED_KEYWORDS = ("need", "diversity", "compliance", "monitoring", "audit", "equal opportunity", "legal")


def check_determination_without_oversight(answers: InterviewAnswers) -> Conflict | None:
    if answers.decision_impact == "determine" and answers.human_oversight == "never":
        return Conflict(
            field="human_oversight",
            message="outputs determine outcomes and no person steps in.",
        )
    return None


def check_actions_without_oversight(answers: InterviewAnswers) -> Conflict | None:
    active_actions = [a for a in answers.actions if a != "none"]
    if active_actions and answers.human_oversight == "never":
        return Conflict(
            field="actions",
            message="the assistant can take actions and no person steps in.",
        )
    return None


def check_sensitive_data_without_stated_need(answers: InterviewAnswers) -> Conflict | None:
    has_sensitive = "protected_characteristics" in answers.data_seen
    if not has_sensitive:
        return None

    # Check whether any operational need or justification is stated in limitations or tasks
    limitation_text = answers.known_limitations.lower()
    task_text = " ".join(answers.tasks).lower()
    need_stated = any(kw in limitation_text or kw in task_text for kw in NEED_KEYWORDS)

    if not need_stated:
        return Conflict(
            field="data_seen",
            message="it sees sensitive fields and no need is stated.",
        )
    return None


def evaluate_conflicts(answers: InterviewAnswers) -> list[Conflict]:
    conflicts: list[Conflict] = []

    c1 = check_determination_without_oversight(answers)
    if c1:
        conflicts.append(c1)

    c2 = check_actions_without_oversight(answers)
    if c2:
        conflicts.append(c2)

    c3 = check_sensitive_data_without_stated_need(answers)
    if c3:
        conflicts.append(c3)

    return conflicts
