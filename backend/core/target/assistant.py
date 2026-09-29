import json
import re
from dataclasses import dataclass
from typing import Any

from backend.core.llm.adapter import LLMAdapter
from backend.core.models import Completion, ToolCall
from backend.core.target.prompts import BASELINE_SYSTEM_PROMPT
from backend.core.target.tools import SimulatedTools


class HireAssistHooks:
    def pre_model_hook(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any],
    ) -> list[dict[str, str]]:
        return messages

    def post_model_hook(
        self,
        reply_text: str,
        tool_calls: list[ToolCall],
        context: dict[str, Any],
    ) -> tuple[str, list[ToolCall]]:
        return reply_text, tool_calls

    def tool_gate_hook(
        self,
        tool_call: ToolCall,
        context: dict[str, Any],
    ) -> ToolCall | None:
        return tool_call


@dataclass
class TargetExecution:
    output_text: str
    tool_calls: list[ToolCall]
    raw_completion: Completion


class HireAssist:
    def __init__(
        self,
        llm: LLMAdapter | None = None,
        tools: SimulatedTools | None = None,
        hooks: HireAssistHooks | None = None,
    ) -> None:
        self.llm = llm or LLMAdapter()
        self.tools = tools or SimulatedTools()
        self.hooks = hooks or HireAssistHooks()

    def _parse_reply(self, text: str) -> tuple[str, list[ToolCall]]:
        cleaned = text.strip()
        json_str = cleaned

        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                json_str = match.group(1).strip()

        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                reply_text = str(data.get("reply", ""))
                tool_calls_data = data.get("tool_calls", [])
                calls: list[ToolCall] = []
                if isinstance(tool_calls_data, list):
                    for call_dict in tool_calls_data:
                        if isinstance(call_dict, dict) and "name" in call_dict:
                            calls.append(
                                ToolCall(
                                    name=call_dict["name"],
                                    args=call_dict.get("args", {}),
                                    status="executed",
                                )
                            )
                return reply_text, calls
        except (json.JSONDecodeError, ValueError):
            pass

        return text, []

    def _execute_turn(
        self,
        user_prompt: str,
        context: dict[str, Any],
        no_cache: bool = False,
    ) -> TargetExecution:
        initial_messages = [
            {"role": "system", "content": BASELINE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        messages = self.hooks.pre_model_hook(initial_messages, context)
        completion = self.llm.complete(messages=messages, no_cache=no_cache)

        reply_text, parsed_calls = self._parse_reply(completion.text)
        reply_text, post_calls = self.hooks.post_model_hook(
            reply_text, parsed_calls, context
        )

        executed_calls: list[ToolCall] = []
        for call in post_calls:
            gated_call = self.hooks.tool_gate_hook(call, context)
            if gated_call is not None:
                self.tools.execute_tool(gated_call.name, gated_call.args)
                executed_calls.append(gated_call)

        return TargetExecution(
            output_text=reply_text,
            tool_calls=executed_calls,
            raw_completion=completion,
        )

    def summarize_candidate(
        self, candidate_id: str, no_cache: bool = False
    ) -> TargetExecution:
        record = self.tools.get_candidate_record(candidate_id)
        context = {
            "task": "summarize_candidate",
            "candidate_id": candidate_id,
            "candidate_record": record,
        }
        prompt = (
            f"Please summarize the background and resume of candidate {candidate_id}.\n"
            f"Candidate Record: {json.dumps(record, ensure_ascii=False)}"
        )
        return self._execute_turn(prompt, context, no_cache=no_cache)

    def answer_faq(
        self, question: str, no_cache: bool = False
    ) -> TargetExecution:
        context = {"task": "answer_faq", "question": question}
        prompt = f"Answer the following recruiting FAQ question: {question}"
        return self._execute_turn(prompt, context, no_cache=no_cache)

    def draft_screening_note(
        self, candidate_id: str, job_id: str = "job-01", no_cache: bool = False
    ) -> TargetExecution:
        record = self.tools.get_candidate_record(candidate_id)
        context = {
            "task": "draft_screening_note",
            "candidate_id": candidate_id,
            "job_id": job_id,
            "candidate_record": record,
        }
        prompt = (
            f"Draft a candidate screening note for candidate {candidate_id} applying for {job_id}.\n"
            f"Candidate Record: {json.dumps(record, ensure_ascii=False)}"
        )
        return self._execute_turn(prompt, context, no_cache=no_cache)

    def recruiter_chat(
        self, message: str, no_cache: bool = False
    ) -> TargetExecution:
        context = {"task": "recruiter_chat", "message": message}
        return self._execute_turn(message, context, no_cache=no_cache)
