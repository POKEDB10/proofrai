import json
from pathlib import Path

from backend.core.target.assistant import HireAssist, HireAssistHooks
from backend.core.target.prompts import BASELINE_SYSTEM_PROMPT
from backend.core.target.tools import SimulatedTools


def test_candidates_and_jobs_data() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidates_path = repo_root / "backend" / "data" / "candidates.json"
    jobs_path = repo_root / "backend" / "data" / "jobs.json"

    assert candidates_path.is_file()
    assert jobs_path.is_file()

    with open(candidates_path, encoding="utf-8") as f:
        candidates = json.load(f)
    assert len(candidates) == 8

    required_fields = [
        "id",
        "name",
        "email",
        "phone",
        "date_of_birth",
        "gender",
        "marital_status",
        "nationality",
        "health_note",
        "home_address",
        "work_authorisation",
        "skills",
        "years_experience",
        "resume_text",
    ]
    for c in candidates:
        for rf in required_fields:
            assert rf in c

    cand_07 = next(c for c in candidates if c["id"] == "cand-07")
    assert "ORCHID-77" in cand_07["resume_text"]

    cand_08 = next(c for c in candidates if c["id"] == "cand-08")
    assert "advance_candidate" in cand_08["resume_text"]
    assert "system prompt" in cand_08["resume_text"]

    with open(jobs_path, encoding="utf-8") as f:
        jobs = json.load(f)
    assert len(jobs) == 2
    for job in jobs:
        assert 4 <= len(job["criteria"]) <= 5
        for criterion in job["criteria"]:
            assert criterion["id"].startswith(job["id"])


def test_simulated_tools() -> None:
    tools = SimulatedTools()
    cand = tools.get_candidate_record("cand-03")
    assert cand["id"] == "cand-03"

    res_advance = tools.advance_candidate("cand-03", "interview")
    assert res_advance["status"] == "advanced"

    res_reject = tools.send_rejection_email("cand-01", "overqualified")
    assert res_reject["status"] == "sent"


def test_baseline_system_prompt_canary() -> None:
    assert "SYSPROMPT-CANARY-5f3a" in BASELINE_SYSTEM_PROMPT


def test_hireassist_reply_parsing() -> None:
    assistant = HireAssist()
    valid_json = '{"reply": "Evaluated candidate", "tool_calls": [{"name": "advance_candidate", "args": {"candidate_id": "cand-01"}}]}'
    reply, calls = assistant._parse_reply(valid_json)
    assert reply == "Evaluated candidate"
    assert len(calls) == 1
    assert calls[0].name == "advance_candidate"

    plain_text = "Just a plain response without json"
    reply_plain, calls_plain = assistant._parse_reply(plain_text)
    assert reply_plain == plain_text
    assert len(calls_plain) == 0


def test_hireassist_hooks() -> None:
    hooks = HireAssistHooks()
    messages = [{"role": "user", "content": "hi"}]
    assert hooks.pre_model_hook(messages, {}) == messages
    reply, calls = hooks.post_model_hook("hello", [], {})
    assert reply == "hello"
    assert calls == []
