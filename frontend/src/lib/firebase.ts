'use client';

import { type FirebaseApp, initializeApp, getApps } from 'firebase/app';
import { type Auth, getAuth, connectAuthEmulator } from 'firebase/auth';
import { type Firestore, getFirestore, connectFirestoreEmulator } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let db: Firestore | null = null;
let emulatorsConnected = false;

function isConfigured(): boolean {
  return typeof window !== 'undefined' && !!firebaseConfig.apiKey && !!firebaseConfig.projectId;
}

function getApp(): FirebaseApp | null {
  if (!isConfigured()) return null;
  if (!app) {
    app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
  }
  return app;
}

export function getFirebaseAuth(): Auth | null {
  const a = getApp();
  if (!a) return null;
  if (!auth) {
    auth = getAuth(a);
    maybeConnectEmulators();
  }
  return auth;
}

export function getFirebaseDb(): Firestore | null {
  const a = getApp();
  if (!a) return null;
  if (!db) {
    db = getFirestore(a);
    maybeConnectEmulators();
  }
  return db;
}

function maybeConnectEmulators() {
  if (emulatorsConnected) return;
  if (process.env.NEXT_PUBLIC_FIREBASE_USE_EMULATOR !== 'true') return;
  emulatorsConnected = true;
  try {
    if (auth) connectAuthEmulator(auth, 'http://localhost:9099', { disableWarnings: true });
    if (db) connectFirestoreEmulator(db, 'localhost', 8080);
  } catch {
    // already connected, ignore
  }
}

export function isFirebaseConfigured(): boolean {
  return isConfigured();
}
