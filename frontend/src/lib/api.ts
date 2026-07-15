const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function authHeader(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('rapp_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new ApiError(res.status, body.error ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  /** Multipart FormData upload -- does NOT set Content-Type (browser supplies
   *  the boundary). Auth header is still injected automatically. */
  postForm: <T>(path: string, form: FormData): Promise<T> => {
    const token =
      typeof window !== 'undefined' ? localStorage.getItem('rapp_token') : null;
    const headers: Record<string, string> = token
      ? { Authorization: `Bearer ${token}` }
      : {};
    return fetch(`${API_URL}${path}`, {
      method: 'POST',
      body: form,
      headers,
    }).then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: res.statusText }));
        throw new ApiError(res.status, body.error ?? res.statusText);
      }
      return res.json() as Promise<T>;
    });
  },
};

export { ApiError };
