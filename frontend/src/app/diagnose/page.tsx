'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import VehicleHeroCard from './VehicleHeroCard';
import ObdCodePicker from './ObdCodePicker';
import ToolSelector from './ToolSelector';
import type { ObdCode } from '@/lib/obdCodes';
import { safeGetJson } from '@/lib/storage';
import { AppLogoMarkIcon, CameraIcon } from '@/app/sharedIcons';

export default function DiagnosePage() {
  const router = useRouter();
  const [vin, setVin] = useState<string>('');
  const [vinData, setVinData] = useState<Record<string, unknown> | null>(null);
  const [symptoms, setSymptoms] = useState('');
  const [selectedObdCodes, setSelectedObdCodes] = useState<ObdCode[]>([]);
  const [tools, setTools] = useState<string[]>([]);
  const [photoPreviews, setPhotoPreviews] = useState<{ url: string; name: string; isHeic: boolean; converting: boolean }[]>([]);
  const [showAllPhotos, setShowAllPhotos] = useState(false);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const storedVin = localStorage.getItem('rapp_vin');
    if (!storedVin) { router.push('/'); return; }
    setVin(storedVin);
    setVinData(safeGetJson<Record<string, unknown> | null>('rapp_vin_data', null));
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
    files.forEach((file) => {
      const name = file.name;
      const ext = name.split('.').pop()?.toLowerCase();
      const isHeic = ext === 'heic' || ext === 'heif' || file.type === 'image/heic' || file.type === 'image/heif';
      const rawUrl = URL.createObjectURL(file);
      // Browsers can't paint HEIC in an <img>, so convert to JPEG client-side
      // for a real preview; show a "converting" placeholder meanwhile.
      const entry = { url: rawUrl, name, isHeic, converting: isHeic };
      setPhotoPreviews((prev) => [...prev, entry]);

      if (isHeic) {
        import('heic2any')
          .then((mod) => (mod.default as (o: { blob: Blob; toType?: string }) => Promise<Blob | Blob[]>)({ blob: file, toType: 'image/jpeg' }))
          .then((out) => {
            const blob = Array.isArray(out) ? out[0] : out;
            const jpegUrl = URL.createObjectURL(blob);
            setPhotoPreviews((prev) =>
              prev.map((p) => (p.url === rawUrl ? { ...p, url: jpegUrl, converting: false } : p))
            );
            URL.revokeObjectURL(rawUrl);
          })
          .catch(() => {
            // Conversion failed — drop the spinner, keep the labeled placeholder.
            setPhotoPreviews((prev) =>
              prev.map((p) => (p.url === rawUrl ? { ...p, converting: false } : p))
            );
          });
      }
    });
    e.target.value = '';
  };

  const hasDiagnosticInput = symptoms.trim().length > 0 || selectedObdCodes.length > 0;

  const handleSubmit = () => {
    if (!hasDiagnosticInput) return;
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
                {c.code}: {c.description}
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
                  <button
                    type="button"
                    key={photo.url}
                    onClick={() => !photo.converting && setLightboxUrl(photo.url)}
                    aria-label={`View ${photo.name}`}
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
                      padding: 0,
                      cursor: photo.converting ? 'default' : 'zoom-in',
                    }}
                  >
                    {photo.converting ? (
                      <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: '0.7rem' }}>
                        <span className="loading-spinner" aria-hidden="true" />
                        Converting…
                      </span>
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={photo.url}
                        alt={`Attached photo ${idx + 1}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    )}
                  </button>
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
        disabled={!hasDiagnosticInput}
        title={hasDiagnosticInput ? undefined : 'Describe a symptom or select at least one OBD-II code to continue'}
      >
        → Run AI Diagnosis &amp; Mod Planner
      </button>
      {!hasDiagnosticInput && (
        <p className="text-muted text-sm" style={{ textAlign: 'center', marginTop: 8 }}>
          Describe a symptom or select at least one OBD-II code above to continue.
        </p>
      )}

      {lightboxUrl && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Photo preview"
          onClick={() => setLightboxUrl(null)}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: 'rgba(2, 6, 23, 0.88)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            cursor: 'zoom-out',
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={lightboxUrl}
            alt="Enlarged attached photo"
            style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 'var(--radius-sm)', boxShadow: '0 12px 48px rgba(0,0,0,0.6)' }}
          />
          <button
            type="button"
            aria-label="Close preview"
            onClick={() => setLightboxUrl(null)}
            style={{
              position: 'fixed',
              top: 20,
              right: 20,
              width: 44,
              height: 44,
              borderRadius: '50%',
              border: '1px solid rgba(255,255,255,0.2)',
              background: 'rgba(15,23,42,0.9)',
              color: '#fff',
              fontSize: '1.4rem',
              lineHeight: 1,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>
      )}
    </main>
  );
}
