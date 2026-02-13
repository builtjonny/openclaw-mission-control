"use client";

import { useState } from "react";
import { UserPlus } from "lucide-react";

import { setLocalAuthToken } from "@/auth/localAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

async function registerUser(data: {
  invite_token: string;
  email: string;
  password: string;
  name: string;
}): Promise<{ token: string } | { error: string }> {
  const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!rawBaseUrl) {
    return { error: "NEXT_PUBLIC_API_URL is not set." };
  }
  const baseUrl = rawBaseUrl.replace(/\/+$/, "");

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  } catch {
    return { error: "Unable to reach backend." };
  }

  if (response.ok) {
    const result = (await response.json()) as { access_token: string };
    return { token: result.access_token };
  }
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return {
    error: body?.detail ?? `Registration failed (HTTP ${response.status}).`,
  };
}

type RegisterFormProps = {
  inviteToken?: string;
  inviteEmail?: string;
  onRegistered?: () => void;
  onSwitchToLogin?: () => void;
};

const defaultOnRegistered = () => window.location.reload();

export function RegisterForm({
  inviteToken: initialToken = "",
  inviteEmail: initialEmail = "",
  onRegistered,
  onSwitchToLogin,
}: RegisterFormProps) {
  const [inviteToken, setInviteToken] = useState(initialToken);
  const [email, setEmail] = useState(initialEmail);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedToken = inviteToken.trim();
    const trimmedEmail = email.trim();
    const trimmedName = name.trim();

    if (!trimmedToken) {
      setError("Invite token is required.");
      return;
    }
    if (!trimmedEmail) {
      setError("Email is required.");
      return;
    }
    if (!trimmedName) {
      setError("Name is required.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    const result = await registerUser({
      invite_token: trimmedToken,
      email: trimmedEmail,
      password,
      name: trimmedName,
    });
    setIsSubmitting(false);

    if ("error" in result) {
      setError(result.error);
      return;
    }

    setLocalAuthToken(result.token);
    setError(null);
    (onRegistered ?? defaultOnRegistered)();
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
              Create Account
            </span>
            <div className="rounded-xl bg-[color:var(--accent-soft)] p-2 text-[color:var(--accent)]">
              <UserPlus className="h-5 w-5" />
            </div>
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight text-strong">
              Set Up Your Account
            </h1>
            <p className="text-sm text-muted">
              Complete your invite by creating a password.
            </p>
          </div>
        </CardHeader>
        <CardContent className="pt-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="reg-invite"
                className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
              >
                Invite Token
              </label>
              <Input
                id="reg-invite"
                type="text"
                value={inviteToken}
                onChange={(e) => setInviteToken(e.target.value)}
                placeholder="Paste invite token"
                disabled={isSubmitting || !!initialToken}
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="reg-email"
                className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
              >
                Email
              </label>
              <Input
                id="reg-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                disabled={isSubmitting || !!initialEmail}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="reg-name"
                className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
              >
                Name
              </label>
              <Input
                id="reg-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                autoFocus
                disabled={isSubmitting}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="reg-password"
                className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
              >
                Password
              </label>
              <Input
                id="reg-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                disabled={isSubmitting}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="reg-confirm"
                className="text-xs font-semibold uppercase tracking-[0.08em] text-muted"
              >
                Confirm Password
              </label>
              <Input
                id="reg-confirm"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
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
              {isSubmitting ? "Creating account..." : "Create account"}
            </Button>
            {onSwitchToLogin && (
              <button
                type="button"
                className="text-xs text-muted underline hover:text-strong"
                onClick={onSwitchToLogin}
              >
                Already have an account? Sign in
              </button>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
