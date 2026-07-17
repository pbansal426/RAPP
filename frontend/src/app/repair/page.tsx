'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import LayoutDiagram from './diagrams/LayoutDiagram';
import WiringDiagram from './diagrams/WiringDiagram';
import ChatPanel from './ChatPanel';
import ConclusionPhase from './ConclusionPhase';
import SaveGuidePrompt from './SaveGuidePrompt';
import { useAuthUser, updateAccount } from '@/lib/auth';
import { completePendingSave } from '@/lib/pendingSave';
import { submitOutcome } from '@/lib/outcomes';
import { safeGetJson } from '@/lib/storage';
import type { RecommendedPart, VehicleInfo } from '@/lib/types';
import {
  AppLogoMarkIcon,
  BoltIcon,
  CameraIcon,
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
  is_blocked_safety?: boolean;
  warning_message?: string | null;
}

interface CheckpointResult {
  is_milestone_met: boolean;
  confidence: number;
  explanation: string;
}

function ReferralNudge() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
      padding: '10px 14px', marginBottom: 12, borderRadius: 8,
      background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.25)',
      fontSize: '0.85rem',
    }}>
      <span>Know someone who&apos;d find this useful? <a href="/settings" style={{ color: 'var(--accent-orange)', fontWeight: 700 }}>Share your referral link</a> and you&apos;ll both get credit.</span>
      <button type="button" onClick={() => setDismissed(true)} aria-label="Dismiss"
        style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1 }}>×</button>
    </div>
  );
}

type CheckpointState =
  | { status: 'idle' }
  | { status: 'open' }
  | { status: 'verifying' }
  | { status: 'done'; result: CheckpointResult }
  | { status: 'error'; message: string };

const TORQUE_REGEX = /torque|tighten|ft-lbs|\bnm\b/i;
const WIRING_REGEX = /wiring|harness|connector|\bpin\b|sensor|circuit/i;

export default function RepairPage() {
  const router = useRouter();
  const [vin, setVin] = useState('');
  const [vinData, setVinData] = useState<VehicleInfo | null>(null);

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
  const [showCompletionSurvey, setShowCompletionSurvey] = useState(false);
  const [outcomeSubmitted, setOutcomeSubmitted] = useState(false);
  const [outcomeDuration, setOutcomeDuration] = useState('');
  const [outcomeCost, setOutcomeCost] = useState('');
  const [outcomeSubmitting, setOutcomeSubmitting] = useState(false);
  const [outcomeError, setOutcomeError] = useState<string | null>(null);
  const conclusionRef = useRef<HTMLDivElement>(null);
  const { user: authUser, loading: authLoading } = useAuthUser();
  const [currentSkillLevel, setCurrentSkillLevel] = useState<string>('Beginner');
  // Stage 2.4: per-step photo checkpoint state keyed by step index
  const [checkpointStates, setCheckpointStates] = useState<Record<number, CheckpointState>>({});
  const checkpointFileRefs = useRef<Record<number, HTMLInputElement | null>>({});

  const setCheckpoint = (idx: number, state: CheckpointState) =>
    setCheckpointStates((prev) => ({ ...prev, [idx]: state }));

  const verifyCheckpoint = async (idx: number, stepText: string, file: File) => {
    setCheckpoint(idx, { status: 'verifying' });
    const form = new FormData();
    form.append('file', file);
    form.append('step_description', stepText);
    try {
      const result = await api.postForm<CheckpointResult>(
        '/api/repair/checkpoint/verify',
        form
      );
      setCheckpoint(idx, { status: 'done', result });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : 'Verification failed. Try a clearer photo.';
      setCheckpoint(idx, { status: 'error', message: msg });
    }
  };

  const generateAndCache = (
    storedVin: string,
    storedSymptoms: string,
    tools: string[],
    sessionId: string,
    parsedVinData: VehicleInfo | null,
    skill: string = currentSkillLevel
  ) => {
    setLoading(true);
    api.post<RepairResponse>('/api/repair', {
      vin: storedVin,
      symptoms: storedSymptoms,
      obd_codes: [],
      tools,
      stripe_session_id: sessionId,
      vehicle: parsedVinData,
      skill_level: skill,
    })
      .then((res) => {
        setRepair(res);
        if (typeof window !== 'undefined') {
          localStorage.setItem(`rapp_repair_${storedVin}`, JSON.stringify(res));
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load repair steps.'))
      .finally(() => setLoading(false));
  };

  const handleSwitchSkillLevel = async (newSkill: string) => {
    setCurrentSkillLevel(newSkill);
    if (typeof window !== 'undefined') {
      localStorage.setItem('rapp_skill_level', newSkill);
    }
    if (authUser) {
      try {
        await updateAccount(authUser.displayName, newSkill);
      } catch {}
    }
    const confirmed = window.confirm(
      `Switching to "${newSkill}" mode will regenerate your procedure steps tailored to this skill level. Continue?`
    );
    if (confirmed && vin) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem(`rapp_repair_${vin}`);
        localStorage.removeItem(`rapp_repair_checked_${vin}`);
      }
      const sessionId = localStorage.getItem(`rapp_unlocked_${vin}`) || '';
      const tools = safeGetJson<string[]>('rapp_tools', []);
      generateAndCache(vin, symptoms, tools, sessionId, vinData, newSkill);
    }
  };

  useEffect(() => {
    if (authLoading) return;

    const storedVin = localStorage.getItem('rapp_vin');
    if (!storedVin) { router.push('/'); return; }
    setVin(storedVin);

    const sessionId = localStorage.getItem(`rapp_unlocked_${storedVin}`);
    const isSubscriber = authUser?.subscriptionStatus === 'active';
    if (!sessionId && !isSubscriber) { router.push('/results'); return; }
    setUnlocked(true);

    const parsedVinData = safeGetJson<VehicleInfo | null>('rapp_vin_data', null);
    if (parsedVinData) setVinData(parsedVinData);

    const storedSymptoms = localStorage.getItem('rapp_symptoms') ?? '';
    setSymptoms(storedSymptoms);
    const tools = safeGetJson<string[]>('rapp_tools', []);

    if (localStorage.getItem(`rapp_outcome_submitted_${storedVin}`) === '1') {
      setOutcomeSubmitted(true);
    }

    const storedParts = safeGetJson<RecommendedPart[] | null>(`rapp_parts_${storedVin}`, null);
    if (storedParts) setParts(storedParts);

    const storedSkill = localStorage.getItem('rapp_skill_level') || authUser?.skillLevel || 'Beginner';
    setCurrentSkillLevel(storedSkill);

    // Once generated (either warmed in the background from /results, or by
    // a previous visit here), the guide is permanent -- reloading this page
    // must never silently re-generate it. Only "Start Over" clears this.
    const cachedRepair = safeGetJson<RepairResponse | null>(`rapp_repair_${storedVin}`, null);
    if (cachedRepair) {
      setRepair(cachedRepair);
      setCheckedSteps(safeGetJson<Record<number, boolean>>(`rapp_repair_checked_${storedVin}`, {}));
      setLoading(false);
      return;
    }

    generateAndCache(storedVin, storedSymptoms, tools, sessionId || '', parsedVinData, storedSkill);
  }, [router, authUser, authLoading]);

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
    const tools = safeGetJson<string[]>('rapp_tools', []);
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

  const submitCompletionSurvey = async () => {
    const duration = parseInt(outcomeDuration, 10);
    const cost = parseFloat(outcomeCost);
    if (!Number.isFinite(duration) || duration <= 0 || !Number.isFinite(cost) || cost < 0) {
      setOutcomeError('Please enter a valid time and cost.');
      return;
    }
    setOutcomeSubmitting(true);
    setOutcomeError(null);
    try {
      await submitOutcome({
        vin,
        make: String(vinData?.make ?? ''),
        model: String(vinData?.model ?? ''),
        year: vinData?.year ? String(vinData.year) : null,
        symptoms,
        actual_cost_usd: cost,
        actual_duration_minutes: duration,
      });
      localStorage.setItem(`rapp_outcome_submitted_${vin}`, '1');
      setOutcomeSubmitted(true);
      setShowCompletionSurvey(false);
    } catch (err) {
      setOutcomeError(err instanceof ApiError ? err.message : 'Could not submit — please try again.');
    } finally {
      setOutcomeSubmitting(false);
    }
  };

  const toggleStep = (idx: number) => setCheckedSteps(prev => {
    const next = { ...prev, [idx]: !prev[idx] };
    if (vin) localStorage.setItem(`rapp_repair_checked_${vin}`, JSON.stringify(next));
    return next;
  });

  // Helper to highlight tools, torque specs, and bailout warnings in step text
  const formatStepText = (text: string) => {
    const hasBailout = /\[POINT OF NO RETURN\]/i.test(text);
    const cleanText = text.replace(/\[POINT OF NO RETURN\]/gi, '').trim();

    const parts = cleanText.split(/(Torque [^.,;]+)/gi);
    const formatted = parts.map((part, i) => {
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

    if (hasBailout) {
      return (
        <div style={{ width: '100%', marginTop: 2 }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'linear-gradient(135deg, #ef4444, #dc2626)',
            color: '#fff',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            fontWeight: 800,
            letterSpacing: '0.5px',
            marginBottom: '8px',
            textTransform: 'uppercase',
            boxShadow: '0 2px 8px rgba(239, 68, 68, 0.4)'
          }}>
            <ShieldAlertIcon size={14} /> Point of No Return / Bailout Threshold
          </div>
          <div style={{ color: '#fef2f2', fontWeight: 600, lineHeight: 1.5 }}>{formatted}</div>
        </div>
      );
    }

    return formatted;
  };

  if (!unlocked && !loading) return null;

  return (
    <main className="repair-shell">
      <div className="repair-main">
        <ReferralNudge />
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
          repair.is_blocked_safety ? (
            <div
              className="card border-red-500 bg-red-950 text-red-500"
              style={{
                padding: '32px 24px',
                borderLeft: '4px solid var(--accent-red)',
                marginTop: '16px',
                border: '2px solid var(--accent-red)',
                borderRadius: '8px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <ShieldAlertIcon size={24} style={{ color: 'var(--accent-red)' }} />
                <h2 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: '#fff' }}>
                  Professional Service Required
                </h2>
              </div>
              <p style={{ fontSize: '1.05rem', lineHeight: 1.6, color: 'var(--text-primary)', marginBottom: 20 }}>
                {repair.warning_message || 'DANGER: A safety-critical system has been detected. Step-by-step DIY repair generation is blocked for your physical safety.'}
              </p>
              
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: 18, borderRadius: 8, marginBottom: 12 }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: 12 }}>
                  Certified Local Repair Directory
                </h3>
                <p className="text-muted text-sm" style={{ marginBottom: 16 }}>
                  For high-risk systems, we strongly recommend booking a certified technician. Use the resources below to locate verified shops near you:
                </p>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <a
                    href={`https://repairpal.com/repair-shops?make=${encodeURIComponent(vinData?.make || '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                    style={{
                      width: 'auto',
                      padding: '10px 20px',
                      background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                      border: 'none',
                      color: '#fff',
                      textDecoration: 'none',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 8,
                      fontWeight: 700
                    }}
                  >
                    Find Shops on RepairPal ↗
                  </a>
                  <a
                    href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent((vinData?.make || '') + ' certified auto repair near me')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                    style={{
                      width: 'auto',
                      padding: '10px 20px',
                      textDecoration: 'none',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 8,
                      fontWeight: 700
                    }}
                  >
                    Search Google Maps ↗
                  </a>
                </div>
              </div>
            </div>
          ) : (
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

                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: 12,
                  padding: '12px 16px',
                  background: 'rgba(30, 41, 59, 0.6)',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  marginBottom: 20
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <QualityCheckIcon size={18} style={{ color: 'var(--accent-orange)' }} />
                    <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#f1f5f9' }}>
                      Active Guidance Level: <span style={{ color: 'var(--accent-yellow)' }}>{currentSkillLevel} Mode</span>
                    </span>
                    {authUser?.completedJobsCount !== undefined && authUser.completedJobsCount > 0 && (
                      <span className="badge" style={{ background: 'rgba(74, 222, 128, 0.15)', color: '#4ade80', fontSize: '0.75rem', fontWeight: 700 }}>
                        {authUser.completedJobsCount} Job{authUser.completedJobsCount > 1 ? 's' : ''} Completed
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Verbosity:</span>
                    {['Beginner', 'Intermediate', 'Advanced'].map((lvl) => {
                      const isActive = currentSkillLevel === lvl;
                      return (
                        <button
                          key={lvl}
                          type="button"
                          onClick={() => !isActive && handleSwitchSkillLevel(lvl)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '0.75rem',
                            fontWeight: isActive ? 800 : 600,
                            background: isActive ? 'var(--accent-orange)' : 'rgba(255, 255, 255, 0.06)',
                            color: isActive ? '#0f172a' : '#cbd5e1',
                            border: 'none',
                            cursor: isActive ? 'default' : 'pointer'
                          }}
                        >
                          {lvl}
                        </button>
                      );
                    })}
                  </div>
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

                        <div style={{ width: '100%' }}>
                          <input
                            ref={(el) => { checkpointFileRefs.current[i] = el; }}
                            type="file"
                            accept="image/*"
                            capture="environment"
                            style={{ display: 'none' }}
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                verifyCheckpoint(i, stepText, file);
                              }
                              e.target.value = '';
                            }}
                          />

                          {(!checkpointStates[i] || checkpointStates[i]?.status === 'idle') && (
                            <button
                              type="button"
                              className="btn-secondary"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                minHeight: '48px',
                                padding: '8px 16px',
                                fontSize: '0.85rem',
                              }}
                              onClick={() => checkpointFileRefs.current[i]?.click()}
                            >
                              <CameraIcon size={16} /> Verify My Work
                            </button>
                          )}

                          {checkpointStates[i]?.status === 'verifying' && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 0' }}>
                              <span className="loading-spinner" style={{ width: 16, height: 16 }} />
                              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                Verifying your work with AI...
                              </span>
                            </div>
                          )}

                          {checkpointStates[i]?.status === 'done' && (() => {
                            const result = (checkpointStates[i] as { status: 'done'; result: CheckpointResult }).result;
                            const isGood = result.is_milestone_met;
                            return (
                              <div style={{
                                marginTop: '8px',
                                padding: '10px 14px',
                                borderRadius: '999px',
                                fontSize: '0.85rem',
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '8px',
                                background: isGood ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                                border: `1px solid ${isGood ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
                                color: isGood ? '#10B981' : '#F59E0B',
                              }}>
                                <span>{isGood ? '✅' : '⚠️'}</span>
                                <span style={{ color: 'var(--text-primary)' }}>{result.explanation}</span>
                              </div>
                            );
                          })()}

                          {checkpointStates[i]?.status === 'error' && (
                            <div style={{
                              marginTop: '8px',
                              padding: '10px 14px',
                              borderRadius: '999px',
                              fontSize: '0.85rem',
                              background: 'rgba(239, 68, 68, 0.12)',
                              border: '1px solid rgba(239, 68, 68, 0.4)',
                              color: '#EF4444',
                            }}>
                              {(checkpointStates[i] as { status: 'error'; message: string }).message}
                              {' '}
                              <button
                                type="button"
                                onClick={() => setCheckpoint(i, { status: 'idle' })}
                                style={{ background: 'none', border: 'none', textDecoration: 'underline', cursor: 'pointer', color: 'inherit', fontSize: 'inherit', minHeight: '48px' }}
                              >
                                Try again
                              </button>
                            </div>
                          )}
                        </div>

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

              {/* ── Outcome capture (Stage 2.1): feeds the /results social-proof badge ── */}
              {outcomeSubmitted ? (
                <div className="card" style={{ border: '1px solid rgba(74,222,128,0.35)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <CheckCircleIcon size={18} style={{ color: '#4ade80' }} />
                    <span style={{ fontWeight: 700 }}>Thanks — your outcome has been recorded.</span>
                  </div>
                </div>
              ) : (
                <div className="card">
                  <p className="card-label">Wrap Up</p>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 8 }}>Finished the job?</h3>
                  <p className="text-muted text-sm" style={{ marginBottom: 12 }}>
                    Tell us how it actually went — this helps future owners of the same vehicle know what to expect.
                  </p>
                  <button
                    data-testid="mark-repair-completed-btn"
                    className="btn btn-primary"
                    type="button"
                    onClick={() => setShowCompletionSurvey(true)}
                    style={{ width: 'auto', padding: '0 20px', minHeight: 44 }}
                  >
                    Mark Repair Completed
                  </button>
                </div>
              )}

              {showCompletionSurvey && (
                <div
                  role="dialog"
                  aria-modal="true"
                  style={{
                    position: 'fixed',
                    inset: 0,
                    background: 'rgba(0,0,0,0.6)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                    padding: 16,
                  }}
                >
                  <div
                    className="card"
                    style={{ width: 'clamp(320px, 90vw, 420px)', background: '#1e293b', border: '1px solid rgba(255,255,255,0.12)' }}
                  >
                    <p className="card-label">Job Outcome Survey</p>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 16 }}>How did it go?</h3>

                    <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                      What was your total time spent on this job? (minutes)
                    </label>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      inputMode="numeric"
                      value={outcomeDuration}
                      onChange={(e) => setOutcomeDuration(e.target.value)}
                      placeholder="e.g. 90"
                      style={{ width: '100%', padding: '10px', borderRadius: 6, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', marginBottom: 16, minHeight: 44 }}
                    />

                    <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                      What did parts/tools actually end up costing you? ($)
                    </label>
                    <input
                      className="input"
                      type="number"
                      min={0}
                      step="0.01"
                      inputMode="decimal"
                      value={outcomeCost}
                      onChange={(e) => setOutcomeCost(e.target.value)}
                      placeholder="e.g. 145.00"
                      style={{ width: '100%', padding: '10px', borderRadius: 6, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', marginBottom: 16, minHeight: 44 }}
                    />

                    {outcomeError && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem', marginBottom: 12 }}>{outcomeError}</p>}

                    <div style={{ display: 'flex', gap: 10 }}>
                      <button
                        className="btn btn-secondary"
                        type="button"
                        onClick={() => { setShowCompletionSurvey(false); setOutcomeError(null); }}
                        style={{ flex: 1, minHeight: 44 }}
                        disabled={outcomeSubmitting}
                      >
                        Cancel
                      </button>
                      <button
                        data-testid="submit-outcome-btn"
                        className="btn btn-primary"
                        type="button"
                        onClick={submitCompletionSurvey}
                        style={{ flex: 1, minHeight: 44 }}
                        disabled={outcomeSubmitting}
                      >
                        {outcomeSubmitting ? <><span className="loading-spinner" aria-hidden="true" /> Submitting…</> : 'Submit'}
                      </button>
                    </div>
                  </div>
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
          )
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
