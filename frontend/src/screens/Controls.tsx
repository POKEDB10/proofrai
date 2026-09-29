import { Fragment, useEffect, useState } from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  Control,
  ControlImpact,
  ExplainConcept,
  getControls,
  getExplainConcepts,
  getRunImpact,
  updateControlStatus,
} from '../api';
import '../styles/controls.css';

const ENFORCEMENT_LABELS: Record<string, string> = {
  pre_model: 'Before model',
  post_model: 'After model',
  tool_gate: 'Tool gate',
  prompt: 'Prompt',
};

const RISK_SHORT_LABELS: Record<string, string> = {
  'CTL-01': 'Disclosure',
  'CTL-02': 'Injection',
  'CTL-03': 'Data leakage',
  'CTL-04': 'Grounding',
  'CTL-05': 'Tool gating',
  'CTL-06': 'Discrimination',
};

export function Controls() {
  const [controls, setControls] = useState<Control[]>([]);
  const [impacts, setImpacts] = useState<ControlImpact[]>([]);
  const [explainConcepts, setExplainConcepts] = useState<ExplainConcept[]>([]);
  const [activeTab, setActiveTab] = useState<'library' | 'impact' | 'explain'>('library');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const runId = typeof window !== 'undefined'
    ? localStorage.getItem('proofrai_run_id') || 'run-01'
    : 'run-01';

  async function loadData() {
    try {
      const data = await getControls();
      setControls(data);
      setErrorMessage(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Load failed';
      setErrorMessage(`Failed to load controls: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  }

  async function loadImpactData() {
    try {
      const data = await getRunImpact(runId);
      setImpacts(data);
    } catch {
      setImpacts([]);
    }
  }

  async function loadExplainData() {
    try {
      const data = await getExplainConcepts();
      setExplainConcepts(data);
    } catch {
      setExplainConcepts([]);
    }
  }

  useEffect(() => {
    loadData();
    loadImpactData();
    loadExplainData();
  }, []);

  async function handleToggleStatus(controlId: string, currentStatus: string) {
    const nextStatus = currentStatus === 'approved' ? 'rejected' : 'approved';
    try {
      const updated = await updateControlStatus(controlId, nextStatus);
      setControls((prev) =>
        prev.map((c) => (c.id === controlId ? updated : c))
      );
      await loadImpactData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Update failed';
      setErrorMessage(`Failed to update control: ${msg}`);
    }
  }

  function toggleExpand(controlId: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(controlId)) {
        next.delete(controlId);
      } else {
        next.add(controlId);
      }
      return next;
    });
  }

  async function handleApproveAll() {
    try {
      for (const c of controls) {
        if (c.status !== 'approved') {
          await updateControlStatus(c.id, 'approved');
        }
      }
      await loadData();
      await loadImpactData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Approval failed';
      setErrorMessage(`Failed to approve controls: ${msg}`);
    }
  }

  const approvedCount = controls.filter((c) => c.status === 'approved').length;

  return (
    <div className="page-container controls-screen">
      <header className="controls-header">
        <div>
          <h1 className="page-title">Controls</h1>
          <div className="controls-approved-summary">
            {approvedCount} of {controls.length} approved
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
          <button type="button" className="btn-secondary" onClick={handleApproveAll}>
            Approve all
          </button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="controls-tabs" aria-label="Controls view options">
        <button
          type="button"
          className={`tab-btn${activeTab === 'library' ? ' active' : ''}`}
          onClick={() => setActiveTab('library')}
        >
          Control library
        </button>
        <button
          type="button"
          className={`tab-btn${activeTab === 'impact' ? ' active' : ''}`}
          onClick={() => setActiveTab('impact')}
        >
          Control impact map
        </button>
        <button
          type="button"
          className={`tab-btn${activeTab === 'explain' ? ' active' : ''}`}
          onClick={() => setActiveTab('explain')}
        >
          Explain concepts
        </button>
      </nav>

      {errorMessage && (
        <div style={{ color: 'var(--fail)', marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)' }}>
          {errorMessage}
        </div>
      )}

      {isLoading ? (
        <div className="empty-state">Loading controls...</div>
      ) : activeTab === 'library' ? (
        <div className="controls-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col" style={{ width: '80px', textAlign: 'center' }}>
                  Approved
                </th>
                <th scope="col" style={{ width: '90px' }}>
                  ID
                </th>
                <th scope="col">Control</th>
                <th scope="col" style={{ width: '140px' }}>
                  Acts at
                </th>
                <th scope="col" style={{ width: '180px' }}>
                  Addresses
                </th>
              </tr>
            </thead>
            <tbody>
              {controls.map((ctl) => {
                const isApproved = ctl.status === 'approved';
                const isExpanded = expandedIds.has(ctl.id);
                const actsAt = ENFORCEMENT_LABELS[ctl.enforcement_point] || ctl.enforcement_point;
                const addresses = RISK_SHORT_LABELS[ctl.id] || ctl.risk;

                return (
                  <Fragment key={ctl.id}>
                    <tr
                      className={`control-row${isExpanded ? ' expanded' : ''}`}
                      onClick={() => toggleExpand(ctl.id)}
                      onKeyDown={(e: KeyboardEvent) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          toggleExpand(ctl.id);
                        }
                      }}
                      tabIndex={0}
                      role="button"
                      aria-expanded={isExpanded}
                    >
                      <td
                        style={{ textAlign: 'center' }}
                        onClick={(e: MouseEvent) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          aria-label={`Approve ${ctl.id} ${ctl.title}`}
                          checked={isApproved}
                          onChange={() => handleToggleStatus(ctl.id, ctl.status)}
                        />
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{ctl.id}</td>
                      <td>{ctl.title}</td>
                      <td>{actsAt}</td>
                      <td>{addresses}</td>
                    </tr>

                    {isExpanded && (
                      <tr>
                        <td colSpan={5} className="control-expanded-cell">
                          <div className="detail-line">
                            <span className="detail-label">Rationale:</span>
                            <span>{ctl.rationale}</span>
                          </div>

                          <div className="detail-line">
                            <span className="detail-label">References:</span>
                            <span>{ctl.references.join(', ')}</span>
                          </div>

                          <div className="detail-line">
                            <span className="detail-label">Test IDs:</span>
                            <span className="detail-tags">
                              {ctl.test_ids.map((tid) => (
                                <span key={tid} className="tag-mono">
                                  {tid}
                                </span>
                              ))}
                            </span>
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
      ) : activeTab === 'impact' ? (
        <div className="controls-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col" style={{ width: '90px' }}>ID</th>
                <th scope="col" style={{ width: '180px' }}>Control</th>
                <th scope="col" style={{ width: '120px' }}>Acts at</th>
                <th scope="col" style={{ width: '130px' }}>Mitigated</th>
                <th scope="col" style={{ width: '130px' }}>Over-blocked</th>
                <th scope="col">Causal impact summary</th>
              </tr>
            </thead>
            <tbody>
              {impacts.length > 0 ? (
                impacts.map((imp) => (
                  <tr key={imp.control_id}>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{imp.control_id}</td>
                    <td>{imp.title}</td>
                    <td>{ENFORCEMENT_LABELS[imp.enforcement_point] || imp.enforcement_point}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {imp.attacks_mitigated.length > 0
                        ? imp.attacks_mitigated.join(', ')
                        : 'None'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {imp.benign_overblocked.length > 0
                        ? imp.benign_overblocked.join(', ')
                        : '0'}
                    </td>
                    <td>{imp.impact_summary}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="empty-state">
                    No run impact evaluated yet. Run the test suite to observe causal outcomes.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="explain-list">
          {explainConcepts.map((item) => (
            <div key={item.id} className="explain-card">
              <h2 className="explain-title">{item.title}</h2>
              <div className="explain-block">
                <span className="explain-label">What is this?</span>
                <span>{item.what_is_this}</span>
              </div>
              <div className="explain-block">
                <span className="explain-label">Why does it matter?</span>
                <span>{item.why_it_matters}</span>
              </div>
              <div className="explain-block">
                <span className="explain-label">Recruiting example:</span>
                <span style={{ fontStyle: 'italic' }}>{item.example}</span>
              </div>
              {item.related_control_id && (
                <div className="explain-block">
                  <span className="explain-label">Addressing control:</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{item.related_control_id}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <footer className="controls-footer">
        <span className="controls-note">Only approved controls run.</span>
        <Link to="/test" className="btn-primary">
          Proceed to test run
        </Link>
      </footer>
    </div>
  );
}
