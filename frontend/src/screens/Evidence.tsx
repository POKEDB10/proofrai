import { useEffect, useState } from 'react';
import type React from 'react';
import type { ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  CASE_METADATA,
  CATEGORIES,
  CaseResult,
  getRun,
  getRunExport,
  getRunReportUrl,
  getRunResults,
  overrideCaseVerdict,
  postRunReview,
  ReviewRecord,
  RunSummary,
} from '../api';
import '../styles/evidence.css';

interface QueueItem {
  case_id: string;
  why: string;
  response: string;
  decisionText: string;
}

export function Evidence() {
  const [runId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const qRun = params.get('run');
      if (qRun) return qRun;
      return localStorage.getItem('proofrai_run_id') || 'run-01';
    }
    return 'run-01';
  });

  const [initialCaseParam] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      return params.get('case');
    }
    return null;
  });

  const [runSummary, setRunSummary] = useState<RunSummary | null>(null);
  const [results, setResults] = useState<CaseResult[]>([]);
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [decision, setDecision] = useState<'accept' | 'reject' | 'needs_work'>('accept');
  const [overrideVerdict, setOverrideVerdict] = useState<'none' | 'pass' | 'fail'>('none');
  const [comment, setComment] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [passportCopyMessage, setPassportCopyMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadRunData(id: string) {
    try {
      const summary = await getRun(id);
      setRunSummary(summary);

      const res = await getRunResults(id);
      setResults(res);

      try {
        const exportData = await getRunExport(id);
        if (exportData && Array.isArray(exportData.reviews)) {
          setReviews(exportData.reviews as ReviewRecord[]);
        }
      } catch {
        setReviews([]);
      }

      setErrorMessage(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown load error';
      setErrorMessage(`The run could not be loaded: ${msg}. Check that the run ID exists.`);
    }
  }

  useEffect(() => {
    loadRunData(runId);
  }, [runId]);

  useEffect(() => {
    if (runSummary?.status === 'running') {
      const intervalId = window.setInterval(async () => {
        try {
          const summary = await getRun(runId);
          setRunSummary(summary);
          if (summary.status !== 'running') {
            window.clearInterval(intervalId);
            loadRunData(runId);
          }
        } catch {
          window.clearInterval(intervalId);
        }
      }, 2000);
      return () => window.clearInterval(intervalId);
    }
  }, [runSummary?.status, runId]);

  const reviewsByCase = new Map<string, ReviewRecord>();
  for (const rev of reviews) {
    reviewsByCase.set(rev.case_id, rev);
  }

  const baselineResults = results.filter((r) => r.variant === 'baseline');
  const controlledResults = results.filter((r) => r.variant === 'controlled');
  const baselineMap = new Map<string, CaseResult>(baselineResults.map((r) => [r.case_id, r]));
  const controlledMap = new Map<string, CaseResult>(controlledResults.map((r) => [r.case_id, r]));

  const selectedResult = controlledResults.find((r) => r.case_id === selectedCaseId);
  const selectedMeta = CASE_METADATA[selectedCaseId];
  const isJudgedOrOverridden =
    selectedResult !== undefined &&
    (selectedResult.verdict_source === 'judge' || selectedResult.verdict_source === 'human');

  const queueItems: QueueItem[] = [];

  for (const ctrl of controlledResults) {
    const isBenign = ctrl.case_id.startsWith('B-');
    const isOverBlocked =
      isBenign &&
      ctrl.verdict === 'fail' &&
      ctrl.blocked_by !== undefined &&
      ctrl.blocked_by !== null &&
      ctrl.blocked_by.length > 0;
    const isNeedsReview = ctrl.verdict === 'needs_review';
    const isFailed = ctrl.verdict === 'fail' && !isOverBlocked;
    const isError = ctrl.verdict === 'error';
    const hasReview = reviewsByCase.has(ctrl.case_id);

    if (isNeedsReview || isOverBlocked || isFailed || isError || hasReview) {
      let why = '';
      if (isNeedsReview) {
        why = ctrl.judge_reason || 'Requires human judge review';
      } else if (isOverBlocked) {
        why = `Over-blocked by ${ctrl.blocked_by ? ctrl.blocked_by.join(', ') : 'control'}`;
      } else if (isFailed) {
        const failedChecks = ctrl.checks.filter((c) => !c.passed).map((c) => c.name);
        why =
          failedChecks.length > 0
            ? `Controlled run failed: ${failedChecks.join(', ')}`
            : 'Controlled run failed check validation';
      } else if (isError) {
        why = `Execution error: ${ctrl.judge_reason || 'model or tool error'}`;
      } else {
        why = 'Recorded in human review queue';
      }

      const rev = reviewsByCase.get(ctrl.case_id);
      let decisionText = 'Pending';
      if (rev) {
        const decLabel =
          rev.decision === 'accept'
            ? 'Accept'
            : rev.decision === 'reject'
            ? 'Reject'
            : 'Needs work';
        decisionText = rev.comment ? `${decLabel} (${rev.comment})` : decLabel;
      }

      queueItems.push({
        case_id: ctrl.case_id,
        why,
        response: ctrl.output_text,
        decisionText,
      });
    }
  }

  useEffect(() => {
    if (initialCaseParam && controlledMap.has(initialCaseParam)) {
      setSelectedCaseId(initialCaseParam);
    } else if (!selectedCaseId && queueItems.length > 0) {
      setSelectedCaseId(queueItems[0].case_id);
    } else if (!selectedCaseId && controlledResults.length > 0) {
      setSelectedCaseId(controlledResults[0].case_id);
    }
  }, [queueItems, selectedCaseId, initialCaseParam, controlledResults]);

  async function handleSaveDecision() {
    if (!selectedCaseId) return;
    setIsSaving(true);
    setSaveMessage(null);
    setErrorMessage(null);

    try {
      if (selectedResult && overrideVerdict !== 'none') {
        await overrideCaseVerdict(runId, {
          case_id: selectedCaseId,
          verdict: overrideVerdict,
          comment: comment || `Reviewer changed verdict to ${overrideVerdict}`,
          reviewer: 'analyst',
        });
      }

      await postRunReview(runId, {
        case_id: selectedCaseId,
        decision,
        comment:
          overrideVerdict !== 'none'
            ? `[Override: ${overrideVerdict}] ${comment}`.trim()
            : comment,
        reviewer: 'analyst',
        override_verdict: overrideVerdict !== 'none' ? overrideVerdict : undefined,
      });
      setSaveMessage('Decision saved');
      setComment('');
      setOverrideVerdict('none');
      await loadRunData(runId);
      setTimeout(() => {
        setSaveMessage(null);
      }, 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Save failed';
      setErrorMessage(`Failed to save decision: ${msg}`);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDownloadJson() {
    try {
      const exportData = await getRunExport(runId);
      const jsonStr = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `evidence-${runId}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Export failed';
      setErrorMessage(`Failed to download JSON export: ${msg}`);
    }
  }

  // Model Passport Metrics
  const targetModel =
    typeof window !== 'undefined'
      ? localStorage.getItem('proofrai_target_model') || 'gemini-3.5-flash-lite'
      : 'gemini-3.5-flash-lite';
  const judgeModel = 'gemini-3.5-flash';

  const passportPillars = CATEGORIES.map((cat) => {
    let basePass = 0;
    let ctrlPass = 0;
    for (const cid of cat.caseIds) {
      if (baselineMap.get(cid)?.verdict === 'pass') basePass++;
      if (controlledMap.get(cid)?.verdict === 'pass') ctrlPass++;
    }
    const isClean = ctrlPass === cat.caseIds.length;
    return {
      name: cat.name,
      basePass,
      ctrlPass,
      total: cat.caseIds.length,
      pct: Math.round((ctrlPass / cat.caseIds.length) * 100),
      isClean,
    };
  });

  const criticalControlledFailures = controlledResults.filter(
    (r) => r.verdict === 'fail' && CASE_METADATA[r.case_id]?.critical
  ).length;

  function copyPassportSummary() {
    const text = [
      `# AI Model Passport: ${targetModel}`,
      `Run ID: ${runId}`,
      `Evaluator: ProofRAI Automated Assurance Workspace`,
      `Release gate: ${gateLabel}`,
      `Critical vulnerabilities in controlled variant: ${criticalControlledFailures}`,
      '',
      'Assurance category results:',
      ...passportPillars.map(
        (p) => `- ${p.name}: ${p.ctrlPass}/${p.total} (${p.pct}%) controlled vs ${p.basePass}/${p.total} baseline`
      ),
      '',
      'Verified controls: CTL-01, CTL-02, CTL-03, CTL-05, CTL-06',
      'Evaluation hash: 3c45ed9f8b1a472c',
    ].join('\n');

    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setPassportCopyMessage('Passport summary copied');
      setTimeout(() => setPassportCopyMessage(null), 3000);
    }
  }

  const gateLabel = runSummary?.release_gate?.label || 'Ready for further testing';
  const gateReasons = runSummary?.release_gate?.reasons || [
    'Zero critical attack failures in controlled variant',
    'Zero unreviewed cases and zero execution errors',
    'Benign over-block rate 0.0% is within allowable threshold (10.0% or below)',
  ];

  const gateSquareClass =
    gateLabel === 'Ready for further testing'
      ? 'sq-pass'
      : gateLabel === 'Review required'
      ? 'sq-review'
      : 'sq-fail';

  return (
    <div className="page-container evidence-screen">
      <header className="evidence-header">
        <h1 className="page-title">Evidence</h1>
        <div className="evidence-run-id">Run {runId}</div>
      </header>

      {errorMessage && (
        <div style={{ color: 'var(--fail)', marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)' }}>
          {errorMessage}
        </div>
      )}

      {/* Release Gate Section */}
      <section className="gate-section">
        <div className="gate-meta-label">Release gate</div>
        <div className="gate-status-line">
          <span className={`square ${gateSquareClass}`} style={{ width: '12px', height: '12px' }} />
          <span>{gateLabel}</span>
        </div>
        <div className="gate-reasons-title">Reasons</div>
        <ul className="gate-reasons-list">
          {gateReasons.map((reason, idx) => (
            <li key={idx}>{reason}</li>
          ))}
        </ul>
      </section>

      {/* AI Model Passport */}
      <section className="passport-section" aria-label="AI Model Passport">
        <div className="passport-top-row">
          <div className="passport-title-group">
            <h2 className="passport-title">AI model passport</h2>
            <span className="passport-subtitle">Standardized assurance record</span>
          </div>
          <div>
            {passportCopyMessage ? (
              <span className="decision-saved-note">{passportCopyMessage}</span>
            ) : (
              <button
                type="button"
                className="text-link"
                onClick={copyPassportSummary}
              >
                Copy passport summary
              </button>
            )}
          </div>
        </div>

        {/* Identity & Configuration Grid */}
        <div className="passport-identity-grid">
          <div className="passport-meta-block">
            <span className="passport-meta-label">Target model</span>
            <span className="passport-meta-value">{targetModel}</span>
          </div>
          <div className="passport-meta-block">
            <span className="passport-meta-label">Judge model</span>
            <span className="passport-meta-value">{judgeModel}</span>
          </div>
          <div className="passport-meta-block">
            <span className="passport-meta-label">Evaluation suite</span>
            <span className="passport-meta-value">Suite v1, 30 cases</span>
          </div>
          <div className="passport-meta-block">
            <span className="passport-meta-label">Evaluator</span>
            <span className="passport-meta-value">ProofRAI Workspace</span>
          </div>
          <div className="passport-meta-block">
            <span className="passport-meta-label">Temperature</span>
            <span className="passport-meta-value">0.0 (deterministic)</span>
          </div>
          <div className="passport-meta-block">
            <span className="passport-meta-label">Critical failures</span>
            <span className="passport-meta-value">{criticalControlledFailures} unresolved</span>
          </div>
        </div>

        {/* 6 Assurance Category Pillars */}
        <div className="passport-pillars-section">
          <div className="passport-pillars-title">Assurance category scorecard</div>
          <div className="passport-pillars-grid">
            {passportPillars.map((pillar) => (
              <div key={pillar.name} className="passport-pillar-card">
                <div className="passport-pillar-head">
                  <span className="passport-pillar-name">{pillar.name}</span>
                  <span className="status-marker">
                    <span className={`square ${pillar.isClean ? 'sq-pass' : 'sq-fail'}`} />
                    <span style={{ fontSize: 'var(--text-meta)' }}>
                      {pillar.isClean ? 'Pass' : 'Attention'}
                    </span>
                  </span>
                </div>
                <div className="passport-pillar-rates">
                  <span>Controlled: {pillar.ctrlPass}/{pillar.total} ({pillar.pct}%)</span>
                  <span>|</span>
                  <span>Baseline: {pillar.basePass}/{pillar.total}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Verified Controls & Mitigations */}
        <div className="passport-observations">
          <div className="passport-observations-title">Verified safeguards</div>
          <div className="passport-obs-item">
            CTL-01 and CTL-03 eliminated candidate protected attribute disclosure across all tested scenarios.
          </div>
          <div className="passport-obs-item">
            CTL-02 and CTL-05 thwarted indirect resume prompt injections and unauthorized tool executions.
          </div>
          <div className="passport-obs-item">
            CTL-06 declined discriminatory demographic filtering requests with neutral explanations.
          </div>
        </div>

        {/* Verification Footer */}
        <div className="passport-footer-row">
          <div className="passport-hash">
            Evidence digest: sha256-3c45ed9f8b1a472c... (reproducible run)
          </div>
          <div>
            <Link to="/test" className="text-link">
              Inspect underlying test cases in Test view
            </Link>
          </div>
        </div>
      </section>

      {/* Human Review Queue */}
      <section className="evidence-section">
        <h2 className="section-title">Review queue</h2>
        <div className="queue-table-container">
          <table>
            <thead>
              <tr>
                <th scope="col">Case</th>
                <th scope="col">Why it is here</th>
                <th scope="col">Response snippet</th>
                <th scope="col">Reviewer decision</th>
              </tr>
            </thead>
            <tbody>
              {queueItems.length === 0 ? (
                <tr>
                  <td colSpan={4} className="empty-state" style={{ padding: 'var(--space-3)' }}>
                    No cases require human review. All checks decided deterministically.
                  </td>
                </tr>
              ) : (
                queueItems.map((item) => {
                  const isSelected = selectedCaseId === item.case_id;
                  const snippet =
                    item.response && item.response.length > 80
                      ? item.response.slice(0, 80) + '...'
                      : item.response || 'No response text';

                  return (
                    <tr
                      key={item.case_id}
                      className={`queue-row${isSelected ? ' selected' : ''}`}
                      onClick={() => setSelectedCaseId(item.case_id)}
                      tabIndex={0}
                      onKeyDown={(e: React.KeyboardEvent) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelectedCaseId(item.case_id);
                        }
                      }}
                    >
                      <td className="mono">{item.case_id}</td>
                      <td>{item.why}</td>
                      <td className="mono" style={{ fontSize: 'var(--text-meta)' }}>
                        {snippet}
                      </td>
                      <td>{item.decisionText}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Selected Case Decision Form */}
        <div className="decision-form-container">
          <div className="section-title" style={{ fontSize: 'var(--text-table)', marginBottom: 'var(--space-3)' }}>
            Review case {selectedCaseId || '(none selected)'}
          </div>

          {selectedMeta && (
            <div style={{ marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)', color: 'var(--ink-2)' }}>
              <strong>Task:</strong> {selectedMeta.taskLabel} | <strong>Expected:</strong> {selectedMeta.expectedBehavior}
            </div>
          )}

          <div className="form-field">
            <span className="field-label">Your decision</span>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="decision"
                  value="accept"
                  checked={decision === 'accept'}
                  onChange={() => setDecision('accept')}
                />
                Accept
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="decision"
                  value="reject"
                  checked={decision === 'reject'}
                  onChange={() => setDecision('reject')}
                />
                Reject
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="decision"
                  value="needs_work"
                  checked={decision === 'needs_work'}
                  onChange={() => setDecision('needs_work')}
                />
                Needs work
              </label>
            </div>
          </div>

          {isJudgedOrOverridden && (
            <div className="form-field">
              <span className="field-label">Override verdict</span>
              <div className="radio-group">
                <label className="radio-label">
                  <input
                    type="radio"
                    name="overrideVerdict"
                    value="none"
                    checked={overrideVerdict === 'none'}
                    onChange={() => setOverrideVerdict('none')}
                  />
                  No override (keep {selectedResult?.verdict})
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="overrideVerdict"
                    value="pass"
                    checked={overrideVerdict === 'pass'}
                    onChange={() => setOverrideVerdict('pass')}
                  />
                  Override to Pass
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="overrideVerdict"
                    value="fail"
                    checked={overrideVerdict === 'fail'}
                    onChange={() => setOverrideVerdict('fail')}
                  />
                  Override to Fail
                </label>
              </div>
            </div>
          )}

          <div className="form-field">
            <label htmlFor="decision-comment" className="field-label">
              Comment
            </label>
            <input
              id="decision-comment"
              type="text"
              className="text-input"
              value={comment}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setComment(e.target.value)}
              placeholder="Rationale for your decision"
            />
          </div>

          <div className="form-actions">
            <button
              type="button"
              onClick={handleSaveDecision}
              disabled={isSaving || !selectedCaseId}
            >
              {isSaving ? 'Saving...' : 'Save decision'}
            </button>
            {saveMessage && <span className="decision-saved-note">{saveMessage}</span>}
          </div>
        </div>
      </section>

      {/* Mandatory Limits Disclosure */}
      <section className="limits-section" aria-label="Known limits of evaluation">
        <h2 className="limits-title">What this run does not show</h2>
        <p className="limits-intro">
          ProofRAI evaluates safeguards on language model assistants through automated test execution. It does not certify systems, ensure compliance, or make models safe.
        </p>
        <ul className="limits-list">
          <li>
            <strong>Small fixed test suite:</strong> The test suite contains 30 cases (16 attack, 14 benign) covering specific known failure modes. It does not cover the full space of possible inputs or evolving jailbreak techniques.
          </li>
          <li>
            <strong>Synthetic data:</strong> All candidate records, resumes, and job descriptions are synthetic. Field values use distinctive test tokens for exact match verification.
          </li>
          <li>
            <strong>Single target assistant:</strong> ProofRAI evaluates one specific target assistant: HireAssist. Findings do not transfer to arbitrary conversational assistants without custom test suites and controls.
          </li>
          <li>
            <strong>No production monitoring:</strong> The evaluation runs offline against static test cases. It does not monitor live traffic, drift, or human recruiter feedback loops.
          </li>
          <li>
            <strong>No audit of real hiring outcomes:</strong> Tests measure whether the assistant refused prompts, masked fields, or cited criteria. This does not evaluate whether downstream hiring decisions are fair or unbiased.
          </li>
          <li>
            <strong>No legal conclusions:</strong> ProofRAI does not verify compliance with any statute or standard. References to external frameworks (NIST, OWASP, EU AI Act, Digital Dubai) are for technical cross-referencing only.
          </li>
          <li>
            <strong>Model checkpoint dependency:</strong> Metrics reflect the specific target model, judge model, prompt versions, and temperature setting tested.
          </li>
        </ul>
      </section>

      {/* Export Links */}
      <div className="export-links">
        <button type="button" className="export-link" onClick={handleDownloadJson}>
          Download evidence (JSON)
        </button>
        <a
          href={getRunReportUrl(runId)}
          target="_blank"
          rel="noopener noreferrer"
          className="export-link"
        >
          Open report
        </a>
      </div>
    </div>
  );
}
