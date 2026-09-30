import { useState } from 'react';
import type { ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  IconSparkles,
  IconShieldCheck,
  IconAlertTriangle,
  IconCheckCircle,
  IconArrowRight,
  IconSave,
  IconFileText,
  IconLock,
  IconUserCheck,
  IconEye,
  IconSliders,
  IconCheck,
  IconAlertCircle,
} from '../components/Icons';
import { Conflict, InterviewAnswers, postInterview } from '../api';
import '../styles/describe.css';

export function Describe() {
  const [tasks, setTasks] = useState<string[]>([
    'summarise_applications',
    'answer_candidate_questions',
    'draft_screening_notes',
  ]);
  const [dataSeen, setDataSeen] = useState<string[]>([
    'work_history',
    'skills_education',
    'contact_details',
    'protected_characteristics',
  ]);
  const [decisionImpact, setDecisionImpact] = useState<'inform' | 'determine' | 'neither'>('inform');
  const [actions, setActions] = useState<string[]>([
    'advance_candidate',
    'send_rejection_email',
  ]);
  const [humanOversight, setHumanOversight] = useState<'never' | 'before_actions' | 'always'>('before_actions');
  const [affectedParties, setAffectedParties] = useState<string[]>([
    'job_candidates',
    'recruiters',
  ]);
  const [decisionSignificance, setDecisionSignificance] = useState<'non_significant' | 'significant' | 'critical'>('significant');
  const [knownLimitations, setKnownLimitations] = useState<string>(
    'Candidate resumes may contain unverified statements or prompt injections. ' +
    'The model does not verify educational credentials or legal work authorisation.'
  );

  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveNote, setSaveNote] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function computeLiveConflicts(): Conflict[] {
    const list: Conflict[] = [];
    if (decisionImpact === 'determine' && humanOversight === 'never') {
      list.push({
        field: 'human_oversight',
        message: 'Outputs determine outcomes autonomously without human oversight intervention.',
      });
    }
    const activeActions = actions.filter((a) => a !== 'none');
    if (activeActions.length > 0 && humanOversight === 'never') {
      list.push({
        field: 'actions',
        message: 'The assistant can execute consequential actions with zero human oversight.',
      });
    }
    if (dataSeen.includes('protected_characteristics')) {
      const needKeywords = ['need', 'diversity', 'compliance', 'monitoring', 'audit', 'equal opportunity', 'legal'];
      const limitLower = knownLimitations.toLowerCase();
      const taskLower = tasks.join(' ').toLowerCase();
      const needStated = needKeywords.some((kw) => limitLower.includes(kw) || taskLower.includes(kw));
      if (!needStated) {
        list.push({
          field: 'data_seen',
          message: 'The model ingests protected demographic characteristics without an explicit legal compliance need in the limitations or task scope.',
        });
      }
    }
    return list;
  }

  function applyCompliantPreset() {
    setTasks(['summarise_applications', 'answer_candidate_questions', 'draft_screening_notes']);
    setDataSeen(['work_history', 'skills_education', 'contact_details', 'protected_characteristics']);
    setDecisionImpact('inform');
    setActions(['advance_candidate', 'send_rejection_email']);
    setHumanOversight('before_actions');
    setAffectedParties(['job_candidates', 'recruiters']);
    setDecisionSignificance('significant');
    setKnownLimitations(
      'Candidate resumes may contain unverified statements or prompt injections. ' +
      'Protected characteristics are collected solely for diversity compliance audit.'
    );
    setConflicts([]);
    setSaveNote(null);
  }

  function applyConflictPreset() {
    setTasks(['summarise_applications', 'draft_screening_notes']);
    setDataSeen(['work_history', 'skills_education', 'protected_characteristics']);
    setDecisionImpact('determine');
    setActions(['advance_candidate']);
    setHumanOversight('never');
    setAffectedParties(['job_candidates']);
    setDecisionSignificance('critical');
    setKnownLimitations('');
    setConflicts([
      {
        field: 'human_oversight',
        message: 'Outputs determine outcomes autonomously without human oversight intervention.',
      },
      {
        field: 'actions',
        message: 'The assistant can execute consequential actions with zero human oversight.',
      },
      {
        field: 'data_seen',
        message: 'The model ingests protected demographic characteristics without an explicit legal compliance need in the limitations or task scope.',
      },
    ]);
    setSaveNote(null);
  }

  function toggleItem(list: string[], item: string): string[] {
    return list.includes(item) ? list.filter((i) => i !== item) : [...list, item];
  }

  function toggleAction(actionItem: string) {
    if (actionItem === 'none') {
      setActions(['none']);
    } else {
      const filtered = actions.filter((a) => a !== 'none');
      if (filtered.includes(actionItem)) {
        const next = filtered.filter((a) => a !== actionItem);
        setActions(next.length > 0 ? next : ['none']);
      } else {
        setActions([...filtered, actionItem]);
      }
    }
  }

  async function handleSaveAnswers() {
    setIsSaving(true);
    setSaveNote(null);
    setErrorMessage(null);

    const answers: InterviewAnswers = {
      tasks,
      data_seen: dataSeen,
      decision_impact: decisionImpact,
      actions,
      human_oversight: humanOversight,
      affected_parties: affectedParties,
      decision_significance: decisionSignificance,
      known_limitations: knownLimitations,
    };

    try {
      const res = await postInterview(answers);
      setConflicts(res.conflicts);
      const count = res.proposed_controls.length;
      setSaveNote(`Saved successfully. Proposed ${count} governance controls.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Save failed';
      setErrorMessage(`Failed to save answers: ${msg}. Check required fields.`);
    } finally {
      setIsSaving(false);
    }
  }

  const effectiveConflicts = conflicts.length > 0 ? conflicts : computeLiveConflicts();
  const oversightConflict = effectiveConflicts.find((c) => c.field === 'human_oversight');
  const actionsConflict = effectiveConflicts.find((c) => c.field === 'actions');
  const dataConflict = effectiveConflicts.find((c) => c.field === 'data_seen');

  return (
    <div className="page-container describe-screen">
      {/* Hero Header */}
      <div className="describe-hero">
        <div className="describe-hero-left">
          <div className="phase-badge">
            <IconSparkles size={12} />
            <span>Phase 1: System Intake</span>
          </div>
          <h1 className="page-title">Describe the Assistant</h1>
          <p className="page-description">
            Complete the 8-point governance intake interview. Responses generate the formal AI System Card, detect safety conflicts in real-time, and propose safeguard controls.
          </p>
        </div>

        <div className="presets-container">
          <button
            type="button"
            className="preset-btn preset-compliant"
            onClick={applyCompliantPreset}
            title="Load compliant recruiting assistant configuration"
          >
            <IconCheckCircle size={13} />
            <span>Compliant Baseline</span>
          </button>
          <button
            type="button"
            className="preset-btn preset-conflict"
            onClick={applyConflictPreset}
            title="Load configuration with known governance conflicts"
          >
            <IconAlertTriangle size={13} />
            <span>Conflict Demo</span>
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="conflict-alert-card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="conflict-alert-title">
            <IconAlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Real-time Conflict Alert or Compliant Status Banner */}
      {effectiveConflicts.length > 0 ? (
        <div className="conflict-alert-card">
          <div className="conflict-alert-header">
            <div className="conflict-alert-title">
              <IconAlertTriangle size={18} />
              <span>{effectiveConflicts.length} Governance Policy Conflict{effectiveConflicts.length > 1 ? 's' : ''} Detected</span>
            </div>
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={applyCompliantPreset}
            >
              Auto-Resolve with Compliant Preset
            </button>
          </div>
          <ul className="conflict-alert-list">
            {effectiveConflicts.map((c, idx) => (
              <li key={idx} className="conflict-alert-item">
                <strong>{c.field.replace('_', ' ').toUpperCase()}:</strong> {c.message}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="conflict-cleared-card">
          <IconShieldCheck size={18} />
          <span><strong>Governance aligned:</strong> All human-in-the-loop and data minimization rules currently satisfied.</span>
        </div>
      )}

      {/* Bento Grid Form */}
      <div className="describe-form-grid">
        {/* Q1: Tasks */}
        <div className="question-card">
          <div className="question-header">
            <div className="question-title">
              <IconFileText size={16} />
              <span>1. What does the assistant do?</span>
            </div>
            <span className="question-badge">Multi-select</span>
          </div>
          <div className="options-tile-grid">
            {[
              { id: 'summarise_applications', label: 'Summarises applications', hint: 'Extracts skills & experience' },
              { id: 'answer_candidate_questions', label: 'Answers questions', hint: 'Responds to applicant inquiries' },
              { id: 'draft_screening_notes', label: 'Drafts screening notes', hint: 'Evaluates against criteria' },
              { id: 'send_messages', label: 'Sends messages', hint: 'Direct outreach to candidates' },
            ].map((t) => {
              const checked = tasks.includes(t.id);
              return (
                <div
                  key={t.id}
                  className={`option-tile${checked ? ' selected' : ''}`}
                  onClick={() => setTasks(toggleItem(tasks, t.id))}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {}}
                    aria-label={t.label}
                  />
                  <div className="option-tile-content">
                    <span className="option-tile-label">{t.label}</span>
                    <span className="option-tile-hint">{t.hint}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Q2: Data Seen */}
        <div className={`question-card${dataConflict ? ' has-conflict' : ''}`}>
          <div className="question-header">
            <div className="question-title">
              <IconEye size={16} />
              <span>2. What data does it see?</span>
            </div>
            {dataConflict && (
              <span className="conflict-inline-pill">
                <IconAlertTriangle size={12} />
                Requires Stated Need
              </span>
            )}
          </div>
          <div className="options-tile-grid">
            {[
              { id: 'work_history', label: 'Work history & experience', hint: 'CVs, job positions, dates' },
              { id: 'skills_education', label: 'Skills & qualifications', hint: 'Degrees, certifications' },
              { id: 'contact_details', label: 'Contact details', hint: 'Email, phone, home address' },
              { id: 'protected_characteristics', label: 'Protected characteristics', hint: 'Age, gender, nationality, health' },
            ].map((d) => {
              const checked = dataSeen.includes(d.id);
              return (
                <div
                  key={d.id}
                  className={`option-tile${checked ? ' selected' : ''}`}
                  onClick={() => setDataSeen(toggleItem(dataSeen, d.id))}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {}}
                    aria-label={d.label}
                  />
                  <div className="option-tile-content">
                    <span className="option-tile-label">{d.label}</span>
                    <span className="option-tile-hint">{d.hint}</span>
                  </div>
                </div>
              );
            })}
          </div>
          {dataConflict && (
            <div className="conflict-inline-pill" style={{ marginTop: 'var(--space-2)' }}>
              <IconAlertTriangle size={12} />
              <span>{dataConflict.message}</span>
            </div>
          )}
        </div>

        {/* Q3: Decision Impact */}
        <div className="question-card">
          <div className="question-header">
            <div className="question-title">
              <IconSliders size={16} />
              <span>3. Outputs are used to:</span>
            </div>
            <span className="question-badge">Single Choice</span>
          </div>
          <div className="options-tile-grid">
            {[
              { id: 'inform', label: 'Inform recruiters', hint: 'Recruiter makes final judgment' },
              { id: 'determine', label: 'Determine outcomes', hint: 'Model autonomously decides' },
              { id: 'neither', label: 'Neither', hint: 'Exploratory/reference only' },
            ].map((opt) => {
              const checked = decisionImpact === opt.id;
              return (
                <div
                  key={opt.id}
                  className={`option-tile${checked ? ' selected' : ''}`}
                  onClick={() => setDecisionImpact(opt.id as any)}
                >
                  <input
                    type="radio"
                    name="decisionImpact"
                    checked={checked}
                    onChange={() => {}}
                    aria-label={opt.label}
                  />
                  <div className="option-tile-content">
                    <span className="option-tile-label">{opt.label}</span>
                    <span className="option-tile-hint">{opt.hint}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Q4: Permitted Actions */}
        <div className={`question-card${actionsConflict ? ' has-conflict' : ''}`}>
          <div className="question-header">
            <div className="question-title">
              <IconLock size={16} />
              <span>4. What actions can it take?</span>
            </div>
            {actionsConflict && (
              <span className="conflict-inline-pill">
                <IconAlertTriangle size={12} />
                Requires Oversight
              </span>
            )}
          </div>
          <div className="options-tile-grid">
            {[
              { id: 'none', label: 'No autonomous actions', hint: 'Read-only recommendations' },
              { id: 'advance_candidate', label: 'Advance candidate', hint: 'Moves candidate to next round' },
              { id: 'send_rejection_email', label: 'Send rejection email', hint: 'Dispatches automated rejections' },
              { id: 'schedule_interview', label: 'Schedule interview', hint: 'Books calendar invites' },
            ].map((act) => {
              const checked = actions.includes(act.id);
              return (
                <div
                  key={act.id}
                  className={`option-tile${checked ? ' selected' : ''}`}
                  onClick={() => toggleAction(act.id)}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {}}
                    aria-label={act.label}
                  />
                  <div className="option-tile-content">
                    <span className="option-tile-label">{act.label}</span>
                    <span className="option-tile-hint">{act.hint}</span>
                  </div>
                </div>
              );
            })}
          </div>
          {actionsConflict && (
            <div className="conflict-inline-pill" style={{ marginTop: 'var(--space-2)' }}>
              <IconAlertTriangle size={12} />
              <span>{actionsConflict.message}</span>
            </div>
          )}
        </div>

        {/* Q5: Human Oversight */}
        <div className={`question-card${oversightConflict ? ' has-conflict' : ''}`}>
          <div className="question-header">
            <div className="question-title">
              <IconUserCheck size={16} />
              <span>5. Where does a person step in?</span>
            </div>
            {oversightConflict && (
              <span className="conflict-inline-pill">
                <IconAlertTriangle size={12} />
                Governance Gap
              </span>
            )}
          </div>
          <div className="options-tile-grid">
            {[
              { id: 'never', label: 'Never', hint: 'Autonomous execution without review' },
              { id: 'before_actions', label: 'Before actions', hint: 'Human must authorise action tools' },
              { id: 'always', label: 'Always', hint: 'Every output reviewed before delivery' },
            ].map((ov) => {
              const checked = humanOversight === ov.id;
              return (
                <div
                  key={ov.id}
                  className={`option-tile${checked ? ' selected' : ''}`}
                  onClick={() => setHumanOversight(ov.id as any)}
                >
                  <input
                    type="radio"
                    name="humanOversight"
                    checked={checked}
                    onChange={() => {}}
                    aria-label={ov.label}
                  />
                  <div className="option-tile-content">
                    <span className="option-tile-label">{ov.label}</span>
                    <span className="option-tile-hint">{ov.hint}</span>
                  </div>
                </div>
              );
            })}
          </div>
          {oversightConflict && (
            <div className="conflict-inline-pill" style={{ marginTop: 'var(--space-2)' }}>
              <IconAlertTriangle size={12} />
              <span>{oversightConflict.message}</span>
            </div>
          )}
        </div>

        {/* Q6: Affected Parties */}
        <div className="question-card">
          <div className="question-header">
            <div className="question-title">
              <span>6. Who is affected?</span>
            </div>
            <span className="question-badge">Stakeholders</span>
          </div>
          <div className="options-tile-grid">
            {[
              { id: 'job_candidates', label: 'Job candidates', hint: 'External applicants' },
              { id: 'recruiters', label: 'Recruiters & managers', hint: 'Internal hiring team' },
              { id: 'compliance_officers', label: 'Compliance & auditors', hint: 'Regulatory oversight' },
            ].map((p) => {
              const checked = affectedParties.includes(p.id);
              return (
                <div
                  key={p.id}
                  className={`option-tile${checked ? ' selected' : ''}`}
                  onClick={() => setAffectedParties(toggleItem(affectedParties, p.id))}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {}}
                    aria-label={p.label}
                  />
                  <div className="option-tile-content">
                    <span className="option-tile-label">{p.label}</span>
                    <span className="option-tile-hint">{p.hint}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Q7: Decision Significance */}
        <div className="question-card">
          <div className="question-header">
            <div className="question-title">
              <span>7. Decision significance</span>
            </div>
            <span className="question-badge">EU AI Act Tier</span>
          </div>
          <div className="options-tile-grid">
            {[
              { id: 'non_significant', label: 'Non-significant', hint: 'Informational screening only' },
              { id: 'significant', label: 'Significant', hint: 'Materially affects employment opportunities' },
              { id: 'critical', label: 'Critical', hint: 'Automated final hiring decision gate' },
            ].map((s) => {
              const checked = decisionSignificance === s.id;
              return (
                <div
                  key={s.id}
                  className={`option-tile${checked ? ' selected' : ''}`}
                  onClick={() => setDecisionSignificance(s.id as any)}
                >
                  <input
                    type="radio"
                    name="decisionSignificance"
                    checked={checked}
                    onChange={() => {}}
                    aria-label={s.label}
                  />
                  <div className="option-tile-content">
                    <span className="option-tile-label">{s.label}</span>
                    <span className="option-tile-hint">{s.hint}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Q8: Known Limitations (Full Width) */}
        <div className="question-card question-card-full">
          <div className="question-header">
            <label htmlFor="known-limitations" className="question-title" style={{ margin: 0 }}>
              <span>8. Known limitations & intended scope</span>
            </label>
            <span className="question-badge">Audit Statement</span>
          </div>
          <textarea
            id="known-limitations"
            className="describe-textarea"
            value={knownLimitations}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setKnownLimitations(e.target.value)}
            placeholder="State known limitations, data exclusions, or human verification rules..."
          />
        </div>
      </div>

      {/* Floating / Bottom Action Bar */}
      <div className="describe-bottom-bar">
        <div className="describe-bottom-left">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSaveAnswers}
            disabled={isSaving}
          >
            <IconSave size={15} />
            <span>{isSaving ? 'Saving Answers...' : 'Save Intake Answers'}</span>
          </button>

          {saveNote && (
            <div className="saved-toast">
              <IconCheck size={14} />
              <span>{saveNote}</span>
            </div>
          )}
        </div>

        <Link to="/card" className="next-step-link">
          <span>Proceed to System Card</span>
          <IconArrowRight size={15} />
        </Link>
      </div>
    </div>
  );
}
