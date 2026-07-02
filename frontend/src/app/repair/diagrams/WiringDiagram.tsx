export default function WiringDiagram() {
  return (
    <div style={{ background: '#181824', borderRadius: 'var(--radius-sm)', padding: '16px', display: 'flex', justifyContent: 'center', border: '1px solid var(--border)', marginTop: 10 }}>
      <svg width="260" height="140" viewBox="0 0 280 150" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="15" y="15" width="70" height="120" rx="6" fill="#242436" stroke="#3b82f6" strokeWidth="2" />
        <text x="50" y="70" fill="#3b82f6" fontSize="10" fontWeight="bold" textAnchor="middle">ECM</text>
        <text x="50" y="85" fill="#3b82f6" fontSize="8" textAnchor="middle">(PIN OUT)</text>

        <path d="M 85 45 L 180 45" stroke="#ef4444" strokeWidth="2" />
        <path d="M 85 75 L 180 75" stroke="#10b981" strokeWidth="2" />
        <path d="M 85 105 L 180 105" stroke="#fbbf24" strokeWidth="2" />

        <rect x="180" y="35" width="85" height="20" rx="4" fill="#242436" stroke="#4a4a68" />
        <text x="222" y="48" fill="var(--text-primary)" fontSize="9" textAnchor="middle">PIN 1: Ignition</text>

        <rect x="180" y="65" width="85" height="20" rx="4" fill="#242436" stroke="#4a4a68" />
        <text x="222" y="78" fill="var(--text-primary)" fontSize="9" textAnchor="middle">PIN 2: Ground</text>

        <rect x="180" y="95" width="85" height="20" rx="4" fill="#242436" stroke="#4a4a68" />
        <text x="222" y="108" fill="var(--text-primary)" fontSize="9" textAnchor="middle">PIN 3: Trigger</text>
      </svg>
    </div>
  );
}
