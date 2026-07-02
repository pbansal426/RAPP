const stroke = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

export function HandToolsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M14.5 3.5 12 6l6 6 2.5-2.5a3.5 3.5 0 0 0-4.9-4.9L14.5 3.5z" />
      <path d="M12 6 4 14a2.4 2.4 0 0 0 3.4 3.4L15 9.6" />
      <path d="M4.5 17.5 3 21l3.5-1.5" />
    </svg>
  );
}

export function SocketSetIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 4v3M12 17v3M4 12h3M17 12h3M6.3 6.3l2.1 2.1M15.6 15.6l2.1 2.1M6.3 17.7l2.1-2.1M15.6 8.4l2.1-2.1" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

export function TorqueWrenchIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M3 12h9" />
      <circle cx="17" cy="12" r="4" />
      <path d="M8 9v6M12 10v4" />
    </svg>
  );
}

export function JackStandsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M6 20 12 5l6 15" />
      <path d="M4 20h16" />
      <path d="M9 13h6" />
    </svg>
  );
}

export function MultimeterIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <rect x="4" y="3" width="16" height="14" rx="2" />
      <path d="M12 7v4l3 2" />
      <path d="M9 21h6M12 17v4" />
    </svg>
  );
}

export function ObdScannerIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <rect x="3" y="6" width="14" height="9" rx="1.5" />
      <path d="M7 20h6M9 15v5M13 15v3" />
      <path d="M17 9h3l1 3-1 3h-3" />
    </svg>
  );
}

export function SafetyGlovesIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M6 21c-1.5 0-2.5-1.2-2.5-2.6V11a1.6 1.6 0 0 1 3.2 0v3" />
      <path d="M6.7 11V6.4a1.5 1.5 0 0 1 3 0V11" />
      <path d="M9.7 11V5.6a1.5 1.5 0 0 1 3 0V11" />
      <path d="M12.7 11V6.4a1.5 1.5 0 0 1 3 0V14c0 3.5-2 7-6 7" />
    </svg>
  );
}

export function PenetratingOilIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" {...stroke} aria-hidden="true">
      <path d="M9 3h4v2.8l1.6 2A2 2 0 0 1 15 9v10a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2V9a2 2 0 0 1 .4-1.2L11 5.8V3z" />
      <path d="M9 12h4" />
      <path d="M18 8c1 1 1.5 2 1.5 3s-.7 1.5-1.5 1.5S17 12 17 11" />
    </svg>
  );
}
