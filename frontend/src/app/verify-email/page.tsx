'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { verifyMagicLink } from '@/lib/auth';
import { AppLogoMarkIcon, CheckCircleIcon } from '@/app/sharedIcons';

function VerifyLinkHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [status, setStatus] = useState<'pending' | 'success' | 'error'>('pending');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setError('This sign-in link is missing its token.');
      return;
    }
    verifyMagicLink(token)
      .then(() => {
        setStatus('success');
        router.replace(searchParams.get('next') || '/garage');
      })
      .catch((err) => {
        setStatus('error');
        setError(err instanceof Error ? err.message : 'This sign-in link is invalid or has expired.');
      });
  }, [token, router, searchParams]);

  return (
    <main className="page">
      <header className="page-header">
        <div className="logo"><AppLogoMarkIcon size={20} /><span>RAPP</span></div>
        <h1 className="page-title">Signing You In</h1>
      </header>

      <div className="card" style={{ textAlign: 'center' }}>
        {status === 'pending' && <div className="loading-spinner" style={{ margin: '0 auto' }} />}
        {status === 'success' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
            <CheckCircleIcon size={28} style={{ color: '#4ade80' }} />
            <p style={{ fontWeight: 700 }}>Signed in — taking you to your garage…</p>
          </div>
        )}
        {status === 'error' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
            <p style={{ color: 'var(--accent-red)' }}>{error}</p>
            <a href="/signin" className="btn btn-primary" style={{ width: 'auto', padding: '0 18px' }}>Request a new link →</a>
          </div>
        )}
      </div>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="loading-spinner" />
      </main>
    }>
      <VerifyLinkHandler />
    </Suspense>
  );
}
