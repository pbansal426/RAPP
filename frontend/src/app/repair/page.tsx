'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import LayoutDiagram from './diagrams/LayoutDiagram';
import WiringDiagram from './diagrams/WiringDiagram';
import ChatPanel from './ChatPanel';
import ConclusionPhase from './ConclusionPhase';
import SaveGuidePrompt from './SaveGuidePrompt';
import { useAuthUser } from '@/lib/auth';
import { completePendingSave } from '@/lib/pendingSave';
import type { RecommendedPart } from '@/lib/types';
import {
  AppLogoMarkIcon,
  BoltIcon,
  WrenchIcon,
  QualityCheckIcon,
  ShieldAlertIcon,
  DisassemblyIcon,
  CogIcon,
  CheckCircleIcon,
  DocumentIcon,
} from '@/app/sharedIcons';

interface RepairResponse {
  repair_steps: string[];
  citations: string[];
}

const TORQUE_REGEX = /torque|tighten|ft-lbs|\bnm\b/i;
const WIRING_REGEX = /wiring|harness|connector|\bpin\b|sensor|circuit/i;

export default function RepairPage() {
  const router = useRouter();
  const [vin, setVin] = useState('');
  const [vinData, setVinData] = useState<Record<string, unknown> | null>(null);
  const [symptoms, setSymptoms] = useState('');
  const [repair, setRepair] = useState<RepairResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unlocked, setUnlocked] = useState(false);
  const [checkedSteps, setCheckedSteps] = useState<Record<number, boolean>>({});
  const [parts, setParts] = useState<RecommendedPart[]>([]);
  const [showSavePrompt, setShowSavePrompt] = useState(false);
  const [savePromptDismissed, setSavePromptDismissed] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const conclusionRef = useRef<HTMLDivElement>(null);
  const { user: authUser } = useAuthUser();

  const generateAndCache = (
    storedVin: string,
    storedSymptoms: string,
    tools: string[],
    sessionId: string,
    parsedVinData: Record<string, unknown> | null
  ) => {
    setLoading(true);
    api.post<RepairResponse>('/api/repair', {
      vin: storedVin,
      symptoms: storedSymptoms,
      obd_codes: [],
      tools,
      stripe_session_id: sessionId,
      vehicle: parsedVinData,
    })
      .then((res) => {
        setRepair(res);
        localStorage.setItem(`rapp_repair_${storedVin}`, JSON.stringify(res));
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load repair steps.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const storedVin = localStorage.getItem('rapp_vin');
    if (!storedVin) { router.push('/'); return; }
    setVin(storedVin);

    const sessionId = localStorage.getItem(`rapp_unlocked_${storedVin}`);
    if (!sessionId) { router.push('/results'); return; }
    setUnlocked(true);

    const storedVinData = localStorage.getItem('rapp_vin_data');
    const parsedVinData = storedVinData ? JSON.parse(storedVinData) : null;
    if (parsedVinData) setVinData(parsedVinData);

    const storedSymptoms = localStorage.getItem('rapp_symptoms') ?? '';
    setSymptoms(storedSymptoms);
    const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];

    const storedParts = localStorage.getItem(`rapp_parts_${storedVin}`);
    if (storedParts) {
      try { setParts(JSON.parse(storedParts)); } catch { /* malformed cache, ignore */ }
    }

    // Once generated (either warmed in the background from /results, or by
    // a previous visit here), the guide is permanent -- reloading this page
    // must never silently re-generate it. Only "Start Over" clears this.
    const cachedRepair = localStorage.getItem(`rapp_repair_${storedVin}`);
    if (cachedRepair) {
      try {
        setRepair(JSON.parse(cachedRepair));
        const cachedChecked = localStorage.getItem(`rapp_repair_checked_${storedVin}`);
        if (cachedChecked) setCheckedSteps(JSON.parse(cachedChecked));
        setLoading(false);
        return;
      } catch {
        // fall through to a fresh generation if the cached value is malformed
      }
    }

    generateAndCache(storedVin, storedSymptoms, tools, sessionId, parsedVinData);
  }, [router]);

  const startOver = () => {
    if (!vin) return;
    const confirmed = window.confirm(
      'Starting over clears your checked-off progress and regenerates this repair guide from scratch. Continue?'
    );
    if (!confirmed) return;
    localStorage.removeItem(`rapp_repair_${vin}`);
    localStorage.removeItem(`rapp_repair_checked_${vin}`);
    setCheckedSteps({});
    setRepair(null);
    setError(null);
    const sessionId = localStorage.getItem(`rapp_unlocked_${vin}`) ?? '';
    const tools = JSON.parse(localStorage.getItem('rapp_tools') ?? '[]') as string[];
    generateAndCache(vin, symptoms, tools, sessionId, vinData);
  };

  // Magic-link auth can't authenticate synchronously (see SaveGuidePrompt),
  // so the actual saveRepair() call for a guide requested-to-be-saved
  // completes here, whenever this page loads with both a signed-in user
  // and a matching pending-save entry -- whether that's an immediate
  // redirect back from /verify-email or a later visit from any device.
  useEffect(() => {
    if (!authUser || !vin) return;
    completePendingSave(vin).then((saved) => {
      if (saved) {
        setJustSaved(true);
        setSavePromptDismissed(true);
      }
    });
  }, [authUser, vin]);

  useEffect(() => {
    if (!repair || !vin) return;
    if (localStorage.getItem(`rapp_garage_dismissed_${vin}`) === '1') {
      setSavePromptDismissed(true);
      return;
    }
    const node = conclusionRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) setShowSavePrompt(true);
      },
      { threshold: 0.3 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [repair, vin]);

  const dismissSavePrompt = () => {
    localStorage.setItem(`rapp_garage_dismissed_${vin}`, '1');
    setSavePromptDismissed(true);
  };

  const toggleStep = (idx: number) => setCheckedSteps(prev => {
    const next = { ...prev, [idx]: !prev[idx] };
    if (vin) localStorage.setItem(`rapp_repair_checked_${vin}`, JSON.stringify(next));
    return next;
  });

  // Helper to highlight tools and torque specs in step text
  const formatStepText = (text: string) => {
    const parts = text.split(/(Torque [^.,;]+)/gi);
    return parts.map((part, i) => {
      if (/^Torque /i.test(part)) {
        return (
          <span key={i} className="torque-spec" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <BoltIcon size={14} /><span>{part}</span>
          </span>
        );
      }
      const subParts = part.split(/(\b(?:socket|wrench|extension|multimeter|jack stands?|ratchet|pliers)\b[^.,;]*)/gi);
      return subParts.map((sub, j) => {
        if (/\b(?:socket|wrench|extension|multimeter|jack stands?|ratchet|pliers)\b/i.test(sub)) {
          return (
            <span key={`${i}-${j}`} className="tool-chip" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <WrenchIcon size={14} /><span>{sub}</span>
            </span>
          );
        }
        return sub;
      });
    });
  };

  if (!unlocked && !loading) return null;

  return (
    <main className="repair-shell">
      <div className="repair-main">
        <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start', marginBottom: 12 }}>
          <button
            id="back-to-results-btn"
            data-testid="back-to-results-btn"
            className="btn btn-secondary"
            type="button"
            onClick={() => router.push('/results')}
            style={{ padding: '6px 12px', fontSize: '0.875rem' }}
          >
            ← Back to Results
          </button>
          {repair && (
            <button
              className="btn btn-secondary"
              type="button"
              onClick={startOver}
              style={{ padding: '6px 12px', fontSize: '0.875rem', marginLeft: 8 }}
            >
              Start Over
            </button>
          )}
        </div>

        <header className="page-header">
          <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
          <h1 className="page-title">Clinic-Grade Repair &amp; Mod Guide</h1>
          {vin && <p className="page-subtitle">VIN: {vin} • Verified Procedure</p>}
        </header>

        {loading && (
          <div className="card" style={{ textAlign: 'center', padding: '48px 28px' }}>
            <div className="loading-spinner" style={{ margin: '0 auto 16px' }} />
            <p className="text-muted">Retrieving vector-verified repair procedures from ChromaDB…</p>
          </div>
        )}

        {error && (
          <div className="card">
            <p style={{ color: 'var(--accent-red)' }}>{error}</p>
          </div>
        )}

        {repair && (
          <>
            {/* Shopping & Parts List Card */}
            <div className="card">
              <p className="card-label">Required Parts &amp; Supplies</p>
              <table className="price-table" style={{ margin: '10px 0 0' }}>
                <thead>
                  <tr>
                    <th>Part / Supply Specification</th>
                    <th>Est. Retail</th>
                    <th>Availability</th>
                  </tr>
                </thead>
                <tbody>
                  {parts.length === 0 && (
                    <tr>
                      <td colSpan={3} className="text-muted text-sm">
                        No specific replacement part was identified from your symptoms — see the step-by-step procedure below for part call-outs.
                      </td>
                    </tr>
                  )}
                  {parts.map((part, i) => {
                    const prices = part.options.map((o) => o.estimated_price);
                    const min = Math.min(...prices);
                    const max = Math.max(...prices);
                    const budget = part.options.find((o) => o.tier === 'Aftermarket / Budget') ?? part.options[0];
                    return (
                      <tr key={i}>
                        <td>{part.part_name}</td>
                        <td className="price-val-green">
                          {min === max ? `$${min.toFixed(2)}` : `$${min.toFixed(2)} – $${max.toFixed(2)}`}
                        </td>
                        <td>
                          {budget ? (
                            <a
                              href={budget.purchase_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: 'var(--accent-yellow)', textDecoration: 'none' }}
                            >
                              {budget.brand} ↗
                            </a>
                          ) : (
                            "AutoZone / O'Reilly / Amazon"
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  <tr>
                    <td>Dielectric Grease &amp; Shop Rags</td>
                    <td>$5</td>
                    <td>In Stock Locally</td>
                  </tr>
                  <tr>
                    <td>Thread locker / Anti-seize lubricant</td>
                    <td>$4</td>
                    <td>In Stock Locally</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Detailed repair steps */}
            <div data-testid="detailed-repair-steps" className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <p className="card-label" style={{ margin: 0 }}>Step-by-Step Procedure</p>
                <span className="badge badge-free">RAG &amp; AI Verified</span>
              </div>

              {(() => {
                const steps = repair.repair_steps.filter(
                  (step) =>
                    step !== "Disconnect negative battery terminal." &&
                    step !== "Replace ignition coil."
                );
                const N = steps.length;
                const p1 = Math.max(1, Math.floor(N / 4));
                const p2 = Math.max(p1 + 1, Math.floor(N / 2));
                const p3 = Math.max(p2 + 1, Math.floor((3 * N) / 4));

                // Determine which step (if any) gets each inline diagram.
                let layoutStepIndex: number | null = null;
                for (let i = p2; i < p3; i++) {
                  if (TORQUE_REGEX.test(steps[i])) { layoutStepIndex = i; break; }
                }
                const layoutFallbackAtPhase3Top = layoutStepIndex === null && p3 > p2;

                let wiringStepIndex: number | null = null;
                for (let i = 0; i < N; i++) {
                  if (WIRING_REGEX.test(steps[i])) { wiringStepIndex = i; break; }
                }

                const getQualityCheck = (text: string) => {
                  const lower = text.toLowerCase();
                  if (lower.includes('battery') || lower.includes('disconnect') || lower.includes('terminal')) {
                    return 'Verify the negative cable terminal is completely isolated and cannot touch any metal parts of the chassis.';
                  }
                  if (lower.includes('torque') || lower.includes('tighten') || lower.includes('ft-lbs')) {
                    return 'Verify your torque wrench click. Stop immediately after the click to avoid over-tightening or stripping threads.';
                  }
                  if (lower.includes('socket') || lower.includes('bolt') || lower.includes('wrench')) {
                    return 'Ensure the socket fits snug on the bolt head. Confirm it is not slipping before applying leverage.';
                  }
                  if (lower.includes('connector') || lower.includes('plug') || lower.includes('wire')) {
                    return 'Check that the connector tab clicks audibly into place. Gently tug the plug to confirm it is locked.';
                  }
                  if (lower.includes('replace') || lower.includes('install') || lower.includes('new')) {
                    return 'Clean any dirt or debris from the mounting surface before installing the new component.';
                  }
                  if (lower.includes('start') || lower.includes('test') || lower.includes('idle')) {
                    return 'Verify there are no active fault codes or check engine warnings on your dashboard before starting.';
                  }
                  return 'Perform a quick visual inspection of the surrounding components to ensure no hoses or wires were pinched.';
                };

                const renderStep = (stepText: string, i: number) => {
                  const isStepChecked = !!checkedSteps[i];

                  return (
                    <li
                      key={i}
                      className="step-item"
                      style={{
                        alignItems: 'flex-start',
                        opacity: 1,
                        pointerEvents: 'auto',
                        transition: 'opacity 0.25s ease',
                        flexDirection: 'column',
                        gap: '8px',
                        padding: '18px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                        <input
                          type="checkbox"
                          className="step-checkbox"
                          checked={isStepChecked}
                          onChange={() => toggleStep(i)}
                        />
                        <span className="step-num" style={{ background: isStepChecked ? '#22c55e' : 'var(--accent-orange)' }}>
                          {isStepChecked ? '✓' : i + 1}
                        </span>
                        <span className={`step-text ${isStepChecked ? 'step-checked' : ''}`} style={{ fontWeight: 600 }}>
                          {formatStepText(stepText)}
                        </span>
                      </div>

                      {!isStepChecked && (
                        <div style={{
                          marginTop: '8px',
                          padding: '10px 14px',
                          background: 'rgba(59,130,246,0.08)',
                          borderLeft: '4px solid #3b82f6',
                          borderRadius: '0 8px 8px 0',
                          fontSize: '0.85rem',
                          color: 'var(--text-primary)',
                          width: '100%',
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '8px'
                        }}>
                          <QualityCheckIcon size={16} style={{ flexShrink: 0, marginTop: 2, color: '#3b82f6' }} />
                          <div><strong>Quality Checkpoint:</strong> {getQualityCheck(stepText)}</div>
                        </div>
                      )}

                      {i === layoutStepIndex && <LayoutDiagram />}
                      {i === wiringStepIndex && <WiringDiagram />}
                    </li>
                  );
                };

                return (
                  <>
                    <div className="phase-section">
                      <div className="phase-header"><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><ShieldAlertIcon size={18} style={{ color: '#f87171' }} /><span>Phase 1: Safety &amp; Vehicle Preparation</span></span></div>
                      <ol className="step-list">
                        {steps.slice(0, p1).map((step, i) => renderStep(step, i))}
                      </ol>
                    </div>

                    {p2 > p1 && (
                      <div className="phase-section">
                        <div className="phase-header"><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><DisassemblyIcon size={18} style={{ color: 'var(--accent-orange)' }} /><span>Phase 2: Disassembly &amp; Access</span></span></div>
                        <ol className="step-list">
                          {steps.slice(p1, p2).map((step, idx) => renderStep(step, idx + p1))}
                        </ol>
                      </div>
                    )}

                    {p3 > p2 && (
                      <div className="phase-section">
                        <div className="phase-header"><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><CogIcon size={18} style={{ color: 'var(--accent-orange)' }} /><span>Phase 3: Component Replacement &amp; Torque</span></span></div>
                        {layoutFallbackAtPhase3Top && <LayoutDiagram />}
                        <ol className="step-list">
                          {steps.slice(p2, p3).map((step, idx) => renderStep(step, idx + p2))}
                        </ol>
                      </div>
                    )}

                    {N > p3 && (
                      <div className="phase-section">
                        <div className="phase-header"><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><CheckCircleIcon size={18} style={{ color: '#4ade80' }} /><span>Phase 4: Reassembly &amp; Torque Verification</span></span></div>
                        <ol className="step-list">
                          {steps.slice(p3).map((step, idx) => renderStep(step, idx + p3))}
                        </ol>
                      </div>
                    )}

                    <div ref={conclusionRef}>
                      <ConclusionPhase symptoms={symptoms} />
                    </div>
                  </>
                );
              })()}
            </div>

            {justSaved && (
              <div className="card" style={{ border: '1px solid var(--accent-orange)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircleIcon size={18} style={{ color: '#4ade80' }} />
                  <span style={{ fontWeight: 700 }}>Saved to your garage.</span>
                </div>
                <a href="/garage" className="btn btn-secondary" style={{ width: 'auto', padding: '0 18px', marginTop: 10 }}>Go to My Garage →</a>
              </div>
            )}

            {showSavePrompt && !savePromptDismissed && !authUser && !justSaved && (
              <SaveGuidePrompt vin={vin} vinData={vinData} symptoms={symptoms} citations={repair.citations} onDismiss={dismissSavePrompt} />
            )}

            {/* Clickable RAG citations */}
            {repair.citations.length > 0 && (
              <div className="card">
                <p className="card-label">Sources &amp; OEM Service Citations (Official Portals)</p>
                <div className="flex gap-2 flex-wrap">
                  {repair.citations.map((cite, i) => {
                    const getCitationLink = (c: string) => {
                      const l = c.toLowerCase();
                      if (l.includes('honda')) return 'https://techinfo.honda.com';
                      if (l.includes('lexus') || l.includes('toyota')) return 'https://techinfo.toyota.com';
                      return 'https://techinfo.toyota.com';
                    };
                    return (
                      <a
                        key={i}
                        href={getCitationLink(cite)}
                        target="_blank"
                        rel="noopener noreferrer"
                        data-testid="rag-citation"
                        className="citation-chip"
                        style={{ textDecoration: 'none', color: 'var(--accent-yellow)', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                      >
                        <DocumentIcon size={15} /><span>{cite} ↗</span>
                      </a>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}

        <button
          className="btn btn-outline mt-4"
          onClick={() => router.push('/')}
          style={{ minHeight: 52 }}
        >
          ← Start New Project
        </button>
      </div>

      <ChatPanel vin={vin} vinData={vinData} symptoms={symptoms} repairSteps={repair?.repair_steps ?? []} />
    </main>
  );
}
