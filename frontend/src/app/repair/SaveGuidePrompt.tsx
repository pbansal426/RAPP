'use client';

import { useState } from 'react';
import { requestMagicLink } from '@/lib/auth';
import { storePendingSave } from '@/lib/pendingSave';

interface SaveGuidePromptProps {
  vin: string;
  vinData: Record<string, unknown> | null;
  symptoms: string;
  citations?: string[];
  onDismiss: () => void;
}

// Magic-link auth can't authenticate synchronously the way password signup
// could -- requesting a link doesn't hand back a session until the user
// clicks it (possibly in another tab). So this form only requests the link
// and stashes the guide to save; the actual saveRepair() call happens in
// repair/page.tsx once useAuthUser() reports a signed-in user with a
// matching rapp_pending_save_{vin} entry still pending.
export default function SaveGuidePrompt({ vin, vinData, symptoms, citations, onDismiss }: SaveGuidePromptProps) {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!email.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const paymentSessionId = localStorage.getItem(`rapp_unlocked_${vin}`) ?? undefined;
      storePendingSave(vin, {
        vin,
        year: vinData ? String(vinData.year ?? '') : undefined,
        make: vinData ? String(vinData.make ?? '') : undefined,
        model: vinData ? String(vinData.model ?? '') : undefined,
        engine: vinData ? String(vinData.engine ?? '') : undefined,
        powertrain: vinData?.powertrain ? String(vinData.powertrain) : undefined,
        symptoms,
        paymentSessionId,
        citations: citations && citations.length > 0 ? citations : undefined,
      });
      const res = await requestMagicLink(email.trim(), displayName.trim() || undefined);
      setSent(true);
      setDevLink(res.magicLink);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send a sign-in link. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card" data-testid="save-guide-prompt" style={{ border: '1px solid var(--accent-orange)', position: 'relative' }}>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={onDismiss}
        style={{ position: 'absolute', top: 14, right: 14, background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.1rem', minHeight: 48, minWidth: 48, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        ✕
      </button>

      {sent ? (
        <>
          <p className="card-label">Check Your Email</p>
          <p style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 4 }}>Almost there</p>
          <p className="text-muted text-sm" style={{ marginBottom: 12 }}>
            We sent a sign-in link to {email.trim()}. Click it to finish saving this guide to your garage.
          </p>
          {devLink && (
            <>
              <p className="text-muted text-sm" style={{ marginBottom: 12 }}>
                No email provider is configured for this environment — use the link below directly.
              </p>
              <a href={devLink} className="btn btn-primary" style={{ width: 'auto', padding: '0 18px' }}>
                Sign In &amp; Save →
              </a>
            </>
          )}
        </>
      ) : (
        <>
          <p className="card-label">Save Your Repair Guide</p>
          <p style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 4 }}>Keep this guide in your garage</p>
          <p className="text-muted text-sm" style={{ marginBottom: 16 }}>
            Optional — a free account (no password, just email) permanently saves this guide, your vehicle&apos;s repair history, and your payment for one-click unlocks next time.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input
              className="input"
              type="text"
              placeholder="Name (optional)"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
            <input
              className="input"
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{error}</p>}
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting || !email.trim()}
            >
              {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Sending…</> : 'Send Sign-In Link & Save'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
