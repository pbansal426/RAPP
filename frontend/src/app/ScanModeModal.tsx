'use client';

interface ScanModeModalProps {
  onChooseWindshield: () => void;
  onChooseDoorJamb: () => void;
  onCancel: () => void;
}

export default function ScanModeModal({ onChooseWindshield, onChooseDoorJamb, onCancel }: ScanModeModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Choose VIN scan location"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(2, 6, 23, 0.92)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
    >
      <div style={{ maxWidth: 360, width: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <p style={{ color: 'var(--text-primary)', fontSize: '1.1rem', fontWeight: 700, textAlign: 'center' }}>
          Where is the VIN?
        </p>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center', marginBottom: 4 }}>
          The camera view is different for each location.
        </p>

        <button
          type="button"
          className="btn btn-primary"
          style={{ height: 'auto', minHeight: 68, flexDirection: 'column', gap: 2, padding: '10px 24px' }}
          onClick={onChooseWindshield}
        >
          <span>Windshield Tag</span>
          <span style={{ fontWeight: 400, fontSize: '0.8rem', opacity: 0.85 }}>
            Base of the driver-side windshield
          </span>
        </button>

        <button
          type="button"
          className="btn btn-secondary"
          style={{ height: 'auto', minHeight: 68, flexDirection: 'column', gap: 2, padding: '10px 24px' }}
          onClick={onChooseDoorJamb}
        >
          <span>Door Jamb Barcode</span>
          <span style={{ fontWeight: 400, fontSize: '0.8rem', opacity: 0.85 }}>
            Sticker inside the driver&apos;s door frame
          </span>
        </button>

        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
