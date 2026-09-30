import sys
import types
from pathlib import Path

# Ensure backend and repository root are in sys.path
_backend_dir = Path(__file__).resolve().parent.parent
_repo_root = _backend_dir.parent

for _p in [str(_backend_dir), str(_repo_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ModuleNotFoundError:
        backend_pkg = types.ModuleType("backend")
        backend_pkg.__path__ = [str(_backend_dir)]
        backend_pkg.__file__ = str(_backend_dir / "__init__.py")
        backend_pkg.__package__ = "backend"
        sys.modules["backend"] = backend_pkg

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.routes import router

app = FastAPI(title="ProofRAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    err_msgs: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(elem) for elem in err.get("loc", []))
        msg = err.get("msg", "invalid input")
        err_msgs.append(f"Validation error on '{loc}': {msg}. Fix: provide a valid value for '{loc}'.")
    combined = " ".join(err_msgs)
    return JSONResponse(status_code=422, content={"detail": combined})


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router)
