import { useState } from 'react';
import type { ChangeEvent } from 'react';
import { Link } from 'react-router-dom';
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
        message: 'outputs determine outcomes and no person steps in.',
      });
    }
    const activeActions = actions.filter((a) => a !== 'none');
    if (activeActions.length > 0 && humanOversight === 'never') {
      list.push({
        field: 'actions',
        message: 'the assistant can take actions and no person steps in.',
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
          message: 'it sees sensitive fields and no need is stated.',
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
      'The model does not verify educational credentials or legal work authorisation.'
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
        message: 'outputs determine outcomes and no person steps in.',
      },
      {
        field: 'actions',
        message: 'the assistant can take actions and no person steps in.',
      },
      {
        field: 'data_seen',
        message: 'it sees sensitive fields and no need is stated.',
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
      setSaveNote(`Answers saved. ${count} controls proposed.`);
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
      <h1 className="page-title">Describe the assistant</h1>
      <p className="describe-intro">
        Eight questions about how it is used. Your answers shape the system card and the proposed controls.
      </p>

      {errorMessage && (
        <div style={{ color: 'var(--fail)', marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)' }}>
          {errorMessage}
        </div>
      )}

      <div style={{ marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)', color: 'var(--ink-2)' }}>
        Presets:{' '}
        <button type="button" className="text-link" onClick={applyCompliantPreset}>
          compliant assistant
        </button>
        {', '}
        <button type="button" className="text-link" onClick={applyConflictPreset}>
          governance conflict
        </button>
      </div>

      <div className="describe-form">

      {/* Question 1: Tasks */}
      <div className="question-block">
        <div className="question-title">What does the assistant do?</div>
        <div className="options-grid">
          <label className="option-label">
            <input
              type="checkbox"
              checked={tasks.includes('summarise_applications')}
              onChange={() => setTasks(toggleItem(tasks, 'summarise_applications'))}
            />
            Summarises applications
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={tasks.includes('answer_candidate_questions')}
              onChange={() => setTasks(toggleItem(tasks, 'answer_candidate_questions'))}
            />
            Answers candidate questions
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={tasks.includes('draft_screening_notes')}
              onChange={() => setTasks(toggleItem(tasks, 'draft_screening_notes'))}
            />
            Drafts screening notes
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={tasks.includes('send_messages')}
              onChange={() => setTasks(toggleItem(tasks, 'send_messages'))}
            />
            Sends messages
          </label>
        </div>
      </div>

      {/* Question 2: Data Seen */}
      <div className="question-block">
        <div className="question-title">What data does it see?</div>
        <div className="options-column">
          <label className="option-label">
            <input
              type="checkbox"
              checked={dataSeen.includes('work_history')}
              onChange={() => setDataSeen(toggleItem(dataSeen, 'work_history'))}
            />
            Work history and experience
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={dataSeen.includes('skills_education')}
              onChange={() => setDataSeen(toggleItem(dataSeen, 'skills_education'))}
            />
            Skills and qualifications
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={dataSeen.includes('contact_details')}
              onChange={() => setDataSeen(toggleItem(dataSeen, 'contact_details'))}
            />
            Contact details (email, phone, address)
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={dataSeen.includes('protected_characteristics')}
              onChange={() => setDataSeen(toggleItem(dataSeen, 'protected_characteristics'))}
            />
            Protected characteristics (date of birth, gender, nationality, health, marital status)
          </label>
        </div>
        {dataConflict && (
          <div className="conflict-flag">
            <span className="status-square sq-review" aria-hidden="true" />
            <span><strong>Conflict:</strong> {dataConflict.message}</span>
          </div>
        )}
      </div>

      {/* Question 3: Outputs are used to */}
      <div className="question-block">
        <div className="question-title">Outputs are used to</div>
        <div className="options-grid">
          <label className="option-label">
            <input
              type="radio"
              name="decisionImpact"
              value="inform"
              checked={decisionImpact === 'inform'}
              onChange={() => setDecisionImpact('inform')}
            />
            inform recruiters
          </label>
          <label className="option-label">
            <input
              type="radio"
              name="decisionImpact"
              value="determine"
              checked={decisionImpact === 'determine'}
              onChange={() => setDecisionImpact('determine')}
            />
            determine outcomes
          </label>
          <label className="option-label">
            <input
              type="radio"
              name="decisionImpact"
              value="neither"
              checked={decisionImpact === 'neither'}
              onChange={() => setDecisionImpact('neither')}
            />
            neither
          </label>
        </div>
      </div>

      {/* Question 4: Permitted actions */}
      <div className="question-block">
        <div className="question-title">What actions can it take?</div>
        <div className="options-column">
          <label className="option-label">
            <input
              type="checkbox"
              checked={actions.includes('none')}
              onChange={() => toggleAction('none')}
            />
            No autonomous actions
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={actions.includes('advance_candidate')}
              onChange={() => toggleAction('advance_candidate')}
            />
            Advance candidate to next stage
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={actions.includes('send_rejection_email')}
              onChange={() => toggleAction('send_rejection_email')}
            />
            Send rejection email
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={actions.includes('schedule_interview')}
              onChange={() => toggleAction('schedule_interview')}
            />
            Schedule interview
          </label>
        </div>
        {actionsConflict && (
          <div className="conflict-flag">
            <span className="status-square sq-review" aria-hidden="true" />
            <span><strong>Conflict:</strong> {actionsConflict.message}</span>
          </div>
        )}
      </div>

      {/* Question 5: Human oversight */}
      <div className="question-block">
        <div className="question-title">Where does a person step in?</div>
        <div className="options-grid">
          <label className="option-label">
            <input
              type="radio"
              name="humanOversight"
              value="never"
              checked={humanOversight === 'never'}
              onChange={() => setHumanOversight('never')}
            />
            never
          </label>
          <label className="option-label">
            <input
              type="radio"
              name="humanOversight"
              value="before_actions"
              checked={humanOversight === 'before_actions'}
              onChange={() => setHumanOversight('before_actions')}
            />
            before actions
          </label>
          <label className="option-label">
            <input
              type="radio"
              name="humanOversight"
              value="always"
              checked={humanOversight === 'always'}
              onChange={() => setHumanOversight('always')}
            />
            always
          </label>
        </div>
        {oversightConflict && (
          <div className="conflict-flag">
            <span className="status-square sq-review" aria-hidden="true" />
            <span><strong>Conflict:</strong> {oversightConflict.message}</span>
          </div>
        )}
      </div>

      {/* Question 6: Affected parties */}
      <div className="question-block">
        <div className="question-title">Who is affected?</div>
        <div className="options-column">
          <label className="option-label">
            <input
              type="checkbox"
              checked={affectedParties.includes('job_candidates')}
              onChange={() => setAffectedParties(toggleItem(affectedParties, 'job_candidates'))}
            />
            Job candidates
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={affectedParties.includes('recruiters')}
              onChange={() => setAffectedParties(toggleItem(affectedParties, 'recruiters'))}
            />
            Recruiters and hiring managers
          </label>
          <label className="option-label">
            <input
              type="checkbox"
              checked={affectedParties.includes('compliance_officers')}
              onChange={() => setAffectedParties(toggleItem(affectedParties, 'compliance_officers'))}
            />
            Compliance and auditors
          </label>
        </div>
      </div>

      {/* Question 7: Decision significance */}
      <div className="question-block">
        <div className="question-title">Decision significance</div>
        <div className="options-column">
          <label className="option-label">
            <input
              type="radio"
              name="decisionSignificance"
              value="non_significant"
              checked={decisionSignificance === 'non_significant'}
              onChange={() => setDecisionSignificance('non_significant')}
            />
            Non-significant (informational screening)
          </label>
          <label className="option-label">
            <input
              type="radio"
              name="decisionSignificance"
              value="significant"
              checked={decisionSignificance === 'significant'}
              onChange={() => setDecisionSignificance('significant')}
            />
            Significant (affects employment opportunity)
          </label>
          <label className="option-label">
            <input
              type="radio"
              name="decisionSignificance"
              value="critical"
              checked={decisionSignificance === 'critical'}
              onChange={() => setDecisionSignificance('critical')}
            />
            Critical (automated final hiring decision)
          </label>
        </div>
      </div>

      {/* Question 8: Known limitations */}
      <div className="question-block">
        <label htmlFor="known-limitations" className="question-title" style={{ display: 'block' }}>
          Known limitations
        </label>
        <textarea
          id="known-limitations"
          className="describe-textarea"
          value={knownLimitations}
          onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setKnownLimitations(e.target.value)}
          placeholder="State known limitations, data exclusions, or human verification rules"
        />
      </div>
      </div>

      {/* Actions */}
      <div className="describe-actions">
        <button
          type="button"
          onClick={handleSaveAnswers}
          disabled={isSaving}
        >
          {isSaving ? 'Saving answers...' : 'Save answers'}
        </button>
        <Link to="/card" className="next-step-link">
          Proceed to system card
        </Link>
        {saveNote && <span className="saved-note">{saveNote}</span>}
      </div>
    </div>
  );
}
