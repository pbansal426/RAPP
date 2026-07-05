'use client';

import { useEffect, useRef, useState } from 'react';
import type { IScannerControls } from '@zxing/browser';
import { extractVinFromBarcodeText } from '@/lib/barcodeVin';

interface DoorJambScanModalProps {
  onDecoded: (vin: string) => void;
  onCancel: () => void;
}

// Barcode decoding runs entirely client-side (via @zxing/browser) — no
// Gemini call is made anywhere in this flow, since a barcode is an exact
// symbol decode, not something that benefits from a vision model.
export default function DoorJambScanModal({ onDecoded, onCancel }: DoorJambScanModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const controlsRef = useRef<IScannerControls | null>(null);
  const decodedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [torchSupported, setTorchSupported] = useState(false);
  const [torchOn, setTorchOn] = useState(false);

  useEffect(() => {
    let cancelled = false;

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Camera access is not supported in this browser.');
      return;
    }

    (async () => {
      try {
        const { BrowserMultiFormatReader, BrowserCodeReader, BarcodeFormat } = await import('@zxing/browser');
        const { DecodeHintType } = await import('@zxing/library');

        // Door-jamb VIN stickers are 1D barcodes — Code 39 is the SAE/DOT
        // convention, Code 128/93 show up on some manufacturers' labels.
        // Restricting formats makes the decoder lock on faster and skips
        // QR/other codes that might share the frame (e.g. a tire label).
        const hints = new Map();
        hints.set(DecodeHintType.POSSIBLE_FORMATS, [
          BarcodeFormat.CODE_39,
          BarcodeFormat.CODE_128,
          BarcodeFormat.CODE_93,
        ]);
        const reader = new BrowserMultiFormatReader(hints);

        const controls = await reader.decodeFromConstraints(
          { video: { facingMode: { ideal: 'environment' } }, audio: false },
          videoRef.current ?? undefined,
          (result) => {
            if (decodedRef.current || !result) return;
            const vin = extractVinFromBarcodeText(result.getText());
            if (vin) {
              decodedRef.current = true;
              controlsRef.current?.stop();
              onDecoded(vin);
            }
          },
        );

        if (cancelled) {
          controls.stop();
          return;
        }
        controlsRef.current = controls;
        if (decodedRef.current) {
          controls.stop();
          return;
        }

        const stream = videoRef.current?.srcObject as MediaStream | undefined;
        const track = stream?.getVideoTracks()[0];
        if (track) {
          setTorchSupported(BrowserCodeReader.mediaStreamIsTorchCompatibleTrack(track));
        }
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setError('Could not access the camera. Check permissions, or use Upload / Manual entry instead.');
        }
      }
    })();

    return () => {
      cancelled = true;
      controlsRef.current?.stop();
    };
  }, [onDecoded]);

  const toggleTorch = async () => {
    const controls = controlsRef.current;
    if (!controls?.switchTorch) return;
    try {
      const next = !torchOn;
      await controls.switchTorch(next);
      setTorchOn(next);
    } catch (err) {
      console.error('Torch toggle failed', err);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Scan door jamb VIN barcode"
      style={{ position: 'fixed', inset: 0, zIndex: 1000, background: '#000', display: 'flex', flexDirection: 'column' }}
    >
      <div style={{ position: 'relative', flex: 1, overflow: 'hidden' }}>
        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
        <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />

        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            left: '10%',
            right: '10%',
            top: '38%',
            height: '24%',
            border: '3px dashed var(--accent-orange)',
            borderRadius: 8,
            boxShadow: '0 0 0 2000px rgba(0,0,0,0.45)',
          }}
        />
        <p
          style={{
            position: 'absolute',
            top: '16%',
            left: 0,
            right: 0,
            textAlign: 'center',
            color: '#fff',
            fontSize: '0.9rem',
            padding: '0 24px',
            textShadow: '0 1px 4px rgba(0,0,0,0.8)',
          }}
        >
          Hold steady over the barcode
        </p>

        {error && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
            <p role="alert" style={{ color: '#fff', textAlign: 'center', background: 'rgba(15,23,42,0.9)', padding: 16, borderRadius: 12 }}>
              {error}
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

      <div style={{ padding: 20, display: 'flex', justifyContent: 'center', background: '#000' }}>
        <button type="button" className="btn btn-secondary" style={{ width: 'auto', padding: '0 32px' }} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
