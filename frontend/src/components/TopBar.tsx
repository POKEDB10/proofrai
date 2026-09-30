import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  IconShieldCheck,
  IconFileText,
  IconSlidersHorizontal,
  IconFlask,
  IconAward,
  IconCpu,
  IconSun,
  IconMoon,
  IconTerminal,
  IconFileCheck,
} from './Icons';
import '../styles/topbar.css';

interface TopBarProps {
  runId?: string;
  targetModel?: string;
}

export function TopBar({
  runId,
  targetModel,
}: TopBarProps) {
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
      <div className="topbar-left">
        <NavLink to="/" className="topbar-brand">
          <div className="topbar-logo-mark">
            <IconShieldCheck size={18} />
          </div>
          <span>ProofRAI</span>
          <span className="topbar-brand-tag">Assurance OS</span>
        </NavLink>

        <nav className="topbar-nav" aria-label="Workflow navigation">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            <span>Overview</span>
          </NavLink>

          <NavLink
            to="/describe"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            <span className="topbar-step-num">1</span>
            <IconFileText size={14} />
            <span>Describe</span>
          </NavLink>

          <NavLink
            to="/card"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            <span className="topbar-step-num">2</span>
            <IconFileCheck size={14} />
            <span>Card</span>
          </NavLink>

          <NavLink
            to="/controls"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            <span className="topbar-step-num">3</span>
            <IconSlidersHorizontal size={14} />
            <span>Controls</span>
            {approvedCount ? (
              <span className="topbar-step-badge">{approvedCount}/6</span>
            ) : null}
          </NavLink>

          <NavLink
            to="/test"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            <span className="topbar-step-num">4</span>
            <IconFlask size={14} />
            <span>Test Workbench</span>
            <span className="topbar-step-badge">
              {displayRunId}
            </span>
          </NavLink>

          <NavLink
            to="/evidence"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            <span className="topbar-step-num">5</span>
            <IconAward size={14} />
            <span>Evidence</span>
          </NavLink>
        </nav>
      </div>

      <div className="topbar-right">
        <div className="topbar-telemetry-chip" title="Evaluation Target Model">
          <span className="topbar-beacon" />
          <IconCpu size={12} />
          <span>{displayModel}</span>
        </div>

        <div className="topbar-telemetry-chip topbar-run-chip" title="Current Test Run ID">
          <IconTerminal size={12} />
          <span>{displayRunId}</span>
        </div>

        <button
          type="button"
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          aria-label="Toggle visual theme"
        >
          {theme === 'dark' ? <IconSun size={15} /> : <IconMoon size={15} />}
        </button>
      </div>
    </header>
  );
}
