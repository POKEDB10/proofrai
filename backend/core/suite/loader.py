from pathlib import Path

import yaml
from pydantic import ValidationError

from backend.core.models import Case


from backend.core.paths import resolve_data_path


def load_suite(path: Path | str = "backend/data/suite.yaml") -> list[Case]:
    file_path = Path(path)
    if not file_path.is_file():
        resolved = resolve_data_path(Path(path).name)
        if resolved.is_file():
            file_path = resolved
        else:
            raise FileNotFoundError(f"Suite file not found: {path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"Malformed YAML in suite file '{path}': {exc}. "
            "Fix: ensure valid YAML syntax in the suite file."
        ) from exc

    if not isinstance(raw_data, list):
        raise TypeError(
            f"Malformed suite file '{path}': expected a top-level list of cases. "
            "Fix: structure the document with a list of case objects starting with '-'."
        )

    cases: list[Case] = []
    seen_ids: set[str] = set()

    for idx, item in enumerate(raw_data):
        if not isinstance(item, dict):
            raise TypeError(
                f"Malformed suite file '{path}' at index {idx}: expected an object. "
                "Fix: each case entry must be a key-value mapping."
            )
        try:
            case_obj = Case.model_validate(item)
            if case_obj.id in seen_ids:
                raise ValueError(
                    f"Duplicate case id '{case_obj.id}' found in suite file '{path}'."
                )
            seen_ids.add(case_obj.id)
            cases.append(case_obj)
        except ValidationError as exc:
            error_messages: list[str] = []
            for err in exc.errors():
                field_name = ".".join(str(loc) for loc in err.get("loc", []))
                err_msg = err.get("msg", "invalid value")
                error_messages.append(
                    f"Field '{field_name}' {err_msg}. "
                    f"Fix: provide a valid '{field_name}' attribute for case."
                )
            combined = "; ".join(error_messages)
            case_id = item.get("id", f"index {idx}")
            raise ValueError(
                f"Malformed suite file '{path}' in case '{case_id}': {combined}"
            ) from exc

    return cases
