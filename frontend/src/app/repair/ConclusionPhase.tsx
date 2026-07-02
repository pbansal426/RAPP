import { FlagIcon, CheckCircleIcon } from '@/app/sharedIcons';

interface ConclusionPhaseProps {
  symptoms: string;
}

export default function ConclusionPhase({ symptoms }: ConclusionPhaseProps) {
  const codes = Array.from(new Set((symptoms.match(/\b[PBCU]\d{4}\b/gi) ?? []).map((c) => c.toUpperCase())));

  return (
    <div className="phase-section" data-testid="conclusion-phase">
      <div className="phase-header"><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><FlagIcon size={18} style={{ color: '#4ade80' }} /><span>Phase 5: Conclusion &amp; Verification</span></span></div>
      <div className="card" style={{ margin: 0 }}>
        <p style={{ fontWeight: 700, marginBottom: 8 }}>Clear the Code(s) &amp; Confirm the Fix</p>
        <p className="text-muted" style={{ marginBottom: 14 }}>
          {codes.length > 0 ? (
            <>Using your OBD-II scanner, select <strong>Clear Codes / Erase</strong> and confirm {codes.map((c) => <span key={c} className="tool-chip">{c}</span>)} no longer returns after a full drive cycle.</>
          ) : (
            <>Using your OBD-II scanner, select <strong>Clear Codes / Erase</strong> and confirm no fault codes return after a full drive cycle.</>
          )}
        </p>

        <p style={{ fontWeight: 700, marginBottom: 8 }}>Test Drive Protocol</p>
        <ul style={{ paddingLeft: 20, marginBottom: 14, fontSize: '0.9rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <li>Idle in place for 2–3 minutes and confirm no warning lights return.</li>
          <li>Drive at low speed (under 30 mph) for 5 minutes, listening/feeling for the original symptom.</li>
          <li>If clear, take a normal 10–15 minute mixed-speed drive to complete a full monitor cycle.</li>
        </ul>

        <p style={{ fontWeight: 700, marginBottom: 8 }}>Watch For (Next 50–100 Miles)</p>
        <ul style={{ paddingLeft: 20, marginBottom: 14, fontSize: '0.9rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <li>Any recurrence of the original symptom or new dashboard warning lights.</li>
          <li>Unusual smells, fluid spots under the vehicle, or new noises.</li>
          <li>Loose panels or fasteners settling — a quick re-torque check after 50 miles is good practice.</li>
        </ul>

        <div className="tool-match-pill" style={{ display: 'inline-flex' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <CheckCircleIcon size={16} style={{ color: '#4ade80' }} />
            <span>You&apos;re done! If the symptom hasn&apos;t returned after your test drive, the repair is complete.</span>
          </span>
        </div>
      </div>
    </div>
  );
}
