from backend.core.controls.impact import compute_control_impact_map
from backend.core.models import CaseResult, Control, ControlEvent


def test_compute_control_impact_map() -> None:
    controls = [
        Control(
            id="CTL-01",
            title="Minimise protected fields",
            risk="Disclosure of protected attributes",
            rationale="Mask fields",
            enforcement_point="pre_model",
            params={},
            references=["NIST AI RMF"],
            test_ids=["A-PII-01"],
            status="approved",
        ),
        Control(
            id="CTL-03",
            title="Scan model output",
            risk="Sensitive data leakage",
            rationale="Regex scan",
            enforcement_point="post_model",
            params={},
            references=["OWASP LLM06"],
            test_ids=["B-SUM-01"],
            status="approved",
        ),
    ]

    results = [
        CaseResult(
            case_id="A-PII-01",
            variant="baseline",
            output_text="Born 1990",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="fail",
            verdict_source="deterministic",
        ),
        CaseResult(
            case_id="A-PII-01",
            variant="controlled",
            output_text="Protected",
            tool_calls=[],
            events=[
                ControlEvent(
                    control_id="CTL-01",
                    stage="pre_model",
                    action="modify",
                    detail="Masked date_of_birth",
                )
            ],
            checks=[],
            verdict="pass",
            verdict_source="deterministic",
        ),
        CaseResult(
            case_id="B-SUM-01",
            variant="baseline",
            output_text="Good candidate",
            tool_calls=[],
            events=[],
            checks=[],
            verdict="pass",
            verdict_source="deterministic",
        ),
        CaseResult(
            case_id="B-SUM-01",
            variant="controlled",
            output_text="Blocked candidate",
            tool_calls=[],
            events=[
                ControlEvent(
                    control_id="CTL-03",
                    stage="post_model",
                    action="block",
                    detail="Over-blocked",
                )
            ],
            checks=[],
            verdict="fail",
            verdict_source="deterministic",
            blocked_by=["CTL-03"],
        ),
    ]

    impacts = compute_control_impact_map(results, controls)
    assert len(impacts) == 2

    ctl01 = next(i for i in impacts if i.control_id == "CTL-01")
    assert "A-PII-01" in ctl01.attacks_mitigated
    assert len(ctl01.benign_overblocked) == 0
    assert ctl01.events_count == 1

    ctl03 = next(i for i in impacts if i.control_id == "CTL-03")
    assert "B-SUM-01" in ctl03.benign_overblocked
    assert len(ctl03.attacks_mitigated) == 0
