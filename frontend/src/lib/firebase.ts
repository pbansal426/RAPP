'use client';

// Firebase Auth/Firestore have been fully replaced by the backend-driven
// auth + SQLAlchemy stack (see src/lib/auth.ts, src/lib/repairs.ts, and
// backend/routers/auth.py / backend/routers/repairs.py). This file is kept
// only as a compatibility shim for the isFirebaseConfigured() check a couple
// of presentational components still call -- account creation is now
// always available since it no longer depends on any external provider.
export function isFirebaseConfigured(): boolean {
  return true;
}
