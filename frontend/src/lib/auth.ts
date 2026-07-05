'use client';

import { useEffect, useState } from 'react';
import { api, ApiError } from './api';

const TOKEN_KEY = 'rapp_token';

export interface AuthUser {
  uid: string;
  email: string;
  displayName: string | null;
  emailVerified: boolean;
}

interface UserResponse {
  id: string;
  email: string;
  display_name: string | null;
  email_verified: boolean;
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
    emailVerified: user.email_verified,
  };
}

// Firebase's onAuthStateChanged gave every useAuthUser() instance a live
// stream of auth changes; a plain REST call doesn't, so we replicate that
// with a tiny pub/sub so signUp/logIn/logOut are reflected immediately by
// any mounted useAuthUser() consumer, not just after a fresh page load.
type Listener = (user: AuthUser | null) => void;
const listeners = new Set<Listener>();

function broadcast(user: AuthUser | null): void {
  listeners.forEach((listener) => listener(user));
}

function storeToken(token: string): void {
  if (typeof window !== 'undefined') localStorage.setItem(TOKEN_KEY, token);
}

export async function signUp(
  email: string,
  password: string,
  displayName?: string
): Promise<AuthUser> {
  const res = await api.post<AuthResponse>('/api/auth/signup', {
    email,
    password,
    display_name: displayName ?? null,
  });
  storeToken(res.token);
  const user = toAuthUser(res.user);
  broadcast(user);
  return user;
}

export async function logIn(email: string, password: string): Promise<AuthUser> {
  const res = await api.post<AuthResponse>('/api/auth/login', { email, password });
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

export async function forgotPassword(email: string): Promise<{ message: string; resetLink: string | null }> {
  const res = await api.post<{ message: string; reset_link: string | null }>(
    '/api/auth/forgot-password',
    { email }
  );
  return { message: res.message, resetLink: res.reset_link };
}

export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  return api.post<{ message: string }>('/api/auth/reset-password', {
    token,
    new_password: newPassword,
  });
}

export async function sendVerification(): Promise<{ message: string; verifyLink: string }> {
  const res = await api.post<{ message: string; verify_link: string }>(
    '/api/auth/send-verification',
    {}
  );
  return { message: res.message, verifyLink: res.verify_link };
}

export async function verifyEmail(token: string): Promise<AuthUser> {
  const res = await api.post<UserResponse>('/api/auth/verify-email', { token });
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
