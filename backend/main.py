import sys
import types
from pathlib import Path

# Current directory where main.py lives (e.g. /var/task on Vercel, or .../backend locally)
_current_dir = Path(__file__).resolve().parent
_parent_dir = _current_dir.parent

for _p in [str(_current_dir), str(_parent_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# In Vercel serverless environments with service root "backend",
# the Lambda function root is /var/task containing app/, core/, data/, etc.
# There is no parent "backend" directory. Register a virtual "backend" package
# so all "from backend.*" imports work seamlessly.
if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ModuleNotFoundError:
        backend_pkg = types.ModuleType("backend")
        backend_pkg.__path__ = [str(_current_dir)]
        backend_pkg.__file__ = str(_current_dir / "__init__.py")
        backend_pkg.__package__ = "backend"
        sys.modules["backend"] = backend_pkg

try:
    from backend.app.main import app
except ModuleNotFoundError:
    from app.main import app

__all__ = ["app"]
