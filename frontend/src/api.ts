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
export type ControlAction = 'pass' | 'modify' | 'block' | 'queue' | 'flag';

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
  override_verdict?: 'pass' | 'fail' | 'needs_review';
}

export interface OverrideRequest {
  case_id: string;
  verdict: 'pass' | 'fail' | 'needs_review';
  comment: string;
  reviewer?: string;
}

export interface OverrideResponse {
  status: string;
  run_id: string;
  case_id: string;
  verdict: Verdict;
  verdict_source: VerdictSource;
  judge_reason?: string;
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

async function extractErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const errJson = (await res.json()) as { detail?: string };
    if (errJson.detail) {
      return errJson.detail;
    }
  } catch {
    return fallback;
  }
  return fallback;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const fallback = `Request failed with status ${res.status}`;
    const detail = await extractErrorMessage(res, fallback);
    throw new Error(detail);
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

export async function overrideCaseVerdict(
  runId: string,
  override: OverrideRequest
): Promise<OverrideResponse> {
  const res = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(override),
  });
  return handleResponse<OverrideResponse>(res);
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
    const fallback = `Request failed with status ${res.status}`;
    const detail = await extractErrorMessage(res, fallback);
    throw new Error(detail);
  }
  return res.text();
}

export interface InterviewAnswers {
  tasks: string[];
  data_seen: string[];
  decision_impact: 'inform' | 'determine' | 'neither';
  actions: string[];
  human_oversight: 'never' | 'before_actions' | 'always';
  affected_parties: string[];
  decision_significance: 'non_significant' | 'significant' | 'critical';
  known_limitations: string;
}

export interface Conflict {
  field: string;
  message: string;
}

export interface InterviewResponse {
  status: string;
  conflicts: Conflict[];
  identified_risks: string[];
  proposed_controls: string[];
}

export interface SystemCardData {
  title: string;
  structured_fields: Record<string, string>;
  intended_use: string;
  known_limits: string;
  status: 'draft' | 'confirmed';
  confirmed_by: string | null;
  confirmed_at: string | null;
}

export async function postInterview(answers: InterviewAnswers): Promise<InterviewResponse> {
  const res = await fetch(`${API_BASE}/interview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(answers),
  });
  return handleResponse<InterviewResponse>(res);
}

export async function getSystemCard(): Promise<SystemCardData> {
  const res = await fetch(`${API_BASE}/card`);
  return handleResponse<SystemCardData>(res);
}

export async function postCardDrafts(): Promise<SystemCardData> {
  const res = await fetch(`${API_BASE}/card/drafts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return handleResponse<SystemCardData>(res);
}

export async function confirmSystemCard(
  confirmedBy: string,
  intendedUse: string,
  knownLimits: string
): Promise<SystemCardData> {
  const res = await fetch(`${API_BASE}/card/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      confirmed_by: confirmedBy,
      intended_use: intendedUse,
      known_limits: knownLimits,
    }),
  });
  return handleResponse<SystemCardData>(res);
}

export interface ControlImpact {
  control_id: string;
  title: string;
  risk: string;
  enforcement_point: string;
  status: string;
  attacks_mitigated: string[];
  attacks_resisted: string[];
  benign_overblocked: string[];
  events_count: number;
  causal_chain: string;
  impact_summary: string;
}

export interface Recommendation {
  id: string;
  title: string;
  vulnerability: string;
  recommended_control_id: string | null;
  suggested_action: string;
  action_type: 'approve_control' | 'review_overblock' | 'review_queue' | 'maintain_status';
  status: 'action_required' | 'informational' | 'optimal';
  severity: 'high' | 'medium' | 'low';
}

export interface ExplainConcept {
  id: string;
  title: string;
  what_is_this: string;
  why_it_matters: string;
  example: string;
  related_control_id: string | null;
  related_risk: string;
}

export interface SinglePromptTestRequest {
  task?: string;
  message: string;
  candidate_id?: string | null;
  no_cache?: boolean;
}

export interface SinglePromptTestResponse {
  case_id: string;
  baseline: CaseResult;
  controlled: CaseResult;
}

export interface SyntheticAttackCaseItem {
  case: Case;
  baseline_result: CaseResult | null;
  controlled_result: CaseResult | null;
}

export interface GenerateSyntheticAttacksRequest {
  category?: string | null;
  evaluate_now?: boolean;
  no_cache?: boolean;
}

export interface GenerateSyntheticAttacksResponse {
  cases: SyntheticAttackCaseItem[];
}

export async function getRunImpact(runId: string): Promise<ControlImpact[]> {
  const res = await fetch(`${API_BASE}/runs/${runId}/impact`);
  return handleResponse<ControlImpact[]>(res);
}

export async function getRunRecommendations(runId: string): Promise<Recommendation[]> {
  const res = await fetch(`${API_BASE}/runs/${runId}/recommendations`);
  return handleResponse<Recommendation[]>(res);
}

export async function getExplainConcepts(): Promise<ExplainConcept[]> {
  const res = await fetch(`${API_BASE}/explain`);
  return handleResponse<ExplainConcept[]>(res);
}

export async function testSinglePrompt(req: SinglePromptTestRequest): Promise<SinglePromptTestResponse> {
  const res = await fetch(`${API_BASE}/test/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  return handleResponse<SinglePromptTestResponse>(res);
}

export async function generateSyntheticAttacks(req: GenerateSyntheticAttacksRequest): Promise<GenerateSyntheticAttacksResponse> {
  const res = await fetch(`${API_BASE}/suite/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  return handleResponse<GenerateSyntheticAttacksResponse>(res);
}


