'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import {
  AppLogoMarkIcon,
  ShieldAlertIcon,
  CheckCircleIcon,
  DocumentIcon,
  QualityCheckIcon,
} from '@/app/sharedIcons';

interface VerifyExternalResponse {
  verified_claims: string[];
  fitment_or_spec_errors: string[];
  missing_safety_warnings: string[];
  accuracy_score: number;
}

function ScoreRing({ score }: { score: number }) {
  const radius = 52;
  const circ = 2 * Math.PI * radius;
  const dash = (score / 100) * circ;
  const color = score >= 85 ? '#4ade80' : score >= 60 ? '#fb923c' : '#f87171';

  return (
    <div
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg
        width={128}
        height={128}
        viewBox="0 0 128 128"
        style={{ transform: 'rotate(-90deg)' }}
      >
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="10"
        />
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center' }}>
        <div style={{ fontSize: '2rem', fontWeight: 900, color, lineHeight: 1 }}>
          {score}
        </div>
        <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontWeight: 600, marginTop: 2 }}>
          / 100
        </div>
      </div>
    </div>
  );
}

export default function CheckAiPage() {
  const router = useRouter();
  const [vin, setVin] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [externalAiText, setExternalAiText] = useState('');
  const [result, setResult] = useState<VerifyExternalResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vin.trim() || !symptoms.trim() || !externalAiText.trim()) {
      setError('Please fill in all three fields.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.post<VerifyExternalResponse>(
        '/api/diagnose/verify-external',
        {
          vin: vin.trim().toUpperCase(),
          symptoms: symptoms.trim(),
          external_ai_text: externalAiText.trim(),
        }
      );
      setResult(data);
      setTimeout(
        () => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }),
        100
      );
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'message' in err) {
        setError((err as { message: string }).message);
      } else {
        setError('Verification failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const scoreLabel = result
    ? result.accuracy_score >= 85
      ? 'Highly Accurate'
      : result.accuracy_score >= 60
        ? 'Partially Accurate'
        : 'Likely Inaccurate'
    : '';

  const scoreColor = result
    ? result.accuracy_score >= 85
      ? '#4ade80'
      : result.accuracy_score >= 60
        ? '#fb923c'
        : '#f87171'
    : '#fff';

  return (
    <main
      style={{
        minHeight: '100vh',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-sans)',
      }}
    >
      {/* ── Hero ── */}
      <section
        style={{
          background:
            'linear-gradient(135deg, rgba(15,23,42,0.98) 0%, rgba(30,41,59,0.95) 100%)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          padding: '48px 24px 40px',
          textAlign: 'center',
        }}
      >
        <div style={{ maxWidth: 680, margin: '0 auto' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              marginBottom: 20,
            }}
          >
            <AppLogoMarkIcon size={26} style={{ color: 'var(--accent-orange)' }} />
            <span
              style={{
                fontSize: '1.05rem',
                fontWeight: 800,
                letterSpacing: '0.08em',
                color: 'var(--accent-orange)',
              }}
            >
              RAPP
            </span>
          </div>

          <h1
            style={{
              fontSize: 'clamp(1.75rem, 5vw, 2.5rem)',
              fontWeight: 900,
              lineHeight: 1.15,
              marginBottom: 14,
              background:
                'linear-gradient(135deg, #f1f5f9, var(--accent-orange))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Did ChatGPT Give You Repair Advice?
          </h1>

          <p
            style={{
              fontSize: '1.1rem',
              color: '#94a3b8',
              lineHeight: 1.65,
              marginBottom: 24,
            }}
          >
            Paste any AI-generated advice below. RAPP cross-references it against
            factory service manuals &amp; NHTSA Technical Service Bulletins to catch
            wrong torque specs, hallucinated part numbers, and missing safety warnings.
          </p>

          <div
            style={{
              display: 'flex',
              gap: 12,
              justifyContent: 'center',
              flexWrap: 'wrap',
            }}
          >
            {[
              { label: 'OEM-Grounded', icon: '📋' },
              { label: 'TSB-Verified', icon: '🔍' },
              { label: 'Safety-First', icon: '🛡️' },
            ].map(({ label, icon }) => (
              <span
                key={label}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '20px',
                  padding: '6px 14px',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  color: '#cbd5e1',
                }}
              >
                {icon} {label}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Form ── */}
      <section style={{ maxWidth: 720, margin: '0 auto', padding: '40px 20px' }}>
        <form id="check-ai-form" onSubmit={handleSubmit}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* VIN */}
            <div>
              <label
                htmlFor="vin-input"
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: '#94a3b8',
                  marginBottom: 8,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Vehicle VIN
              </label>
              <input
                id="vin-input"
                type="text"
                className="input"
                value={vin}
                onChange={(e) => setVin(e.target.value.toUpperCase())}
                placeholder="e.g. 1HGBH41JXMN109186"
                maxLength={17}
                style={{
                  width: '100%',
                  fontFamily: 'monospace',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                }}
                autoComplete="off"
                spellCheck={false}
              />
              <p
                style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 6 }}
              >
                The VIN lets us pull vehicle-specific OEM specs &amp; TSBs for your
                exact trim.
              </p>
            </div>

            {/* Symptoms */}
            <div>
              <label
                htmlFor="symptoms-input"
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: '#94a3b8',
                  marginBottom: 8,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Symptoms / Problem Description
              </label>
              <textarea
                id="symptoms-input"
                className="input"
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
                placeholder="e.g. Engine misfiring on cylinder 3, P0303 DTC code"
                rows={3}
                style={{ width: '100%', resize: 'vertical', minHeight: 80 }}
              />
            </div>

            {/* AI Text */}
            <div>
              <label
                htmlFor="ai-text-input"
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: '#94a3b8',
                  marginBottom: 8,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Paste AI Advice (ChatGPT, Claude, Gemini, etc.)
              </label>
              <textarea
                id="ai-text-input"
                className="input"
                value={externalAiText}
                onChange={(e) => setExternalAiText(e.target.value)}
                placeholder="Paste the full AI response here…"
                rows={8}
                style={{ width: '100%', resize: 'vertical', minHeight: 160 }}
              />
            </div>

            {error && (
              <div
                style={{
                  padding: '12px 16px',
                  background: 'rgba(239,68,68,0.12)',
                  border: '1px solid rgba(239,68,68,0.3)',
                  borderRadius: 8,
                  color: '#fca5a5',
                  fontSize: '0.9rem',
                }}
              >
                {error}
              </div>
            )}

            <button
              id="verify-ai-btn"
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{
                minHeight: 52,
                fontSize: '1rem',
                fontWeight: 800,
                gap: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {loading ? (
                <>
                  <span className="loading-spinner" aria-hidden="true" /> Verifying
                  against OEM database…
                </>
              ) : (
                <>
                  <QualityCheckIcon size={18} /> Verify This Advice
                </>
              )}
            </button>
          </div>
        </form>

        {/* ── Results ── */}
        {result && (
          <div ref={resultsRef} style={{ marginTop: 40 }}>

            {/* Accuracy Score Ring */}
            <div
              style={{
                background:
                  'linear-gradient(135deg, rgba(15,23,42,0.9), rgba(30,41,59,0.8))',
                border: `2px solid ${scoreColor}33`,
                borderRadius: 16,
                padding: '32px 28px',
                marginBottom: 24,
                textAlign: 'center',
              }}
            >
              <p
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: '#94a3b8',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  marginBottom: 20,
                }}
              >
                OEM Accuracy Score
              </p>
              <ScoreRing score={result.accuracy_score} />
              <div style={{ marginTop: 16 }}>
                <span style={{ fontSize: '1.2rem', fontWeight: 800, color: scoreColor }}>
                  {scoreLabel}
                </span>
              </div>
              {result.accuracy_score < 90 && (
                <div
                  style={{
                    marginTop: 20,
                    padding: '14px 18px',
                    background: 'rgba(251,146,60,0.1)',
                    border: '1px solid rgba(251,146,60,0.25)',
                    borderRadius: 10,
                    fontSize: '0.88rem',
                    color: '#fdba74',
                    lineHeight: 1.5,
                  }}
                >
                  <strong>Heads up:</strong> This advice scored below 90/100 — some claims
                  may not match factory specs for your specific vehicle. Unlock the official
                  RAPP OEM procedure below.
                </div>
              )}
            </div>

            {/* Verified Claims */}
            {result.verified_claims.length > 0 && (
              <div className="card" style={{ marginBottom: 16 }}>
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}
                >
                  <CheckCircleIcon size={18} style={{ color: '#4ade80' }} />
                  <p
                    className="card-label"
                    style={{ margin: 0, color: '#4ade80' }}
                  >
                    Verified Claims ({result.verified_claims.length})
                  </p>
                </div>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 20,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  {result.verified_claims.map((c, i) => (
                    <li
                      key={i}
                      style={{ color: '#a7f3d0', fontSize: '0.9rem', lineHeight: 1.5 }}
                    >
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Spec Errors */}
            {result.fitment_or_spec_errors.length > 0 && (
              <div
                className="card"
                style={{ marginBottom: 16, borderLeft: '4px solid #f87171' }}
              >
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}
                >
                  <ShieldAlertIcon size={18} style={{ color: '#f87171' }} />
                  <p
                    className="card-label"
                    style={{ margin: 0, color: '#f87171' }}
                  >
                    Fitment / Spec Errors ({result.fitment_or_spec_errors.length})
                  </p>
                </div>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 20,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  {result.fitment_or_spec_errors.map((e, i) => (
                    <li
                      key={i}
                      style={{ color: '#fca5a5', fontSize: '0.9rem', lineHeight: 1.5 }}
                    >
                      {e}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Missing Safety Warnings */}
            {result.missing_safety_warnings.length > 0 && (
              <div
                className="card"
                style={{ marginBottom: 16, borderLeft: '4px solid #fb923c' }}
              >
                <div
                  style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}
                >
                  <ShieldAlertIcon size={18} style={{ color: '#fb923c' }} />
                  <p
                    className="card-label"
                    style={{ margin: 0, color: '#fb923c' }}
                  >
                    Missing Safety Warnings ({result.missing_safety_warnings.length})
                  </p>
                </div>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 20,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  {result.missing_safety_warnings.map((w, i) => (
                    <li
                      key={i}
                      style={{ color: '#fdba74', fontSize: '0.9rem', lineHeight: 1.5 }}
                    >
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Conversion CTA */}
            <div
              style={{
                marginTop: 28,
                padding: '28px 24px',
                background:
                  'linear-gradient(135deg, rgba(251,146,60,0.12), rgba(234,88,12,0.08))',
                border: '1px solid rgba(251,146,60,0.25)',
                borderRadius: 14,
                textAlign: 'center',
              }}
            >
              <DocumentIcon size={28} style={{ color: 'var(--accent-orange)', marginBottom: 12 }} />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, marginBottom: 10 }}>
                Get the Exact OEM Procedure
              </h2>
              <p
                style={{
                  color: '#94a3b8',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                  marginBottom: 20,
                }}
              >
                Unlock the factory-verified, step-by-step repair guide for your exact VIN —
                with correct torque specs, OEM part numbers, and NHTSA safety call-outs.
              </p>
              <div
                style={{
                  display: 'flex',
                  gap: 12,
                  justifyContent: 'center',
                  flexWrap: 'wrap',
                }}
              >
                <button
                  id="get-oem-procedure-btn"
                  className="btn btn-primary"
                  type="button"
                  onClick={() => {
                    if (vin) {
                      if (typeof window !== 'undefined') {
                        localStorage.setItem('rapp_vin', vin);
                        if (symptoms) localStorage.setItem('rapp_symptoms', symptoms);
                      }
                      router.push('/results');
                    } else {
                      router.push('/');
                    }
                  }}
                  style={{ width: 'auto', padding: '12px 24px', fontWeight: 800 }}
                >
                  Get Official Repair Guide →
                </button>
                <button
                  id="check-ai-start-over-btn"
                  className="btn btn-secondary"
                  type="button"
                  onClick={() => {
                    setResult(null);
                    setExternalAiText('');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  style={{ width: 'auto', padding: '12px 24px' }}
                >
                  Check Another Answer
                </button>
              </div>
            </div>
          </div>
        )}

        <button
          className="btn btn-outline"
          type="button"
          onClick={() => router.push('/')}
          style={{ marginTop: 40, minHeight: 44, width: '100%' }}
        >
          ← Back to Home
        </button>
      </section>
    </main>
  );
}
