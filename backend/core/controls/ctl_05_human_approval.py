from typing import Any

from backend.core.models import Control, ControlEvent, ToolCall

CONSEQUENTIAL_TOOLS = ["advance_candidate", "send_rejection_email"]


class HumanApprovalControl:
    def __init__(self, control: Control | None = None) -> None:
        self.control_id = control.id if control else "CTL-05"
        self.consequential_tools = CONSEQUENTIAL_TOOLS
        if control and control.params and "consequential_tools" in control.params:
            self.consequential_tools = control.params["consequential_tools"]

    def run_tool_gate(
        self,
        tool_call: ToolCall,
        context: dict[str, Any],
    ) -> tuple[ToolCall, bool, ControlEvent]:
        if tool_call.name in self.consequential_tools:
            queued_call = ToolCall(
                name=tool_call.name,
                args=tool_call.args,
                status="queued",
            )
            event = ControlEvent(
                control_id=self.control_id,
                stage="tool_gate",
                action="queue",
                detail=(
                    f"Consequential tool '{tool_call.name}' intercepted and "
                    "queued for human recruiter approval"
                ),
            )
            return queued_call, False, event

        event = ControlEvent(
            control_id=self.control_id,
            stage="tool_gate",
            action="pass",
            detail=f"Tool '{tool_call.name}' permitted for automated execution",
        )
        return tool_call, True, event
