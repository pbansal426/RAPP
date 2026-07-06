'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { logOut, updateAccount, useAuthUser } from '@/lib/auth';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading } = useAuthUser();
  const [displayName, setDisplayName] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [nameSaved, setNameSaved] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push('/signin?next=/settings');
  }, [loading, user, router]);

  useEffect(() => {
    if (user) setDisplayName(user.displayName ?? '');
  }, [user]);

  if (loading || !user) {
    return (
      <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </main>
    );
  }

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingName(true);
    setNameError(null);
    setNameSaved(false);
    try {
      await updateAccount(displayName.trim() || null);
      setNameSaved(true);
    } catch (err) {
      setNameError(err instanceof Error ? err.message : 'Could not save your name.');
    } finally {
      setSavingName(false);
    }
  };

  const handleLogOut = async () => {
    await logOut();
    router.push('/');
  };

  return (
    <main className="page">
      <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start', marginBottom: 12 }}>
        <button
          className="btn btn-secondary"
          type="button"
          onClick={() => router.push('/garage')}
          style={{ padding: '6px 12px', fontSize: '0.875rem' }}
        >
          ← My Garage
        </button>
      </div>

      <header className="page-header">
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">Account Settings</h1>
        <p className="page-subtitle">Manage your profile and account.</p>
      </header>

      <div className="card">
        <p className="card-label">Account</p>
        <p className="text-muted text-sm" style={{ marginBottom: 4 }}>
          Signed in as <strong style={{ color: 'var(--text-primary)' }}>{user.email}</strong>
        </p>
      </div>

      <form className="card" onSubmit={handleSaveName}>
        <p className="card-label">Display Name</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
          <label htmlFor="settings-name" className="sr-only">Display name</label>
          <input
            id="settings-name"
            className="input"
            type="text"
            placeholder="Name (optional)"
            value={displayName}
            onChange={(e) => { setDisplayName(e.target.value); setNameSaved(false); }}
          />
          {nameError && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{nameError}</p>}
          {nameSaved && <p className="text-muted text-sm">Saved.</p>}
          <button type="submit" className="btn btn-secondary" style={{ width: 'auto', padding: '0 18px' }} disabled={savingName}>
            {savingName ? <><span className="loading-spinner" aria-hidden="true" /> Saving…</> : 'Save Name'}
          </button>
        </div>
      </form>

      <div className="card">
        <p className="card-label">Session</p>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ width: 'auto', padding: '0 18px', marginTop: 8 }}
          onClick={handleLogOut}
        >
          Log Out
        </button>
      </div>
    </main>
  );
}
