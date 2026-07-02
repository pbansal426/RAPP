'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import VehicleHeroCard from './VehicleHeroCard';
import ObdCodePicker from './ObdCodePicker';
import type { ObdCode } from '@/lib/obdCodes';
import {
  HandToolsIcon,
  SocketSetIcon,
  TorqueWrenchIcon,
  JackStandsIcon,
  MultimeterIcon,
  ObdScannerIcon,
  SafetyGlovesIcon,
  PenetratingOilIcon,
} from './toolIcons';

const TOOLS = [
  { id: 'tool-hand-tools', label: 'Basic Hand Tools', Icon: HandToolsIcon },
  { id: 'tool-socket-set', label: 'Socket Set & Ratchet', Icon: SocketSetIcon },
  { id: 'tool-torque-wrench', label: 'Torque Wrench', Icon: TorqueWrenchIcon },
  { id: 'tool-jack-stands', label: 'Jack & Jack Stands', Icon: JackStandsIcon },
  { id: 'tool-multimeter', label: 'Digital Multimeter', Icon: MultimeterIcon },
  { id: 'tool-obd-scanner', label: 'OBD-II Scanner', Icon: ObdScannerIcon },
  { id: 'tool-nitrile-gloves', label: 'Safety Glasses & Gloves', Icon: SafetyGlovesIcon },
  { id: 'tool-wd40', label: 'Penetrating Oil (WD-40)', Icon: PenetratingOilIcon },
];

export default function DiagnosePage() {
  const router = useRouter();
  const [vin, setVin] = useState<string>('');
  const [vinData, setVinData] = useState<Record<string, unknown> | null>(null);
  const [symptoms, setSymptoms] = useState('');
  const [tools, setTools] = useState<string[]>([]);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const storedVin = localStorage.getItem('rapp_vin');
    if (!storedVin) { router.push('/'); return; }
    setVin(storedVin);
    const stored = localStorage.getItem('rapp_vin_data');
    if (stored) setVinData(JSON.parse(stored));
  }, [router]);

  const toggleTool = (tool: string) =>
    setTools((prev) => prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool]);

  const handleObdSelect = (code: ObdCode) => {
    setSymptoms((prev) => {
      const entry = `${code.code} - ${code.description}`;
      if (!prev.trim()) return entry;
      return `${prev.trim()}\n${entry}`;
    });
  };

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(file);
    });
  };

  const handleSubmit = () => {
    if (!symptoms.trim()) return;
    localStorage.setItem('rapp_symptoms', symptoms.trim());
    localStorage.setItem('rapp_tools', JSON.stringify(tools));
    router.push('/results');
  };

  return (
    <main className="page">
      <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start', marginBottom: 12 }}>
        <button
          id="back-to-home-btn"
          data-testid="back-to-home-btn"
          className="btn btn-secondary"
          type="button"
          onClick={() => router.push('/')}
          style={{ padding: '6px 12px', fontSize: '0.875rem' }}
        >
          ← Back to Identification
        </button>
      </div>

      <header className="page-header">
        <p className="logo">⚙ RAPP</p>
        <h1 className="page-title">Diagnostic Input</h1>
        <p className="page-subtitle">What&apos;s wrong, and what have you got to fix it?</p>
      </header>

      <VehicleHeroCard vin={vin} vinData={vinData} />

      <div className="card">
        <p className="card-label">Step 2 of 4 — Symptoms &amp; OBD-II Codes</p>

        <ObdCodePicker onSelect={handleObdSelect} />

        <label htmlFor="symptoms-input" className="sr-only">Describe symptoms, OBD-II codes, or desired modification</label>
        <textarea
          id="symptoms-input"
          data-testid="symptoms-input"
          className="input textarea"
          style={{ marginTop: 12 }}
          placeholder="Describe the symptom (e.g. rough idle, grinding noise on braking) or pick a code above."
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
          rows={4}
        />

        <div style={{ marginTop: 14 }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ width: 'auto', padding: '0 18px' }}
            onClick={() => photoInputRef.current?.click()}
          >
            📷 Attach Dashboard / Engine Bay Photo
          </button>
          <input
            type="file"
            ref={photoInputRef}
            accept="image/*"
            capture="environment"
            style={{ display: 'none' }}
            onChange={handlePhotoChange}
          />
          {photoPreviewUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={photoPreviewUrl}
              alt="Attached vehicle photo preview"
              style={{ display: 'block', marginTop: 12, maxWidth: '100%', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}
            />
          )}
        </div>
      </div>

      <div className="card">
        <p className="card-label">Tools in Your Garage</p>
        <p className="text-muted text-sm" style={{ marginBottom: 12 }}>
          None owned? Leave blank — we&apos;ll guide you on what to buy.
        </p>
        <div className="checkbox-group" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
          {TOOLS.map(({ id, label, Icon }) => (
            <label key={id} htmlFor={id} className="checkbox-label" style={{ height: 'auto', minHeight: 52, padding: '10px 14px' }}>
              <input
                type="checkbox"
                id={id}
                data-testid={id}
                checked={tools.includes(id)}
                onChange={() => toggleTool(id)}
              />
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: '0.9rem', lineHeight: 1.25 }}>
                <Icon /> {label}
              </span>
            </label>
          ))}
        </div>
      </div>

      <button
        id="submit-diagnose-btn"
        data-testid="submit-diagnose-btn"
        className="btn btn-primary"
        onClick={handleSubmit}
        disabled={!symptoms.trim()}
      >
        → Run AI Diagnosis &amp; Mod Planner
      </button>
    </main>
  );
}
