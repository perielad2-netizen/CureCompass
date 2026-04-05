import { notifyAuthChanged } from "@/lib/auth-events";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

type RequestOptions = {
  token?: string;
  body?: unknown;
  /** When false, do not try refresh on 401 (e.g. login/register). Default true. */
  authRetry?: boolean;
  /** Appended as query string (e.g. { locale: "he" } → ?locale=he). */
  searchParams?: Record<string, string | undefined>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function formatFastAPIDetail(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "Request failed";
  const p = payload as { detail?: unknown };
  const d = p.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((item: { msg?: string; loc?: unknown[] }) => {
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") {
          const loc = Array.isArray(item.loc) ? item.loc.filter((x) => x !== "body").join(".") : "";
          return loc ? `${loc}: ${item.msg}` : item.msg;
        }
        return JSON.stringify(item);
      })
      .join(" ");
  }
  return "Request failed";
}

function resolveToken(explicit?: string): string | undefined {
  if (explicit !== undefined) return explicit || undefined;
  if (typeof window === "undefined") return undefined;
  return localStorage.getItem("cc_access_token") ?? undefined;
}

async function tryRefresh(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  const refresh = localStorage.getItem("cc_refresh_token");
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = (await res.json()) as { access_token: string; refresh_token: string };
    localStorage.setItem("cc_access_token", data.access_token);
    localStorage.setItem("cc_refresh_token", data.refresh_token);
    notifyAuthChanged();
    return true;
  } catch {
    return false;
  }
}

async function handleJsonResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* ignore */
    }
    throw new ApiError(formatFastAPIDetail(body), res.status, body);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

function buildUrl(path: string, searchParams?: Record<string, string | undefined>): string {
  const entries = searchParams
    ? Object.entries(searchParams).filter(([, v]) => v !== undefined && v !== "")
    : [];
  if (!entries.length) return path;
  const q = new URLSearchParams(entries as [string, string][]).toString();
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}${q}`;
}

export async function apiGet<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const authRetry = options.authRetry !== false;
  const token = resolveToken(options.token);
  const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const url = `${API_BASE_URL}${buildUrl(path, options.searchParams)}`;

  let res = await fetch(url, { cache: "no-store", headers });

  if (res.status === 401 && authRetry && token && (await tryRefresh())) {
    const t2 = resolveToken();
    res = await fetch(url, {
      cache: "no-store",
      headers: t2 ? { Authorization: `Bearer ${t2}` } : {},
    });
  }

  return handleJsonResponse<T>(res);
}

export async function apiPost<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const authRetry = options.authRetry !== false;
  const token = resolveToken(options.token);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(options.body ?? {}),
  });

  if (res.status === 401 && authRetry && token && (await tryRefresh())) {
    const t2 = resolveToken();
    const h2: Record<string, string> = { "Content-Type": "application/json" };
    if (t2) h2.Authorization = `Bearer ${t2}`;
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: h2,
      body: JSON.stringify(options.body ?? {}),
    });
  }

  return handleJsonResponse<T>(res);
}

/** POST multipart (e.g. file upload). Do not set Content-Type; the browser sets the boundary. */
export async function apiPostFormData<T>(path: string, formData: FormData, options: RequestOptions = {}): Promise<T> {
  const authRetry = options.authRetry !== false;
  const token = resolveToken(options.token);
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (res.status === 401 && authRetry && token && (await tryRefresh())) {
    const t2 = resolveToken();
    const h2: Record<string, string> = {};
    if (t2) h2.Authorization = `Bearer ${t2}`;
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: h2,
      body: formData,
    });
  }

  return handleJsonResponse<T>(res);
}

export async function apiPut<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const authRetry = options.authRetry !== false;
  const token = resolveToken(options.token);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(options.body ?? {}),
  });

  if (res.status === 401 && authRetry && token && (await tryRefresh())) {
    const t2 = resolveToken();
    const h2: Record<string, string> = { "Content-Type": "application/json" };
    if (t2) h2.Authorization = `Bearer ${t2}`;
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "PUT",
      headers: h2,
      body: JSON.stringify(options.body ?? {}),
    });
  }

  return handleJsonResponse<T>(res);
}

export async function apiPatch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const authRetry = options.authRetry !== false;
  const token = resolveToken(options.token);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(options.body ?? {}),
  });

  if (res.status === 401 && authRetry && token && (await tryRefresh())) {
    const t2 = resolveToken();
    const h2: Record<string, string> = { "Content-Type": "application/json" };
    if (t2) h2.Authorization = `Bearer ${t2}`;
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "PATCH",
      headers: h2,
      body: JSON.stringify(options.body ?? {}),
    });
  }

  return handleJsonResponse<T>(res);
}

export async function apiDelete<T = void>(path: string, options: RequestOptions = {}): Promise<T> {
  const authRetry = options.authRetry !== false;
  const token = resolveToken(options.token);
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let res = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    cache: "no-store",
    headers,
  });

  if (res.status === 401 && authRetry && token && (await tryRefresh())) {
    const t2 = resolveToken();
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "DELETE",
      cache: "no-store",
      headers: t2 ? { Authorization: `Bearer ${t2}` } : {},
    });
  }

  return handleJsonResponse<T>(res);
}
