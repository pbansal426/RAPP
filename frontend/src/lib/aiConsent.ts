// Session-scoped consent gate for operations that spend the live Gemini API
// key -- repair-guide generation and the repair chat assistant. Gemini usage is
// BLOCKED BY DEFAULT at the start of every browser session: the user must
// explicitly approve once, after which further AI calls this session proceed
// without re-prompting. Consent lives in sessionStorage (not localStorage) so
// it resets when the tab/session ends -- i.e. "off by default" on every fresh
// visit, matching the owner's requirement that nothing touches their Gemini
// quota without permission.
//
// This is the UI-side companion to the agent-side rule in memory
// `gemini-key-usage-blocked`; both exist so the paid/quota-limited key
// (free tier ~20 requests/day) is never spent silently.

const CONSENT_KEY = 'rapp_ai_consent';

/** True once the user has approved Gemini usage this browser session. */
export function hasAiConsent(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return window.sessionStorage.getItem(CONSENT_KEY) === 'granted';
  } catch {
    return false;
  }
}

/** Record consent for the rest of this session. */
export function grantAiConsent(): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(CONSENT_KEY, 'granted');
  } catch {
    /* sessionStorage unavailable (e.g. hardened private mode) -- no-op; the
       caller then simply keeps treating the session as un-consented. */
  }
}

/** Clear consent (e.g. a "stop using AI" affordance). */
export function revokeAiConsent(): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(CONSENT_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Ensure the user has approved a Gemini-spending action, prompting once per
 * session if they haven't. Returns true if the action may proceed.
 *
 * `action` is a short human phrase completing "This will use AI to ___",
 * e.g. "generate your step-by-step repair guide".
 */
export function confirmAiUsage(action: string): boolean {
  if (hasAiConsent()) return true;
  if (typeof window === 'undefined') return false;
  const ok = window.confirm(
    `This will use AI to ${action}.\n\n` +
      'It sends a request to the Gemini API, which uses this app’s API ' +
      'quota/credits (the free tier is limited to roughly 20 requests per day). ' +
      'Continue?'
  );
  if (ok) grantAiConsent();
  return ok;
}
