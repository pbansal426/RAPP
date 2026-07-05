'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { logIn } from '@/lib/auth';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await logIn(email.trim(), password);
      router.push(searchParams.get('next') || '/garage');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not log in. Please try again.');
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
        <h1 className="page-title">Log In</h1>
        <p className="page-subtitle">Access your garage and saved repair guides.</p>
      </header>

      <form className="card" onSubmit={handleSubmit}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label htmlFor="signin-email" className="sr-only">Email</label>
          <input
            id="signin-email"
            className="input"
            type="email"
            placeholder="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <label htmlFor="signin-password" className="sr-only">Password</label>
          <input
            id="signin-password"
            className="input"
            type="password"
            placeholder="Password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{error}</p>}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting || !email.trim() || !password.trim()}
          >
            {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Logging in…</> : 'Log In'}
          </button>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
            <a href="/signup" className="text-muted text-sm" style={{ textDecoration: 'none' }}>
              New here? Create an account
            </a>
            <a href="/forgot-password" className="text-muted text-sm" style={{ textDecoration: 'none' }}>
              Forgot password?
            </a>
          </div>
        </div>
      </form>
    </main>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </main>
    }>
      <SignInForm />
    </Suspense>
  );
}
