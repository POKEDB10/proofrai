export interface Completion {
  text: string;
  provider: string;
  model: string;
  temperature: number;
  cached: boolean;
  latency_ms: number;
}

export type ToolCallStatus = 'executed' | 'queued' | 'refused';

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  status: ToolCallStatus;
}

export type ControlStage = 'pre_model' | 'prompt' | 'post_model' | 'tool_gate';
export type ControlAction = 'pass' | 'modify' | 'block' | 'queue';

export interface ControlEvent {
  control_id: string;
  stage: ControlStage;
  action: ControlAction;
  detail: string;
}

export interface Span {
  start: number;
  end: number;
  label: string;
}

export interface CheckResult {
  name: string;
  passed: boolean;
  detail: string;
  spans: Span[];
}

export type Verdict = 'pass' | 'fail' | 'error' | 'needs_review';
export type VerdictSource = 'deterministic' | 'judge' | 'human';

export interface CaseResult {
  case_id: string;
  variant: 'baseline' | 'controlled';
  output_text: string;
  tool_calls: ToolCall[];
  events: ControlEvent[];
  checks: CheckResult[];
  verdict: Verdict;
  verdict_source: VerdictSource;
  judge_reason?: string;
  blocked_by?: string[];
}

export type ControlStatus = 'proposed' | 'approved' | 'rejected';

export interface Control {
  id: string;
  title: string;
  risk: string;
  rationale: string;
  enforcement_point: ControlStage;
  params: Record<string, unknown>;
  references: string[];
  test_ids: string[];
  status: ControlStatus;
}

export interface CheckSpec {
  name: string;
  args?: Record<string, unknown>;
}

export interface Case {
  id: string;
  group: 'attack' | 'benign';
  risk: string;
  task: string;
  input: string | Record<string, unknown>;
  checks: CheckSpec[];
  judge: string | null;
  critical: boolean;
}
