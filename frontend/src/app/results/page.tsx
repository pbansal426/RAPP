'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import PartsPurchasePlan from './PartsPurchasePlan';
import { signUp } from '@/lib/auth';
import { saveRepair } from '@/lib/repairs';
import {
  HandToolsIcon,
  SocketSetIcon,
  TorqueWrenchIcon,
  JackStandsIcon,
  MultimeterIcon,
  ObdScannerIcon,
  SafetyGlovesIcon,
  PenetratingOilIcon,
} from '@/app/diagnose/toolIcons';
import {
  AppLogoMarkIcon,
  AlertTriangleIcon,
  ToolboxIcon,
  CheckCircleIcon,
  BoltIcon,
  CartIcon,
  BuildingIcon,
  WrenchIcon,
  StarIcon,
  UnlockIcon,
  ChecklistIcon,
  QualityCheckIcon,
} from '@/app/sharedIcons';
import { getComplaintsSummary, getOpenRecalls } from '@/lib/vehicleSafety';
import type {
  ComplaintsSummaryResponse,
  DiagnosisResponse,
  RecallsResponse,
  VehicleInfo,
} from '@/lib/types';

interface CheckoutResponse {
  checkout_url: string;
  // "live" means checkout_url is a real checkout.stripe.com page the user
  // must actually complete -- "mock" is our own stub that just redirects
  // straight back (see handlePay).
  mode: 'mock' | 'live';
}

const SAFETY_KEYWORDS = ['airbag', 'srs', 'ev battery', 'hybrid battery', 'high voltage', 'fuel line', 'fuel leak'];

export default function ResultsPage() {
  const router = useRouter();
  const [vin, setVin] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [diagnosis, setDiagnosis] = useState<DiagnosisResponse | null>(null);
  const [vinData, setVinData] = useState<VehicleInfo | null>(null);
  const [safetyWarning, setSafetyWarning] = useState<string | null>(null);
  const [recalls, setRecalls] = useState<RecallsResponse | null>(null);
  const [complaintsSummary, setComplaintsSummary] = useState<ComplaintsSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [payLoading, setPayLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [ownedTools, setOwnedTools] = useState<string[]>([]);

  // Garage Vault Sign-up State
  const [garageEmail, setGarageEmail] = useState('');
  const [garagePassword, setGaragePassword] = useState('');
  const [garageName, setGarageName] = useState('');
  const [garageSubmitting, setGarageSubmitting] = useState(false);
  const [garageError, setGarageError] = useState<string | null>(null);
  const [garageSaved, setGarageSaved] = useState(false);

  const handleGarageSignUp = async () => {
    if (!garageEmail.trim() || !garagePassword.trim()) return;
    setGarageSubmitting(true);
    setGarageError(null);
    try {
      await signUp(garageEmail.trim(), garagePassword, garageName.trim() || undefined);
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
      });
      setGarageSaved(true);
    } catch (err) {
      setGarageError(err instanceof Error ? err.message : 'Could not create your account. Please try again.');
    } finally {
      setGarageSubmitting(false);
    }
  };

  useEffect(() => {
    const storedVin = localStorage.getItem('rapp_vin');
    // Symptoms text is optional (OBD codes/tools/photos alone are enough
    // context), so an empty string is valid -- only a completely missing
    // key (never went through /diagnose) should redirect home.
    const storedSymptoms = localStorage.getItem('rapp_symptoms');
    if (!storedVin || storedSymptoms === null) { router.push('/'); return; }
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

    const storedVinData = localStorage.getItem('rapp_vin_data');
    const parsedVehicle: VehicleInfo | null = storedVinData ? JSON.parse(storedVinData) : null;
    if (parsedVehicle) setVinData(parsedVehicle);

    // Recalls/complaints are independent of symptoms (they exist whether or
    // not this visit's symptom matches one) and free to look up -- fire
    // them as soon as year/make/model are known, don't gate on the
    // diagnose call below. Both endpoints degrade to an empty result
    // server-side on failure, so a rejected promise here would only mean a
    // genuine frontend/network issue -- still just silently skip, since
    // this is supplementary trust-building content, not core to the page.
    if (parsedVehicle?.year && parsedVehicle.make && parsedVehicle.model) {
      getOpenRecalls(parsedVehicle.year, parsedVehicle.make, parsedVehicle.model)
        .then(setRecalls)
        .catch(() => {});
      getComplaintsSummary(parsedVehicle.year, parsedVehicle.make, parsedVehicle.model)
        .then(setComplaintsSummary)
        .catch(() => {});
    }

    const obdCodes = JSON.parse(localStorage.getItem('rapp_obd_codes') ?? '[]') as string[];

    api.post<DiagnosisResponse>('/api/diagnose', {
      vin: storedVin,
      symptoms: storedSymptoms,
      obd_codes: obdCodes,
      tools,
      vehicle: parsedVehicle,
    })
      .then(setDiagnosis)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Diagnosis failed.'))
      .finally(() => setLoading(false));
  }, [router]);

  const handlePay = async () => {
    setPayLoading(true);
    try {
      const { checkout_url, mode } = await api.post<CheckoutResponse>('/api/payments/create-checkout', {
        vin,
        price_type: 'single',
        symptoms,
      });

      if (mode === 'live') {
        // A real Stripe-hosted Checkout page -- this MUST be a genuine
        // full-page navigation. The user has to actually enter a card and
        // complete payment there before Stripe redirects them back to our
        // success_url; there's no session to "skip ahead" to yet.
        window.location.href = checkout_url;
        return;
      }

      // Mock stub: a backend URL that just 303s straight back to our own
      // success route with no real payment step in between. Doing a
      // full-page hop to the backend here caused a blank page when the
      // backend was slow/unreachable, so we stay in the SPA instead: pull
      // the session id out and route straight to the success handler.
      let sessionId = 'cs_test_stub';
      try {
        sessionId = new URL(checkout_url).searchParams.get('session_id') || sessionId;
      } catch {
        // checkout_url wasn't absolute — fall back to the stub session id
      }
      router.push(`/repair/success?session_id=${encodeURIComponent(sessionId)}&vin=${encodeURIComponent(vin)}`);
    } catch {
      setPayLoading(false);
      alert('Payment service unavailable. Please try again.');
    }
  };

  // Compute required tools
  const getToolRequirements = () => {
    const text = symptoms.toLowerCase();
    const req = [
      { id: 'tool-hand-tools', label: 'Basic Hand Tools (Screwdrivers, Pliers)', estCost: 15, Icon: HandToolsIcon },
      { id: 'tool-socket-set', label: 'Socket Set & Ratchet', estCost: 25, Icon: SocketSetIcon },
      { id: 'tool-torque-wrench', label: 'Torque Wrench', estCost: 20, Icon: TorqueWrenchIcon },
    ];
    if (/(suspension|coilover|spring|strut|shock|exhaust|muffler|wheel|brake|rotor|caliper|pad|oil)/i.test(text)) {
      req.push({ id: 'tool-jack-stands', label: 'Jack & Jack Stands', estCost: 30, Icon: JackStandsIcon });
    }
    if (/(sensor|electrical|wire|harness|ignition|coil|plug|light|alternator|battery|voltage)/i.test(text)) {
      req.push({ id: 'tool-multimeter', label: 'Digital Multimeter', estCost: 12, Icon: MultimeterIcon });
    }
    if (/(code|scan|obd|engine light|check engine|trouble)/i.test(text)) {
      req.push({ id: 'tool-obd-scanner', label: 'OBD-II Scanner', estCost: 20, Icon: ObdScannerIcon });
    }
    if (/(nitrile|glove|glasses|safety|eye)/i.test(text) || true) {
      req.push({ id: 'tool-nitrile-gloves', label: 'Safety Glasses & Gloves', estCost: 5, Icon: SafetyGlovesIcon });
    }
    if (/(rust|stuck|bolt|nut|spray|seized|suspension|exhaust)/i.test(text)) {
      req.push({ id: 'tool-wd40', label: 'Penetrating Oil (WD-40)', estCost: 6, Icon: PenetratingOilIcon });
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
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
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
          <span className="safety-banner-icon" aria-hidden="true"><AlertTriangleIcon size={20} /></span>
          <span>{safetyWarning}</span>
        </div>
      )}

      {/* ── NHTSA open recalls: live lookup, never a stale ingested snapshot ── */}
      {recalls && recalls.count > 0 && (
        <div
          data-testid="open-recalls-banner"
          className="card"
          style={{ border: '1px solid var(--accent-red)' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <AlertTriangleIcon size={20} />
            <p className="card-label" style={{ margin: 0, color: 'var(--accent-red)' }}>
              {recalls.count} Open Recall{recalls.count > 1 ? 's' : ''} — Free Dealer Repair Available
            </p>
          </div>
          <p className="text-muted text-sm" style={{ marginBottom: 12 }}>
            NHTSA lists {recalls.count} open safety recall{recalls.count > 1 ? 's' : ''} for this vehicle. Manufacturer recalls are repaired free of charge at any dealership.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {recalls.open_recalls.map((r) => (
              <div key={r.campaign_number} style={{ borderTop: '1px solid var(--border-color, rgba(255,255,255,0.1))', paddingTop: 10 }}>
                <p style={{ fontWeight: 700, marginBottom: 4 }}>{r.component || 'Recall'} — Campaign #{r.campaign_number}</p>
                <p className="text-muted text-sm" style={{ marginBottom: 4 }}>{r.summary}</p>
                <p className="text-muted text-sm">{r.remedy}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {recalls && recalls.count === 0 && (
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircleIcon size={16} style={{ color: '#4ade80' }} />
          <span className="text-muted text-sm">No open NHTSA recalls found for this vehicle as of today.</span>
        </div>
      )}

      {/* ── NHTSA complaints: unverified consumer reports, statistical signal only ── */}
      {complaintsSummary && complaintsSummary.total_complaints > 0 && (
        <div className="card">
          <p className="card-label" style={{ marginBottom: 4 }}>Common Reported Issues</p>
          <p className="text-muted text-sm" style={{ marginBottom: 12 }}>
            Based on {complaintsSummary.total_complaints} unverified NHTSA consumer complaints for this vehicle — not confirmed defects, just what owners report most.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {complaintsSummary.top_components.map((c) => (
              <span key={c.component} className="badge" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                {c.component} ({c.count})
              </span>
            ))}
          </div>
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
                <div style={{ marginTop: 14, padding: 12, background: 'rgba(239,68,68,0.15)', borderRadius: 8, border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', fontSize: '0.9rem', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <AlertTriangleIcon size={20} style={{ flexShrink: 0, marginTop: 2 }} />
                  <div><strong>High-Risk Alert:</strong> Delaying this repair or modification risks secondary cascading component damage. Estimated potential collateral cost if ignored: <strong>$1,200+</strong>.</div>
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
            <p style={{ fontSize: '0.9rem', color: '#60a5fa', fontWeight: 600, marginBottom: 8, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <ToolboxIcon size={18} /><span>No Owned Tools Selected</span>
            </p>
            <p className="text-muted text-sm" style={{ marginBottom: 10 }}>
              No worries! You can still easily complete this project. Here is your budget-optimized tool purchase plan:
            </p>
            <ul style={{ paddingLeft: 20, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {toolRequirements.map(t => (
                <li key={t.id} style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <t.Icon size={16} /> <span><strong>{t.label}</strong> (Est: ${t.estCost}) — <span style={{ color: '#4ade80' }}>Buy on Amazon or AutoZone</span></span>
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
              {missingTools.length === 0 ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircleIcon size={16} style={{ color: '#4ade80' }} />
                  <span>Reassurance: You own all required tools to complete this project safely.</span>
                </span>
              ) : (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <BoltIcon size={16} style={{ color: 'var(--accent-orange)' }} />
                  <span>RAPP matched {toolRequirements.length - missingTools.length} of {toolRequirements.length} tools. You have basic gear ready.</span>
                </span>
              )}
            </div>

            {missingTools.length > 0 && (
              <div style={{ marginTop: 10, padding: 12, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.2)', borderRadius: 8 }}>
                <p style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent-yellow)', marginBottom: 6, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <CartIcon size={16} /><span>Missing Tools Needed (Purchase Guide):</span>
                </p>
                <ul style={{ paddingLeft: 6, listStyle: 'none', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {missingTools.map(t => (
                    <li key={t.id} style={{ marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <t.Icon size={16} /> <span>{t.label} (Est: ${t.estCost})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Affiliate Marketing Parts Purchase Plan ── */}
      <PartsPurchasePlan
        parts={diagnosis?.recommended_parts ?? []}
        vehicleTitle={`${vinData?.year ?? ''} ${vinData?.make ?? ''} ${vinData?.model ?? ''}`.trim() || 'your vehicle'}
      />

      {/* ── Price & Value Comparison Table ── */}
      <div className="card" style={{ marginTop: 24, background: 'rgba(15, 23, 42, 0.4)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <p className="card-label">Why DIY With RAPP?</p>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: 8 }}>Project Route &amp; Cost Breakdown</h2>
        <p className="text-muted text-sm">See how guided RAPP self-repair/modification compares against traditional garage rates:</p>
        
        <table className="price-table" style={{ borderColor: 'rgba(255, 255, 255, 0.15)', background: 'rgba(15, 23, 42, 0.6)' }}>
          <thead>
            <tr style={{ background: '#1e293b' }}>
              <th style={{ color: '#fff', borderBottom: '2px solid rgba(255, 255, 255, 0.15)', padding: '14px 16px' }}>Repair Method</th>
              <th style={{ color: '#fff', borderBottom: '2px solid rgba(255, 255, 255, 0.15)', padding: '14px 16px' }}>Estimated Cost</th>
              <th style={{ color: '#fff', borderBottom: '2px solid rgba(255, 255, 255, 0.15)', padding: '14px 16px' }}>Value &amp; Details</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <td style={{ padding: '14px 16px' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: '#f1f5f9', fontWeight: 600 }}>
                  <BuildingIcon size={16} />
                  <span>Dealership / Pro Shop</span>
                </span>
              </td>
              <td style={{ padding: '14px 16px', color: '#f1f5f9' }}>
                {diagnosis?.cost_breakdown
                  ? `$${diagnosis.cost_breakdown.dealership_cost_range[0]} – $${diagnosis.cost_breakdown.dealership_cost_range[1]}`
                  : '$450 – $900'}
              </td>
              <td style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f1f5f9' }}>3 – 5 Days Timeframe</span>
                  <span className="text-muted text-sm" style={{ fontSize: '0.8rem', color: '#94a3b8' }}>High labor markup + OEM overhead + appointment delays</span>
                </div>
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <td style={{ padding: '14px 16px' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: '#f1f5f9', fontWeight: 600 }}>
                  <WrenchIcon size={16} />
                  <span>Independent Auto Shop</span>
                </span>
              </td>
              <td style={{ padding: '14px 16px', color: '#f1f5f9' }}>
                {diagnosis?.cost_breakdown
                  ? `$${diagnosis.cost_breakdown.independent_shop_range[0]} – $${diagnosis.cost_breakdown.independent_shop_range[1]}`
                  : '$200 – $400'}
              </td>
              <td style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f1f5f9' }}>1 – 2 Days Timeframe</span>
                  <span className="text-muted text-sm" style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Variable quality & labor rates ($150+/hr)</span>
                </div>
              </td>
            </tr>
            <tr className="price-row-highlight" style={{ background: 'rgba(249, 115, 22, 0.15)', borderLeft: '4px solid var(--accent-orange)' }}>
              <td style={{ padding: '14px 16px' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: '#fff', fontWeight: 700 }}>
                  <BoltIcon size={16} style={{ color: 'var(--accent-yellow)' }} />
                  <span>RAPP Guided DIY</span>
                </span>
              </td>
              <td className="price-val-green" style={{ padding: '14px 16px', color: '#4ade80', fontWeight: 800 }}>
                {diagnosis?.cost_breakdown
                  ? `$${(diagnosis.cost_breakdown.parts_total + 4.00).toFixed(2)}`
                  : '$39.00'}
              </td>
              <td style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-yellow)' }}>
                    {diagnosis?.cost_breakdown
                      ? `${diagnosis.cost_breakdown.estimated_labor_hours} Hours completion`
                      : '2 – 3 Hours completion'}
                  </span>
                  <span className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.85)', fontSize: '0.8rem' }}>
                    Save up to 85% today with exact step-by-step guidance & verified parts (includes $4.00 guide fee)
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ── Post-Repair Garage Vault Sign-Up ── */}
      <div className="card" style={{ border: '1px solid var(--accent-orange)', marginTop: 24, position: 'relative' }}>
        <p className="card-label" style={{ color: 'var(--accent-orange)', margin: 0 }}>Secure Garage Archive</p>
        
        {garageSaved ? (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircleIcon size={18} style={{ color: '#4ade80' }} />
              <span>This repair guide and vehicle profile are saved to your garage.</span>
            </div>
            <a href="/garage" className="btn btn-secondary" style={{ width: 'auto', padding: '0 18px', marginTop: 8 }}>Go to My Garage →</a>
          </div>
        ) : (
          <div style={{ marginTop: 10 }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 4 }}>Save to My Garage &amp; Keep Guide Forever</h3>
            <p className="text-muted text-sm" style={{ marginBottom: 16 }}>
              Create a free account to permanently archive your vehicle profile, diagnostic guide, and payment preferences.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 380 }}>
              <input
                className="input"
                type="text"
                placeholder="Name (optional)"
                value={garageName}
                onChange={(e) => setGarageName(e.target.value)}
                style={{ padding: '10px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
              />
              <input
                className="input"
                type="email"
                placeholder="Email"
                value={garageEmail}
                onChange={(e) => setGarageEmail(e.target.value)}
                style={{ padding: '10px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
              />
              <input
                className="input"
                type="password"
                placeholder="Password"
                value={garagePassword}
                onChange={(e) => setGaragePassword(e.target.value)}
                style={{ padding: '10px', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }}
              />
              {garageError && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem', margin: 0 }}>{garageError}</p>}
              <button
                className="btn btn-primary"
                onClick={handleGarageSignUp}
                disabled={garageSubmitting || !garageEmail.trim() || !garagePassword.trim()}
                style={{ marginTop: 6, minHeight: 40 }}
              >
                {garageSubmitting ? <><span className="loading-spinner" aria-hidden="true" /> Saving…</> : 'Save to My Garage'}
              </button>
            </div>
          </div>
        )}
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
          <span className="badge" style={{ background: 'rgba(251,191,36,0.15)', color: 'var(--accent-yellow)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <StarIcon size={14} /><span>Premium OEM Service Access</span>
          </span>
        </div>
        <div className="paywall-gate-title" style={{ fontSize: '1.4rem', fontWeight: 900, color: '#fff', letterSpacing: '-0.01em', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <UnlockIcon size={22} /><span>Unlock Step-by-Step OEM Guide</span>
        </div>
        
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><ChecklistIcon size={16} style={{ color: 'var(--accent-orange)' }} /> <strong>4-Phase Garage Safe Checklist</strong></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><WrenchIcon size={16} style={{ color: 'var(--accent-orange)' }} /> <strong>Exact Socket & Tool Wrench Sizes</strong></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><BoltIcon size={16} style={{ color: 'var(--accent-orange)' }} /> <strong>Precise Bolt Torque Specs</strong> (Prevents stripping)</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><QualityCheckIcon size={16} style={{ color: 'var(--accent-orange)' }} /> <strong>Constant Quality Checkpoints</strong></div>
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
