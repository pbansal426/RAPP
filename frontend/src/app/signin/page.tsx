'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { requestMagicLink } from '@/lib/auth';
import { AppLogoMarkIcon, CheckCircleIcon } from '@/app/sharedIcons';

function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);

  const next = searchParams.get('next');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await requestMagicLink(email.trim());
      setSent(true);
      setDevLink(res.magicLink ? `${res.magicLink}${next ? `&next=${encodeURIComponent(next)}` : ''}` : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send a sign-in link. Please try again.');
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
        <h1 className="page-title">Sign In</h1>
        <p className="page-subtitle">No password needed — we&apos;ll email you a one-click sign-in link.</p>
      </header>

      <div className="card">
        {sent ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center', textAlign: 'center' }}>
            <CheckCircleIcon size={28} style={{ color: '#4ade80' }} />
            <p style={{ fontWeight: 700 }}>Check your email</p>
            <p className="text-muted text-sm">We sent a sign-in link to {email.trim()}.</p>
            {devLink && (
              <>
                <p className="text-muted text-sm">No email provider is configured for this environment — use the link below directly.</p>
                <a href={devLink} className="btn btn-primary" style={{ width: 'auto', padding: '0 18px' }}>
                  Sign In →
                </a>
              </>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
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
              {error && <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{error}</p>}
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting || !email.trim()}
              >
                {submitting ? <><span className="loading-spinner" aria-hidden="true" /> Sending…</> : 'Send Sign-In Link'}
              </button>
              <p className="text-muted text-sm" style={{ textAlign: 'center', marginTop: 4 }}>
                New here? Just enter your email — your account is created automatically.
              </p>
            </div>
          </form>
        )}
      </div>
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
