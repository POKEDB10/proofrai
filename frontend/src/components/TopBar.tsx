import { NavLink } from 'react-router-dom';

interface TopBarProps {
  runId?: string;
  targetModel?: string;
}

export function TopBar({
  runId,
  targetModel = 'gemini-3.5-flash-lite',
}: TopBarProps) {
  const displayRunId =
    runId ||
    (typeof window !== 'undefined'
      ? localStorage.getItem('proofrai_run_id') || 'run-01'
      : 'run-01');
  return (
    <header className="topbar">
      <div className="topbar-left">
        <NavLink to="/" className="topbar-wordmark" style={{ textDecoration: 'none' }}>
          ProofRAI
        </NavLink>
        <nav className="topbar-nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            1 Describe
          </NavLink>
          <NavLink
            to="/card"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            2 Card
          </NavLink>
          <NavLink
            to="/controls"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            3 Controls
          </NavLink>
          <NavLink
            to="/test"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            4 Test
          </NavLink>
          <NavLink
            to="/evidence"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            5 Evidence
          </NavLink>
        </nav>
      </div>
      <div className="topbar-right">
        <span>{displayRunId}</span>
        <span>{targetModel}</span>
      </div>
    </header>
  );
}
