'use client';

import { saveRepair, type SavedRepairInput } from './repairs';

const PENDING_KEY_PREFIX = 'rapp_pending_save_';

// Guards against completing the same vin's pending save twice concurrently
// -- e.g. React 18 StrictMode double-invokes effects in dev, and the two
// calls would otherwise both read the pending entry before either finished
// removing it, saving the same repair twice. Deliberately in-memory (not
// persisted): it only needs to dedupe within one page load, not survive a
// reload -- a reload legitimately should retry if the previous attempt
// never reached the "remove from localStorage" step.
const inFlight = new Set<string>();

// Magic-link auth can't authenticate synchronously (requesting a link
// doesn't hand back a session until the user clicks it, possibly in
// another tab), so a "save to garage" action taken while signed out has to
// be deferred: stash the payload now, complete the actual saveRepair()
// call later once a session exists -- see completePendingSave().
export function storePendingSave(vin: string, payload: SavedRepairInput): void {
  localStorage.setItem(`${PENDING_KEY_PREFIX}${vin}`, JSON.stringify(payload));
}

// Called from any page that both requires auth and might be visited right
// after the user clicks their magic link (currently /repair, whenever a
// signed-in user loads it) -- completes the deferred save if one is
// pending for this vin. Returns true if a save was completed.
export async function completePendingSave(vin: string): Promise<boolean> {
  if (inFlight.has(vin)) return false;
  const raw = localStorage.getItem(`${PENDING_KEY_PREFIX}${vin}`);
  if (!raw) return false;
  inFlight.add(vin);
  try {
    const payload = JSON.parse(raw) as SavedRepairInput;
    await saveRepair(payload);
    localStorage.removeItem(`${PENDING_KEY_PREFIX}${vin}`);
    return true;
  } catch {
    return false;
  } finally {
    inFlight.delete(vin);
  }
}

// Clicking a magic link redirects to /garage by default (not back to
// whichever page requested it), so /garage can't rely on knowing a single
// vin the way /repair does -- it scans every pending-save entry instead.
// Returns true if at least one save was completed.
export async function completeAllPendingSaves(): Promise<boolean> {
  const vins = Object.keys(localStorage)
    .filter((key) => key.startsWith(PENDING_KEY_PREFIX))
    .map((key) => key.slice(PENDING_KEY_PREFIX.length));
  let any = false;
  for (const vin of vins) {
    const completed = await completePendingSave(vin);
    any = any || completed;
  }
  return any;
}
