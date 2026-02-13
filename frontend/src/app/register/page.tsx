"use client";

export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { isLocalAuthMode } from "@/auth/localAuth";
import { RegisterForm } from "@/components/organisms/RegisterForm";

function RegisterContent() {
  const searchParams = useSearchParams();
  const inviteToken = searchParams.get("token") ?? "";
  const inviteEmail = searchParams.get("email") ?? "";

  if (!isLocalAuthMode()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app">
        <p className="text-muted">
          Registration is only available in local auth mode.
        </p>
      </div>
    );
  }

  return (
    <RegisterForm
      inviteToken={inviteToken}
      inviteEmail={inviteEmail}
      onSwitchToLogin={() => (window.location.href = "/")}
    />
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-app">
          <p className="text-muted">Loading...</p>
        </div>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
