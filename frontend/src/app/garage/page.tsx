'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { logIn, signUp, logOut, useAuthUser } from '@/lib/auth';
import { listRepairs, type SavedRepair } from '@/lib/repairs';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

export default function GaragePage() {
  const router = useRouter();
  const { user, loading, configured } = useAuthUser();
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [repairs, setRepairs] = useState<SavedRepair[] | null>(null);

  useEffect(() => {
    if (!user) { setRepairs(null); return; }
    listRepairs(user.uid).then(setRepairs).catch(() => setRepairs([]));
  }, [user]);

  const handleAuthSubmit = async () => {
    if (!email.trim() || !password.trim()) return;
    setSubmitting(true);
    setAuthError(null);
    try {
      if (mode === 'login') {
        await logIn(email.trim(), password);
      } else {
        await signUp(email.trim(), password, displayName.trim() || undefined);
      }
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setSubmitting(false);
    }
  };

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

      {configured && loading && (
        <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
          <div className="loading-spinner" style={{ margin: '0 auto' }} />
        </div>
      )}

      {configured && !loading && !user && (
        <div className="card">
          <p className="card-label">{mode === 'login' ? 'Log In' : 'Create Account'}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
            {mode === 'signup' && (
              <input className="input" type="text" placeholder="Name (optional)" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            )}
            <input className="input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <input className="input" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
            {authError && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{authError}</p>}
            <button className="btn btn-primary" onClick={handleAuthSubmit} disabled={submitting || !email.trim() || !password.trim()}>
              {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Please wait…</> : mode === 'login' ? 'Log In' : 'Create Account'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setAuthError(null); }}
            >
              {mode === 'login' ? 'New here? Create an account' : 'Already have an account? Log in'}
            </button>
          </div>
        </div>
      )}

      {configured && !loading && user && (
        <>
          <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="text-muted text-sm">Signed in as <strong style={{ color: 'var(--text-primary)' }}>{user.email}</strong></span>
            <button className="btn btn-secondary" style={{ width: 'auto', padding: '0 16px' }} onClick={() => logOut()}>Log Out</button>
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
