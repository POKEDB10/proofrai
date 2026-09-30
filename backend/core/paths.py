from pathlib import Path

# Locate backend root directory:
# In repo: .../backend
# On Vercel (/var/task): /var/task
_THIS_DIR = Path(__file__).resolve().parent  # backend/core
_BACKEND_DIR = _THIS_DIR.parent             # backend or /var/task
_DATA_DIR = _BACKEND_DIR / "data"


def get_data_dir() -> Path:
    if _DATA_DIR.is_dir():
        return _DATA_DIR
    if Path("backend/data").is_dir():
        return Path("backend/data")
    if Path("data").is_dir():
        return Path("data")
    return _DATA_DIR


def resolve_data_path(filename: str) -> Path:
    direct = get_data_dir() / filename
    if direct.exists():
        return direct
    for alt in [Path("data") / filename, Path("backend/data") / filename]:
        if alt.exists():
            return alt
    return direct
