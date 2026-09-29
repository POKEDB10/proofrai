from typing import Any

from backend.core.controls.ctl_01_minimise_fields import MinimiseFieldsControl
from backend.core.controls.ctl_02_untrusted_documents import UntrustedDocumentsControl
from backend.core.controls.ctl_03_scan_output import ScanOutputControl
from backend.core.controls.ctl_05_human_approval import HumanApprovalControl
from backend.core.models import Control, ControlEvent, ToolCall
from backend.core.target.assistant import HireAssistHooks


class ControlPipeline(HireAssistHooks):
    def __init__(self, controls: list[Control]) -> None:
        self.approved_controls = [c for c in controls if c.status == "approved"]
        self.events: list[ControlEvent] = []

        self.ctl_01: MinimiseFieldsControl | None = None
        self.ctl_02: UntrustedDocumentsControl | None = None
        self.ctl_03: ScanOutputControl | None = None
        self.ctl_05: HumanApprovalControl | None = None

        for c in self.approved_controls:
            if c.id == "CTL-01":
                self.ctl_01 = MinimiseFieldsControl(c)
            elif c.id == "CTL-02":
                self.ctl_02 = UntrustedDocumentsControl(c)
            elif c.id == "CTL-03":
                self.ctl_03 = ScanOutputControl(c)
            elif c.id == "CTL-05":
                self.ctl_05 = HumanApprovalControl(c)

    def get_events(self) -> list[ControlEvent]:
        return list(self.events)

    def clear_events(self) -> None:
        self.events.clear()

    def pre_model_hook(
        self,
        messages: list[dict[str, str]],
        context: dict[str, Any],
    ) -> list[dict[str, str]]:
        current_messages = messages
        if self.ctl_01:
            current_messages, event = self.ctl_01.run_pre_model(
                current_messages, context
            )
            self.events.append(event)
        if self.ctl_02:
            current_messages, event = self.ctl_02.run_pre_model(
                current_messages, context
            )
            self.events.append(event)
        return current_messages

    def post_model_hook(
        self,
        reply_text: str,
        tool_calls: list[ToolCall],
        context: dict[str, Any],
    ) -> tuple[str, list[ToolCall]]:
        current_text = reply_text
        current_calls = tool_calls
        if self.ctl_03:
            current_text, current_calls, event = self.ctl_03.run_post_model(
                current_text, current_calls, context
            )
            self.events.append(event)
        return current_text, current_calls

    def tool_gate_hook(
        self,
        tool_call: ToolCall,
        context: dict[str, Any],
    ) -> ToolCall | None:
        if self.ctl_05:
            gated_call, _should_execute, event = self.ctl_05.run_tool_gate(
                tool_call, context
            )
            self.events.append(event)
            return gated_call
        return tool_call
