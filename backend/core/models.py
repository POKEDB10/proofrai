from typing import Any, Literal

from pydantic import BaseModel, Field


class Completion(BaseModel):
    text: str
    provider: str
    model: str
    temperature: float
    cached: bool
    latency_ms: int


ToolCallStatus = Literal["executed", "queued", "refused"]


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus = "executed"


ControlStage = Literal["pre_model", "prompt", "post_model", "tool_gate"]
ControlAction = Literal["pass", "modify", "block", "queue"]


class ControlEvent(BaseModel):
    control_id: str
    stage: ControlStage
    action: ControlAction
    detail: str


class Span(BaseModel):
    start: int
    end: int
    label: str


class CheckResult(BaseModel):
    name: str
    passed: bool
    detail: str
    spans: list[Span] = Field(default_factory=list)


Verdict = Literal["pass", "fail", "error", "needs_review"]
VerdictSource = Literal["deterministic", "judge", "human"]


class CaseResult(BaseModel):
    case_id: str
    variant: Literal["baseline", "controlled"]
    output_text: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    events: list[ControlEvent] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    verdict: Verdict
    verdict_source: VerdictSource
    judge_reason: str | None = None
    blocked_by: list[str] | None = None


ControlStatus = Literal["proposed", "approved", "rejected"]


class Control(BaseModel):
    id: str
    title: str
    risk: str
    rationale: str
    enforcement_point: ControlStage
    params: dict[str, Any] = Field(default_factory=dict)
    references: list[str] = Field(default_factory=list)
    test_ids: list[str] = Field(default_factory=list)
    status: ControlStatus = "proposed"


class CheckSpec(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class Case(BaseModel):
    id: str
    group: Literal["attack", "benign"]
    risk: str
    task: str
    input: str | dict[str, Any]
    checks: list[CheckSpec] = Field(default_factory=list)
    judge: str | None = None
    critical: bool = False
