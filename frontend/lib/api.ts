const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function throwApiError(res: Response): Promise<never> {
  const body = await res.json().catch(() => ({ detail: res.statusText }));
  throw new ApiError(res.status, body.detail ?? "Request failed");
}

/**
 * For calls made FROM THE BROWSER (Client Components) — routes through
 * Next.js's own /api/proxy/* Route Handler, never straight to FastAPI, so the
 * JWT cookie never has to be readable by client-side JS.
 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const res = await fetch(`/api/proxy${path}`, {
    ...options,
    headers: isFormData ? options.headers : { "Content-Type": "application/json", ...options.headers },
    credentials: "include",
  });
  if (!res.ok) return throwApiError(res);
  if (res.status === 204) return undefined as T;
  return res.json();
}

/**
 * For calls made FROM A SERVER COMPONENT (async function Page()) — talks to
 * FastAPI directly, forwarding the session cookie read from next/headers.
 */
export async function apiFetchServer<T>(
  path: string,
  token: string | undefined,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    cache: "no-store", // this is per-user data — never let Next.js cache it
  });
  if (!res.ok) return throwApiError(res);
  return res.json();
}
