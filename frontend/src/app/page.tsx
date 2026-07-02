'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';

interface VinData {
  vin: string;
  year: number | string | null;
  make: string;
  model: string;
  engine: string;
  drive_type: string;
}

export default function HomePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Manual VIN input state
  const [vin, setVin] = useState('');
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cascading YMM dropdown state
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMake, setSelectedMake] = useState('');
  const [selectedModel, setSelectedModel] = useState('');

  const years = Array.from({ length: 2026 - 2015 + 1 }, (_, i) => String(2015 + i)); // 2015 to 2026
  const makes = ['HONDA', 'TOYOTA', 'FORD', 'LEXUS', 'CHEVROLET'];
  
  const modelsPerMake: Record<string, string[]> = {
    HONDA: ['CIVIC', 'ACCORD'],
    TOYOTA: ['CAMRY', 'COROLLA'],
    FORD: ['F-150'],
    LEXUS: ['RX350'],
    CHEVROLET: ['SILVERADO']
  };

  const handleYearChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedYear(e.target.value);
    setSelectedMake('');
    setSelectedModel('');
  };

  const handleMakeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMake(e.target.value);
    setSelectedModel('');
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

  const handleYmmSubmit = async () => {
    if (!selectedYear || !selectedMake || !selectedModel) {
      setError('Please select Year, Make, and Model.');
      return;
    }
    setError(null);
    setLoading(true);

    const yy = selectedYear.substring(2); // last 2 digits

    const makeCodes: Record<string, string> = {
      HONDA: 'HONDA',
      TOYOTA: 'TOYOT',
      FORD: 'FORDX',
      LEXUS: 'LEXUS',
      CHEVROLET: 'CHEVR'
    };

    const modelCodes: Record<string, string> = {
      CIVIC: 'CIVICXX',
      ACCORD: 'ACCORDX',
      'F-150': 'F150XXX',
      CAMRY: 'CAMRYXX',
      COROLLA: 'COROLLA',
      RX350: 'RX350XX',
      SILVERADO: 'SILVERA'
    };

    const syntheticVin = `SYN${yy}${makeCodes[selectedMake]}${modelCodes[selectedModel]}`;

    try {
      const data = await api.get<VinData>(`/api/vin/${syntheticVin}`);
      localStorage.setItem('rapp_vin', syntheticVin);
      localStorage.setItem('rapp_vin_data', JSON.stringify(data));
      router.push('/diagnose');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not decode synthetic VIN. Please try again.');
    } finally {
      setLoading(false);
    }
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
        setError('No 17-character alphanumeric VIN found in the image. Please check the image and try again.');
      }
    } catch (err) {
      console.error(err);
      setError('OCR processing failed. Please enter VIN manually.');
    } finally {
      setOcrLoading(false);
      e.target.value = '';
    }
  };

  return (
    <main className="page">
      <header className="page-header">
        <p className="logo">⚙ RAPP</p>
        <h1 className="page-title">Vehicle Repair &amp;<br />Modification AI Engine</h1>
        <p className="page-subtitle">Enter your VIN to get tool-aware repair and modification instructions in seconds.</p>
      </header>

      <div className="card">
        <p className="card-label">Step 1 of 4 — Vehicle Identification</p>

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
            {loading ? <><span className="loading-spinner" aria-hidden="true" /> Decoding VIN…</> : '→ Decode VIN'}
          </button>

          <button
            id="scan-barcode-btn"
            data-testid="scan-barcode-btn"
            className="btn btn-secondary"
            type="button"
            onClick={handleScanClick}
            disabled={loading || ocrLoading}
          >
            {ocrLoading ? '⏳ Scanning Image…' : '📷 Scan Barcode / QR'}
          </button>

          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            accept="image/*"
            onChange={handleFileChange}
          />
        </div>
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <p className="card-label">Or Select Vehicle Manually (3-Step Cascade)</p>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label htmlFor="select-year" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
              1. Select Year
            </label>
            <select
              id="select-year"
              data-testid="select-year"
              className="input"
              value={selectedYear}
              onChange={handleYearChange}
              style={{ backgroundColor: 'var(--bg-input, #1e293b)', color: '#f8fafc', width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color, #334155)' }}
            >
              <option value="">-- Select Year --</option>
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="select-make" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
              2. Select Make
            </label>
            <select
              id="select-make"
              data-testid="select-make"
              className="input"
              value={selectedMake}
              onChange={handleMakeChange}
              disabled={!selectedYear}
              style={{ backgroundColor: 'var(--bg-input, #1e293b)', color: '#f8fafc', width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color, #334155)', opacity: selectedYear ? 1 : 0.5 }}
            >
              <option value="">-- Select Make --</option>
              {makes.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="select-model" style={{ display: 'block', fontSize: '0.875rem', marginBottom: 4, fontWeight: 500 }}>
              3. Select Model
            </label>
            <select
              id="select-model"
              data-testid="select-model"
              className="input"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={!selectedMake}
              style={{ backgroundColor: 'var(--bg-input, #1e293b)', color: '#f8fafc', width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color, #334155)', opacity: selectedMake ? 1 : 0.5 }}
            >
              <option value="">-- Select Model --</option>
              {selectedMake &&
                modelsPerMake[selectedMake].map((mod) => (
                  <option key={mod} value={mod}>{mod}</option>
                ))}
            </select>
          </div>

          <button
            id="submit-ymm-btn"
            data-testid="submit-ymm-btn"
            className="btn btn-primary"
            onClick={handleYmmSubmit}
            disabled={loading || ocrLoading || !selectedYear || !selectedMake || !selectedModel}
            style={{ marginTop: 8 }}
          >
            {loading ? <><span className="loading-spinner" aria-hidden="true" /> Processing…</> : '→ Confirm Vehicle'}
          </button>
        </div>
      </div>

      <p className="text-muted text-sm" style={{ textAlign: 'center', marginTop: 16 }}>
        Your VIN is on your dashboard (driver side), door sticker, or registration.
      </p>
    </main>
  );
}
