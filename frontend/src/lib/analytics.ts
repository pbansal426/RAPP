'use client';

import posthog from 'posthog-js';

const KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? 'https://us.i.posthog.com';

let initialized = false;

/** Idempotent init. No-ops entirely if NEXT_PUBLIC_POSTHOG_KEY is unset. */
export function initAnalytics(): void {
  if (initialized || !KEY || typeof window === 'undefined') return;
  posthog.init(KEY, { api_host: HOST, capture_pageview: false });
  initialized = true;
}

/** Fire an event. No-ops if PostHog was never initialized (key unset). */
export function track(event: string, properties?: Record<string, unknown>): void {
  if (!initialized) return;
  posthog.capture(event, properties);
}
