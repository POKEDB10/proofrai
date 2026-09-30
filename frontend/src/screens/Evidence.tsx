import { useEffect, useState } from 'react';
import type { ChangeEvent } from 'react';
import {
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

  const [runSummary, setRunSummary] = useState<RunSummary | null>(null);
  const [results, setResults] = useState<CaseResult[]>([]);
  const [reviews, setReviews] = useState<ReviewRecord[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [decision, setDecision] = useState<'accept' | 'reject' | 'needs_work'>('accept');
  const [overrideVerdict, setOverrideVerdict] = useState<'none' | 'pass' | 'fail'>('none');
  const [comment, setComment] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
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

  const controlledResults = results.filter((r) => r.variant === 'controlled');
  const selectedResult = controlledResults.find((r) => r.case_id === selectedCaseId);
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
    if (!selectedCaseId && queueItems.length > 0) {
      setSelectedCaseId(queueItems[0].case_id);
    }
  }, [queueItems, selectedCaseId]);

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
      const data = await getRunExport(runId);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `evidence_${runId}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Export failed';
      setErrorMessage(`Failed to download evidence: ${msg}`);
    }
  }

  const gateLabel = runSummary?.release_gate?.label || 'Review required';
  const gateSquareClass =
    gateLabel === 'Ready for further testing'
      ? 'sq-pass'
      : gateLabel === 'Unresolved risk'
      ? 'sq-fail'
      : 'sq-review';

  const gateReasons = runSummary?.release_gate?.reasons || [];

  return (
    <div className="page-container evidence-screen">
      <header className="evidence-header">
        <div>
          <h1 className="page-title">Evidence</h1>
          <div className="evidence-run-id">Run {runId}</div>
        </div>
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
          <span className={`status-square ${gateSquareClass}`} aria-hidden="true" />
          <span>{gateLabel}</span>
        </div>
        <div className="gate-reasons-title">Reasons</div>
        <ul className="gate-reasons-list">
          {gateReasons.length > 0 ? (
            gateReasons.map((reason, idx) => <li key={idx}>{reason}</li>)
          ) : (
            <li>No run results evaluated yet.</li>
          )}
        </ul>

        {/* Human Decisions Displayed under Gate without altering gate label */}
        {reviews.length > 0 && (
          <div style={{ marginTop: 'var(--space-3)' }}>
            <div className="gate-reasons-title">Human decisions</div>
            <ul className="gate-reasons-list">
              {reviews.map((rev, idx) => {
                const decLabel =
                  rev.decision === 'accept'
                    ? 'Accept'
                    : rev.decision === 'reject'
                    ? 'Reject'
                    : 'Needs work';
                return (
                  <li key={idx}>
                    {rev.case_id}: {decLabel}: {rev.comment} (by {rev.reviewer})
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>

      {/* Review Queue Table */}
      <section className="evidence-section">
        <h2 className="section-title">Review queue</h2>
        <div className="queue-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col" style={{ width: '120px' }}>
                  Case
                </th>
                <th scope="col" style={{ width: '280px' }}>
                  Why it is here
                </th>
                <th scope="col">Response</th>
                <th scope="col" style={{ width: '220px' }}>
                  Decision
                </th>
              </tr>
            </thead>
            <tbody>
              {queueItems.length > 0 ? (
                queueItems.map((item) => {
                  const isSelected = selectedCaseId === item.case_id;
                  const responseExcerpt =
                    item.response.length > 140
                      ? `${item.response.slice(0, 140)}...`
                      : item.response || 'No response recorded';
                  return (
                    <tr
                      key={item.case_id}
                      className={`queue-row${isSelected ? ' selected' : ''}`}
                      onClick={() => setSelectedCaseId(item.case_id)}
                    >
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{item.case_id}</td>
                      <td>{item.why}</td>
                      <td
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: 'var(--text-mono)',
                          whiteSpace: 'pre-wrap',
                          maxWidth: '440px',
                          overflow: 'hidden',
                          lineHeight: '1.4',
                        }}
                        title={item.response}
                      >
                        {responseExcerpt}
                      </td>
                      <td>{item.decisionText}</td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={4} className="empty-state">
                    {runSummary?.status === 'running'
                      ? `Running case ${runSummary.progress.current} of ${runSummary.progress.total}`
                      : results.length === 0
                      ? 'No runs yet. Run the suite to compare baseline and controlled.'
                      : 'No cases require human review. All test cases completed successfully.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Decision Form */}
      <section className="evidence-section">
        <h2 className="section-title">Your decision</h2>
        <div className="decision-form-container">
          <div className="form-field">
            <label htmlFor="case-select" className="field-label">
              Case
            </label>
            <select
              id="case-select"
              value={selectedCaseId}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setSelectedCaseId(e.target.value)}
            >
              {queueItems.length > 0 ? (
                queueItems.map((item) => (
                  <option key={item.case_id} value={item.case_id}>
                    {item.case_id}
                  </option>
                ))
              ) : (
                <option value="">No cases selected</option>
              )}
            </select>
          </div>

          <div className="radio-group" role="radiogroup" aria-label="Review decision">
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

          {isJudgedOrOverridden && (
            <div className="form-field">
              <label className="field-label">Override judged verdict</label>
              <div className="radio-group" role="radiogroup" aria-label="Override judged verdict">
                <label className="radio-label">
                  <input
                    type="radio"
                    name="overrideVerdict"
                    value="none"
                    checked={overrideVerdict === 'none'}
                    onChange={() => setOverrideVerdict('none')}
                  />
                  No override ({selectedResult?.verdict})
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="overrideVerdict"
                    value="pass"
                    checked={overrideVerdict === 'pass'}
                    onChange={() => setOverrideVerdict('pass')}
                  />
                  Pass
                </label>
                <label className="radio-label">
                  <input
                    type="radio"
                    name="overrideVerdict"
                    value="fail"
                    checked={overrideVerdict === 'fail'}
                    onChange={() => setOverrideVerdict('fail')}
                  />
                  Fail
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
              placeholder="Enter rationale for this decision"
              value={comment}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setComment(e.target.value)}
            />
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="button button-primary"
              onClick={handleSaveDecision}
              disabled={isSaving || !selectedCaseId}
            >
              Save decision
            </button>
            {saveMessage && <span className="decision-saved-note">{saveMessage}</span>}
          </div>
        </div>
      </section>

      {/* Export Links */}
      <div className="export-links">
        <button type="button" onClick={handleDownloadJson} className="export-link">
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
