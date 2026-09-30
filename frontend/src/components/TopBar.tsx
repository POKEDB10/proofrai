import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  IconCpu,
  IconTerminal,
  IconSun,
  IconMoon,
} from './Icons';
import '../styles/topbar.css';

/* ProofRAI shield+check logo mark — inline SVG, zero external deps */
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

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('proofrai_theme', theme);
    }
  }, [theme]);

  function toggleTheme() {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }

  const displayRunId =
    runId ||
    (typeof window !== 'undefined'
      ? localStorage.getItem('proofrai_run_id') || 'run-01'
      : 'run-01');

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
            <span className="topbar-step-badge">{displayRunId}</span>
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

        <div className="topbar-chip topbar-chip-run" title="Current test run ID">
          <IconTerminal size={12} />
          <span className="topbar-chip-text">{displayRunId}</span>
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
