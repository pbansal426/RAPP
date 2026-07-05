'use client';

import { useEffect, useRef, useState } from 'react';
import { useCameraStream } from '@/lib/useCameraStream';

interface DecodedVehicle {
  vin: string;
  year: number | string | null;
  make: string;
  model: string;
  engine: string;
  drive_type: string;
  [key: string]: unknown;
}

interface WindshieldScanModalProps {
  onDetected: (vin: string, decodedVehicle: DecodedVehicle) => void;
  onCancel: () => void;
}

// How often to sample a frame while scanning. This is a real Gemini vision
// call per attempt (not a local/free operation like the door-jamb barcode
// loop), so polling at video framerate would multiply API usage for no
// benefit -- ~1.5s still reads as "live" to the user while keeping call
// volume sane.
const SCAN_INTERVAL_MS = 1500;

type ScanStatus = 'scanning' | 'unverified' | 'error';

// Live-scans the camera feed and keeps trying until a VIN is both read *and*
// mapped to a vehicle via NHTSA -- a text-only read that fails to decode
// (misread character, momentary NHTSA hiccup) is treated as not-yet-found
// rather than accepted, matching the always-on feel of a barcode scanner.
export default function WindshieldScanModal({ onDetected, onCancel }: WindshieldScanModalProps) {
  const { videoRef, ready, error: cameraError, torchSupported, torchOn, toggleTorch, captureFrame } =
    useCameraStream();
  const [status, setStatus] = useState<ScanStatus>('scanning');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const onDetectedRef = useRef(onDetected);
  onDetectedRef.current = onDetected;
  const scanningRef = useRef(false); // guards against overlapping in-flight requests
  const doneRef = useRef(false); // stop polling once mapped, or on teardown

  useEffect(() => {
    if (!ready) return;

    const attempt = async () => {
      if (doneRef.current || scanningRef.current) return;
      scanningRef.current = true;
      try {
        const blob = await captureFrame();
        if (!blob || doneRef.current) return;

        const formData = new FormData();
        formData.append('file', blob, 'vin-scan-frame.jpg');
        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/api/vin/ocr`, { method: 'POST', body: formData });
        if (doneRef.current) return;

        if (res.ok) {
          const data = await res.json();
          if (data?.vin && data?.decoded_vehicle?.make) {
            doneRef.current = true;
            onDetectedRef.current(data.vin, data.decoded_vehicle);
            return;
          }
          if (data?.vin) {
            setStatus('unverified');
            setStatusMessage(`Read ${data.vin} but couldn't verify it — hold steady…`);
          } else {
            setStatus('scanning');
            setStatusMessage(null);
          }
        } else if (res.status === 422) {
          // Normal while the user is still framing the tag -- no VIN read yet.
          setStatus('scanning');
          setStatusMessage(null);
        } else {
          const body = await res.json().catch(() => ({}) as { error?: string });
          doneRef.current = true;
          setStatus('error');
          setStatusMessage(body.error || 'VIN scanning is unavailable right now. Try Upload or Manual entry.');
        }
      } catch (err) {
        console.error(err);
        // Transient/network hiccup -- keep retrying on the next tick.
      } finally {
        scanningRef.current = false;
      }
    };

    const interval = setInterval(attempt, SCAN_INTERVAL_MS);
    attempt();
    return () => {
      doneRef.current = true;
      clearInterval(interval);
    };
  }, [ready, captureFrame]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Scan windshield VIN tag"
      style={{ position: 'fixed', inset: 0, zIndex: 1000, background: '#000', display: 'flex', flexDirection: 'column' }}
    >
      <div style={{ position: 'relative', flex: 1, overflow: 'hidden' }}>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />

        <div
          aria-hidden="true"
          className={status === 'scanning' ? 'vin-scan-pulse' : undefined}
          style={{
            position: 'absolute',
            left: '8%',
            right: '8%',
            top: '42%',
            height: '16%',
            border: `3px dashed ${status === 'error' ? 'var(--accent-red)' : 'var(--accent-orange)'}`,
            borderRadius: 8,
            boxShadow: '0 0 0 2000px rgba(0,0,0,0.45)',
          }}
        />
        <p
          role="status"
          style={{
            position: 'absolute',
            top: '20%',
            left: 0,
            right: 0,
            textAlign: 'center',
            color: '#fff',
            fontSize: '0.9rem',
            padding: '0 24px',
            textShadow: '0 1px 4px rgba(0,0,0,0.8)',
          }}
        >
          {statusMessage ?? (ready ? 'Hold the VIN tag inside the frame — scanning automatically…' : 'Starting camera…')}
        </p>

        {cameraError && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
            <p role="alert" style={{ color: '#fff', textAlign: 'center', background: 'rgba(15,23,42,0.9)', padding: 16, borderRadius: 12 }}>
              {cameraError}
            </p>
          </div>
        )}

        {status === 'error' && statusMessage && !cameraError && (
          <div style={{ position: 'absolute', left: 0, right: 0, bottom: 24, display: 'flex', justifyContent: 'center', padding: '0 24px' }}>
            <p role="alert" style={{ color: '#fff', textAlign: 'center', background: 'rgba(127,29,29,0.9)', padding: '10px 16px', borderRadius: 12 }}>
              {statusMessage}
            </p>
          </div>
        )}

        {torchSupported && (
          <button
            type="button"
            onClick={toggleTorch}
            aria-pressed={torchOn}
            aria-label="Toggle flash"
            style={{
              position: 'absolute',
              top: 16,
              right: 16,
              width: 48,
              height: 48,
              borderRadius: 24,
              border: 'none',
              background: torchOn ? 'var(--accent-orange)' : 'rgba(15,23,42,0.75)',
              color: '#fff',
              fontSize: '1.2rem',
              cursor: 'pointer',
            }}
          >
            {torchOn ? '⚡️' : '🔦'}
          </button>
        )}
      </div>

      <div style={{ padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000' }}>
        <button type="button" className="btn btn-secondary" style={{ width: 'auto', padding: '0 32px' }} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
