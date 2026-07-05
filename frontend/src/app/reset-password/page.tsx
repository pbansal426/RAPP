'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { resetPassword } from '@/lib/auth';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) return;
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reset your password. The link may have expired.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="page">
      <header className="page-header">
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">Set a New Password</h1>
      </header>

      <div className="card">
        {!token ? (
          <p style={{ color: 'var(--accent-red)' }}>
            This reset link is missing its token. Request a new one from the{' '}
            <a href="/forgot-password" style={{ color: 'var(--accent-orange)' }}>forgot password page</a>.
          </p>
        ) : done ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <p className="card-label">Password updated</p>
            <p className="text-muted text-sm">You can now log in with your new password.</p>
            <a href="/signin" className="btn btn-primary" style={{ width: 'auto', padding: '0 18px' }}>Log In →</a>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <label htmlFor="new-password" className="sr-only">New password</label>
            <input
              id="new-password"
              className="input"
              type="password"
              placeholder="New password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <label htmlFor="confirm-password" className="sr-only">Confirm new password</label>
            <input
              id="confirm-password"
              className="input"
              type="password"
              placeholder="Confirm new password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{error}</p>}
            <button type="submit" className="btn btn-primary" disabled={submitting || !password.trim()}>
              {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Updating…</> : 'Update Password'}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </main>
    }>
      <ResetPasswordForm />
    </Suspense>
  );
}
