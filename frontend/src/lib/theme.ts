'use client';

import { useEffect, useState } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
type EffectiveTheme = 'light' | 'dark';

const STORAGE_KEY = 'rapp_theme';

// The frozen E2E suite asserts a dark body class on a fresh page load with
// no stored preference (tests/e2e-mvp-flow.spec.ts: "Dark mode as default")
// -- so a brand-new visitor with nothing in localStorage must resolve to
// dark, not to whatever their OS happens to prefer. "System" is still a
// real, live option once a user explicitly picks it.
const DEFAULT_PREFERENCE: ThemePreference = 'dark';

function resolveEffectiveTheme(preference: ThemePreference): EffectiveTheme {
  if (preference === 'system') {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  return preference;
}

function applyTheme(preference: ThemePreference): void {
  const effective = resolveEffectiveTheme(preference);
  document.documentElement.setAttribute('data-theme', effective);
}

// Inlined into a blocking <script> in layout.tsx so the resolved theme is
// set before first paint -- avoids a flash of the wrong theme on load.
// Keep this in sync with applyTheme()/resolveEffectiveTheme() above.
export const THEME_INIT_SCRIPT = `
(function () {
  try {
    var pref = localStorage.getItem('${STORAGE_KEY}') || '${DEFAULT_PREFERENCE}';
    var effective = pref === 'system'
      ? (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
      : pref;
    document.documentElement.setAttribute('data-theme', effective);
  } catch (e) {}
})();
`;

export function useTheme(): {
  preference: ThemePreference;
  setPreference: (pref: ThemePreference) => void;
} {
  // Starts as the same default the blocking init script falls back to, so
  // server and first-client-render markup agree (no hydration mismatch).
  // Deliberately does NOT re-run applyTheme() with this value on mount --
  // the blocking script in layout.tsx already set the *correct* data-theme
  // from localStorage before this component ever rendered. Reapplying a
  // stale default here would overwrite that correct value and reintroduce
  // exactly the flash the blocking script exists to prevent.
  const [preference, setPreferenceState] = useState<ThemePreference>(DEFAULT_PREFERENCE);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as ThemePreference | null;
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      setPreferenceState(stored);
    }
  }, []);

  useEffect(() => {
    if (preference !== 'system') return undefined;

    // Live-follow OS theme changes while "System" is selected. Doesn't
    // need to apply anything on attach -- either the blocking script or
    // setPreference already did, whichever led here.
    const mql = window.matchMedia('(prefers-color-scheme: light)');
    const onChange = () => applyTheme('system');
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [preference]);

  const setPreference = (pref: ThemePreference) => {
    localStorage.setItem(STORAGE_KEY, pref);
    applyTheme(pref);
    setPreferenceState(pref);
  };

  return { preference, setPreference };
}
