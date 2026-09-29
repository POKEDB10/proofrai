import { Fragment, useEffect, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';
import {
  CaseResult,
  CheckResult,
  getRun,
  getRunResults,
  startRun,
} from '../api';
import '../styles/test.css';

const ATTACK_CASES = [
  'A-DISC-01',
  'A-DISC-02',
  'A-DISC-03',
  'A-DISC-04',
  'A-PII-01',
  'A-PII-02',
  'A-PII-03',
  'A-INJ-01',
  'A-INJ-02',
  'A-INJ-03',
  'A-INJ-04',
  'A-LEAK-01',
  'A-LEAK-02',
  'A-PROXY-01',
  'A-PROXY-02',
  'A-AUTH-01',
];

const BENIGN_CASES = [
  'B-SUM-01',
  'B-SUM-02',
  'B-SUM-03',
  'B-SUM-04',
  'B-FAQ-01',
  'B-FAQ-02',
  'B-FAQ-03',
  'B-NOTE-01',
  'B-NOTE-02',
  'B-NOTE-03',
  'B-EDGE-01',
  'B-EDGE-02',
  'B-EDGE-03',
  'B-EDGE-04',
];

const ALL_CASES = [...ATTACK_CASES, ...BENIGN_CASES];

const TASK_LABELS: Record<string, string> = {
  'A-DISC-01': 'Filter by age',
  'A-DISC-02': 'Rank by gender',
  'A-DISC-03': 'Filter by nationality',
  'A-DISC-04': 'Filter by family status',
  'A-PII-01': 'Request date of birth',
  'A-PII-02': 'Request marital status and health',
  'A-PII-03': 'Request full candidate record',
  'A-INJ-01': 'Summarise resume (cand-07)',
  'A-INJ-02': 'Advance candidate injection',
  'A-INJ-03': 'Rating override injection',
  'A-INJ-04': 'Tool call and prompt extraction',
  'A-LEAK-01': 'Extract system prompt canary',
  'A-LEAK-02': 'Inquire hidden system instructions',
  'A-PROXY-01': 'Infer age from graduation year',
  'A-PROXY-02': 'Infer ethnicity from languages',
  'A-AUTH-01': 'Spoof compliance officer audit',
  'B-SUM-01': 'Summarise candidate 01',
  'B-SUM-02': 'Summarise candidate 02',
  'B-SUM-03': 'Summarise candidate 03',
  'B-SUM-04': 'Summarise candidate 04',
  'B-FAQ-01': 'Answer office location FAQ',
  'B-FAQ-02': 'Answer interview stages FAQ',
  'B-FAQ-03': 'Answer visa sponsorship FAQ',
  'B-NOTE-01': 'Draft screening notes (cand-01)',
  'B-NOTE-02': 'Draft screening notes (cand-02)',
  'B-NOTE-03': 'Draft screening notes (cand-03)',
  'B-EDGE-01': 'Summarise empty skill list',
  'B-EDGE-02': 'Summarise long experience',
  'B-EDGE-03': 'Answer salary guidance FAQ',
  'B-EDGE-04': 'Summarise non-standard formatting',
};

type FilterType = 'all' | 'failures' | 'overblocked' | 'needs_review';

function renderHighlightedText(text: string, checks: CheckResult[]) {
  if (!text) {
    return <span className="empty-state">No response text recorded</span>;
  }

  interface SpanMarker {
    start: number;
    end: number;
    label: string;
    checkName: string;
  }

  const markers: SpanMarker[] = [];
  for (const check of checks) {
    if (!check.passed || check.name === 'canary_absent' || check.name === 'tool_not_executed') {
      for (const span of check.spans) {
        if (span.start >= 0 && span.end > span.start && span.end <= text.length) {
          markers.push({
            start: span.start,
            end: span.end,
            label: span.label,
            checkName: check.name,
          });
        }
      }
    }
  }

  if (markers.length === 0) {
    return <span>{text}</span>;
  }

  markers.sort((a, b) => a.start - b.start);

  const elements: ReactNode[] = [];
  let lastIdx = 0;

  for (let i = 0; i < markers.length; i++) {
    const m = markers[i];
    if (m.start < lastIdx) {
      continue;
    }
    if (m.start > lastIdx) {
      elements.push(text.slice(lastIdx, m.start));
    }
    const isCanaryOrTool = m.label === 'canary' || m.label === 'tool_call';
    const markClass = isCanaryOrTool ? 'mark-canary' : 'mark-fail';
    elements.push(
      <mark key={`m-${m.start}-${m.end}`} className={markClass} title={m.checkName}>
        {text.slice(m.start, m.end)}
      </mark>
    );
    lastIdx = m.end;
  }

  if (lastIdx < text.length) {
    elements.push(text.slice(lastIdx));
  }

  return <>{elements}</>;
}

export function Test() {
  const [runId, setRunId] = useState<string>(() => {
    return localStorage.getItem('proofrai_run_id') || 'run-01';
  });
  const [results, setResults] = useState<CaseResult[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [runningProgress, setRunningProgress] = useState<string>('');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [expandedCases, setExpandedCases] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<FilterType>('all');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadExistingRun(id: string) {
    try {
      const res = await getRunResults(id);
      setResults(res);
      setErrorMessage(null);
    } catch {
      // Run does not exist yet
    }
  }

  useEffect(() => {
    loadExistingRun(runId);
  }, [runId]);

  async function handleRunSuite() {
    setIsRunning(true);
    setErrorMessage(null);
    const newRunId = `run-${Date.now().toString(36)}`;
    setRunId(newRunId);
    localStorage.setItem('proofrai_run_id', newRunId);
    setRunningProgress('Running case 1 of 30');

    try {
      await startRun(newRunId);

      const intervalId = window.setInterval(async () => {
        try {
          const summary = await getRun(newRunId);
          const currentRes = await getRunResults(newRunId);
          setResults(currentRes);

          if (summary.status === 'running') {
            const current = summary.progress.current;
            setRunningProgress(`Running case ${current} of 30`);
          } else {
            window.clearInterval(intervalId);
            setIsRunning(false);
            setRunningProgress('');
          }
        } catch (pollErr: unknown) {
          window.clearInterval(intervalId);
          setIsRunning(false);
          setRunningProgress('');
          const errText = pollErr instanceof Error ? pollErr.message : 'Unknown polling error';
          setErrorMessage(`The run stopped: ${errText}. Progress is saved. Run again to continue.`);
        }
      }, 2000);
    } catch (startErr: unknown) {
      setIsRunning(false);
      setRunningProgress('');
      const errText = startErr instanceof Error ? startErr.message : 'Unknown start error';
      setErrorMessage(`The run stopped: ${errText}. Progress is saved. Run again to continue.`);
    }
  }

  function toggleExpandCase(caseId: string) {
    setSelectedCaseId(caseId);
    setExpandedCases((prev) => {
      const next = new Set(prev);
      if (next.has(caseId)) {
        next.delete(caseId);
      } else {
        next.add(caseId);
      }
      return next;
    });
  }

  const baselineMap = new Map<string, CaseResult>();
  const controlledMap = new Map<string, CaseResult>();
  for (const r of results) {
    if (r.variant === 'baseline') {
      baselineMap.set(r.case_id, r);
    } else {
      controlledMap.set(r.case_id, r);
    }
  }

  // Summary counts
  let attackBasePass = 0;
  let attackCtrlPass = 0;
  for (const cid of ATTACK_CASES) {
    if (baselineMap.get(cid)?.verdict === 'pass') attackBasePass++;
    if (controlledMap.get(cid)?.verdict === 'pass') attackCtrlPass++;
  }

  let benignBasePass = 0;
  let benignCtrlPass = 0;
  let overBlockedCount = 0;
  for (const cid of BENIGN_CASES) {
    if (baselineMap.get(cid)?.verdict === 'pass') benignBasePass++;
    const ctrlRes = controlledMap.get(cid);
    if (ctrlRes?.verdict === 'pass') benignCtrlPass++;
    if (ctrlRes?.verdict === 'fail' && ctrlRes.blocked_by && ctrlRes.blocked_by.length > 0) {
      overBlockedCount++;
    }
  }

  // Filtered cases list
  const filteredCases = ALL_CASES.filter((cid) => {
    const ctrl = controlledMap.get(cid);
    if (filter === 'all') return true;
    if (filter === 'failures') return ctrl?.verdict === 'fail';
    if (filter === 'needs_review') return ctrl?.verdict === 'needs_review';
    if (filter === 'overblocked') {
      return (
        BENIGN_CASES.includes(cid) &&
        ctrl?.verdict === 'fail' &&
        ctrl.blocked_by &&
        ctrl.blocked_by.length > 0
      );
    }
    return true;
  });

  // SVG grid sizing
  const CELL_SIZE = 18;
  const CELL_GAP = 3;
  const GROUP_GAP = 24;
  const START_X = 85;

  function getCellCoordinates(index: number, isBenign: boolean) {
    if (!isBenign) {
      return START_X + index * (CELL_SIZE + CELL_GAP);
    }
    return START_X + 16 * (CELL_SIZE + CELL_GAP) + GROUP_GAP + index * (CELL_SIZE + CELL_GAP);
  }

  function getVerdictFill(result?: CaseResult, isBenign?: boolean) {
    if (!result) return { fill: 'none', isHatch: false, hatchType: '' };
    if (isBenign && result.verdict === 'fail' && result.blocked_by && result.blocked_by.length > 0) {
      return { fill: 'var(--fail)', isHatch: true, hatchType: 'overblocked' };
    }
    if (result.verdict === 'pass') return { fill: 'var(--pass)', isHatch: false, hatchType: '' };
    if (result.verdict === 'fail') return { fill: 'var(--fail)', isHatch: false, hatchType: '' };
    if (result.verdict === 'needs_review') return { fill: 'var(--review)', isHatch: false, hatchType: '' };
    if (result.verdict === 'error') return { fill: 'var(--ink-2)', isHatch: true, hatchType: 'error' };
    return { fill: 'none', isHatch: false, hatchType: '' };
  }

  return (
    <div className="page-container test-screen">
      <header className="test-header">
        <div>
          <h1 className="page-title">Test</h1>
          <div className="test-meta">
            Target gemini-3.5-flash-lite&nbsp;&nbsp;&nbsp;Judge gemini-3.5-flash&nbsp;&nbsp;&nbsp;Suite v1, 30 cases&nbsp;&nbsp;&nbsp;Controls 3c45ed
          </div>
        </div>
        <div className="test-actions">
          {isRunning && <span className="running-indicator">{runningProgress}</span>}
          <button type="button" onClick={handleRunSuite} disabled={isRunning}>
            Run suite
          </button>
        </div>
      </header>

      {errorMessage && (
        <div style={{ color: 'var(--fail)', marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)' }}>
          {errorMessage}
        </div>
      )}

      <section className="plate-section">
        <h2 className="plate-title">Results plate</h2>
        <svg
          viewBox="0 0 760 76"
          className="results-plate-svg"
          role="img"
          aria-label="Test suite results plate showing baseline and controlled verdicts"
        >
          <defs>
            <pattern id="hatch-error" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink-2)" strokeWidth="1.5" />
            </pattern>
            <pattern id="hatch-overblocked" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--surface)" strokeWidth="1.5" />
            </pattern>
          </defs>

          {/* Row labels */}
          <text x="0" y="17" className="mono" fill="var(--ink-2)" fontSize="12">
            baseline
          </text>
          <text x="0" y="41" className="mono" fill="var(--ink-2)" fontSize="12">
            controlled
          </text>

          {/* Group labels */}
          <text
            x={START_X + (16 * (CELL_SIZE + CELL_GAP) - CELL_GAP) / 2}
            y="66"
            textAnchor="middle"
            fill="var(--ink-2)"
            fontSize="12"
          >
            Attack, 16
          </text>
          <text
            x={START_X + 16 * (CELL_SIZE + CELL_GAP) + GROUP_GAP + (14 * (CELL_SIZE + CELL_GAP) - CELL_GAP) / 2}
            y="66"
            textAnchor="middle"
            fill="var(--ink-2)"
            fontSize="12"
          >
            Benign, 14
          </text>

          {/* Baseline Row: Attack cells */}
          {ATTACK_CASES.map((cid, i) => {
            const x = getCellCoordinates(i, false);
            const res = baselineMap.get(cid);
            const verdictInfo = getVerdictFill(res, false);
            const isSelected = selectedCaseId === cid;
            const verdictLabel = res ? res.verdict : 'unrun';
            return (
              <g
                key={`base-atk-${cid}`}
                className="plate-cell cell-animate"
                role="button"
                tabIndex={0}
                aria-label={`${cid} baseline ${verdictLabel}`}
                onClick={() => toggleExpandCase(cid)}
                onKeyDown={(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleExpandCase(cid);
                  }
                }}
              >
                <title>{`${cid} (baseline): ${verdictLabel}`}</title>
                <rect
                  x={x}
                  y={4}
                  width={CELL_SIZE}
                  height={CELL_SIZE}
                  fill={verdictInfo.fill}
                  stroke={isSelected ? 'var(--ink)' : res ? 'none' : 'var(--rule)'}
                  strokeWidth={isSelected ? 2 : 1}
                />
                {verdictInfo.isHatch && (
                  <rect
                    x={x}
                    y={4}
                    width={CELL_SIZE}
                    height={CELL_SIZE}
                    fill={`url(#hatch-${verdictInfo.hatchType})`}
                    stroke={isSelected ? 'var(--ink)' : 'none'}
                    strokeWidth={isSelected ? 2 : 0}
                  />
                )}
              </g>
            );
          })}

          {/* Baseline Row: Benign cells */}
          {BENIGN_CASES.map((cid, j) => {
            const x = getCellCoordinates(j, true);
            const res = baselineMap.get(cid);
            const verdictInfo = getVerdictFill(res, true);
            const isSelected = selectedCaseId === cid;
            const verdictLabel = res ? res.verdict : 'unrun';
            return (
              <g
                key={`base-ben-${cid}`}
                className="plate-cell cell-animate"
                role="button"
                tabIndex={0}
                aria-label={`${cid} baseline ${verdictLabel}`}
                onClick={() => toggleExpandCase(cid)}
                onKeyDown={(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleExpandCase(cid);
                  }
                }}
              >
                <title>{`${cid} (baseline): ${verdictLabel}`}</title>
                <rect
                  x={x}
                  y={4}
                  width={CELL_SIZE}
                  height={CELL_SIZE}
                  fill={verdictInfo.fill}
                  stroke={isSelected ? 'var(--ink)' : res ? 'none' : 'var(--rule)'}
                  strokeWidth={isSelected ? 2 : 1}
                />
                {verdictInfo.isHatch && (
                  <rect
                    x={x}
                    y={4}
                    width={CELL_SIZE}
                    height={CELL_SIZE}
                    fill={`url(#hatch-${verdictInfo.hatchType})`}
                    stroke={isSelected ? 'var(--ink)' : 'none'}
                    strokeWidth={isSelected ? 2 : 0}
                  />
                )}
              </g>
            );
          })}

          {/* Controlled Row: Attack cells */}
          {ATTACK_CASES.map((cid, i) => {
            const x = getCellCoordinates(i, false);
            const res = controlledMap.get(cid);
            const verdictInfo = getVerdictFill(res, false);
            const isSelected = selectedCaseId === cid;
            const verdictLabel = res ? res.verdict : 'unrun';
            return (
              <g
                key={`ctrl-atk-${cid}`}
                className="plate-cell cell-animate"
                role="button"
                tabIndex={0}
                aria-label={`${cid} controlled ${verdictLabel}`}
                onClick={() => toggleExpandCase(cid)}
                onKeyDown={(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleExpandCase(cid);
                  }
                }}
              >
                <title>{`${cid} (controlled): ${verdictLabel}`}</title>
                <rect
                  x={x}
                  y={28}
                  width={CELL_SIZE}
                  height={CELL_SIZE}
                  fill={verdictInfo.fill}
                  stroke={isSelected ? 'var(--ink)' : res ? 'none' : 'var(--rule)'}
                  strokeWidth={isSelected ? 2 : 1}
                />
                {verdictInfo.isHatch && (
                  <rect
                    x={x}
                    y={28}
                    width={CELL_SIZE}
                    height={CELL_SIZE}
                    fill={`url(#hatch-${verdictInfo.hatchType})`}
                    stroke={isSelected ? 'var(--ink)' : 'none'}
                    strokeWidth={isSelected ? 2 : 0}
                  />
                )}
              </g>
            );
          })}

          {/* Controlled Row: Benign cells */}
          {BENIGN_CASES.map((cid, j) => {
            const x = getCellCoordinates(j, true);
            const res = controlledMap.get(cid);
            const verdictInfo = getVerdictFill(res, true);
            const isSelected = selectedCaseId === cid;
            const isOverBlocked =
              res?.verdict === 'fail' && res.blocked_by && res.blocked_by.length > 0;
            const verdictLabel = isOverBlocked ? 'over-blocked' : res ? res.verdict : 'unrun';
            return (
              <g
                key={`ctrl-ben-${cid}`}
                className="plate-cell cell-animate"
                role="button"
                tabIndex={0}
                aria-label={`${cid} controlled ${verdictLabel}`}
                onClick={() => toggleExpandCase(cid)}
                onKeyDown={(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleExpandCase(cid);
                  }
                }}
              >
                <title>{`${cid} (controlled): ${verdictLabel}`}</title>
                <rect
                  x={x}
                  y={28}
                  width={CELL_SIZE}
                  height={CELL_SIZE}
                  fill={verdictInfo.fill}
                  stroke={isSelected ? 'var(--ink)' : res ? 'none' : 'var(--rule)'}
                  strokeWidth={isSelected ? 2 : 1}
                />
                {verdictInfo.isHatch && (
                  <rect
                    x={x}
                    y={28}
                    width={CELL_SIZE}
                    height={CELL_SIZE}
                    fill={`url(#hatch-${verdictInfo.hatchType})`}
                    stroke={isSelected ? 'var(--ink)' : 'none'}
                    strokeWidth={isSelected ? 2 : 0}
                  />
                )}
              </g>
            );
          })}
        </svg>
      </section>

      {/* Summary lines */}
      <div className="test-summary">
        <div className="summary-row">
          <span className="summary-label">Attack pass rate</span>
          <span className="summary-val mono">{results.length > 0 ? `${attackBasePass} of 16` : '--'}</span>
          <span className="summary-sep">to</span>
          <span className="summary-val mono">{results.length > 0 ? `${attackCtrlPass} of 16` : '--'}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">Benign completion</span>
          <span className="summary-val mono">{results.length > 0 ? `${benignBasePass} of 14` : '--'}</span>
          <span className="summary-sep">to</span>
          <span className="summary-val mono">{results.length > 0 ? `${benignCtrlPass} of 14` : '--'}</span>
        </div>
        <div className="summary-row">
          <span className="summary-label">Over-blocked</span>
          <span className="summary-val mono">{results.length > 0 ? overBlockedCount : '--'}</span>
        </div>
      </div>

      {/* Filter links */}
      <div className="filter-bar">
        <span className="filter-title">Filter:</span>
        <button
          type="button"
          className={`filter-link${filter === 'all' ? ' active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All
        </button>
        <button
          type="button"
          className={`filter-link${filter === 'failures' ? ' active' : ''}`}
          onClick={() => setFilter('failures')}
        >
          Failures
        </button>
        <button
          type="button"
          className={`filter-link${filter === 'overblocked' ? ' active' : ''}`}
          onClick={() => setFilter('overblocked')}
        >
          Over-blocked
        </button>
        <button
          type="button"
          className={`filter-link${filter === 'needs_review' ? ' active' : ''}`}
          onClick={() => setFilter('needs_review')}
        >
          Needs review
        </button>
      </div>

      {/* Cases Table */}
      <div className="cases-table-container">
        <table>
          <thead>
            <tr>
              <th scope="col" style={{ width: '120px' }}>Case</th>
              <th scope="col">Task</th>
              <th scope="col" style={{ width: '130px' }}>Baseline</th>
              <th scope="col" style={{ width: '140px' }}>Controlled</th>
              <th scope="col" style={{ width: '150px' }}>Acted</th>
            </tr>
          </thead>
          <tbody>
            {filteredCases.map((cid) => {
              const baseRes = baselineMap.get(cid);
              const ctrlRes = controlledMap.get(cid);
              const isExpanded = expandedCases.has(cid);
              const isSelected = selectedCaseId === cid;
              const isOverBlocked =
                BENIGN_CASES.includes(cid) &&
                ctrlRes?.verdict === 'fail' &&
                ctrlRes.blocked_by &&
                ctrlRes.blocked_by.length > 0;

              const actedControls = ctrlRes?.events
                ? Array.from(new Set(ctrlRes.events.map((e) => e.control_id))).join(', ')
                : '';

              return (
                <Fragment key={cid}>
                  <tr
                    className={`case-row${isSelected ? ' selected' : ''}`}
                    onClick={() => toggleExpandCase(cid)}
                  >
                    <td className="mono">
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 16 16"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          aria-hidden="true"
                        >
                          <path d={isExpanded ? 'M4 10l4-4 4 4' : 'M4 6l4 4 4-4'} />
                        </svg>
                        {cid}
                      </span>
                    </td>
                    <td>{TASK_LABELS[cid] || cid}</td>
                    <td>
                      {baseRes ? (
                        <span className="status-marker">
                          <span
                            className={`square ${
                              baseRes.verdict === 'pass'
                                ? 'sq-pass'
                                : baseRes.verdict === 'fail'
                                ? 'sq-fail'
                                : baseRes.verdict === 'needs_review'
                                ? 'sq-review'
                                : 'sq-error'
                            }`}
                          />
                          {baseRes.verdict === 'pass'
                            ? 'Pass'
                            : baseRes.verdict === 'fail'
                            ? 'Fail'
                            : baseRes.verdict === 'needs_review'
                            ? 'Review'
                            : 'Error'}
                        </span>
                      ) : (
                        '--'
                      )}
                    </td>
                    <td>
                      {ctrlRes ? (
                        <span className="status-marker">
                          <span
                            className={`square ${
                              isOverBlocked
                                ? 'sq-overblocked'
                                : ctrlRes.verdict === 'pass'
                                ? 'sq-pass'
                                : ctrlRes.verdict === 'fail'
                                ? 'sq-fail'
                                : ctrlRes.verdict === 'needs_review'
                                ? 'sq-review'
                                : 'sq-error'
                            }`}
                          />
                          {isOverBlocked
                            ? 'Over-blocked'
                            : ctrlRes.verdict === 'pass'
                            ? 'Pass'
                            : ctrlRes.verdict === 'fail'
                            ? 'Fail'
                            : ctrlRes.verdict === 'needs_review'
                            ? 'Review'
                            : 'Error'}
                        </span>
                      ) : (
                        '--'
                      )}
                    </td>
                    <td className="mono">{actedControls || '--'}</td>
                  </tr>

                  {isExpanded && (
                    <tr>
                      <td colSpan={5} style={{ padding: 0 }}>
                        <div className="expanded-container">
                          <div className="expanded-split">
                            {/* Baseline Column */}
                            <div className="expanded-pane">
                              <div className="pane-heading">
                                <span>Baseline</span>
                                <span className="meta-cached">cached</span>
                              </div>
                              <div className="response-box">
                                {renderHighlightedText(baseRes?.output_text || '', baseRes?.checks || [])}
                              </div>

                              <div className="sub-heading">Control events</div>
                              {baseRes?.events && baseRes.events.length > 0 ? (
                                <ul className="events-list">
                                  {baseRes.events.map((ev, idx) => (
                                    <li key={`be-${idx}`} className="event-item mono">
                                      {ev.control_id} {ev.action} {ev.detail}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <div className="empty-state">No control events fired</div>
                              )}

                              <div className="sub-heading">Checks</div>
                              {baseRes?.checks && baseRes.checks.length > 0 ? (
                                <ul className="checks-list">
                                  {baseRes.checks.map((ck, idx) => (
                                    <li key={`bc-${idx}`} className="check-item">
                                      <span className="mono">{ck.name}</span>
                                      <span
                                        className={`square ${ck.passed ? 'sq-pass' : 'sq-fail'}`}
                                      />
                                      <span>{ck.passed ? 'Pass' : 'Fail'}</span>
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <div className="empty-state">No checks configured</div>
                              )}
                            </div>

                            {/* Controlled Column */}
                            <div className="expanded-pane">
                              <div className="pane-heading">
                                <span>Controlled</span>
                                <span className="meta-cached">cached</span>
                              </div>
                              <div className="response-box">
                                {renderHighlightedText(ctrlRes?.output_text || '', ctrlRes?.checks || [])}
                              </div>

                              <div className="sub-heading">Control events</div>
                              {ctrlRes?.events && ctrlRes.events.length > 0 ? (
                                <ul className="events-list">
                                  {ctrlRes.events.map((ev, idx) => (
                                    <li key={`ce-${idx}`} className="event-item mono">
                                      {ev.control_id} {ev.action} {ev.detail}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <div className="empty-state">No control events fired</div>
                              )}

                              <div className="sub-heading">Checks</div>
                              {ctrlRes?.checks && ctrlRes.checks.length > 0 ? (
                                <ul className="checks-list">
                                  {ctrlRes.checks.map((ck, idx) => (
                                    <li key={`cc-${idx}`} className="check-item">
                                      <span className="mono">{ck.name}</span>
                                      <span
                                        className={`square ${ck.passed ? 'sq-pass' : 'sq-fail'}`}
                                      />
                                      <span>{ck.passed ? 'Pass' : 'Fail'}</span>
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <div className="empty-state">No checks configured</div>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
