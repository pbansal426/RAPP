'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { logOut, useAuthUser } from '@/lib/auth';
import { listRepairs, type SavedRepair } from '@/lib/repairs';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

export default function GaragePage() {
  const router = useRouter();
  const { user, loading, configured } = useAuthUser();
  const [repairs, setRepairs] = useState<SavedRepair[] | null>(null);

  useEffect(() => {
    if (!user) { setRepairs(null); return; }
    listRepairs().then(setRepairs).catch(() => setRepairs([]));
  }, [user]);

  useEffect(() => {
    if (configured && !loading && !user) router.push('/signin?next=/garage');
  }, [configured, loading, user, router]);

  return (
    <main className="page">
      <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start', marginBottom: 12 }}>
        <button
          className="btn btn-secondary"
          type="button"
          onClick={() => router.push('/')}
          style={{ padding: '6px 12px', fontSize: '0.875rem' }}
        >
          ← Home
        </button>
      </div>

      <header className="page-header">
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">My Garage</h1>
        <p className="page-subtitle">Your saved vehicles and repair guides.</p>
      </header>

      {!configured && (
        <div className="card">
          <p className="text-muted">Account features aren&apos;t configured for this environment yet — check back soon.</p>
        </div>
      )}

      {configured && (loading || !user) && (
        <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
          <div className="loading-spinner" style={{ margin: '0 auto' }} />
        </div>
      )}

      {configured && !loading && user && (
        <>
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="text-muted text-sm">Signed in as <strong style={{ color: 'var(--text-primary)' }}>{user.email}</strong></span>
            <div style={{ display: 'flex', gap: 10 }}>
              <a href="/settings" className="btn btn-secondary" style={{ width: 'auto', padding: '0 16px', textDecoration: 'none' }}>Settings</a>
              <button className="btn btn-secondary" style={{ width: 'auto', padding: '0 16px' }} onClick={() => logOut()}>Log Out</button>
            </div>
          </div>

          {repairs === null && (
            <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
              <div className="loading-spinner" style={{ margin: '0 auto' }} />
            </div>
          )}

          {repairs && repairs.length === 0 && (
            <div className="card">
              <p className="text-muted">No saved repairs yet. Unlock a repair guide and save it to see it here.</p>
            </div>
          )}

          {repairs && repairs.length > 0 && (
            <div className="checkbox-group">
              {repairs.map((r) => (
                <div key={r.id} className="card" style={{ margin: 0 }}>
                  <p style={{ fontWeight: 700, marginBottom: 4 }}>
                    {[r.year, r.make, r.model].filter(Boolean).join(' ') || r.vin}
                  </p>
                  <p className="text-muted text-sm" style={{ marginBottom: 4 }}>VIN: {r.vin}</p>
                  <p className="text-muted text-sm" style={{ marginBottom: 4 }}>{r.symptoms}</p>
                  {r.savedAt && <p className="text-muted text-sm">Saved {r.savedAt}</p>}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
