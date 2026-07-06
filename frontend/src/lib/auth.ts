'use client';

import { useEffect, useState } from 'react';
import { api, ApiError } from './api';

const TOKEN_KEY = 'rapp_token';

export interface AuthUser {
  uid: string;
  email: string;
  displayName: string | null;
}

interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
}

interface AuthResponse {
  token: string;
  user: UserResponse;
}

function toAuthUser(user: UserResponse): AuthUser {
  return {
    uid: user.id,
    email: user.email,
    displayName: user.display_name,
  };
}

// Firebase's onAuthStateChanged gave every useAuthUser() instance a live
// stream of auth changes; a plain REST call doesn't, so we replicate that
// with a tiny pub/sub so logIn/logOut are reflected immediately by any
// mounted useAuthUser() consumer, not just after a fresh page load.
type Listener = (user: AuthUser | null) => void;
const listeners = new Set<Listener>();

function broadcast(user: AuthUser | null): void {
  listeners.forEach((listener) => listener(user));
}

function storeToken(token: string): void {
  if (typeof window !== 'undefined') localStorage.setItem(TOKEN_KEY, token);
}

// Magic-link auth: requesting a link doubles as signup (first request for
// an email creates the account) and login (every later request signs the
// same account back in) -- there's no separate signup/login distinction to
// make client-side.
export async function requestMagicLink(
  email: string,
  displayName?: string
): Promise<{ message: string; magicLink: string | null }> {
  const res = await api.post<{ message: string; magic_link: string | null }>(
    '/api/auth/request-link',
    { email, display_name: displayName ?? null }
  );
  return { message: res.message, magicLink: res.magic_link };
}

export async function verifyMagicLink(token: string): Promise<AuthUser> {
  const res = await api.post<AuthResponse>('/api/auth/verify-link', { token });
  storeToken(res.token);
  const user = toAuthUser(res.user);
  broadcast(user);
  return user;
}

export async function logOut(): Promise<void> {
  if (typeof window !== 'undefined') localStorage.removeItem(TOKEN_KEY);
  broadcast(null);
}

export async function updateAccount(displayName: string | null): Promise<AuthUser> {
  const res = await api.patch<UserResponse>('/api/auth/me', { display_name: displayName });
  const user = toAuthUser(res);
  broadcast(user);
  return user;
}

export function useAuthUser(): {
  user: AuthUser | null;
  loading: boolean;
  configured: boolean;
} {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const listener: Listener = (u) => setUser(u);
    listeners.add(listener);

    const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
    if (!token) {
      setLoading(false);
      return () => {
        listeners.delete(listener);
      };
    }
    api
      .get<UserResponse>('/api/auth/me')
      .then((u) => setUser(toAuthUser(u)))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
        }
        setUser(null);
      })
      .finally(() => setLoading(false));

    return () => {
      listeners.delete(listener);
    };
  }, []);

  // Account creation/login is backend-driven and always available now
  // (no external provider config required).
  return { user, loading, configured: true };
}
