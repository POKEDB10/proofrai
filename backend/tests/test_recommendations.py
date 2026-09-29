from backend.core.gate.recommendations import generate_recommendations
from backend.core.models import CaseResult, Control


def test_generate_recommendations_unapproved_control() -> None:
    controls = [
        Control(
            id="CTL-02",
            title="Treat candidate documents as untrusted",
            risk="Prompt injection from candidate resume",
            rationale="Delimit resume",
            enforcement_point="pre_model",
            params={},
            references=["OWASP LLM01"],
            test_ids=["A-INJ-01"],
            status="proposed",
        ),
    ]

    results = [
        CaseResult(
            case_id="A-INJ-01",
            variant="controlled",
            output_text="Injected output",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="fail",
            verdict_source="deterministic",
        ),
    ]

    recs = generate_recommendations(results, controls)
    assert len(recs) >= 1
    inj_rec = next((r for r in recs if r.recommended_control_id == "CTL-02"), None)
    assert inj_rec is not None
    assert inj_rec.action_type == "approve_control"
    assert inj_rec.severity == "high"


def test_generate_recommendations_overblocking() -> None:
    controls = [
        Control(
            id="CTL-03",
            title="Scan model output",
            risk="PII leak",
            rationale="Redact",
            enforcement_point="post_model",
            params={},
            references=["OWASP LLM06"],
            test_ids=[],
            status="approved",
        ),
    ]

    results = [
        CaseResult(
            case_id="B-SUM-01",
            variant="controlled",
            output_text="Redacted",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="fail",
            verdict_source="deterministic",
            blocked_by=["CTL-03"],
        ),
    ]

    recs = generate_recommendations(results, controls)
    overblock_rec = next((r for r in recs if r.action_type == "review_overblock"), None)
    assert overblock_rec is not None
    assert overblock_rec.severity == "medium"
