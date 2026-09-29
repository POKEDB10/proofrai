import json
from pathlib import Path
from typing import Any


class SimulatedTools:
    def __init__(self, data_dir: Path | str = "backend/data") -> None:
        self.data_dir = Path(data_dir)
        self._candidates: dict[str, dict[str, Any]] = {}
        self._advanced_candidates: list[dict[str, str]] = []
        self._sent_rejections: list[dict[str, str]] = []
        self._load_candidates()

    def _load_candidates(self) -> None:
        candidates_file = self.data_dir / "candidates.json"
        if candidates_file.is_file():
            with open(candidates_file, encoding="utf-8") as f:
                records = json.load(f)
                for rec in records:
                    self._candidates[rec["id"]] = rec

    def get_candidate_record(self, candidate_id: str) -> dict[str, Any]:
        return self._candidates.get(
            candidate_id, {"error": f"Candidate {candidate_id} not found"}
        )

    def advance_candidate(
        self, candidate_id: str, stage: str = "technical_screen"
    ) -> dict[str, str]:
        record = {"candidate_id": candidate_id, "stage": stage}
        self._advanced_candidates.append(record)
        return {"status": "advanced", "candidate_id": candidate_id, "stage": stage}

    def send_rejection_email(
        self, candidate_id: str, reason: str = "qualifications"
    ) -> dict[str, str]:
        record = {"candidate_id": candidate_id, "reason": reason}
        self._sent_rejections.append(record)
        return {"status": "sent", "candidate_id": candidate_id, "reason": reason}

    def execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "get_candidate_record":
            return self.get_candidate_record(args.get("candidate_id", ""))
        if name == "advance_candidate":
            return self.advance_candidate(
                args.get("candidate_id", ""),
                args.get("stage", "technical_screen"),
            )
        if name == "send_rejection_email":
            return self.send_rejection_email(
                args.get("candidate_id", ""),
                args.get("reason", "qualifications"),
            )
        return {"error": f"Unknown tool: {name}"}
