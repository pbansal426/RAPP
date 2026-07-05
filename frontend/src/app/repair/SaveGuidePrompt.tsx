'use client';

import { useState } from 'react';
import { signUp } from '@/lib/auth';
import { saveRepair } from '@/lib/repairs';
import { CheckCircleIcon } from '@/app/sharedIcons';

interface SaveGuidePromptProps {
  vin: string;
  vinData: Record<string, unknown> | null;
  symptoms: string;
  citations?: string[];
  onDismiss: () => void;
}

export default function SaveGuidePrompt({ vin, vinData, symptoms, citations, onDismiss }: SaveGuidePromptProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Account creation is backend-driven and always available now.
  const configured = true;

  const handleSubmit = async () => {
    if (!email.trim() || !password.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await signUp(email.trim(), password, displayName.trim() || undefined);
      const paymentSessionId = localStorage.getItem(`rapp_unlocked_${vin}`) ?? undefined;
      await saveRepair({
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
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create your account. Please try again.');
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

      {saved ? (
        <>
          <p className="card-label">Saved</p>
          <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleIcon size={18} style={{ color: '#4ade80' }} /><span>This repair guide is saved to your garage.</span>
          </div>
          <a href="/garage" className="btn btn-secondary" style={{ width: 'auto', padding: '0 18px', marginTop: 8 }}>Go to My Garage →</a>
        </>
      ) : !configured ? (
        <>
          <p className="card-label">Save Your Repair Guide</p>
          <p className="text-muted text-sm">Account creation isn&apos;t configured for this environment yet — check back soon.</p>
        </>
      ) : (
        <>
          <p className="card-label">Save Your Repair Guide</p>
          <p style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 4 }}>Keep this guide in your garage</p>
          <p className="text-muted text-sm" style={{ marginBottom: 16 }}>
            Optional — a free account permanently saves this guide, your vehicle&apos;s repair history, and your payment for one-click unlocks next time.
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
            <input
              className="input"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{error}</p>}
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting || !email.trim() || !password.trim()}
            >
              {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Saving…</> : 'Create Account & Save'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
