import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  IconShield,
  IconShieldAlert,
  IconCheckCheck,
  IconRotateCcw,
  IconExternalLink,
  IconLock,
  IconEye,
  IconArrowRight,
  IconChevronDown,
  IconChevronUp,
  IconLayers,
  IconAlertTriangle,
  IconCheckCircle,
  IconFileCheck,
  IconGitBranch,
} from '../components/Icons';
import { Control, getControls, updateControlStatus } from '../api';
import '../styles/controls.css';

const ENFORCEMENT_DETAILS: Record<string, { label: string; icon: typeof IconShield; color: string }> = {
  pre_model: { label: 'Pre-Model Filter', icon: IconShield, color: 'var(--primary)' },
  post_model: { label: 'Post-Model Scan', icon: IconEye, color: 'var(--sky)' },
  tool_gate: { label: 'Tool Execution Gate', icon: IconLock, color: 'var(--review)' },
  prompt: { label: 'Prompt Delimiter', icon: IconLayers, color: 'var(--lavender)' },
};

const REFERENCE_URLS: Record<string, string> = {
  'NIST AI RMF Map': 'https://airc.nist.gov/',
  'NIST AI RMF Manage': 'https://airc.nist.gov/',
  'NIST AI RMF Govern': 'https://airc.nist.gov/',
  'OWASP LLM01': 'https://genai.owasp.org/llm01-prompt-injection/',
  'OWASP LLM06': 'https://genai.owasp.org/llm06-sensitive-information-disclosure/',
  'EU AI Act reference': 'https://artificialintelligenceact.eu/',
  'Digital Dubai fairness guideline': 'https://www.digitaldubai.ae/',
};

export function Controls() {
  const [controls, setControls] = useState<Control[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [activeStage, setActiveStage] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadData() {
    try {
      const data = await getControls();
      setControls(data);
      const approved = data.filter((c) => c.status === 'approved').length;
      if (typeof window !== 'undefined') {
        localStorage.setItem('proofrai_approved_count', approved.toString());
      }
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
      setControls((prev) => {
        const next = prev.map((c) => (c.id === controlId ? updated : c));
        const approved = next.filter((c) => c.status === 'approved').length;
        if (typeof window !== 'undefined') {
          localStorage.setItem('proofrai_approved_count', approved.toString());
        }
        return next;
      });
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
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Approval failed';
      setErrorMessage(`Failed to approve controls: ${msg}`);
    }
  }

  async function handleResetAll() {
    try {
      for (const c of controls) {
        if (c.status !== 'rejected') {
          await updateControlStatus(c.id, 'rejected');
        }
      }
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Reset failed';
      setErrorMessage(`Failed to reset controls: ${msg}`);
    }
  }

  const approvedCount = controls.filter((c) => c.status === 'approved').length;
  const coveragePercent = controls.length > 0 ? Math.round((approvedCount / controls.length) * 100) : 0;

  const stageCounts = {
    all: controls.length,
    pre_model: controls.filter((c) => c.enforcement_point === 'pre_model').length,
    post_model: controls.filter((c) => c.enforcement_point === 'post_model').length,
    tool_gate: controls.filter((c) => c.enforcement_point === 'tool_gate').length,
  };

  const filteredControls = controls.filter((c) => {
    if (activeStage === 'all') return true;
    return c.enforcement_point === activeStage;
  });

  return (
    <div className="page-container controls-screen">
      {/* Editorial Header */}
      <div className="controls-hero">
        <div className="controls-hero-left">
          <div className="phase-badge">
            <IconShield size={12} />
            <span>Phase 3: Safeguard Controls</span>
          </div>
          <h1 className="page-title">Safeguard Control Library</h1>
          <p className="page-description">
            The Control Engine intercepts model inputs and outputs across four enforcement stages: pre-model input sanitisation, prompt delimiters, post-model disclosure scanners, and tool execution gates.
          </p>
        </div>

        <div className="controls-actions-group">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleResetAll}
            title="Disable all active controls"
          >
            <IconRotateCcw size={13} />
            <span>Disable All</span>
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleApproveAll}
            title="Activate all recommended safeguard controls"
          >
            <IconCheckCheck size={14} />
            <span>Approve All Recommended</span>
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="conflict-alert-card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="conflict-alert-title">
            <IconAlertTriangle size={16} />
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Metrics Stat Cards */}
      <div className="controls-stats-grid">
        <div className="controls-stat-card">
          <div className="controls-stat-top">
            <span>Active Safeguards</span>
            <IconShield size={14} />
          </div>
          <div className="controls-stat-value">
            <span style={{ color: approvedCount === controls.length ? 'var(--pass)' : 'var(--ink)' }}>
              {approvedCount}
            </span>
            <span style={{ fontSize: '13px', color: 'var(--ink-2)' }}>/ {controls.length} Approved</span>
          </div>
          <div className="controls-stat-sub">
            {coveragePercent}% policy coverage active
          </div>
        </div>

        <div className="controls-stat-card">
          <div className="controls-stat-top">
            <span>Enforcement Stages</span>
            <IconLayers size={14} />
          </div>
          <div className="controls-stat-value">
            <span>4 Points</span>
          </div>
          <div className="controls-stat-sub">
            Pre-model, prompt, post-model, tool gate
          </div>
        </div>

        <div className="controls-stat-card">
          <div className="controls-stat-top">
            <span>Framework Alignment</span>
            <IconFileCheck size={14} />
          </div>
          <div className="controls-stat-value">
            <span>4 Frameworks</span>
          </div>
          <div className="controls-stat-sub">
            NIST AI RMF, OWASP LLM, EU AI Act, Dubai
          </div>
        </div>

        <div className="controls-stat-card">
          <div className="controls-stat-top">
            <span>Evaluation Linkage</span>
            <IconCheckCircle size={14} />
          </div>
          <div className="controls-stat-value">
            <span>30 Cases</span>
          </div>
          <div className="controls-stat-sub">
            Tied to comparative test suite
          </div>
        </div>
      </div>

      {/* Section 6: Control Impact Map */}
      <div style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--rule)', borderRadius: 'var(--radius-card)', padding: '16px 20px', marginBottom: 'var(--space-5)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <IconGitBranch size={16} style={{ color: 'var(--primary)' }} />
            <h2 style={{ fontSize: '14px', fontWeight: 700, margin: 0 }}>Section 6 &bull; Control Impact Map</h2>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--ink-3)' }}>
            Risk / Control / Result
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '10px' }}>
          <div style={{ padding: '10px 14px', backgroundColor: 'var(--ground-secondary)', borderRadius: 'var(--radius-control)', border: '1px solid var(--rule-soft)', fontSize: '12px' }}>
            <div style={{ color: 'var(--fail)', fontWeight: 700, marginBottom: '2px' }}>PII Leakage Vector</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; Output PII Scanner (CTL-03)</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; Sensitive data pattern detected</div>
            <div style={{ color: 'var(--pass)', fontWeight: 600, marginTop: '2px' }}>&check; Sensitive disclosure redacted or response blocked</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--ground-secondary)', borderRadius: 'var(--radius-control)', border: '1px solid var(--rule-soft)', fontSize: '12px' }}>
            <div style={{ color: 'var(--fail)', fontWeight: 700, marginBottom: '2px' }}>Prompt Injection Vector</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; Input Sanitisation & Delimiters (CTL-02)</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; Adversarial instruction pattern identified</div>
            <div style={{ color: 'var(--pass)', fontWeight: 600, marginTop: '2px' }}>&check; Delimited as passive data / Assistant continues safely</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--ground-secondary)', borderRadius: 'var(--radius-control)', border: '1px solid var(--rule-soft)', fontSize: '12px' }}>
            <div style={{ color: 'var(--fail)', fontWeight: 700, marginBottom: '2px' }}>Tool Hijack Vector</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; Consequential Action Gate (CTL-05)</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; High-impact tool invocation attempted</div>
            <div style={{ color: 'var(--pass)', fontWeight: 600, marginTop: '2px' }}>&check; Execution intercepted / Queued for human approval</div>
          </div>

          <div style={{ padding: '10px 14px', backgroundColor: 'var(--ground-secondary)', borderRadius: 'var(--radius-control)', border: '1px solid var(--rule-soft)', fontSize: '12px' }}>
            <div style={{ color: 'var(--fail)', fontWeight: 700, marginBottom: '2px' }}>Proxy Bias Vector</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; Pre-Model Policy Filter (CTL-06)</div>
            <div style={{ color: 'var(--ink-2)' }}>&darr; Inferred demographic characteristic</div>
            <div style={{ color: 'var(--pass)', fontWeight: 600, marginTop: '2px' }}>&check; Prompt declined before model invocation</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="controls-filter-bar">
        <div className="controls-filter-tabs controls-tabs">
          <button
            type="button"
            className={`controls-filter-tab controls-tab${activeStage === 'all' ? ' active' : ''}`}
            onClick={() => setActiveStage('all')}
          >
            <span>All Controls</span>
            <span className="controls-count-badge">{stageCounts.all}</span>
          </button>
          <button
            type="button"
            className={`controls-filter-tab controls-tab${activeStage === 'pre_model' ? ' active' : ''}`}
            onClick={() => setActiveStage('pre_model')}
          >
            <span>Pre-Model</span>
            <span className="controls-count-badge">{stageCounts.pre_model}</span>
          </button>
          <button
            type="button"
            className={`controls-filter-tab controls-tab${activeStage === 'post_model' ? ' active' : ''}`}
            onClick={() => setActiveStage('post_model')}
          >
            <span>Post-Model</span>
            <span className="controls-count-badge">{stageCounts.post_model}</span>
          </button>
          <button
            type="button"
            className={`controls-filter-tab controls-tab${activeStage === 'tool_gate' ? ' active' : ''}`}
            onClick={() => setActiveStage('tool_gate')}
          >
            <span>Tool Gate</span>
            <span className="controls-count-badge">{stageCounts.tool_gate}</span>
          </button>
        </div>
      </div>

      {/* Control Cards Grid */}
      {isLoading ? (
        <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
          <p style={{ color: 'var(--ink-2)' }}>Loading control safeguards...</p>
        </div>
      ) : (
        <div className="controls-card-grid controls-grid">
          {filteredControls.map((c) => {
            const isApproved = c.status === 'approved';
            const isExpanded = expandedIds.has(c.id);
            const stageConfig = ENFORCEMENT_DETAILS[c.enforcement_point] || {
              label: c.enforcement_point,
              icon: IconShield,
              color: 'var(--ink-2)',
            };
            const StageIcon = stageConfig.icon;

            return (
              <div
                key={c.id}
                className={`control-item-card ${isApproved ? 'is-approved approved' : 'is-rejected rejected'}`}
              >
                <div>
                  <div className="control-card-header">
                    <div className="control-card-meta">
                      <span className="control-id-pill">{c.id}</span>
                      <span className="badge badge-primary">
                        <StageIcon size={10} />
                        <span>{stageConfig.label}</span>
                      </span>
                    </div>

                    {/* Restrained Switch */}
                    <label className="switch-control" title={`Control status: ${c.status}`}>
                      <input
                        type="checkbox"
                        className="switch-input"
                        checked={isApproved}
                        onChange={() => handleToggleStatus(c.id, c.status)}
                      />
                      <span className="switch-slider" />
                    </label>
                  </div>

                  <h3 className="control-title">{c.title}</h3>

                  <div style={{ marginTop: '6px', marginBottom: '8px' }}>
                    <span className="control-risk-tag">
                      <IconShieldAlert size={11} />
                      <span>{c.risk}</span>
                    </span>
                  </div>

                  <p className="control-rationale">{c.rationale}</p>
                </div>

                <div className="control-footer-meta">
                  {/* Framework References */}
                  {c.references && c.references.length > 0 && (
                    <div className="framework-refs-list">
                      {c.references.map((ref, idx) => {
                        const url = REFERENCE_URLS[ref];
                        return url ? (
                          <a
                            key={idx}
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="framework-pill"
                          >
                            <span>{ref}</span>
                            <IconExternalLink size={9} />
                          </a>
                        ) : (
                          <span key={idx} className="framework-pill">
                            {ref}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  {/* Linked Test IDs */}
                  {c.test_ids && c.test_ids.length > 0 && (
                    <div className="linked-tests-list">
                      <span style={{ fontSize: '10px', color: 'var(--ink-3)', fontWeight: 600 }}>
                        Tests:
                      </span>
                      {c.test_ids.map((tid) => {
                        const isSuiteCase = tid.startsWith('A-') || tid.startsWith('B-');
                        return isSuiteCase ? (
                          <span key={tid}>
                            <Link
                              to={`/test?case=${encodeURIComponent(tid)}`}
                              className="test-pill test-pill-interactive"
                            >
                              {tid}
                            </Link>
                          </span>
                        ) : (
                          <span key={tid} className="test-pill">
                            {tid}
                          </span>
                        );
                      })}

                    </div>
                  )}

                  {/* Parameter Accordion */}
                  {c.params && Object.keys(c.params).length > 0 && (
                    <div>
                      <button
                        type="button"
                        className="params-toggle-btn"
                        onClick={() => toggleExpand(c.id)}
                      >
                        {isExpanded ? <IconChevronUp size={11} /> : <IconChevronDown size={11} />}
                        <span>{isExpanded ? 'Hide Parameters' : 'View Enforcement Config'}</span>
                      </button>
                      {isExpanded && (
                        <pre className="params-viewer">
                          {JSON.stringify(c.params, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Bottom Step Link */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', backgroundColor: 'var(--surface)', border: '1px solid var(--rule)', borderRadius: 'var(--radius-card)', marginTop: 'var(--space-4)' }}>
        <Link to="/card" className="btn btn-secondary">
          <span>&larr; Back to System Card</span>
        </Link>
        <Link to="/test" className="next-step-link">
          <span>Proceed to Test Workbench</span>
          <IconArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}
