import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.models import CaseResult, Control

DEFAULT_LEDGER_PATH = Path("backend/data/ledger.db")


def get_db(db_path: Path | str = DEFAULT_LEDGER_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        target_model TEXT NOT NULL,
        judge_model TEXT NOT NULL,
        temperature REAL NOT NULL,
        suite_version TEXT NOT NULL,
        control_config_hash TEXT NOT NULL,
        controls_yaml TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        run_id TEXT NOT NULL,
        case_id TEXT NOT NULL,
        variant TEXT NOT NULL,
        output_text TEXT NOT NULL,
        tool_calls TEXT NOT NULL,
        events TEXT NOT NULL,
        checks TEXT NOT NULL,
        verdict TEXT NOT NULL,
        verdict_source TEXT NOT NULL,
        judge_reason TEXT,
        blocked_by TEXT,
        PRIMARY KEY (run_id, case_id, variant),
        FOREIGN KEY (run_id) REFERENCES runs (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        case_id TEXT NOT NULL,
        decision TEXT NOT NULL,
        comment TEXT NOT NULL,
        reviewer TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS controls_snapshot (
        run_id TEXT NOT NULL,
        control_id TEXT NOT NULL,
        title TEXT NOT NULL,
        risk TEXT NOT NULL,
        rationale TEXT NOT NULL,
        enforcement_point TEXT NOT NULL,
        status TEXT NOT NULL,
        params TEXT NOT NULL,
        references_json TEXT NOT NULL,
        PRIMARY KEY (run_id, control_id),
        FOREIGN KEY (run_id) REFERENCES runs (id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_card (
        run_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        intended_use TEXT NOT NULL,
        known_limits TEXT NOT NULL,
        confirmed_by TEXT,
        confirmed_at TEXT,
        FOREIGN KEY (run_id) REFERENCES runs (id)
    );
    """)
    conn.commit()


def save_run(
    conn: sqlite3.Connection,
    run_id: str,
    provider: str,
    target_model: str,
    judge_model: str,
    temperature: float,
    suite_version: str,
    control_config_hash: str,
    controls_yaml: str,
    created_at: str,
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO runs (
            id, provider, target_model, judge_model, temperature,
            suite_version, control_config_hash, controls_yaml, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            provider,
            target_model,
            judge_model,
            temperature,
            suite_version,
            control_config_hash,
            controls_yaml,
            created_at,
        ),
    )
    conn.commit()


def save_controls_snapshot(
    conn: sqlite3.Connection,
    run_id: str,
    controls: list[Control],
) -> None:
    cursor = conn.cursor()
    for c in controls:
        cursor.execute(
            """
            INSERT OR REPLACE INTO controls_snapshot (
                run_id, control_id, title, risk, rationale,
                enforcement_point, status, params, references_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                c.id,
                c.title,
                c.risk,
                c.rationale,
                c.enforcement_point,
                c.status,
                json.dumps(c.params, sort_keys=True),
                json.dumps(c.references, sort_keys=True),
            ),
        )
    conn.commit()


def save_result(
    conn: sqlite3.Connection,
    run_id: str,
    result: CaseResult,
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO results (
            run_id, case_id, variant, output_text, tool_calls,
            events, checks, verdict, verdict_source, judge_reason, blocked_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            result.case_id,
            result.variant,
            result.output_text,
            json.dumps([tc.model_dump() for tc in result.tool_calls], sort_keys=True),
            json.dumps([ev.model_dump() for ev in result.events], sort_keys=True),
            json.dumps([ck.model_dump() for ck in result.checks], sort_keys=True),
            result.verdict,
            result.verdict_source,
            result.judge_reason,
            json.dumps(result.blocked_by, sort_keys=True) if result.blocked_by else None,
        ),
    )
    conn.commit()


def load_results_for_run(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[CaseResult]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT case_id, variant, output_text, tool_calls,
               events, checks, verdict, verdict_source, judge_reason, blocked_by
        FROM results
        WHERE run_id = ?
        ORDER BY case_id ASC, variant ASC
        """,
        (run_id,),
    )
    results: list[CaseResult] = []
    for row in cursor.fetchall():
        blocked_by_raw = row["blocked_by"]
        blocked_by = json.loads(blocked_by_raw) if blocked_by_raw else None
        results.append(
            CaseResult(
                case_id=row["case_id"],
                variant=row["variant"],
                output_text=row["output_text"],
                tool_calls=json.loads(row["tool_calls"]),
                events=json.loads(row["events"]),
                checks=json.loads(row["checks"]),
                verdict=row["verdict"],
                verdict_source=row["verdict_source"],
                judge_reason=row["judge_reason"],
                blocked_by=blocked_by,
            )
        )
    return results


def save_review(
    conn: sqlite3.Connection,
    run_id: str,
    case_id: str,
    decision: str,
    comment: str,
    reviewer: str = "analyst",
    created_at: str = "",
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reviews (run_id, case_id, decision, comment, reviewer, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_id, case_id, decision, comment, reviewer, created_at),
    )
    conn.commit()


def load_reviews_for_run(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, run_id, case_id, decision, comment, reviewer, created_at
        FROM reviews
        WHERE run_id = ?
        ORDER BY id ASC
        """,
        (run_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def save_system_card(
    conn: sqlite3.Connection,
    run_id: str,
    title: str,
    intended_use: str,
    known_limits: str,
    confirmed_by: str | None = None,
    confirmed_at: str | None = None,
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO system_card (
            run_id, title, intended_use, known_limits, confirmed_by, confirmed_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_id, title, intended_use, known_limits, confirmed_by, confirmed_at),
    )
    conn.commit()


def load_system_card(
    conn: sqlite3.Connection,
    run_id: str,
) -> dict[str, Any] | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT run_id, title, intended_use, known_limits, confirmed_by, confirmed_at
        FROM system_card
        WHERE run_id = ?
        """,
        (run_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def load_run(
    conn: sqlite3.Connection,
    run_id: str,
) -> dict[str, Any] | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, provider, target_model, judge_model, temperature,
               suite_version, control_config_hash, controls_yaml, created_at
        FROM runs
        WHERE id = ?
        """,
        (run_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def load_controls_snapshot(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT control_id, title, risk, rationale,
               enforcement_point, status, params, references_json
        FROM controls_snapshot
        WHERE run_id = ?
        ORDER BY control_id ASC
        """,
        (run_id,),
    )
    items: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        d = dict(row)
        d["params"] = json.loads(d["params"])
        d["references"] = json.loads(d["references_json"])
        items.append(d)
    return items


def override_case_verdict(
    conn: sqlite3.Connection,
    run_id: str,
    case_id: str,
    new_verdict: str,
    comment: str,
    reviewer: str = "analyst",
) -> CaseResult | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT case_id, variant, output_text, tool_calls,
               events, checks, verdict, verdict_source, judge_reason, blocked_by
        FROM results
        WHERE run_id = ? AND case_id = ? AND variant = 'controlled'
        """,
        (run_id, case_id),
    )
    row = cursor.fetchone()
    if not row:
        return None

    orig_verdict = row["verdict"]
    orig_reason = row["judge_reason"] or ""

    if "Original judge verdict:" not in orig_reason:
        kept_reason = (
            f"Original judge verdict: {orig_verdict}. Reason: {orig_reason or 'No judge reason recorded'}"
        )
    else:
        kept_reason = orig_reason

    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute(
        """
        UPDATE results
        SET verdict = ?, verdict_source = 'human', judge_reason = ?
        WHERE run_id = ? AND case_id = ? AND variant = 'controlled'
        """,
        (new_verdict, kept_reason, run_id, case_id),
    )

    cursor.execute(
        """
        INSERT INTO reviews (run_id, case_id, decision, comment, reviewer, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            case_id,
            f"override:{new_verdict}",
            comment or f"Overrode verdict from {orig_verdict} to {new_verdict}",
            reviewer,
            now_iso,
        ),
    )
    conn.commit()

    blocked_by_raw = row["blocked_by"]
    blocked_by = json.loads(blocked_by_raw) if blocked_by_raw else None

    return CaseResult(
        case_id=row["case_id"],
        variant="controlled",
        output_text=row["output_text"],
        tool_calls=json.loads(row["tool_calls"]),
        events=json.loads(row["events"]),
        checks=json.loads(row["checks"]),
        verdict=new_verdict,  # type: ignore[arg-type]
        verdict_source="human",
        judge_reason=kept_reason,
        blocked_by=blocked_by,
    )
