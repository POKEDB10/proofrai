from pathlib import Path

import yaml
from pydantic import ValidationError

from backend.core.models import Control


from backend.core.paths import resolve_data_path


def load_control_library(path: Path | str = "backend/data/control_library.yaml") -> list[Control]:
    file_path = Path(path)
    if not file_path.is_file():
        resolved = resolve_data_path(Path(path).name)
        if resolved.is_file():
            file_path = resolved
        else:
            raise FileNotFoundError(f"Control library file not found: {path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Malformed YAML in control file '{path}': {exc}. "
            "Fix: ensure valid YAML syntax in the file."
        ) from exc

    if not isinstance(raw_data, list):
        raise TypeError(
            f"Malformed control file '{path}': expected a top-level list of controls. "
            "Fix: structure the document with a list of control objects starting with '-'."
        )

    controls: list[Control] = []
    for idx, item in enumerate(raw_data):
        if not isinstance(item, dict):
            raise TypeError(
                f"Malformed control file '{path}' at index {idx}: expected an object. "
                "Fix: each control item must be a key-value mapping."
            )
        try:
            control = Control.model_validate(item)
            controls.append(control)
        except ValidationError as exc:
            error_messages: list[str] = []
            for err in exc.errors():
                field_name = ".".join(str(loc) for loc in err.get("loc", []))
                err_msg = err.get("msg", "invalid value")
                error_messages.append(
                    f"Field '{field_name}' {err_msg}. "
                    f"Fix: provide a valid '{field_name}' attribute for control."
                )
            combined = "; ".join(error_messages)
            control_id = item.get("id", f"index {idx}")
            raise ValueError(
                f"Malformed control file '{path}' in control '{control_id}': {combined}"
            ) from exc

    return controls
