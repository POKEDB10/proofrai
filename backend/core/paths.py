import os
import shutil
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
            if bundled_file.is_file():
                try:
                    shutil.copy2(str(bundled_file), str(tmp_file))
                except Exception:
                    pass
        return tmp_file

    if bundled_file.exists():
        return bundled_file
    for alt in [Path("data") / filename, Path("backend/data") / filename]:
        if alt.exists():
            return alt
    return bundled_file
