'use client';

import { collection, addDoc, getDocs, query, orderBy, serverTimestamp } from 'firebase/firestore';
import { getFirebaseDb } from './firebase';

export interface SavedRepairInput {
  vin: string;
  year?: string;
  make?: string;
  model?: string;
  engine?: string;
  symptoms: string;
}

export interface SavedRepair extends SavedRepairInput {
  id: string;
  savedAt: string | null;
}

export async function saveRepair(uid: string, repair: SavedRepairInput): Promise<void> {
  const db = getFirebaseDb();
  if (!db) throw new Error('Firebase is not configured.');
  await addDoc(collection(db, 'users', uid, 'repairs'), {
    ...repair,
    savedAt: serverTimestamp(),
  });
}

export async function listRepairs(uid: string): Promise<SavedRepair[]> {
  const db = getFirebaseDb();
  if (!db) return [];
  const q = query(collection(db, 'users', uid, 'repairs'), orderBy('savedAt', 'desc'));
  const snap = await getDocs(q);
  return snap.docs.map((d) => {
    const data = d.data();
    return {
      id: d.id,
      vin: data.vin,
      year: data.year,
      make: data.make,
      model: data.model,
      engine: data.engine,
      symptoms: data.symptoms,
      savedAt: data.savedAt?.toDate ? data.savedAt.toDate().toLocaleDateString() : null,
    } as SavedRepair;
  });
}
