"use client";

import { useState } from "react";
import { Lock, Mail } from "lucide-react";

import { setLocalAuthToken } from "@/auth/localAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const LOCAL_AUTH_TOKEN_MIN_LENGTH = 50;

type AuthTab = "email" | "token";

async function loginWithCredentials(
  email: string,
  password: string,
): Promise<{ token: string } | { error: string }> {
  const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!rawBaseUrl) {
    return { error: "NEXT_PUBLIC_API_URL is not set." };
  }
  const baseUrl = rawBaseUrl.replace(/\/+$/, "");

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    return { error: "Unable to reach backend." };
  }

  if (response.ok) {
    const data = (await response.json()) as { access_token: string };
    return { token: data.access_token };
  }
  if (response.status === 401) {
    return { error: "Invalid email or password." };
  }
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return {
    error: body?.detail ?? `Login failed (HTTP ${response.status}).`,
  };
}

async function validateLocalToken(token: string): Promise<string | null> {
  const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!rawBaseUrl) {
    return "NEXT_PUBLIC_API_URL is not set.";
  }

  const baseUrl = rawBaseUrl.replace(/\/+$/, "");

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/users/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    return "Unable to reach backend to validate token.";
  }

  if (response.ok) {
    return null;
  }
  if (response.status === 401 || response.status === 403) {
    return "Token is invalid.";
  }
  return `Unable to validate token (HTTP ${response.status}).`;
}

type LocalAuthLoginProps = {
  onAuthenticated?: () => void;
  onSwitchToRegister?: () => void;
};

const defaultOnAuthenticated = () => window.location.reload();

export function LocalAuthLogin({
  onAuthenticated,
  onSwitchToRegister,
}: LocalAuthLoginProps) {
  const [tab, setTab] = useState<AuthTab>("email");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleEmailLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    if (!trimmedEmail) {
      setError("Email is required.");
      return;
    }
    if (!trimmedPassword) {
      setError("Password is required.");
      return;
    }

    setIsSubmitting(true);
    const result = await loginWithCredentials(trimmedEmail, trimmedPassword);
    setIsSubmitting(false);

    if ("error" in result) {
      setError(result.error);
      return;
    }

    setLocalAuthToken(result.token);
    setError(null);
    (onAuthenticated ?? defaultOnAuthenticated)();
  };

  const handleTokenLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleaned = token.trim();
    if (!cleaned) {
      setError("Bearer token is required.");
      return;
    }
    if (cleaned.length < LOCAL_AUTH_TOKEN_MIN_LENGTH) {
      setError(
        `Bearer token must be at least ${LOCAL_AUTH_TOKEN_MIN_LENGTH} characters.`,
      );
      return;
    }

    setIsSubmitting(true);
    const validationError = await validateLocalToken(cleaned);
    setIsSubmitting(false);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLocalAuthToken(cleaned);
    setError(null);
    (onAuthenticated ?? defaultOnAuthenticated)();
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-app px-4 py-10">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-28 -left-24 h-72 w-72 rounded-full bg-[color:var(--accent-soft)] blur-3xl" />
        <div className="absolute -right-28 -bottom-24 h-80 w-80 rounded-full bg-[rgba(14,165,233,0.12)] blur-3xl" />
      </div>

      <Card className="relative w-full max-w-lg animate-fade-in-up">
        <CardHeader className="space-y-5 border-b border-[color:var(--border)] pb-5">
          <div className="flex items-center justify-between">
            <span className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-muted)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.08em] text-muted">
              Self-host mode
            </span>
            <div className="rounded-xl bg-[color:var(--accent-soft)] p-2 text-[color:var(--accent)]">
              {tab === "email" ? (
                <Mail className="h-5 w-5" />
              ) : (
                <Lock className="h-5 w-5" />
              )}
            </div>
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight text-strong">
              Local Authentication
            </h1>
            <p className="text-sm text-muted">
              {tab === "email"
                ? "Sign in with your email and password."
                : "Enter your access token to unlock Mission Control."}
            </p>
          </div>
        </CardHeader>
        <CardContent className="pt-5">
          {tab === "email" ? (
            <form onSubmit={handleEmailLogin} className="space-y-4">
              <div className="space-y-2">
                <label
                  htmlFor="login-email"
                  className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
                >
                  Email
                </label>
                <Input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoFocus
                  disabled={isSubmitting}
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="login-password"
                  className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
                >
                  Password
                </label>
                <Input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  disabled={isSubmitting}
                />
              </div>
              {error && (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {error}
                </p>
              )}
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Signing in..." : "Sign in"}
              </Button>
              <div className="flex items-center justify-between text-xs text-muted">
                <button
                  type="button"
                  className="underline hover:text-strong"
                  onClick={() => {
                    setError(null);
                    setTab("token");
                  }}
                >
                  Use access token instead
                </button>
                {onSwitchToRegister && (
                  <button
                    type="button"
                    className="underline hover:text-strong"
                    onClick={onSwitchToRegister}
                  >
                    Create account
                  </button>
                )}
              </div>
            </form>
          ) : (
            <form onSubmit={handleTokenLogin} className="space-y-4">
              <div className="space-y-2">
                <label
                  htmlFor="local-auth-token"
                  className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
                >
                  Access token
                </label>
                <Input
                  id="local-auth-token"
                  type="password"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                  placeholder="Paste token"
                  autoFocus
                  disabled={isSubmitting}
                  className="font-mono"
                />
              </div>
              {error ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {error}
                </p>
              ) : (
                <p className="text-xs text-muted">
                  Token must be at least {LOCAL_AUTH_TOKEN_MIN_LENGTH}{" "}
                  characters.
                </p>
              )}
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Validating..." : "Continue"}
              </Button>
              <button
                type="button"
                className="text-xs text-muted underline hover:text-strong"
                onClick={() => {
                  setError(null);
                  setTab("email");
                }}
              >
                Sign in with email instead
              </button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
