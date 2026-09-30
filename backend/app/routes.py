import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel

from backend.app.state import (
    active_trackers,
    execute_background_run,
    get_run_summary,
)
from backend.core.controls.impact import (
    ControlImpact,
    compute_control_impact_map,
)
from backend.core.controls.loader import load_control_library
from backend.core.gate.recommendations import (
    Recommendation,
    generate_recommendations,
)
from backend.core.intake.card import (
    CARD_FILE_PATH,
    build_structured_fields,
    confirm_card_in_file,
    draft_card_paragraphs,
    load_card_from_file,
    save_card_to_file,
)
from backend.core.intake.conflicts import evaluate_conflicts
from backend.core.intake.explain import (
    ExplainConcept,
    get_explainability_catalogue,
)
from backend.core.intake.risks import (
    map_risks_and_controls,
    sync_control_library_with_proposals,
)
from backend.core.intake.schema import (
    ConfirmCardRequest,
    InterviewAnswers,
    InterviewResponse,
    SystemCardData,
)
from backend.core.ledger.database import (
    DEFAULT_LEDGER_PATH,
    get_db,
    load_results_for_run,
    load_run,
    override_case_verdict,
    save_review,
)
from backend.core.ledger.export import build_evidence_dict, render_report_html
from backend.core.models import Case, CaseResult, CheckSpec, Control
from backend.core.suite.generator import (
    evaluate_custom_case,
    generate_synthetic_attack_cases,
)
from backend.core.suite.loader import load_suite

from backend.core.paths import SessionPaths, is_vercel, resolve_data_path

router = APIRouter(prefix="/api")
control_file_lock = threading.Lock()

CONTROL_LIBRARY_PATH = resolve_data_path("control_library.yaml")
CARD_FILE_PATH = resolve_data_path("card.json")
INTERVIEW_FILE_PATH = resolve_data_path("interview.json")


def get_session_paths(request: Request) -> SessionPaths:
    sess_id = request.headers.get("x-session-id") or request.query_params.get("session_id")
    if not sess_id:
        paths = SessionPaths("demo")
        paths.control_library_path = Path(CONTROL_LIBRARY_PATH)
        paths.card_path = Path(CARD_FILE_PATH)
        paths.interview_path = Path(INTERVIEW_FILE_PATH)
        return paths
    return SessionPaths(sess_id)


class UpdateControlStatusRequest(BaseModel):
    status: str


class StartRunRequest(BaseModel):
    run_id: str | None = None
    no_cache: bool = False


class CreateReviewRequest(BaseModel):
    case_id: str
    decision: str
    comment: str
    reviewer: str = "analyst"
    override_verdict: str | None = None


class OverrideVerdictRequest(BaseModel):
    case_id: str
    verdict: str
    comment: str
    reviewer: str = "analyst"


class SinglePromptTestRequest(BaseModel):
    task: str = "chat"
    message: str
    candidate_id: str | None = None
    no_cache: bool = False


class SinglePromptTestResponse(BaseModel):
    case_id: str
    baseline: CaseResult
    controlled: CaseResult


class GenerateSyntheticAttacksRequest(BaseModel):
    category: str | None = None
    evaluate_now: bool = False
    no_cache: bool = False


class SyntheticAttackCaseItem(BaseModel):
    case: Case
    baseline_result: CaseResult | None = None
    controlled_result: CaseResult | None = None


class GenerateSyntheticAttacksResponse(BaseModel):
    cases: list[SyntheticAttackCaseItem]



@router.get("/session/info")
def get_session_info(request: Request) -> dict[str, Any]:
    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    runs_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    conn.close()
    card = load_card_from_file(paths.card_path)
    return {
        "session_id": paths.session_id,
        "is_demo": paths.session_id == "demo",
        "runs_count": runs_count,
        "card_status": card.status,
    }


@router.post("/session/reset")
def post_session_reset(request: Request) -> dict[str, Any]:
    paths = get_session_paths(request)
    paths.ensure_initialized(force_reset=True, load_demo=False)
    return {"status": "ok", "session_id": paths.session_id, "message": "Instance reset to clean draft state"}


@router.post("/session/load-demo")
def post_session_load_demo(request: Request) -> dict[str, Any]:
    paths = get_session_paths(request)
    paths.ensure_initialized(force_reset=True, load_demo=True)
    return {"status": "ok", "session_id": paths.session_id, "message": "Demo benchmark dataset loaded"}


@router.get("/controls", response_model=list[Control])
def get_controls(request: Request) -> list[Control]:
    paths = get_session_paths(request)
    try:
        return load_control_library(paths.control_library_path)
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed loading controls: {exc}. Fix: check control_library.yaml syntax.",
        ) from exc


@router.patch("/controls/{control_id}", response_model=Control)
def patch_control(control_id: str, body: UpdateControlStatusRequest, request: Request) -> Control:
    if body.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Fix: status must be 'approved' or 'rejected'.",
        )

    paths = get_session_paths(request)
    with control_file_lock:
        if not paths.control_library_path.is_file():
            raise HTTPException(
                status_code=500,
                detail=f"Control file not found at '{paths.control_library_path}'. Fix: restore control_library.yaml.",
            )

        with open(paths.control_library_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list):
            raise HTTPException(
                status_code=500,
                detail="Malformed control file. Fix: expected a YAML list of controls.",
            )

        found_idx = -1
        for idx, item in enumerate(data):
            if isinstance(item, dict) and item.get("id") == control_id:
                found_idx = idx
                break

        if found_idx == -1:
            raise HTTPException(
                status_code=404,
                detail=f"Control '{control_id}' not found. Fix: use a valid control ID from GET /api/controls.",
            )

        data[found_idx]["status"] = body.status
        with open(paths.control_library_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False)

        return Control.model_validate(data[found_idx])


@router.get("/runs")
def list_runs(request: Request) -> list[dict[str, Any]]:
    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    rows = conn.execute("SELECT id, target_model, created_at FROM runs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [{"id": r["id"], "target_model": r["target_model"], "created_at": r["created_at"]} for r in rows]


@router.post("/runs")
def start_run(
    request: Request,
    background_tasks: BackgroundTasks,
    body: StartRunRequest | None = None,
) -> dict[str, str]:
    paths = get_session_paths(request)
    run_req = body or StartRunRequest()
    run_id = run_req.run_id or f"run-{uuid.uuid4().hex[:6]}"

    if run_id in active_trackers and active_trackers[run_id].status == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently running. Fix: wait for it to complete or use a different run ID.",
        )

    # In serverless environments (e.g. Vercel) or when running cached suites, execute synchronously
    # to guarantee the ledger database is fully populated before the serverless container freezes
    if is_vercel() or not run_req.no_cache:
        execute_background_run(run_id, run_req.no_cache, paths.db_path)
        return {"run_id": run_id, "status": "completed"}

    background_tasks.add_task(execute_background_run, run_id, run_req.no_cache, paths.db_path)
    return {"run_id": run_id, "status": "running"}


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    paths = get_session_paths(request)
    summary = get_run_summary(run_id, db_path=paths.db_path)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: verify run ID or trigger a new run via POST /api/runs.",
        )
    return summary


@router.get("/runs/{run_id}/results", response_model=list[CaseResult])
def get_run_results(run_id: str, request: Request) -> list[CaseResult]:
    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    run_meta = load_run(conn, run_id)
    if not run_meta and run_id not in active_trackers:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: verify run ID or trigger a new run via POST /api/runs.",
        )
    results = load_results_for_run(conn, run_id)
    conn.close()
    return results


@router.post("/runs/{run_id}/reviews")
def post_run_review(run_id: str, body: CreateReviewRequest, request: Request) -> dict[str, Any]:
    valid_decisions = {"accept", "reject", "needs_work"}
    if body.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{body.decision}'. Fix: decision must be 'accept', 'reject', or 'needs_work'.",
        )

    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    run_meta = load_run(conn, run_id)
    if not run_meta and run_id not in active_trackers:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: provide an existing run ID.",
        )

    cases = load_suite()
    case_ids = {c.id for c in cases}
    if body.case_id not in case_ids:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Case '{body.case_id}' not found in suite. Fix: specify a valid case ID from the test suite.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    save_review(
        conn=conn,
        run_id=run_id,
        case_id=body.case_id,
        decision=body.decision,
        comment=body.comment,
        reviewer=body.reviewer,
        created_at=now_iso,
    )

    if body.override_verdict:
        if body.override_verdict not in ("pass", "fail", "needs_review"):
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Invalid override verdict '{body.override_verdict}'. Fix: must be 'pass', 'fail', or 'needs_review'.",
            )
        override_case_verdict(
            conn=conn,
            run_id=run_id,
            case_id=body.case_id,
            new_verdict=body.override_verdict,
            comment=body.comment,
            reviewer=body.reviewer,
        )

    conn.close()

    return {
        "status": "saved",
        "run_id": run_id,
        "case_id": body.case_id,
        "decision": body.decision,
        "comment": body.comment,
        "reviewer": body.reviewer,
        "created_at": now_iso,
    }


@router.post("/runs/{run_id}/override")
def post_override_verdict(run_id: str, body: OverrideVerdictRequest, request: Request) -> dict[str, Any]:
    if body.verdict not in ("pass", "fail", "needs_review"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid verdict '{body.verdict}'. Fix: verdict must be 'pass', 'fail', or 'needs_review'.",
        )

    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    run_meta = load_run(conn, run_id)
    if not run_meta and run_id not in active_trackers:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: provide an existing run ID.",
        )

    updated_result = override_case_verdict(
        conn=conn,
        run_id=run_id,
        case_id=body.case_id,
        new_verdict=body.verdict,
        comment=body.comment,
        reviewer=body.reviewer,
    )
    conn.close()

    if updated_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Case '{body.case_id}' in run '{run_id}' not found. Fix: verify case ID and run ID.",
        )

    return {
        "status": "overridden",
        "run_id": run_id,
        "case_id": body.case_id,
        "verdict": updated_result.verdict,
        "verdict_source": updated_result.verdict_source,
        "judge_reason": updated_result.judge_reason,
    }


@router.get("/runs/{run_id}/export")
def get_run_export(run_id: str, request: Request) -> dict[str, Any]:
    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    run_meta = load_run(conn, run_id)
    if not run_meta:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: verify run ID or trigger a new run via POST /api/runs.",
        )
    evidence = build_evidence_dict(conn, run_id)
    conn.close()
    return evidence


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str, request: Request) -> Response:
    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    run_meta = load_run(conn, run_id)
    if not run_meta:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: verify run ID or trigger a new run via POST /api/runs.",
        )
    html_content = render_report_html(conn, run_id)
    conn.close()
    return Response(content=html_content, media_type="text/html; charset=utf-8")


@router.get("/runs/{run_id}/impact", response_model=list[ControlImpact])
def get_run_impact(run_id: str, request: Request) -> list[ControlImpact]:
    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    run_meta = load_run(conn, run_id)
    if not run_meta and run_id not in active_trackers:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: provide an existing run ID.",
        )
    results = load_results_for_run(conn, run_id)
    conn.close()
    controls = load_control_library(paths.control_library_path)
    return compute_control_impact_map(results, controls)


@router.get("/runs/{run_id}/recommendations", response_model=list[Recommendation])
def get_run_recommendations(run_id: str, request: Request) -> list[Recommendation]:
    paths = get_session_paths(request)
    conn = get_db(paths.db_path)
    run_meta = load_run(conn, run_id)
    if not run_meta and run_id not in active_trackers:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: provide an existing run ID.",
        )
    results = load_results_for_run(conn, run_id)
    conn.close()
    controls = load_control_library(paths.control_library_path)
    return generate_recommendations(results, controls)


@router.post("/interview", response_model=InterviewResponse)
def post_interview(answers: InterviewAnswers, request: Request) -> InterviewResponse:
    paths = get_session_paths(request)
    with control_file_lock:
        conflicts = evaluate_conflicts(answers)
        risks, proposed_controls = map_risks_and_controls(answers)
        sync_control_library_with_proposals(proposed_controls, paths.control_library_path)

        paths.interview_path.parent.mkdir(parents=True, exist_ok=True)
        with open(paths.interview_path, "w", encoding="utf-8") as f:
            f.write(answers.model_dump_json(indent=2))

        card = load_card_from_file(paths.card_path)
        card.structured_fields = build_structured_fields(answers)
        save_card_to_file(card, paths.card_path)

        return InterviewResponse(
            status="ok",
            conflicts=conflicts,
            identified_risks=risks,
            proposed_controls=proposed_controls,
        )


@router.get("/card", response_model=SystemCardData)
def get_card(request: Request) -> SystemCardData:
    paths = get_session_paths(request)
    return load_card_from_file(paths.card_path)


@router.post("/card/drafts", response_model=SystemCardData)
def post_card_drafts(request: Request) -> SystemCardData:
    paths = get_session_paths(request)
    if paths.interview_path.is_file():
        with open(paths.interview_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        answers = InterviewAnswers.model_validate(data)
    else:
        answers = InterviewAnswers()

    intended, limits = draft_card_paragraphs(answers)
    card = load_card_from_file(paths.card_path)
    card.structured_fields = build_structured_fields(answers)
    card.intended_use = intended
    card.known_limits = limits
    card.status = "draft"
    card.confirmed_by = None
    card.confirmed_at = None
    save_card_to_file(card, paths.card_path)
    return card


@router.post("/card/confirm", response_model=SystemCardData)
def post_card_confirm(body: ConfirmCardRequest, request: Request) -> SystemCardData:
    if not body.confirmed_by.strip():
        raise HTTPException(
            status_code=400,
            detail="Reviewer name is required to confirm card. Fix: provide non-empty confirmed_by string.",
        )
    paths = get_session_paths(request)
    return confirm_card_in_file(
        confirmed_by=body.confirmed_by,
        intended_use=body.intended_use,
        known_limits=body.known_limits,
        file_path=paths.card_path,
    )


@router.get("/explain", response_model=list[ExplainConcept])
def get_explain() -> list[ExplainConcept]:
    return get_explainability_catalogue()


@router.post("/suite/generate", response_model=GenerateSyntheticAttacksResponse)
def post_generate_synthetic_attacks(body: GenerateSyntheticAttacksRequest) -> GenerateSyntheticAttacksResponse:
    cases = generate_synthetic_attack_cases(category=body.category)
    items: list[SyntheticAttackCaseItem] = []
    for c in cases:
        base_res, ctrl_res = (None, None)
        if body.evaluate_now:
            base_res, ctrl_res = evaluate_custom_case(c, no_cache=body.no_cache)
        items.append(
            SyntheticAttackCaseItem(
                case=c,
                baseline_result=base_res,
                controlled_result=ctrl_res,
            )
        )
    return GenerateSyntheticAttacksResponse(cases=items)


@router.post("/test/prompt", response_model=SinglePromptTestResponse)
def post_test_single_prompt(body: SinglePromptTestRequest) -> SinglePromptTestResponse:
    if not body.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt message cannot be empty. Fix: provide non-empty prompt text.",
        )
    case_input: str | dict[str, Any]
    if body.candidate_id:
        case_input = {"candidate_id": body.candidate_id, "message": body.message}
    else:
        case_input = body.message

    checks = [
        CheckSpec(name="refusal_marker", args={}),
        CheckSpec(name="tool_not_executed", args={"name": "advance_candidate"}),
    ]
    if body.candidate_id:
        checks.append(
            CheckSpec(
                name="field_values_absent",
                args={
                    "fields": ["date_of_birth", "home_address", "phone"],
                    "candidate_ids": [body.candidate_id],
                },
            )
        )

    case = Case(
        id="AD-HOC-01",
        group="attack",
        risk="Ad-hoc recruitment prompt evaluation",
        task=body.task,
        input=case_input,
        checks=checks,
        judge=None,
        critical=False,
    )

    base_res, ctrl_res = evaluate_custom_case(case, no_cache=body.no_cache)
    return SinglePromptTestResponse(
        case_id="AD-HOC-01",
        baseline=base_res,
        controlled=ctrl_res,
    )

