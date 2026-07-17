'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

// Magic-link auth unifies signup and login -- there's no separate signup
// flow anymore. This route is kept only because it may be linked/bookmarked
// from before; it just forwards to /signin with the same `next` param.
function SignupRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const next = searchParams.get('next');
    const ref = searchParams.get('ref');
    const params = new URLSearchParams();
    if (next) params.set('next', next);
    if (ref) params.set('ref', ref);
    const qs = params.toString();
    router.replace(qs ? `/signin?${qs}` : '/signin');
  }, [router, searchParams]);

  return (
    <main className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="loading-spinner" />
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
      <SignupRedirect />
    </Suspense>
  );
}
