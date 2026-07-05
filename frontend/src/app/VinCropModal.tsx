'use client';

import { useRef, useState } from 'react';

interface VinCropModalProps {
  imageUrl: string;
  onConfirm: (canvas: HTMLCanvasElement) => void;
  onCancel: () => void;
}

interface Rect {
  x: number; // fraction of displayed image, 0-1
  y: number;
  width: number;
  height: number;
}

const DEFAULT_RECT: Rect = { x: 0.1, y: 0.35, width: 0.8, height: 0.3 };

// Otsu's method: finds the grayscale threshold that best splits the image
// into two classes (tag vs. background) without a hand-picked magic number,
// since lighting/exposure varies a lot across phone photos.
function otsuThreshold(histogram: number[], total: number): number {
  let sumAll = 0;
  for (let i = 0; i < 256; i++) sumAll += i * histogram[i];

  let sumB = 0;
  let weightB = 0;
  let maxVariance = 0;
  let threshold = 128;

  for (let t = 0; t < 256; t++) {
    weightB += histogram[t];
    if (weightB === 0) continue;
    const weightF = total - weightB;
    if (weightF === 0) break;

    sumB += t * histogram[t];
    const meanB = sumB / weightB;
    const meanF = (sumAll - sumB) / weightF;
    const variance = weightB * weightF * (meanB - meanF) * (meanB - meanF);
    if (variance > maxVariance) {
      maxVariance = variance;
      threshold = t;
    }
  }
  return threshold;
}

function preprocess(canvas: HTMLCanvasElement): void {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const { data } = imageData;
  const gray = new Uint8ClampedArray(data.length / 4);

  for (let i = 0; i < gray.length; i++) {
    const r = data[i * 4];
    const g = data[i * 4 + 1];
    const b = data[i * 4 + 2];
    gray[i] = 0.299 * r + 0.587 * g + 0.114 * b;
  }

  const histogram = new Array(256).fill(0);
  for (let i = 0; i < gray.length; i++) histogram[gray[i]]++;
  const threshold = otsuThreshold(histogram, gray.length);

  for (let i = 0; i < gray.length; i++) {
    const v = gray[i] > threshold ? 255 : 0;
    data[i * 4] = v;
    data[i * 4 + 1] = v;
    data[i * 4 + 2] = v;
  }
  ctx.putImageData(imageData, 0, 0);
}

export default function VinCropModal({ imageUrl, onConfirm, onCancel }: VinCropModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [rect, setRect] = useState<Rect>(DEFAULT_RECT);
  const dragStart = useRef<{ x: number; y: number } | null>(null);

  const getRelativePoint = (e: React.PointerEvent): { x: number; y: number } => {
    const box = containerRef.current!.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (e.clientX - box.left) / box.width)),
      y: Math.min(1, Math.max(0, (e.clientY - box.top) / box.height)),
    };
  };

  const handlePointerDown = (e: React.PointerEvent) => {
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    const p = getRelativePoint(e);
    dragStart.current = p;
    setRect({ x: p.x, y: p.y, width: 0, height: 0 });
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragStart.current) return;
    const p = getRelativePoint(e);
    const start = dragStart.current;
    setRect({
      x: Math.min(start.x, p.x),
      y: Math.min(start.y, p.y),
      width: Math.abs(p.x - start.x),
      height: Math.abs(p.y - start.y),
    });
  };

  const handlePointerUp = () => {
    dragStart.current = null;
  };

  const handleUseFullPhoto = () => {
    setRect({ x: 0, y: 0, width: 1, height: 1 });
  };

  const handleConfirm = () => {
    const img = imgRef.current;
    if (!img) return;
    const r = rect.width > 0.02 && rect.height > 0.02 ? rect : { x: 0, y: 0, width: 1, height: 1 };

    const sx = r.x * img.naturalWidth;
    const sy = r.y * img.naturalHeight;
    const sw = r.width * img.naturalWidth;
    const sh = r.height * img.naturalHeight;

    // Upscale small crops so character strokes are thick enough for OCR,
    // but cap it so huge photos don't produce an unreasonably large canvas.
    const targetWidth = Math.min(2400, Math.max(1200, sw * 2));
    const scale = targetWidth / sw;

    const canvas = document.createElement('canvas');
    canvas.width = Math.round(sw * scale);
    canvas.height = Math.round(sh * scale);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
    preprocess(canvas);

    onConfirm(canvas);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Crop VIN tag photo"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(2, 6, 23, 0.92)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        gap: 16,
      }}
    >
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', textAlign: 'center', maxWidth: 480 }}>
        Drag a box tightly around just the VIN text for the best free-OCR result — cropping out background clutter matters more than anything else.
      </p>

      <div
        ref={containerRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        style={{
          position: 'relative',
          maxWidth: '90vw',
          maxHeight: '60vh',
          touchAction: 'none',
          cursor: 'crosshair',
          lineHeight: 0,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Captured VIN tag photo — drag to crop"
          style={{ maxWidth: '90vw', maxHeight: '60vh', display: 'block', userSelect: 'none' }}
          draggable={false}
        />
        <div
          style={{
            position: 'absolute',
            left: `${rect.x * 100}%`,
            top: `${rect.y * 100}%`,
            width: `${rect.width * 100}%`,
            height: `${rect.height * 100}%`,
            border: '2px solid var(--accent-orange)',
            background: 'rgba(249, 115, 22, 0.12)',
            boxShadow: '0 0 0 2000px rgba(2, 6, 23, 0.55)',
            pointerEvents: 'none',
          }}
        />
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
        <button type="button" className="btn btn-secondary" style={{ width: 'auto', padding: '0 18px', minHeight: 48 }} onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn btn-secondary" style={{ width: 'auto', padding: '0 18px', minHeight: 48 }} onClick={handleUseFullPhoto}>
          Use Whole Photo
        </button>
        <button type="button" className="btn btn-primary" style={{ width: 'auto', padding: '0 18px', minHeight: 48 }} onClick={handleConfirm}>
          Scan Cropped Area →
        </button>
      </div>
    </div>
  );
}
