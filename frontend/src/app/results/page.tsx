'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';

interface DiagnoseResponse {
  summary: string;
  is_high_risk: boolean;
  high_risk_system: string | null;
  warning_message: string | null;
}

interface CheckoutResponse {
  checkout_url: string;
}

const SAFETY_KEYWORDS = ['airbag', 'srs', 'ev battery', 'hybrid battery', 'high voltage', 'fuel line', 'fuel leak'];

export default function ResultsPage() {
  const router = useRouter();
  const [vin, setVin] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [diagnosis, setDiagnosis] = useState<DiagnoseResponse | null>(null);
  const [safetyWarning, setSafetyWarning] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [payLoading, setPayLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [ownedTools, setOwnedTools] = useState<string[]>([]);

  useEffect(() => {
    const storedVin = localStorage.getItem('rapp_vin');
    const storedSymptoms = localStorage.getItem('rapp_symptoms');
    if (!storedVin || !storedSymptoms) { router.push('/'); return; }
    setVin(storedVin);
    setSymptoms(storedSymptoms);

    // Check safety keywords client-side immediately (no API needed)
    const lower = storedSymptoms.toLowerCase();
    if (SAFETY_KEYWORDS.some((kw) => lower.includes(kw))) {
      setSafetyWarning(
        'DANGER: This symptom involves a safety-critical system. Professional service is strongly recommended before proceeding.'
      );
    }

    const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
    setOwnedTools(tools);

    api.post<DiagnoseResponse>('/api/diagnose', {
      vin: storedVin,
      symptoms: storedSymptoms,
      obd_codes: [],
      tools,
    })
      .then(setDiagnosis)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Diagnosis failed.'))
      .finally(() => setLoading(false));
  }, [router]);

  const handlePay = async () => {
    setPayLoading(true);
    try {
      const { checkout_url } = await api.post<CheckoutResponse>('/api/payments/create-checkout', {
        vin,
        price_type: 'single',
      });
      window.location.href = checkout_url;
    } catch {
      setPayLoading(false);
      alert('Payment service unavailable. Please try again.');
    }
  };

  // Compute required tools
  const getToolRequirements = () => {
    const text = symptoms.toLowerCase();
    const req = [
      { id: 'tool-hand-tools', label: '🔧 Basic Hand Tools (Screwdrivers, Pliers)', estCost: 15 },
      { id: 'tool-socket-set', label: '🔌 Socket Set & Ratchet', estCost: 25 },
      { id: 'tool-torque-wrench', label: '🔧 Torque Wrench', estCost: 20 },
    ];
    if (/(suspension|coilover|spring|strut|shock|exhaust|muffler|wheel|brake|rotor|caliper|pad|oil)/i.test(text)) {
      req.push({ id: 'tool-jack-stands', label: '🚗 Jack & Jack Stands', estCost: 30 });
    }
    if (/(sensor|electrical|wire|harness|ignition|coil|plug|light|alternator|battery|voltage)/i.test(text)) {
      req.push({ id: 'tool-multimeter', label: '⚡ Digital Multimeter', estCost: 12 });
    }
    if (/(code|scan|obd|engine light|check engine|trouble)/i.test(text)) {
      req.push({ id: 'tool-obd-scanner', label: '🖥️ OBD-II Scanner', estCost: 20 });
    }
    if (/(nitrile|glove|glasses|safety|eye)/i.test(text) || true) {
      req.push({ id: 'tool-nitrile-gloves', label: '🧤 Safety Glasses & Gloves', estCost: 5 });
    }
    if (/(rust|stuck|bolt|nut|spray|seized|suspension|exhaust)/i.test(text)) {
      req.push({ id: 'tool-wd40', label: '🧴 Penetrating Oil (WD-40)', estCost: 6 });
    }
    return req;
  };

  const toolRequirements = getToolRequirements();
  const missingTools = toolRequirements.filter(t => !ownedTools.includes(t.id));
  const hasNoTools = ownedTools.length === 0;

  return (
    <main className="page">
      <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start', marginBottom: 12 }}>
        <button
          id="back-to-diagnose-btn"
          data-testid="back-to-diagnose-btn"
          className="btn btn-secondary"
          type="button"
          onClick={() => router.push('/diagnose')}
          style={{ padding: '6px 12px', fontSize: '0.875rem' }}
        >
          ← Back to Diagnosis
        </button>
      </div>

      <header className="page-header">
        <p className="logo">⚙ RAPP</p>
        <h1 className="page-title">Diagnostic & Mod Planning Results</h1>
      </header>

      {/* ── Non-dismissible safety warning ── */}
      {safetyWarning && (
        <div
          data-testid="safety-warning-banner"
          className="safety-banner border-orange-500 bg-orange-950 text-orange-500"
          role="alert"
          aria-live="assertive"
        >
          <span className="safety-banner-icon" aria-hidden="true">⚠️</span>
          <span>{safetyWarning}</span>
        </div>
      )}

      {/* ── Free diagnosis summary ── */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <p className="card-label" style={{ margin: 0 }}>Free Diagnosis & Mod Overview</p>
          <span className="badge badge-free">Verified AI Analysis</span>
        </div>

        <div data-testid="free-diagnosis-summary">
          {loading && <p className="text-muted">Analyzing vehicle OBD-II diagnostics and symptoms…</p>}
          {error && <p style={{ color: 'var(--accent-red)' }}>{error}</p>}
          {diagnosis && (
            <div>
              <p style={{ fontSize: '1.05rem', lineHeight: 1.6, fontWeight: 500 }}>{diagnosis.summary}</p>
              {diagnosis.is_high_risk && (
                <div style={{ marginTop: 14, padding: 12, background: 'rgba(239,68,68,0.15)', borderRadius: 8, border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', fontSize: '0.9rem' }}>
                  ⚠️ <strong>High-Risk Alert:</strong> Delaying this repair/modification risks secondary cascading component damage. Estimated potential collateral repair cost if ignored: <strong>$1,200+</strong>.
                </div>
              )}
            </div>
          )}
          {!loading && !diagnosis && !error && (
            <p className="text-muted">Target reported: {symptoms}</p>
          )}
        </div>
      </div>

      {/* ── Smart Tool Purchase & Match Planner ── */}
      <div className="card">
        <p className="card-label">Garage Tool Planner</p>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 8 }}>Tool & Hardware Compatibility</h3>

        {hasNoTools ? (
          <div style={{ padding: '14px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', borderRadius: 8, marginTop: 10 }}>
            <p style={{ fontSize: '0.9rem', color: '#60a5fa', fontWeight: 600, marginBottom: 8 }}>
              🛠️ No Owned Tools Selected
            </p>
            <p className="text-muted text-sm" style={{ marginBottom: 10 }}>
              No worries! You can still easily complete this project. Here is your budget-optimized tool purchase plan:
            </p>
            <ul style={{ paddingLeft: 20, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {toolRequirements.map(t => (
                <li key={t.id} style={{ marginBottom: 4 }}>
                  <strong>{t.label}</strong> (Est: ${t.estCost}) — <span style={{ color: '#4ade80' }}>Buy on Amazon or AutoZone</span>
                </li>
              ))}
            </ul>
            <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-yellow)', marginTop: 8 }}>
              Total Estimated Tool Budget: ~${toolRequirements.reduce((acc, curr) => acc + curr.estCost, 0)}
            </p>
          </div>
        ) : (
          <div>
            <div className="tool-match-pill" style={{ display: 'inline-flex', marginBottom: 12 }}>
              {missingTools.length === 0 
                ? '✅ Reassurance: You own all required tools to complete this repair/modification safely!'
                : `⚡ RAPP matched ${toolRequirements.length - missingTools.length} of ${toolRequirements.length} tools. You have basic gear ready.`}
            </div>

            {missingTools.length > 0 && (
              <div style={{ marginTop: 10, padding: 12, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 8 }}>
                <p style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent-yellow)', marginBottom: 6 }}>
                  🛒 Missing Tools Needed (Smart Purchase Guide):
                </p>
                <ul style={{ paddingLeft: 18, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {missingTools.map(t => (
                    <li key={t.id} style={{ marginBottom: 4 }}>
                      {t.label} (Est: ${t.estCost})
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Price & Value Comparison Table ── */}
      <div className="card">
        <p className="card-label">Why DIY With RAPP?</p>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: 8 }}>Project Route Comparison</h2>
        <p className="text-muted text-sm">See how guided RAPP self-repair/modification compares against traditional garage rates:</p>
        
        <table className="price-table">
          <thead>
            <tr>
              <th>Method</th>
              <th>Est. Cost</th>
              <th>Timeframe</th>
              <th>Value Advantage</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>🏢 Dealership / Pro Shop</td>
              <td>$450 – $900</td>
              <td>3 – 5 Days</td>
              <td className="text-muted">High labor markup + appointment delays</td>
            </tr>
            <tr>
              <td>🔧 Independent Shop</td>
              <td>$200 – $400</td>
              <td>1 – 2 Days</td>
              <td className="text-muted">Variable quality & labor costs ($150+/hr)</td>
            </tr>
            <tr className="price-row-highlight">
              <td>⚡ RAPP Guided DIY</td>
              <td className="price-val-green">$35 – $80</td>
              <td>2 – 3 Hours</td>
              <td>Save up to 90% today with precise guided instructions</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ── Locked repair steps (hidden by default) ── */}
      <div data-testid="locked-repair-steps" style={{ display: 'none' }} aria-hidden="true">
        <p>Locked repair content placeholder.</p>
      </div>

      {/* ── Premium Sleek Frosted Glass Paywall Gate ── */}
      <div className="premium-paywall sticky-mobile-cta" style={{
        background: 'rgba(26, 26, 38, 0.75)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderRadius: 'var(--radius)',
        padding: '36px 28px',
        textAlign: 'center',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
          <span className="badge" style={{ background: 'rgba(251,191,36,0.15)', color: 'var(--accent-yellow)' }}>
            ⭐ Premium OEM Service Access
          </span>
        </div>
        <p className="paywall-gate-title" style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.01em' }}>
          🔓 Unlock Step-by-Step OEM Guide
        </p>
        
        <div style={{
          textAlign: 'left',
          maxWidth: '380px',
          margin: '18px auto 24px',
          fontSize: '0.88rem',
          lineHeight: '1.6',
          color: 'var(--text-primary)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8' }}>💡 <strong>4-Phase Garage Safe Checklist</strong></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8' }}>🔧 <strong>Exact Socket & Tool Wrench Sizes</strong></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8' }}>⚡ <strong>Precise Bolt Torque Specs</strong> (Prevents stripping)</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8' }}>🔍 <strong>Constant Quality Checkpoints</strong></div>
        </div>

        <button
          id="payment-cta-btn"
          data-testid="payment-cta-btn"
          className="btn btn-primary"
          onClick={handlePay}
          disabled={payLoading || loading}
          style={{
            maxWidth: 380,
            margin: '0 auto',
            minHeight: 56,
            background: 'linear-gradient(135deg, #f59e0b, #d97706)',
            boxShadow: '0 4px 20px rgba(217,119,6,0.3)',
            borderRadius: '8px'
          }}
        >
          {payLoading
            ? <><span className="loading-spinner" aria-hidden="true" /> Securing Access…</>
            : 'Unlock Complete Guide — $4.00'}
        </button>
        <p className="text-muted text-sm" style={{ marginTop: 12 }}>
          Secure Checkout • Instant Lifetime Access • 100% Satisfaction Guarantee
        </p>
      </div>
    </main>
  );
}
