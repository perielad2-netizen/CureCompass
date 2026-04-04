"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, apiPost } from "@/lib/api";

function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    if (!token) {
      setError("Missing reset token. Open the link from your email.");
      return;
    }
    try {
      await apiPost("/auth/reset-password", {
        body: { token, password },
        authRetry: false,
      });
      setMessage("Password updated. Redirecting to sign in…");
      setTimeout(() => router.replace("/login"), 1500);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Reset failed.");
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
      <h1 className="text-2xl font-semibold">Set a new password</h1>
      <p className="mt-1 text-sm text-slate-600">Choose a new password for your account.</p>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          type="password"
          placeholder="New password (min 6 characters)"
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <button type="submit" className="w-full rounded-lg bg-primary px-4 py-2 text-white">
          Update password
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        <Link href="/login" className="font-medium text-primary">
          Sign in
        </Link>
      </p>
    </section>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="container-page py-10">
      <Suspense fallback={<p className="text-slate-600">Loading…</p>}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
