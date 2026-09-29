from typing import Any, Literal

from pydantic import BaseModel, Field

DecisionImpact = Literal["inform", "determine", "neither"]
HumanOversight = Literal["never", "before_actions", "always"]
DecisionSignificance = Literal["non_significant", "significant", "critical"]
CardStatus = Literal["draft", "confirmed"]


class InterviewAnswers(BaseModel):
    tasks: list[str] = Field(
        default_factory=lambda: [
            "summarise_applications",
            "answer_candidate_questions",
            "draft_screening_notes",
        ]
    )
    data_seen: list[str] = Field(
        default_factory=lambda: [
            "work_history",
            "skills_education",
            "contact_details",
            "protected_characteristics",
        ]
    )
    decision_impact: DecisionImpact = "inform"
    actions: list[str] = Field(
        default_factory=lambda: [
            "advance_candidate",
            "send_rejection_email",
        ]
    )
    human_oversight: HumanOversight = "before_actions"
    affected_parties: list[str] = Field(
        default_factory=lambda: [
            "job_candidates",
            "recruiters",
        ]
    )
    decision_significance: DecisionSignificance = "significant"
    known_limitations: str = (
        "Candidate resumes may contain unverified statements or prompt injections. "
        "The model does not verify educational credentials or legal work authorisation."
    )


class Conflict(BaseModel):
    field: str
    message: str


class InterviewResponse(BaseModel):
    status: str = "ok"
    conflicts: list[Conflict] = Field(default_factory=list)
    identified_risks: list[str] = Field(default_factory=list)
    proposed_controls: list[str] = Field(default_factory=list)


class SystemCardData(BaseModel):
    title: str = "HireAssist Recruiting Assistant"
    structured_fields: dict[str, Any] = Field(default_factory=dict)
    intended_use: str = ""
    known_limits: str = ""
    status: CardStatus = "draft"
    confirmed_by: str | None = None
    confirmed_at: str | None = None


class ConfirmCardRequest(BaseModel):
    confirmed_by: str
    intended_use: str
    known_limits: str
