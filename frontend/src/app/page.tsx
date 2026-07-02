'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import { fetchAllMakes, fetchModels, POWERTRAINS, type MakeGroups } from '@/lib/nhtsa';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

interface VinData {
  vin: string;
  year: number | string | null;
  make: string;
  model: string;
  engine: string;
  drive_type: string;
}

const YEARS = Array.from({ length: 2026 - 1990 + 1 }, (_, i) => String(2026 - i));

// Reproduces the legacy synthetic-VIN scheme (SYN + YY + 5-char make + 7-char
// X-padded model) for any make/model — e.g. 2023/HONDA/ACCORD → SYN23HONDAACCORDX.
function buildSyntheticVin(year: string, make: string, model: string): string {
  const yy = year.substring(2);
  const makeCode = make.toUpperCase().replace(/[^A-Z0-9]/g, '').padEnd(5, 'X').slice(0, 5);
  const modelCode = model.toUpperCase().replace(/[^A-Z0-9]/g, '').padEnd(7, 'X').slice(0, 7);
  return `SYN${yy}${makeCode}${modelCode}`;
}

export default function HomePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Manual VIN input state
  const [vin, setVin] = useState('');
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cascading YMM dropdown state (data live from NHTSA)
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMake, setSelectedMake] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedPowertrain, setSelectedPowertrain] = useState<string>('Gasoline');
  const [engineDetail, setEngineDetail] = useState('');
  const [makeGroups, setMakeGroups] = useState<MakeGroups | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [ymmError, setYmmError] = useState<string | null>(null);

  // Prefetch the full make list so the dropdown is ready by the time a year is picked.
  useEffect(() => {
    fetchAllMakes().then(setMakeGroups).catch(() => setYmmError('Could not load vehicle makes. Check your connection.'));
  }, []);

  useEffect(() => {
    if (!selectedYear || !selectedMake) { setModels([]); return; }
    let cancelled = false;
    setModelsLoading(true);
    fetchModels(selectedMake, selectedYear)
      .then((m) => { if (!cancelled) setModels(m); })
      .catch(() => { if (!cancelled) setYmmError('Could not load models for this make/year.'); })
      .finally(() => { if (!cancelled) setModelsLoading(false); });
    return () => { cancelled = true; };
  }, [selectedYear, selectedMake]);

  const handleYearChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedYear(e.target.value);
    setSelectedMake('');
    setSelectedModel('');
    setYmmError(null);
  };

  const handleMakeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMake(e.target.value);
    setSelectedModel('');
    setYmmError(null);
  };

  const handleSubmit = async () => {
    const trimmed = vin.trim().toUpperCase();
    if (trimmed.length !== 17) {
      setError('VIN must be exactly 17 characters.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await api.get<VinData>(`/api/vin/${trimmed}`);
      localStorage.setItem('rapp_vin', trimmed);
      localStorage.setItem('rapp_vin_data', JSON.stringify(data));
      router.push('/diagnose');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not decode VIN. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleYmmSubmit = () => {
    if (!selectedYear || !selectedMake || !selectedModel) {
      setError('Please select Year, Make, and Model.');
      return;
    }
    setError(null);

    const displayModel = models.find((m) => m.toUpperCase() === selectedModel) ?? selectedModel;
    const engine = [selectedPowertrain, engineDetail.trim()].filter(Boolean).join(' · ');
    const syntheticVin = buildSyntheticVin(selectedYear, selectedMake, selectedModel);

    localStorage.setItem('rapp_vin', syntheticVin);
    localStorage.setItem('rapp_vin_data', JSON.stringify({
      vin: syntheticVin,
      year: selectedYear,
      make: selectedMake,
      model: displayModel,
      engine,
      drive_type: '',
      powertrain: selectedPowertrain,
    }));
    router.push('/diagnose');
  };

  const handleScanClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setOcrLoading(true);
    try {
      const { createWorker } = await import('tesseract.js');
      const worker = await createWorker('eng');
      const ret = await worker.recognize(file);
      await worker.terminate();

      const text = ret.data.text;
      const cleanedText = text.toUpperCase().replace(/[\s\-_]/g, '');
      const match = cleanedText.match(/[A-Z0-9]{17}/);
      if (match) {
        setVin(match[0]);
      } else {
        setError('No 17-character VIN found in the image. Try a closer, well-lit shot of the tag.');
      }
    } catch (err) {
      console.error(err);
      setError('Could not read the image. Please enter the VIN manually.');
    } finally {
      setOcrLoading(false);
      e.target.value = '';
    }
  };

  return (
    <main className="page">
      <header className="page-header">
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">Vehicle Repair &amp;<br />Modification AI Engine</h1>
        <p className="page-subtitle">Instant tool-aware repair instructions and diagnostic routing.</p>
      </header>

      <div className="card">
        <p className="card-label">Step 1 — Vehicle Identification</p>

        <label htmlFor="vin-input" className="sr-only">Vehicle Identification Number (VIN)</label>
        <input
          id="vin-input"
          data-testid="vin-input"
          className="input"
          type="text"
          placeholder="Enter 17-character VIN"
          value={vin}
          maxLength={17}
          autoCapitalize="characters"
          spellCheck={false}
          onChange={(e) => setVin(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          aria-describedby={error ? 'vin-error' : undefined}
        />
        <p className="text-muted text-sm" style={{ marginTop: 8 }}>
          Located at the base of the driver&apos;s windshield or door jamb — or photograph the tag below.
        </p>

        {error && (
          <p id="vin-error" role="alert" style={{ color: 'var(--accent-red)', fontSize: '0.875rem', marginTop: 8 }}>
            {error}
          </p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
          <button
            id="submit-vin-btn"
            data-testid="submit-vin-btn"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || ocrLoading}
            aria-busy={loading}
          >
            {loading ? <><span className="loading-spinner" aria-hidden="true" /> Decoding VIN…</> : 'Decode VIN'}
          </button>

          <button
            id="scan-barcode-btn"
            data-testid="scan-barcode-btn"
            className="btn btn-secondary"
            type="button"
            onClick={handleScanClick}
            disabled={loading || ocrLoading}
          >
            {ocrLoading ? <><span className="loading-spinner" aria-hidden="true" /> Reading VIN tag…</> : 'Photograph VIN Tag'}
          </button>

          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
          />
        </div>
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <p className="card-label">Select Vehicle by Make &amp; Model</p>
        <p className="text-muted text-sm" style={{ marginBottom: 14 }}>
          Choose from the federal vehicle registry.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label htmlFor="select-year" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
              1. Year
            </label>
            <select
              id="select-year"
              data-testid="select-year"
              className="select"
              value={selectedYear}
              onChange={handleYearChange}
            >
              <option value="">— Select Year —</option>
              {YEARS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="select-make" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
              2. Make
            </label>
            <select
              id="select-make"
              data-testid="select-make"
              className="select"
              value={selectedMake}
              onChange={handleMakeChange}
              disabled={!selectedYear || !makeGroups}
            >
              <option value="">— Select Make —</option>
              {makeGroups && (
                <>
                  <optgroup label="Popular">
                    {makeGroups.popular.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </optgroup>
                  <optgroup label="All Makes (A–Z)">
                    {makeGroups.other.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </optgroup>
                </>
              )}
            </select>
          </div>

          <div>
            <label htmlFor="select-model" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
              3. Model
            </label>
            <select
              id="select-model"
              data-testid="select-model"
              className="select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={!selectedMake || modelsLoading || models.length === 0}
            >
              <option value="">{modelsLoading ? 'Loading models…' : '— Select Model —'}</option>
              {models.map((m) => (
                <option key={m} value={m.toUpperCase()}>{m}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="select-powertrain" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
                4. Powertrain
              </label>
              <select
                id="select-powertrain"
                data-testid="select-powertrain"
                className="select"
                value={selectedPowertrain}
                onChange={(e) => setSelectedPowertrain(e.target.value)}
                disabled={!selectedModel}
              >
                {POWERTRAINS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="engine-detail" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
                Engine <span className="text-muted">(optional)</span>
              </label>
              <input
                id="engine-detail"
                data-testid="engine-detail"
                className="input"
                style={{ minHeight: 52 }}
                type="text"
                placeholder="e.g. 2.0T, 5.7L V8"
                value={engineDetail}
                onChange={(e) => setEngineDetail(e.target.value)}
                disabled={!selectedModel}
              />
            </div>
          </div>

          {ymmError && (
            <p role="alert" style={{ color: 'var(--accent-red)', fontSize: '0.875rem' }}>{ymmError}</p>
          )}

          <button
            id="submit-ymm-btn"
            data-testid="submit-ymm-btn"
            className="btn btn-primary"
            onClick={handleYmmSubmit}
            disabled={loading || ocrLoading || !selectedYear || !selectedMake || !selectedModel}
          >
            Continue with Selected Vehicle
          </button>
        </div>
      </div>
    </main>
  );
}
