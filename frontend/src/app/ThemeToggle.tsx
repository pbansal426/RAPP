'use client';

import { useTheme, type ThemePreference } from '@/lib/theme';

const OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
];

export default function ThemeToggle() {
  const { preference, setPreference } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      style={{
        display: 'inline-flex',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: '100px',
        padding: 2,
        gap: 2,
      }}
    >
      {OPTIONS.map((opt) => {
        const active = preference === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            data-testid={`theme-toggle-${opt.value}`}
            onClick={() => setPreference(opt.value)}
            style={{
              minHeight: 32,
              padding: '0 12px',
              borderRadius: '100px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 700,
              background: active ? 'var(--accent-orange)' : 'transparent',
              color: active ? '#fff' : 'var(--text-secondary)',
              transition: 'background var(--transition), color var(--transition)',
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
