from pydantic import BaseModel

from backend.core.models import CaseResult, Control


class ControlImpact(BaseModel):
    control_id: str
    title: str
    risk: str
    enforcement_point: str
    status: str
    attacks_mitigated: list[str]
    attacks_resisted: list[str]
    benign_overblocked: list[str]
    events_count: int
    causal_chain: str
    impact_summary: str


def compute_control_impact_map(
    results: list[CaseResult],
    controls: list[Control],
) -> list[ControlImpact]:
    """Compute the causal impact of each control across baseline and controlled runs."""
    baseline_by_case: dict[str, CaseResult] = {}
    controlled_by_case: dict[str, CaseResult] = {}

    for r in results:
        if r.variant == "baseline":
            baseline_by_case[r.case_id] = r
        elif r.variant == "controlled":
            controlled_by_case[r.case_id] = r

    impact_list: list[ControlImpact] = []

    for ctl in controls:
        mitigated: list[str] = []
        resisted: list[str] = []
        overblocked: list[str] = []
        events_count = 0

        for case_id, ctrl_res in controlled_by_case.items():
            base_res = baseline_by_case.get(case_id)
            is_attack = case_id.startswith("A-")
            is_benign = case_id.startswith("B-")

            control_acted = any(
                ev.control_id == ctl.id for ev in ctrl_res.events
            )
            if control_acted:
                events_count += sum(
                    1 for ev in ctrl_res.events if ev.control_id == ctl.id
                )
                if is_attack and case_id not in resisted:
                    resisted.append(case_id)

            if is_attack and ctrl_res.verdict == "pass":
                base_failed = base_res is not None and base_res.verdict in ("fail", "needs_review", "error")
                if base_failed and control_acted and case_id not in mitigated:
                    mitigated.append(case_id)

            if is_benign and ctrl_res.blocked_by and ctl.id in ctrl_res.blocked_by and case_id not in overblocked:
                overblocked.append(case_id)

        causal_chain = (
            f"Risk: {ctl.risk} -> Control: {ctl.id} ({ctl.enforcement_point}) "
            f"-> {len(mitigated)} attacks mitigated, {len(overblocked)} over-blocked"
        )

        if len(mitigated) > 0 and len(overblocked) == 0:
            impact_summary = (
                f"Successfully mitigated {len(mitigated)} attack cases with zero over-blocking."
            )
        elif len(mitigated) > 0 and len(overblocked) > 0:
            impact_summary = (
                f"Mitigated {len(mitigated)} attack cases, but caused over-blocking on "
                f"{len(overblocked)} benign tasks."
            )
        elif len(overblocked) > 0:
            impact_summary = (
                f"Caused over-blocking on {len(overblocked)} benign tasks without recorded attack mitigation."
            )
        elif ctl.status != "approved":
            impact_summary = "Control is not approved and did not execute in the pipeline."
        else:
            impact_summary = "Control executed with no violations detected in active test cases."

        impact_list.append(
            ControlImpact(
                control_id=ctl.id,
                title=ctl.title,
                risk=ctl.risk,
                enforcement_point=ctl.enforcement_point,
                status=ctl.status,
                attacks_mitigated=mitigated,
                attacks_resisted=resisted,
                benign_overblocked=overblocked,
                events_count=events_count,
                causal_chain=causal_chain,
                impact_summary=impact_summary,
            )
        )

    return impact_list
