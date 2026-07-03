'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import VehicleHeroCard from './VehicleHeroCard';
import ObdCodePicker from './ObdCodePicker';
import ToolSelector from './ToolSelector';
import type { ObdCode } from '@/lib/obdCodes';
import { AppLogoMarkIcon, CameraIcon } from '@/app/sharedIcons';

export default function DiagnosePage() {
  const router = useRouter();
  const [vin, setVin] = useState<string>('');
  const [vinData, setVinData] = useState<Record<string, unknown> | null>(null);
  const [symptoms, setSymptoms] = useState('');
  const [selectedObdCodes, setSelectedObdCodes] = useState<ObdCode[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [photoPreviews, setPhotoPreviews] = useState<{ url: string; name: string; isHeic: boolean }[]>([]);
  const [showAllPhotos, setShowAllPhotos] = useState(false);
  const photoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const storedVin = localStorage.getItem('rapp_vin');
    if (!storedVin) { router.push('/'); return; }
    setVin(storedVin);
    const stored = localStorage.getItem('rapp_vin_data');
    if (stored) setVinData(JSON.parse(stored));
  }, [router]);

  const handleObdSelect = (code: ObdCode) => {
    setSelectedObdCodes((prev) => {
      if (prev.some((c) => c.code === code.code)) return prev;
      return [...prev, code];
    });
  };

  const removeObdCode = (codeStr: string) => {
    setSelectedObdCodes((prev) => prev.filter((c) => c.code !== codeStr));
  };

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length === 0) return;
    const newPreviews = files.map((file) => {
      const name = file.name;
      const ext = name.split('.').pop()?.toLowerCase();
      const isHeic = ext === 'heic' || ext === 'heif' || file.type === 'image/heic' || file.type === 'image/heif';
      return {
        url: URL.createObjectURL(file),
        name,
        isHeic,
      };
    });
    setPhotoPreviews((prev) => [...prev, ...newPreviews]);
  };

  const handleSubmit = () => {
    if (!symptoms.trim() && selectedObdCodes.length === 0) return;
    localStorage.setItem('rapp_symptoms', symptoms.trim());
    localStorage.setItem(
      'rapp_obd_codes',
      JSON.stringify(selectedObdCodes.map((c) => `${c.code} - ${c.description}`))
    );
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
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">Diagnostic Input</h1>
        <p className="page-subtitle">Select symptoms, OBD-II codes, or desired modifications.</p>
      </header>

      <VehicleHeroCard vin={vin} vinData={vinData} />

      <div className="card">
        <p className="card-label">Step 2 — Symptoms &amp; OBD-II Codes</p>

        <ObdCodePicker onSelect={handleObdSelect} />

        {selectedObdCodes.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '12px 0' }}>
            {selectedObdCodes.map((c) => (
              <span
                key={c.code}
                className="obd-chip"
                style={{
                  background: '#0b1329', // Deep industrial navy background
                  border: '1px solid #f97316', // Orange warning highlight/border
                  color: '#f8fafc', // Crisp engineered text color (slate-50)
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', // crisp engineered text
                  letterSpacing: '0.03em',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 12px',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  borderRadius: '6px',
                  boxShadow: '0 2px 8px rgba(249, 115, 22, 0.15)',
                }}
              >
                ⚠️ {c.code}: {c.description}
                <button
                  type="button"
                  onClick={() => removeObdCode(c.code)}
                  aria-label={`Remove ${c.code}`}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#f97316',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    fontSize: '1.1rem',
                    lineHeight: 1,
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 0,
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

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
            <CameraIcon /> Attach Dashboard or Engine Bay Photo(s)
          </button>
          <input
            type="file"
            ref={photoInputRef}
            accept="image/*,.heic,.heif"
            multiple
            capture="environment"
            style={{ display: 'none' }}
            onChange={handlePhotoChange}
          />
          {photoPreviews.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))',
                  gap: 10,
                }}
              >
                {(showAllPhotos ? photoPreviews : photoPreviews.slice(0, 3)).map((photo, idx) => (
                  <div
                    key={photo.url}
                    style={{
                      position: 'relative',
                      borderRadius: 'var(--radius-sm)',
                      overflow: 'hidden',
                      border: '1px solid var(--border)',
                      aspectRatio: '4/3',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'rgba(30, 41, 59, 0.4)',
                    }}
                  >
                    {photo.isHeic ? (
                      <div
                        style={{
                          width: '100%',
                          height: '100%',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          background: '#0b1329', // Deep industrial navy background
                          border: '1px solid #f97316', // Orange warning highlights/borders
                          color: '#f8fafc',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                          fontSize: '0.75rem',
                          textAlign: 'center',
                          padding: 8,
                          gap: 4,
                        }}
                      >
                        <svg
                          width="24"
                          height="24"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="#f97316"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M21 16V8a2 2 0 0 0-2-2h-2l-1.5-2.5h-7L7 6H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                        <span style={{ fontWeight: 800, color: '#f97316', letterSpacing: '0.05em' }}>HEIC PREVIEW</span>
                        <span
                          style={{
                            fontSize: '0.65rem',
                            opacity: 0.7,
                            textOverflow: 'ellipsis',
                            overflow: 'hidden',
                            whiteSpace: 'nowrap',
                            width: '100%',
                            padding: '0 4px',
                          }}
                        >
                          {photo.name}
                        </span>
                      </div>
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={photo.url}
                        alt={`Attached photo ${idx + 1}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    )}
                  </div>
                ))}
              </div>
              {photoPreviews.length > 3 && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ marginTop: 10, padding: '4px 12px', fontSize: '0.8rem', width: 'auto' }}
                  onClick={() => setShowAllPhotos(!showAllPhotos)}
                >
                  {showAllPhotos ? 'Collapse photos' : `+${photoPreviews.length - 3} more photo${photoPreviews.length - 3 > 1 ? 's' : ''}`}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <p className="card-label">Tools in Your Garage</p>
        <p className="text-muted text-sm" style={{ marginBottom: 12 }}>
          Select specific ecosystems and specs you own — AI will tailor instructions and recommend any missing tools.
        </p>
        <ToolSelector selectedTools={tools} onChange={setTools} />
      </div>

      <button
        id="submit-diagnose-btn"
        data-testid="submit-diagnose-btn"
        className="btn btn-primary"
        onClick={handleSubmit}
        disabled={!symptoms.trim() && selectedObdCodes.length === 0}
      >
        → Run AI Diagnosis &amp; Mod Planner
      </button>
    </main>
  );
}
