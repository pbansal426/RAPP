export default function LayoutDiagram() {
  return (
    <div style={{ background: '#181824', borderRadius: 'var(--radius-sm)', padding: '16px', display: 'flex', justifyContent: 'center', border: '1px solid var(--border)', marginTop: 10 }}>
      <svg width="260" height="140" viewBox="0 0 280 150" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="20" width="260" height="110" rx="10" fill="#242436" stroke="#4a4a68" strokeWidth="2" />
        {[0, 1, 2, 3].map((idx) => {
          const cx = 45 + idx * 63;
          return (
            <g key={idx}>
              <circle cx={cx} cy="75" r="22" fill="#181824" stroke="#ff9f0b" strokeWidth="2" />
              <rect x={cx - 6} y="62" width="12" height="26" rx="2" fill="#4a4a68" />
              <text x={cx} y="115" fill="var(--text-secondary)" fontSize="10" textAnchor="middle">CYL {idx + 1}</text>
            </g>
          );
        })}
        <path d="M 45 75 L 234 75" stroke="#3b82f6" strokeWidth="2" strokeDasharray="4" />
        <text x="140" y="45" fill="#4ade80" fontSize="9" fontWeight="bold" textAnchor="middle">TIGHTENING SEQUENCE: 1 → 3 → 4 → 2</text>
      </svg>
    </div>
  );
}
