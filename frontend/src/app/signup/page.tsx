'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { signUp } from '@/lib/auth';
import { AppLogoMarkIcon } from '@/app/sharedIcons';

function SignUpForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [displayName, setDisplayName] = useState('');
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
      await signUp(email.trim(), password, displayName.trim() || undefined);
      router.push(searchParams.get('next') || '/garage');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create your account. Please try again.');
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
        <h1 className="page-title">Create Account</h1>
        <p className="page-subtitle">Save your vehicles and repair guides for free.</p>
      </header>

      <form className="card" onSubmit={handleSubmit}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <label htmlFor="signup-name" className="sr-only">Name (optional)</label>
          <input
            id="signup-name"
            className="input"
            type="text"
            placeholder="Name (optional)"
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
          <label htmlFor="signup-email" className="sr-only">Email</label>
          <input
            id="signup-email"
            className="input"
            type="email"
            placeholder="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <label htmlFor="signup-password" className="sr-only">Password</label>
          <input
            id="signup-password"
            className="input"
            type="password"
            placeholder="Password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{error}</p>}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting || !email.trim() || !password.trim()}
          >
            {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Creating account…</> : 'Create Account'}
          </button>
          <a href="/signin" className="text-muted text-sm" style={{ textDecoration: 'none', textAlign: 'center', marginTop: 4 }}>
            Already have an account? Log in
          </a>
        </div>
      </form>
    </main>
  );
}

export default function SignUpPage() {
  return (
    <Suspense fallback={
      <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </main>
    }>
      <SignUpForm />
    </Suspense>
  );
}
