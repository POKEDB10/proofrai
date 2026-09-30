import json
import os
import re
import shutil
import sqlite3
from pathlib import Path

# Locate backend root directory:
# In repo: .../backend
# On Vercel (/var/task): /var/task
_THIS_DIR = Path(__file__).resolve().parent  # backend/core
_BACKEND_DIR = _THIS_DIR.parent             # backend or /var/task
_DATA_DIR = _BACKEND_DIR / "data"


def is_vercel() -> bool:
    return bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))


def get_bundled_data_dir() -> Path:
    if _DATA_DIR.is_dir():
        return _DATA_DIR
    if Path("backend/data").is_dir():
        return Path("backend/data")
    if Path("data").is_dir():
        return Path("data")
    return _DATA_DIR


def get_data_dir() -> Path:
    if is_vercel():
        tmp_dir = Path("/tmp/data")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return tmp_dir
    return get_bundled_data_dir()


def resolve_data_path(filename: str) -> Path:
    bundled_dir = get_bundled_data_dir()
    bundled_file = bundled_dir / filename

    if is_vercel():
        tmp_file = Path("/tmp/data") / filename
        if not tmp_file.exists():
            tmp_file.parent.mkdir(parents=True, exist_ok=True)
            for source in [bundled_file, Path("data") / filename, Path("backend/data") / filename, _DATA_DIR / filename]:
                if source.is_file():
                    try:
                        shutil.copy2(str(source), str(tmp_file))
                        break
                    except Exception:
                        pass
        return tmp_file

    if bundled_file.exists():
        return bundled_file
    for alt in [Path("data") / filename, Path("backend/data") / filename]:
        if alt.exists():
            return alt
    return bundled_file


def sanitize_session_id(session_id: str | None) -> str:
    if not session_id:
        return "demo"
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)
    return cleaned[:64] or "demo"


class SessionPaths:
    """Manages isolated instance data per user session."""
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = sanitize_session_id(session_id)
        if is_vercel():
            base = Path("/tmp/sessions")
        else:
            base = Path("backend/data/sessions")

        self.session_dir = base / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.control_library_path = self.session_dir / "control_library.yaml"
        self.card_path = self.session_dir / "card.json"
        self.interview_path = self.session_dir / "interview.json"
        self.db_path = self.session_dir / "ledger.db"

        self.ensure_initialized()

    def ensure_initialized(self, force_reset: bool = False, load_demo: bool = False) -> None:
        bundled = get_bundled_data_dir()
        is_demo = (self.session_id == "demo") or load_demo

        # 1. control_library.yaml
        if force_reset or not self.control_library_path.exists():
            bundled_ctl = bundled / "control_library.yaml"
            if bundled_ctl.exists():
                shutil.copy2(str(bundled_ctl), str(self.control_library_path))

        # 2. interview.json
        if force_reset or not self.interview_path.exists():
            bundled_interview = bundled / "interview.json"
            if bundled_interview.exists():
                shutil.copy2(str(bundled_interview), str(self.interview_path))

        # 3. card.json
        if force_reset or not self.card_path.exists():
            if is_demo:
                bundled_card = bundled / "card.json"
                if bundled_card.exists():
                    shutil.copy2(str(bundled_card), str(self.card_path))
            else:
                draft_card = {
                    "title": "HireAssist Recruiting Assistant",
                    "structured_fields": {
                        "Tasks performed": "Summarise applications, Answer candidate questions, Draft screening notes",
                        "Data processed": "Work history and experience, Skills and qualifications",
                        "Decision role": "Informational only (provides summary notes to human recruiter)",
                        "Permitted actions": "No autonomous actions",
                        "Human oversight": "Always (human recruiter makes all shortlist decisions)",
                        "Target candidates": "All applicants",
                        "Significance level": "Non-significant (informational screening)",
                        "Known limitations": "Cannot verify credentials independently"
                    },
                    "intended_use": "HireAssist assists recruiting teams by drafting candidate summaries and screening notes. Human recruiters retain full decision authority.",
                    "known_limits": "The system does not make unilateral hiring commitments and cannot independently verify external credentials.",
                    "status": "draft",
                    "confirmed_by": None,
                    "confirmed_at": None
                }
                with open(self.card_path, "w", encoding="utf-8") as f:
                    json.dump(draft_card, f, indent=2)

        # 4. ledger.db
        if force_reset or not self.db_path.exists():
            if is_demo:
                bundled_db = bundled / "ledger.db"
                if bundled_db.exists():
                    shutil.copy2(str(bundled_db), str(self.db_path))
            else:
                if self.db_path.exists():
                    try:
                        self.db_path.unlink()
                    except Exception:
                        pass
                for aux in [self.session_dir / "ledger.db-wal", self.session_dir / "ledger.db-shm"]:
                    if aux.exists():
                        try:
                            aux.unlink()
                        except Exception:
                            pass
                from backend.core.ledger.database import init_db
                conn = sqlite3.connect(str(self.db_path))
                conn.execute("PRAGMA journal_mode=WAL;")
                init_db(conn)
                conn.close()
