'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import { track } from '@/lib/analytics';
import { fetchAllMakes, fetchModels, POWERTRAINS, type MakeGroups } from '@/lib/nhtsa';
import { getTrimsForModel, lookupVehicleSpecs } from '@/lib/vehicleSpecs';
import { isValidVinCheckDigit } from '@/lib/vinCheckDigit';
import { AppLogoMarkIcon } from '@/app/sharedIcons';
import VinCropModal from './VinCropModal';
import ScanModeModal from './ScanModeModal';
import WindshieldScanModal from './WindshieldScanModal';
import DoorJambScanModal from './DoorJambScanModal';

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
  const uploadInputRef = useRef<HTMLInputElement>(null);

  // Manual VIN input state
  const [vin, setVin] = useState('');
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cropImageUrl, setCropImageUrl] = useState<string | null>(null);

  // Scan flow: chooser -> live camera modal (windshield tag photo, or door jamb barcode)
  const [scanChooserOpen, setScanChooserOpen] = useState(false);
  const [scanMode, setScanMode] = useState<'windshield' | 'doorjamb' | null>(null);

  // Cascading YMM dropdown state (data live from NHTSA)
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMake, setSelectedMake] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedTrim, setSelectedTrim] = useState('');
  const [selectedDriveType, setSelectedDriveType] = useState('');
  const [powertrainLocked, setPowertrainLocked] = useState(false);
  const [engineLocked, setEngineLocked] = useState(false);
  const [driveLocked, setDriveLocked] = useState(false);
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

  // Auto-populate and lock specs when the curated table has unambiguous
  // data for this year/make/model/trim; unknown vehicles keep manual inputs.
  useEffect(() => {
    const match = selectedModel
      ? lookupVehicleSpecs(selectedYear, selectedMake, selectedModel, selectedTrim)
      : null;

    if (match?.powertrain) {
      setSelectedPowertrain(match.powertrain);
      setPowertrainLocked(true);
    } else {
      setPowertrainLocked(false);
    }
    if (match?.engine) {
      setEngineDetail(match.engine);
      setEngineLocked(true);
    } else {
      setEngineLocked(false);
    }
    if (match?.drive_type) {
      setSelectedDriveType(match.drive_type);
      setDriveLocked(true);
    } else {
      setDriveLocked(false);
    }
  }, [selectedYear, selectedMake, selectedModel, selectedTrim]);

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
    setSelectedTrim('');
    setSelectedDriveType('');
    setYmmError(null);
  };

  const handleMakeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMake(e.target.value);
    setSelectedModel('');
    setSelectedTrim('');
    setSelectedDriveType('');
    setYmmError(null);
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedModel(val);
    if (val) {
      const trims = getTrimsForModel(val);
      setSelectedTrim(trims[0] || 'Base');
    } else {
      setSelectedTrim('');
    }
    setYmmError(null);
  };

  const decodeAndGo = async (
    vinCandidate: string,
    method: 'manual' | 'scan' = 'manual',
  ) => {
    const trimmed = vinCandidate.trim().toUpperCase();
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
      track('vin_submitted', { method });
      router.push('/diagnose');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not decode VIN. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => decodeAndGo(vin);

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
      trim: selectedTrim,
      drive_type: selectedDriveType || '',
      engine,
      powertrain: selectedPowertrain,
    }));
    track('vin_submitted', { method: 'ymm' });
    router.push('/diagnose');
  };

  // Shared by Upload (existing photo) and the Windshield live-capture modal —
  // both hand over exactly one still image and go through the identical
  // Gemini-OCR-first, Tesseract-crop-fallback pipeline. One Gemini call per
  // image, never a stream of frames.
  const processVinImage = async (image: File | Blob) => {
    setError(null);
    setOcrLoading(true);
    let startedCrop = false;
    try {
      // First try backend OCR endpoint (supports HEIC, Vision AI, check-digits, and NHTSA auto-decode)
      const formData = new FormData();
      formData.append('file', image, image instanceof File ? image.name : 'vin-capture.jpg');
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/vin/ocr`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        if (data && data.vin) {
          setVin(data.vin);
          if (data.decoded_vehicle && data.decoded_vehicle.make) {
            localStorage.setItem('rapp_vin', data.vin);
            localStorage.setItem('rapp_vin_data', JSON.stringify(data.decoded_vehicle));
            track('vin_submitted', { method: 'photo' });
            router.push('/diagnose');
            return;
          }
          return;
        }
      }

      // Client-side fallback if backend API key is unconfigured or offline.
      // Raw full-photo OCR is unusable in practice -- the VIN tag is a tiny
      // fraction of a typical photo, and Tesseract tries to read the
      // surrounding paint/glass texture as text. Cropping tightly to just
      // the tag is what actually makes free OCR work, so hand off to a
      // crop step instead of running Tesseract on the whole frame.
      startedCrop = true;
      setCropImageUrl(URL.createObjectURL(image));
    } catch (err) {
      console.error(err);
      setError('Could not read the image. Please enter the VIN manually.');
    } finally {
      if (!startedCrop) setOcrLoading(false);
    }
  };

  const handleUploadFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processVinImage(file);
    e.target.value = '';
  };

  // WindshieldScanModal scans the live feed itself and only calls this once
  // it has both a VIN and a decoded vehicle in hand, so no second /api/vin
  // round-trip is needed here -- just persist and go, same as every other
  // successful identification path.
  const handleWindshieldDetected = (detectedVin: string, decodedVehicle: VinData) => {
    setScanMode(null);
    setVin(detectedVin);
    localStorage.setItem('rapp_vin', detectedVin);
    localStorage.setItem('rapp_vin_data', JSON.stringify(decodedVehicle));
    track('vin_submitted', { method: 'scan' });
    router.push('/diagnose');
  };

  const handleDoorJambDecoded = async (candidateVin: string) => {
    setScanMode(null);
    setVin(candidateVin);
    await decodeAndGo(candidateVin, 'scan');
  };

  const handleCropCancel = () => {
    if (cropImageUrl) URL.revokeObjectURL(cropImageUrl);
    setCropImageUrl(null);
    setOcrLoading(false);
  };

  const handleCropConfirm = async (canvas: HTMLCanvasElement) => {
    if (cropImageUrl) URL.revokeObjectURL(cropImageUrl);
    setCropImageUrl(null);
    try {
      const { createWorker, PSM } = await import('tesseract.js');
      const worker = await createWorker('eng');
      await worker.setParameters({
        tessedit_char_whitelist: 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789',
        tessedit_pageseg_mode: PSM.SINGLE_LINE,
      });
      const ret = await worker.recognize(canvas);
      await worker.terminate();

      const cleanedText = ret.data.text.toUpperCase().replace(/[^A-Z0-9]/g, '');
      const match = cleanedText.match(/[A-Z0-9]{17}/);
      if (match) {
        setVin(match[0]);
        if (!isValidVinCheckDigit(match[0])) {
          setError('This may not be a fully accurate read (failed VIN check-digit validation) — please verify it against the tag before continuing.');
        }
      } else {
        setError('No 17-character VIN found in the cropped area. Try cropping tighter around just the text, or enter the VIN manually.');
      }
    } catch (err) {
      console.error(err);
      setError('Could not read the image. Please enter the VIN manually.');
    } finally {
      setOcrLoading(false);
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
            onClick={() => setScanChooserOpen(true)}
            disabled={loading || ocrLoading}
          >
            {ocrLoading ? <><span className="loading-spinner" aria-hidden="true" /> Reading VIN tag…</> : 'Scan VIN'}
          </button>

          <button
            id="upload-vin-photo-btn"
            data-testid="upload-vin-photo-btn"
            className="btn btn-secondary"
            type="button"
            onClick={() => uploadInputRef.current?.click()}
            disabled={loading || ocrLoading}
          >
            {ocrLoading ? <><span className="loading-spinner" aria-hidden="true" /> Reading VIN tag…</> : 'Upload Photo'}
          </button>

          {/* No `capture` attribute here — this opens the photo library, not the camera. */}
          <input
            type="file"
            ref={uploadInputRef}
            style={{ display: 'none' }}
            accept="image/*,.heic,.heif"
            onChange={handleUploadFileChange}
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
              onChange={handleModelChange}
              disabled={!selectedMake || modelsLoading || models.length === 0}
            >
              <option value="">{modelsLoading ? 'Loading models…' : '— Select Model —'}</option>
              {models.map((m) => (
                <option key={m} value={m.toUpperCase()}>{m}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="select-trim" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
              4. Trim
            </label>
            <select
              id="select-trim"
              data-testid="select-trim"
              className="select"
              value={selectedTrim}
              onChange={(e) => setSelectedTrim(e.target.value)}
              disabled={!selectedModel}
            >
              <option value="">— Select Trim —</option>
              {selectedModel && getTrimsForModel(selectedModel).map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ flex: 1 }}>
              <label htmlFor="select-powertrain" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
                Powertrain
              </label>
              <select
                id="select-powertrain"
                data-testid="select-powertrain"
                className="select"
                value={selectedPowertrain}
                onChange={(e) => setSelectedPowertrain(e.target.value)}
                disabled={!selectedModel || powertrainLocked}
              >
                {POWERTRAINS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label htmlFor="select-drive" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
                Drive Type
              </label>
              <select
                id="select-drive"
                data-testid="select-drive"
                className="select"
                value={selectedDriveType}
                onChange={(e) => setSelectedDriveType(e.target.value)}
                disabled={!selectedModel || driveLocked}
              >
                <option value="">— Select Drive —</option>
                <option value="FWD">FWD</option>
                <option value="RWD">RWD</option>
                <option value="AWD">AWD</option>
                <option value="4WD">4WD</option>
              </select>
            </div>
          </div>

          <div>
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
              disabled={!selectedModel || engineLocked}
            />
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

      {cropImageUrl && (
        <VinCropModal imageUrl={cropImageUrl} onConfirm={handleCropConfirm} onCancel={handleCropCancel} />
      )}

      {scanChooserOpen && (
        <ScanModeModal
          onChooseWindshield={() => { setScanChooserOpen(false); setScanMode('windshield'); }}
          onChooseDoorJamb={() => { setScanChooserOpen(false); setScanMode('doorjamb'); }}
          onCancel={() => setScanChooserOpen(false)}
        />
      )}

      {scanMode === 'windshield' && (
        <WindshieldScanModal onDetected={handleWindshieldDetected} onCancel={() => setScanMode(null)} />
      )}

      {scanMode === 'doorjamb' && (
        <DoorJambScanModal onDecoded={handleDoorJambDecoded} onCancel={() => setScanMode(null)} />
      )}
    </main>
  );
}
