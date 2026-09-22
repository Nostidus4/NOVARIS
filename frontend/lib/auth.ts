"use client";

import { clientApiBase } from "./client-api";

const SESSION_KEY = "qshield.auth.session";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
};

export type AuthSession = {
  accessToken: string;
  expiresAt: number | null;
  user: AuthUser;
};

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  expires_at: number | null;
  user: AuthUser;
};

type RegisterResponse = {
  user: AuthUser;
  email_confirmation_required: boolean;
  access_token: string | null;
  refresh_token: string | null;
  token_type: string;
  expires_in: number | null;
  expires_at: number | null;
};

export type RegistrationResult = {
  session: AuthSession | null;
  user: AuthUser;
  emailConfirmationRequired: boolean;
};

function parseError(body: unknown, fallback: string): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

async function responseBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function loginWithPassword(
  email: string,
  password: string,
  remember: boolean,
): Promise<AuthSession> {
  const response = await fetch(`${clientApiBase()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await responseBody(response);
  if (!response.ok) {
    throw new Error(parseError(body, "Không thể đăng nhập. Vui lòng thử lại."));
  }

  const payload = body as LoginResponse;
  const session: AuthSession = {
    accessToken: payload.access_token,
    expiresAt: payload.expires_at,
    user: payload.user,
  };
  storeSession(session, remember);
  return session;
}

export async function registerWithPassword(
  displayName: string,
  email: string,
  password: string,
): Promise<RegistrationResult> {
  const response = await fetch(`${clientApiBase()}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: displayName, email, password }),
  });
  const body = await responseBody(response);
  if (!response.ok) {
    throw new Error(parseError(body, "Không thể tạo tài khoản. Vui lòng thử lại."));
  }

  const payload = body as RegisterResponse;
  const session = payload.access_token
    ? {
        accessToken: payload.access_token,
        expiresAt: payload.expires_at,
        user: payload.user,
      }
    : null;
  if (session) storeSession(session, true);
  return {
    session,
    user: payload.user,
    emailConfirmationRequired: payload.email_confirmation_required,
  };
}

export function storeSession(session: AuthSession, remember: boolean): void {
  clearStoredSession();
  const storage = remember ? window.localStorage : window.sessionStorage;
  storage.setItem(SESSION_KEY, JSON.stringify(session));
}

function readSession(storage: Storage): AuthSession | null {
  const value = storage.getItem(SESSION_KEY);
  if (!value) return null;
  try {
    const session = JSON.parse(value) as AuthSession;
    if (!session.accessToken || !session.user?.id || !session.user?.email) return null;
    if (session.expiresAt && session.expiresAt * 1000 <= Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

export function getStoredSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  const persistent = readSession(window.localStorage);
  if (persistent) return persistent;
  return readSession(window.sessionStorage);
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(SESSION_KEY);
  window.sessionStorage.removeItem(SESSION_KEY);
}

export async function verifySession(session: AuthSession): Promise<AuthUser> {
  const response = await fetch(`${clientApiBase()}/auth/me`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: "no-store",
  });
  const body = await responseBody(response);
  if (!response.ok) {
    throw new Error(parseError(body, "Phiên đăng nhập đã hết hạn."));
  }
  return (body as { user: AuthUser }).user;
}

export async function logout(): Promise<void> {
  const session = getStoredSession();
  clearStoredSession();
  if (!session) return;
  try {
    await fetch(`${clientApiBase()}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${session.accessToken}` },
    });
  } catch {
    // The local session is already gone; provider sign-out can safely fail offline.
  }
}

export function safeNextPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/overview";
  if (
    value === "/login" ||
    value.startsWith("/login?") ||
    value === "/register" ||
    value.startsWith("/register?")
  ) {
    return "/overview";
  }
  return value;
}
