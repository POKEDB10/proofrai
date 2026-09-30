import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  IconCpu,
  IconTerminal,
  IconSun,
  IconMoon,
  IconLayers,
  IconRotateCcw,
  IconCheckCircle,
} from './Icons';
import {
  listRuns,
  RunListItem,
  getSessionId,
  createNewSession,
  resetSession,
  loadDemoSession,
} from '../api';
import '../styles/topbar.css';


/* ProofRAI shield+check logo mark - inline SVG, zero external deps */
function LogoMark() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className="topbar-logo-mark"
    >
      <rect width="32" height="32" rx="7" className="topbar-logo-bg" />
      {/* Shield body */}
      <path
        d="M16 5L24 9.5V17C24 21.5 20.5 25.5 16 27C11.5 25.5 8 21.5 8 17V9.5L16 5Z"
        className="topbar-logo-shield-fill"
      />
      <path
        d="M16 5L24 9.5V17C24 21.5 20.5 25.5 16 27C11.5 25.5 8 21.5 8 17V9.5L16 5Z"
        className="topbar-logo-shield-stroke"
        strokeWidth="1.25"
        fill="none"
      />
      {/* Checkmark */}
      <path
        d="M12 16.5L15 19.5L20.5 13"
        className="topbar-logo-check"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

interface TopBarProps {
  runId?: string;
  targetModel?: string;
}

export function TopBar({ runId, targetModel }: TopBarProps) {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('proofrai_theme') as 'dark' | 'light') || 'dark';
    }
    return 'dark';
  });

  const [activeRunId, setActiveRunId] = useState<string>(() => {
    if (runId) return runId;
    if (typeof window !== 'undefined') {
      return localStorage.getItem('proofrai_run_id') || 'run-01';
    }
    return 'run-01';
  });

  const [sessionId, setSessionIdState] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return getSessionId();
    }
    return 'demo';
  });

  const [availableRuns, setAvailableRuns] = useState<RunListItem[]>([]);
  const [isRunMenuOpen, setIsRunMenuOpen] = useState<boolean>(false);
  const [isInstanceMenuOpen, setIsInstanceMenuOpen] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('proofrai_theme', theme);
    }
  }, [theme]);

  useEffect(() => {
    async function fetchRuns() {
      try {
        const runs = await listRuns();
        if (runs.length > 0) {
          setAvailableRuns(runs);
        }
      } catch {
        // keep default
      }
    }
    fetchRuns();

    function handleRunChange(e: Event) {
      const custom = e as CustomEvent<string>;
      if (custom.detail) {
        setActiveRunId(custom.detail);
      } else {
        const stored = localStorage.getItem('proofrai_run_id');
        if (stored) setActiveRunId(stored);
      }
    }

    function handleSessionChange(e: Event) {
      const custom = e as CustomEvent<string>;
      if (custom.detail) {
        setSessionIdState(custom.detail);
      }
    }

    window.addEventListener('proofrai_run_changed', handleRunChange);
    window.addEventListener('proofrai_session_changed', handleSessionChange);
    return () => {
      window.removeEventListener('proofrai_run_changed', handleRunChange);
      window.removeEventListener('proofrai_session_changed', handleSessionChange);
    };
  }, []);

  function toggleTheme() {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }

  function handleSelectRun(id: string) {
    setActiveRunId(id);
    if (typeof window !== 'undefined') {
      localStorage.setItem('proofrai_run_id', id);
      window.dispatchEvent(new CustomEvent('proofrai_run_changed', { detail: id }));
    }
    setIsRunMenuOpen(false);
  }

  function handleStartFresh() {
    setIsInstanceMenuOpen(false);
    createNewSession();
    if (typeof window !== 'undefined') {
      localStorage.removeItem('proofrai_run_id');
      window.location.href = '/describe';
    }
  }

  async function handleResetCurrent() {
    setIsResetting(true);
    try {
      await resetSession();
      if (typeof window !== 'undefined') {
        localStorage.removeItem('proofrai_run_id');
        window.location.reload();
      }
    } finally {
      setIsResetting(false);
      setIsInstanceMenuOpen(false);
    }
  }

  async function handleLoadDemo() {
    setIsResetting(true);
    try {
      await loadDemoSession();
      if (typeof window !== 'undefined') {
        localStorage.setItem('proofrai_run_id', 'run-01');
        window.location.reload();
      }
    } finally {
      setIsResetting(false);
      setIsInstanceMenuOpen(false);
    }
  }

  const displayModel =
    targetModel ||
    (typeof window !== 'undefined'
      ? localStorage.getItem('proofrai_target_model') || 'gemini-3.5-flash-lite'
      : 'gemini-3.5-flash-lite');

  const approvedCount =
    typeof window !== 'undefined'
      ? localStorage.getItem('proofrai_approved_count')
      : null;

  return (
    <header className="topbar">
      {/* Brand section */}
      <div className="topbar-left">
        <NavLink to="/" className="topbar-brand" aria-label="ProofRAI home">
          <LogoMark />
          <div className="topbar-wordmark">
            <span className="topbar-wordmark-name">ProofRAI</span>
            <span className="topbar-wordmark-sub">Assurance OS</span>
          </div>
        </NavLink>

        <div className="topbar-separator" aria-hidden="true" />

        {/* Step navigation */}
        <nav className="topbar-nav" aria-label="Workflow steps">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `topbar-step${isActive ? ' active' : ''}`}
          >
            <span className="topbar-step-label">Overview</span>
          </NavLink>

          <NavLink
            to="/describe"
            className={({ isActive }) => `topbar-step${isActive ? ' active' : ''}`}
          >
            <span className="topbar-step-num">1</span>
            <span className="topbar-step-label">Describe</span>
          </NavLink>

          <NavLink
            to="/card"
            className={({ isActive }) => `topbar-step${isActive ? ' active' : ''}`}
          >
            <span className="topbar-step-num">2</span>
            <span className="topbar-step-label">Card</span>
          </NavLink>

          <NavLink
            to="/controls"
            className={({ isActive }) => `topbar-step${isActive ? ' active' : ''}`}
          >
            <span className="topbar-step-num">3</span>
            <span className="topbar-step-label">Controls</span>
            {approvedCount ? (
              <span className="topbar-step-badge">{approvedCount}/6</span>
            ) : null}
          </NavLink>

          <NavLink
            to="/test"
            className={({ isActive }) => `topbar-step${isActive ? ' active' : ''}`}
          >
            <span className="topbar-step-num">4</span>
            <span className="topbar-step-label">Test</span>
            <span className="topbar-step-badge">{activeRunId}</span>
          </NavLink>

          <NavLink
            to="/evidence"
            className={({ isActive }) => `topbar-step${isActive ? ' active' : ''}`}
          >
            <span className="topbar-step-num">5</span>
            <span className="topbar-step-label">Evidence</span>
          </NavLink>
        </nav>
      </div>

      {/* Right telemetry + controls */}
      <div className="topbar-right">
        <div className="topbar-chip topbar-chip-model" title="Target evaluation model">
          <span className="topbar-chip-dot" aria-label="Online" />
          <IconCpu size={12} />
          <span className="topbar-chip-text">{displayModel}</span>
        </div>

        {/* Workspace Instance Isolation Selector */}
        <div className="topbar-run-container">
          <button
            type="button"
            className="topbar-chip topbar-chip-interactive"
            onClick={() => {
              setIsInstanceMenuOpen((prev) => !prev);
              setIsRunMenuOpen(false);
            }}
            title="Workspace Instance: Isolated SQLite and Control Card per user"
            aria-expanded={isInstanceMenuOpen}
          >
            <IconLayers size={12} />
            <span className="topbar-chip-text">
              {sessionId === 'demo' ? 'Instance: Demo' : `Instance: ${sessionId.slice(0, 10)}`}
            </span>
            <span style={{ fontSize: '9px', opacity: 0.7, marginLeft: '2px' }}>▼</span>
          </button>

          {isInstanceMenuOpen && (
            <div className="topbar-run-dropdown" style={{ minWidth: '270px' }}>
              <div className="topbar-run-dropdown-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Workspace Isolation</span>
                <span className="font-mono" style={{ fontSize: '10px', color: 'var(--ink-3)' }}>
                  {sessionId === 'demo' ? 'Shared Demo' : 'Private Instance'}
                </span>
              </div>
              <div style={{ padding: '8px 12px', fontSize: '11px', color: 'var(--ink-3)', borderBottom: '1px solid var(--rule-soft)', background: 'var(--ground)' }}>
                Session ID: <span className="font-mono" style={{ color: 'var(--ink)', fontWeight: 600 }}>{sessionId}</span>
              </div>
              <div className="topbar-run-dropdown-list">
                <button
                  type="button"
                  className="topbar-run-dropdown-item"
                  onClick={handleStartFresh}
                  disabled={isResetting}
                  title="Generate a new isolated session ID and start from Phase 1"
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '12px', color: 'var(--ink)' }}>New Fresh Instance</div>
                    <div style={{ fontSize: '11px', color: 'var(--ink-3)' }}>Clean slate for a new visitor</div>
                  </div>
                  <IconRotateCcw size={14} />
                </button>

                <button
                  type="button"
                  className="topbar-run-dropdown-item"
                  onClick={handleResetCurrent}
                  disabled={isResetting}
                  title="Reset your current instance to clean draft state"
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '12px', color: 'var(--ink)' }}>Reset Current Instance</div>
                    <div style={{ fontSize: '11px', color: 'var(--ink-3)' }}>Clear runs & draft card in this session</div>
                  </div>
                  <IconRotateCcw size={14} />
                </button>

                <button
                  type="button"
                  className="topbar-run-dropdown-item"
                  onClick={handleLoadDemo}
                  disabled={isResetting}
                  title="Load the 4 pre-computed benchmark runs into this instance"
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '12px', color: 'var(--primary)' }}>Load Demo Benchmark</div>
                    <div style={{ fontSize: '11px', color: 'var(--ink-3)' }}>Populate with 4 benchmark runs</div>
                  </div>
                  <IconCheckCircle size={14} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Interactive Run Selector */}
        <div className="topbar-run-container">
          <button
            type="button"
            className="topbar-chip topbar-chip-run topbar-chip-interactive"
            onClick={() => {
              setIsRunMenuOpen((prev) => !prev);
              setIsInstanceMenuOpen(false);
            }}
            title="Click to view or switch benchmark runs"
            aria-expanded={isRunMenuOpen}
          >
            <IconTerminal size={12} />
            <span className="topbar-chip-text">{activeRunId}</span>
            <span style={{ fontSize: '9px', opacity: 0.7, marginLeft: '2px' }}>▼</span>
          </button>

          {isRunMenuOpen && (
            <div className="topbar-run-dropdown">
              <div className="topbar-run-dropdown-header">
                <span>Select Evaluation Run</span>
              </div>
              <div className="topbar-run-dropdown-list">
                {availableRuns.length > 0 ? (
                  availableRuns.map((r) => {
                    const isSelected = r.id === activeRunId;
                    return (
                      <button
                        key={r.id}
                        type="button"
                        className={`topbar-run-dropdown-item${isSelected ? ' selected' : ''}`}
                        onClick={() => handleSelectRun(r.id)}
                      >
                        <span className="font-mono" style={{ fontWeight: 600 }}>{r.id}</span>
                        <span style={{ fontSize: '11px', color: 'var(--ink-3)' }}>
                          {r.target_model || 'default'}
                        </span>
                      </button>
                    );
                  })
                ) : (
                  <button
                    type="button"
                    className="topbar-run-dropdown-item selected"
                    onClick={() => handleSelectRun('run-01')}
                  >
                    <span className="font-mono">run-01 (default benchmark)</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <button
          type="button"
          className="topbar-theme-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          aria-label="Toggle display theme"
        >
          {theme === 'dark' ? <IconSun size={15} /> : <IconMoon size={15} />}
        </button>
      </div>
    </header>
  );
}
