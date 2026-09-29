import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel

from backend.app.state import (
    active_trackers,
    execute_background_run,
    get_run_summary,
)
from backend.core.controls.loader import load_control_library
from backend.core.ledger.database import (
    DEFAULT_LEDGER_PATH,
    get_db,
    load_results_for_run,
    load_run,
    save_review,
)
from backend.core.ledger.export import build_evidence_dict, render_report_html
from backend.core.models import CaseResult, Control
from backend.core.suite.loader import load_suite

router = APIRouter(prefix="/api")
control_file_lock = threading.Lock()
CONTROL_LIBRARY_PATH = Path("backend/data/control_library.yaml")


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


@router.get("/controls", response_model=list[Control])
def get_controls() -> list[Control]:
    try:
        return load_control_library(CONTROL_LIBRARY_PATH)
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed loading controls: {exc}. Fix: check backend/data/control_library.yaml syntax.",
        ) from exc


@router.patch("/controls/{control_id}", response_model=Control)
def patch_control(control_id: str, body: UpdateControlStatusRequest) -> Control:
    if body.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Fix: status must be 'approved' or 'rejected'.",
        )

    with control_file_lock:
        if not CONTROL_LIBRARY_PATH.is_file():
            raise HTTPException(
                status_code=500,
                detail=f"Control file not found at '{CONTROL_LIBRARY_PATH}'. Fix: restore control_library.yaml.",
            )

        with open(CONTROL_LIBRARY_PATH, encoding="utf-8") as f:
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
        with open(CONTROL_LIBRARY_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False)

        return Control.model_validate(data[found_idx])


@router.post("/runs")
def start_run(
    background_tasks: BackgroundTasks,
    body: StartRunRequest | None = None,
) -> dict[str, str]:
    run_req = body or StartRunRequest()
    run_id = run_req.run_id or f"run-{uuid.uuid4().hex[:6]}"

    if run_id in active_trackers and active_trackers[run_id].status == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently running. Fix: wait for it to complete or use a different run ID.",
        )

    background_tasks.add_task(execute_background_run, run_id, run_req.no_cache)
    return {"run_id": run_id, "status": "running"}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    summary = get_run_summary(run_id)
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found. Fix: verify run ID or trigger a new run via POST /api/runs.",
        )
    return summary


@router.get("/runs/{run_id}/results", response_model=list[CaseResult])
def get_run_results(run_id: str) -> list[CaseResult]:
    conn = get_db(DEFAULT_LEDGER_PATH)
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
def post_run_review(run_id: str, body: CreateReviewRequest) -> dict[str, Any]:
    valid_decisions = {"accept", "reject", "needs_work"}
    if body.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{body.decision}'. Fix: decision must be 'accept', 'reject', or 'needs_work'.",
        )

    conn = get_db(DEFAULT_LEDGER_PATH)
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


@router.get("/runs/{run_id}/export")
def get_run_export(run_id: str) -> dict[str, Any]:
    conn = get_db(DEFAULT_LEDGER_PATH)
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
def get_run_report(run_id: str) -> Response:
    conn = get_db(DEFAULT_LEDGER_PATH)
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
