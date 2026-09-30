import { NavLink } from 'react-router-dom';

interface TopBarProps {
  runId?: string;
  targetModel?: string;
}

export function TopBar({
  runId,
  targetModel,
}: TopBarProps) {
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
  const controlsText = approvedCount ? `3 Controls (${approvedCount} approved)` : '3 Controls';
  const testText = displayRunId ? `4 Test (${displayRunId})` : '4 Test';

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
            {controlsText}
          </NavLink>
          <NavLink
            to="/test"
            className={({ isActive }) =>
              `topbar-step${isActive ? ' active' : ''}`
            }
          >
            {testText}
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
        <span>{displayModel}</span>
      </div>
    </header>
  );
}
