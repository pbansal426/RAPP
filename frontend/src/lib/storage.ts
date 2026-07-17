/**
 * Safe localStorage JSON accessor.
 *
 * Reading `JSON.parse(localStorage.getItem(key))` bare is a latent white-screen:
 * a truncated / malformed / half-written entry throws `SyntaxError` during render
 * and takes the whole page down. `safeGetJson` returns a typed fallback instead of
 * throwing on SSR, a missing key, or any parse error.
 */
export function safeGetJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  const raw = window.localStorage.getItem(key);
  if (raw == null) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    if (process.env.NODE_ENV !== 'production') {
      console.warn(`[safeGetJson] malformed JSON for key "${key}", using fallback`);
    }
    return fallback;
  }
}
