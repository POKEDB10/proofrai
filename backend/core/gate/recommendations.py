from pydantic import BaseModel

from backend.core.models import CaseResult, Control


class Recommendation(BaseModel):
    id: str
    title: str
    vulnerability: str
    recommended_control_id: str | None
    suggested_action: str
    action_type: str
    status: str
    severity: str


def generate_recommendations(
    results: list[CaseResult],
    controls: list[Control],
) -> list[Recommendation]:
    """Analyze test run results and controls to produce actionable recommendations."""
    recommendations: list[Recommendation] = []
    controlled_by_case: dict[str, CaseResult] = {}
    baseline_by_case: dict[str, CaseResult] = {}

    for r in results:
        if r.variant == "controlled":
            controlled_by_case[r.case_id] = r
        elif r.variant == "baseline":
            baseline_by_case[r.case_id] = r

    controls_by_id = {c.id: c for c in controls}

    # 1. Check for unapproved controls that address active attack vulnerabilities
    # If any attack case failed or had issues, check which control was designed for it
    control_to_attacks = {
        "CTL-01": ["A-PII-01", "A-PII-02", "A-PII-03"],
        "CTL-02": ["A-INJ-01", "A-INJ-02", "A-INJ-03", "A-INJ-04"],
        "CTL-03": ["A-LEAK-01", "A-LEAK-02", "A-PII-01"],
        "CTL-04": ["B-NOTE-01", "B-NOTE-02", "B-NOTE-03"],
        "CTL-05": ["A-INJ-02", "A-AUTH-01"],
        "CTL-06": ["A-DISC-01", "A-DISC-02", "A-DISC-03", "A-DISC-04", "A-PROXY-01", "A-PROXY-02"],
    }

    for ctl_id, target_cases in control_to_attacks.items():
        ctl = controls_by_id.get(ctl_id)
        if ctl and ctl.status != "approved":
            # Check if any associated cases failed in controlled variant
            failed_targets = [
                cid for cid in target_cases
                if controlled_by_case.get(cid) and controlled_by_case[cid].verdict in ("fail", "needs_review")
            ]
            if failed_targets:
                recommendations.append(
                    Recommendation(
                        id=f"rec-{ctl_id.lower()}",
                        title=f"Approve {ctl.title}",
                        vulnerability=f"Active vulnerability in {ctl.risk.lower()} ({', '.join(failed_targets)}).",
                        recommended_control_id=ctl_id,
                        suggested_action=f"Approve {ctl_id} to enforce safeguards at {ctl.enforcement_point}.",
                        action_type="approve_control",
                        status="action_required",
                        severity="high",
                    )
                )

    # 2. Check for over-blocking of benign tasks
    overblocked_cases: list[CaseResult] = []
    for cid, ctrl_res in controlled_by_case.items():
        if cid.startswith("B-") and ctrl_res.verdict == "fail" and ctrl_res.blocked_by:
            overblocked_cases.append(ctrl_res)

    if overblocked_cases:
        blocked_ids = [c.case_id for c in overblocked_cases]
        culprit_controls = list({c_id for r in overblocked_cases if r.blocked_by for c_id in r.blocked_by})
        recommendations.append(
            Recommendation(
                id="rec-overblock-tuning",
                title="Calibrate over-blocking safeguards",
                vulnerability=f"{len(overblocked_cases)} legitimate recruiting tasks were over-blocked ({', '.join(blocked_ids)}).",
                recommended_control_id=culprit_controls[0] if culprit_controls else None,
                suggested_action=(
                    f"Review pattern thresholds in {', '.join(culprit_controls)} "
                    "to prevent false-positive suppression of benign candidate interactions."
                ),
                action_type="review_overblock",
                status="action_required",
                severity="medium",
            )
        )

    # 3. Check for pending human reviews
    pending_review_cases = [
        cid for cid, r in controlled_by_case.items() if r.verdict == "needs_review"
    ]
    if pending_review_cases:
        recommendations.append(
            Recommendation(
                id="rec-human-review",
                title="Resolve pending human reviews",
                vulnerability=f"{len(pending_review_cases)} cases require human reviewer decision ({', '.join(pending_review_cases[:4])}).",
                recommended_control_id=None,
                suggested_action="Review case responses in the evidence queue to accept, reject, or mark for revision.",
                action_type="review_queue",
                status="action_required",
                severity="medium",
            )
        )

    # 4. If all controls approved and no overblocking, provide status confirmation
    if not recommendations:
        recommendations.append(
            Recommendation(
                id="rec-optimal",
                title="Controls active and calibrated",
                vulnerability="No unmitigated critical vulnerabilities or excessive false-positive over-blocking detected.",
                recommended_control_id=None,
                suggested_action="Continue regular regression testing and monitor production interactions.",
                action_type="maintain_status",
                status="optimal",
                severity="low",
            )
        )

    return recommendations
