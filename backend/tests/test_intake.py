import pytest
from pydantic import ValidationError

from backend.core.intake.card import (
    build_structured_fields,
    confirm_card_in_file,
    draft_card_paragraphs,
    load_card_from_file,
    save_card_to_file,
)
from backend.core.intake.conflicts import (
    check_actions_without_oversight,
    check_determination_without_oversight,
    check_sensitive_data_without_stated_need,
    evaluate_conflicts,
)
from backend.core.intake.risks import map_risks_and_controls
from backend.core.intake.schema import InterviewAnswers, SystemCardData
from backend.core.models import Completion


def test_interview_schema_validation() -> None:
    answers = InterviewAnswers()
    assert "summarise_applications" in answers.tasks
    assert answers.human_oversight == "before_actions"
    assert answers.decision_impact == "inform"

    # Invalid human oversight literal
    with pytest.raises(ValidationError):
        InterviewAnswers(human_oversight="invalid_oversight")  # type: ignore[arg-type]


def test_conflict_rules() -> None:
    # 1. Determination without oversight
    a1 = InterviewAnswers(decision_impact="determine", human_oversight="never")
    c1 = check_determination_without_oversight(a1)
    assert c1 is not None
    assert c1.field == "human_oversight"
    assert "outputs determine outcomes and no person steps in" in c1.message

    # 2. Actions without oversight
    a2 = InterviewAnswers(actions=["advance_candidate"], human_oversight="never")
    c2 = check_actions_without_oversight(a2)
    assert c2 is not None
    assert c2.field == "actions"
    assert "the assistant can take actions and no person steps in" in c2.message

    # 3. Sensitive data without stated need
    a3 = InterviewAnswers(
        data_seen=["protected_characteristics"],
        known_limitations="General recruiting limitation with no justification.",
        tasks=["summarise_applications"],
    )
    c3 = check_sensitive_data_without_stated_need(a3)
    assert c3 is not None
    assert c3.field == "data_seen"
    assert "it sees sensitive fields and no need is stated" in c3.message

    # 4. Sensitive data with need stated in limitations -> No conflict
    a4 = InterviewAnswers(
        data_seen=["protected_characteristics"],
        known_limitations="Protected fields needed for diversity monitoring and compliance audits.",
    )
    c4 = check_sensitive_data_without_stated_need(a4)
    assert c4 is None

    # 5. Evaluate all conflicts on compliant answers -> zero conflicts
    compliant = InterviewAnswers(
        data_seen=["work_history", "skills_education"],
        actions=["none"],
        decision_impact="inform",
        human_oversight="always",
    )
    assert len(evaluate_conflicts(compliant)) == 0


def test_risk_map_controls() -> None:
    # Baseline full recruiting assistant
    a_full = InterviewAnswers(
        tasks=["summarise_applications", "draft_screening_notes"],
        data_seen=["contact_details", "protected_characteristics"],
        actions=["advance_candidate", "send_rejection_email"],
        decision_significance="significant",
    )
    risks, controls = map_risks_and_controls(a_full)
    assert len(risks) == 6
    assert set(controls) == {"CTL-01", "CTL-02", "CTL-03", "CTL-04", "CTL-05", "CTL-06"}

    # Restricted informational assistant with no tools and no sensitive fields
    a_safe = InterviewAnswers(
        tasks=["answer_candidate_questions"],
        data_seen=["work_history"],
        actions=["none"],
        decision_significance="non_significant",
        decision_impact="neither",
    )
    _risks_safe, controls_safe = map_risks_and_controls(a_safe)
    assert "CTL-01" not in controls_safe
    assert "CTL-04" not in controls_safe
    assert "CTL-05" not in controls_safe
    assert "CTL-02" in controls_safe  # handles candidate history


def test_system_card_generation_and_confirmation(tmp_path: pytest.TempPathFactory) -> None:
    answers = InterviewAnswers(
        tasks=["summarise_applications"],
        data_seen=["work_history", "skills_education"],
        decision_impact="inform",
        actions=["none"],
        human_oversight="before_actions",
        decision_significance="non_significant",
    )

    structured = build_structured_fields(answers)
    assert structured["Assistant"] == "HireAssist"
    assert structured["Decision role"] == "Informs recruiters"
    assert structured["Permitted actions"] == "No autonomous actions"

    # LLM paragraph draft with mock adapter
    class DummyLLM:
        def complete(self, messages: list[dict[str, str]], temperature: float = 0.0) -> Completion:
            return Completion(
                text=(
                    '{"intended_use": "HireAssist helps recruiters parse candidate summaries.", '
                    '"known_limits": "Recruiters must verify candidate statements."}'
                ),
                provider="mock",
                model="mock-model",
                temperature=0.0,
                cached=True,
                latency_ms=10,
            )

    intended, limits = draft_card_paragraphs(answers, adapter=DummyLLM())  # type: ignore[arg-type]
    assert "HireAssist helps recruiters" in intended
    assert "Recruiters must verify" in limits

    # Save to file
    card_file = tmp_path / "card.json"
    card = SystemCardData(
        title="HireAssist Recruiting Assistant",
        structured_fields=structured,
        intended_use=intended,
        known_limits=limits,
        status="draft",
    )
    save_card_to_file(card, card_file)

    loaded = load_card_from_file(card_file)
    assert loaded.status == "draft"
    assert loaded.confirmed_by is None

    # Confirm card
    confirmed = confirm_card_in_file(
        confirmed_by="Recruiting Lead",
        intended_use="Updated intended use text.",
        known_limits="Updated limitations.",
        file_path=card_file,
    )
    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_by == "Recruiting Lead"
    assert confirmed.confirmed_at is not None
    assert confirmed.intended_use == "Updated intended use text."
