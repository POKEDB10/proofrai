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

export interface RunProgress {
  current: number;
  total: number;
  percent: number;
}

export interface RunCounts {
  total_cases: number;
  completed_cases: number;
  attack_total: number;
  attack_passed: number;
  benign_total: number;
  benign_completed: number;
  over_blocked: number;
  needs_review: number;
  errors: number;
}

export interface ReleaseGateSummary {
  label: 'Unresolved risk' | 'Review required' | 'Ready for further testing';
  reasons: string[];
}

export interface RunSummary {
  id: string;
  status: 'running' | 'completed' | 'failed';
  progress: RunProgress;
  counts: RunCounts;
  release_gate: ReleaseGateSummary | null;
}

export interface StartRunResponse {
  run_id: string;
  status: string;
}

export interface ReviewRequest {
  case_id: string;
  decision: 'accept' | 'reject' | 'needs_work';
  comment: string;
  reviewer?: string;
}

export interface ReviewRecord {
  status: string;
  run_id: string;
  case_id: string;
  decision: string;
  comment: string;
  reviewer: string;
  created_at: string;
}

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = (await res.json()) as { detail?: string };
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Body is not JSON
    }
    throw new Error(errorDetail);
  }
  return (await res.json()) as T;
}

export async function getControls(): Promise<Control[]> {
  const res = await fetch(`${API_BASE}/controls`);
  return handleResponse<Control[]>(res);
}

export async function updateControlStatus(
  controlId: string,
  status: 'approved' | 'rejected'
): Promise<Control> {
  const res = await fetch(`${API_BASE}/controls/${encodeURIComponent(controlId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return handleResponse<Control>(res);
}

export async function startRun(
  runId?: string,
  noCache: boolean = false
): Promise<StartRunResponse> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId, no_cache: noCache }),
  });
  return handleResponse<StartRunResponse>(res);
}

export async function getRun(runId: string): Promise<RunSummary> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}`);
  return handleResponse<RunSummary>(res);
}

export async function getRunResults(runId: string): Promise<CaseResult[]> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}/results`);
  return handleResponse<CaseResult[]>(res);
}

export async function postRunReview(
  runId: string,
  review: ReviewRequest
): Promise<ReviewRecord> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(review),
  });
  return handleResponse<ReviewRecord>(res);
}

export async function getRunExport(
  runId: string
): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}/export`);
  return handleResponse<Record<string, unknown>>(res);
}

export function getRunReportUrl(runId: string): string {
  return `${API_BASE}/runs/${encodeURIComponent(runId)}/report`;
}

export async function getRunReport(runId: string): Promise<string> {
  const res = await fetch(getRunReportUrl(runId));
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = (await res.json()) as { detail?: string };
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Body is not JSON
    }
    throw new Error(errorDetail);
  }
  return res.text();
}
