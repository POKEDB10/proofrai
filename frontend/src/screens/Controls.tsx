import { Fragment, useEffect, useState } from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';
import { Control, getControls, updateControlStatus } from '../api';
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
  'CTL-04': 'Unauthorised actions',
  'CTL-05': 'High-impact actions',
  'CTL-06': 'Ungrounded claims',
};

export function Controls() {
  const [controls, setControls] = useState<Control[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  useEffect(() => {
    loadData();
  }, []);

  async function handleToggleStatus(controlId: string, currentStatus: string) {
    const nextStatus = currentStatus === 'approved' ? 'rejected' : 'approved';
    try {
      const updated = await updateControlStatus(controlId, nextStatus);
      setControls((prev) =>
        prev.map((c) => (c.id === controlId ? updated : c))
      );
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

  function handleGoToTest() {
    window.location.href = '/test';
  }

  const approvedCount = controls.filter((c) => c.status === 'approved').length;

  return (
    <div className="page-container controls-screen">
      <header className="controls-header">
        <h1 className="page-title">Controls</h1>
        <div className="controls-approved-summary">
          {approvedCount} of {controls.length} approved
        </div>
      </header>

      {errorMessage && (
        <div style={{ color: 'var(--fail)', marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)' }}>
          {errorMessage}
        </div>
      )}

      {isLoading ? (
        <div className="empty-state">Loading controls...</div>
      ) : (
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
      )}

      <footer className="controls-footer">
        <span className="controls-note">Only approved controls run.</span>
        <button type="button" onClick={handleGoToTest}>
          Go to test
        </button>
      </footer>
    </div>
  );
}
