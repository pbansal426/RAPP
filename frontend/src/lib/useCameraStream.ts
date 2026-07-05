'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface UseCameraStreamResult {
  videoRef: React.RefObject<HTMLVideoElement>;
  ready: boolean;
  error: string | null;
  torchSupported: boolean;
  torchOn: boolean;
  toggleTorch: () => Promise<void>;
  captureFrame: (quality?: number) => Promise<Blob | null>;
}

// Live rear-camera preview for the windshield-tag capture flow. Door-jamb
// barcode scanning manages its own stream via @zxing/browser's
// decodeFromConstraints instead of this hook, since that library already
// owns the full stream lifecycle for its continuous decode loop.
export function useCameraStream(): UseCameraStreamResult {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
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
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }

        // Dynamically imported so the windshield-only path never pulls in
        // the barcode-decode chunk unless a scan modal is actually opened.
        const { BrowserCodeReader } = await import('@zxing/browser');
        const track = stream.getVideoTracks()[0];
        if (track && !cancelled) {
          setTorchSupported(BrowserCodeReader.mediaStreamIsTorchCompatibleTrack(track));
        }
        if (!cancelled) setReady(true);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setError('Could not access the camera. Check permissions, or use Upload / Manual entry instead.');
        }
      }
    })();

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, []);

  const toggleTorch = useCallback(async () => {
    const track = streamRef.current?.getVideoTracks()[0];
    if (!track) return;
    try {
      const { BrowserCodeReader } = await import('@zxing/browser');
      const next = !torchOn;
      await BrowserCodeReader.mediaStreamSetTorch(track, next);
      setTorchOn(next);
    } catch (err) {
      console.error('Torch toggle failed', err);
    }
  }, [torchOn]);

  const captureFrame = useCallback(async (quality = 0.92): Promise<Blob | null> => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return null;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), 'image/jpeg', quality));
  }, []);

  return { videoRef, ready, error, torchSupported, torchOn, toggleTorch, captureFrame };
}
