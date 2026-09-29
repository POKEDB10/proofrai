import { Fragment, useEffect, useState } from 'react';
import type { ChangeEvent } from 'react';
import {
  confirmSystemCard,
  getSystemCard,
  postCardDrafts,
  SystemCardData,
} from '../api';
import '../styles/card.css';

export function Card() {
  const [card, setCard] = useState<SystemCardData | null>(null);
  const [intendedUse, setIntendedUse] = useState<string>('');
  const [knownLimits, setKnownLimits] = useState<string>('');
  const [confirmedBy, setConfirmedBy] = useState<string>('Jane Doe');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRegenerating, setIsRegenerating] = useState<boolean>(false);
  const [isConfirming, setIsConfirming] = useState<boolean>(false);
  const [feedbackNote, setFeedbackNote] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadCard() {
    try {
      const data = await getSystemCard();
      setCard(data);
      setIntendedUse(data.intended_use);
      setKnownLimits(data.known_limits);
      if (data.confirmed_by) {
        setConfirmedBy(data.confirmed_by);
      }
      setErrorMessage(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Load failed';
      setErrorMessage(`Failed to load system card: ${msg}`);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadCard();
  }, []);

  async function handleRegenerateDrafts() {
    setIsRegenerating(true);
    setFeedbackNote(null);
    setErrorMessage(null);

    try {
      const updated = await postCardDrafts();
      setCard(updated);
      setIntendedUse(updated.intended_use);
      setKnownLimits(updated.known_limits);
      setFeedbackNote('Drafts regenerated');
      setTimeout(() => setFeedbackNote(null), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Regeneration failed';
      setErrorMessage(`Failed to regenerate drafts: ${msg}`);
    } finally {
      setIsRegenerating(false);
    }
  }

  async function handleConfirmCard() {
    if (!confirmedBy.trim()) {
      setErrorMessage('Please provide a reviewer name to confirm the card.');
      return;
    }

    setIsConfirming(true);
    setFeedbackNote(null);
    setErrorMessage(null);

    try {
      const confirmed = await confirmSystemCard(confirmedBy, intendedUse, knownLimits);
      setCard(confirmed);
      setFeedbackNote('Card confirmed');
      setTimeout(() => setFeedbackNote(null), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Confirmation failed';
      setErrorMessage(`Failed to confirm card: ${msg}`);
    } finally {
      setIsConfirming(false);
    }
  }

  function formatDate(isoString: string | null): string {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  }

  const isConfirmed = card?.status === 'confirmed';
  const confirmationText = isConfirmed
    ? `Confirmed by ${card?.confirmed_by} on ${formatDate(card?.confirmed_at)}.`
    : 'Draft. Not confirmed.';

  return (
    <div className="page-container card-screen">
      <h1 className="page-title">System card</h1>

      {errorMessage && (
        <div style={{ color: 'var(--fail)', marginBottom: 'var(--space-3)', fontSize: 'var(--text-table)' }}>
          {errorMessage}
        </div>
      )}

      {isLoading ? (
        <div className="empty-state">Loading system card...</div>
      ) : (
        <div className="card-document">
          <div className="card-doc-title">{card?.title || 'HireAssist Recruiting Assistant'}</div>

          {/* Structured Fields Two-Column List */}
          <div className="structured-list">
            {card?.structured_fields &&
              Object.entries(card.structured_fields).map(([key, val]) => (
                <Fragment key={key}>
                  <div className="structured-key">{key}</div>
                  <div className="structured-value">{val}</div>
                </Fragment>
              ))}
          </div>

          {/* Status Line */}
          <div className={`card-status-line${isConfirmed ? ' confirmed' : ''}`}>
            {confirmationText}
          </div>

          {/* Editable Drafts */}
          <div className="card-textarea-block">
            <label htmlFor="intended-use" className="card-textarea-label">
              Intended use
            </label>
            <textarea
              id="intended-use"
              className="card-textarea"
              value={intendedUse}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setIntendedUse(e.target.value)}
              placeholder="Describe intended use and operational workflow"
            />
          </div>

          <div className="card-textarea-block">
            <label htmlFor="known-limits" className="card-textarea-label">
              Known limits
            </label>
            <textarea
              id="known-limits"
              className="card-textarea"
              value={knownLimits}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setKnownLimits(e.target.value)}
              placeholder="Describe known limits, boundaries, and validation requirements"
            />
          </div>

          {/* Confirmation Form */}
          <div className="confirm-bar">
            <label htmlFor="reviewer-name" className="structured-key" style={{ width: '120px' }}>
              Confirmed by:
            </label>
            <input
              id="reviewer-name"
              type="text"
              className="reviewer-input"
              value={confirmedBy}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setConfirmedBy(e.target.value)}
              placeholder="Reviewer full name"
            />
          </div>

          <div className="card-actions-bar">
            <button
              type="button"
              onClick={handleConfirmCard}
              disabled={isConfirming}
            >
              Confirm card
            </button>
            <button
              type="button"
              className="card-text-link"
              onClick={handleRegenerateDrafts}
              disabled={isRegenerating}
            >
              Regenerate drafts
            </button>
            {feedbackNote && <span style={{ color: 'var(--pass)', fontWeight: 600, fontSize: 'var(--text-table)' }}>{feedbackNote}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
