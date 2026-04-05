"use client";

import { FormEvent, useLayoutEffect, useState } from "react";
import { Link, useRouter } from "@/i18n/navigation";
import { notifyAuthChanged } from "@/lib/auth-events";
import { ApiError, apiPost } from "@/lib/api";
import { redirectAuthenticatedUser } from "@/lib/redirect-if-authed";

export default function RegisterPage() {
  const router = useRouter();
  /** null = undecided (SSR / first paint), true = show sign-up form, false = signed in → redirect */
  const [guestForm, setGuestForm] = useState<boolean | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useLayoutEffect(() => {
    const token = localStorage.getItem("cc_access_token");
    if (!token) {
      setGuestForm(true);
      return;
    }
    setGuestForm(false);
    void redirectAuthenticatedUser(router);
  }, [router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const tokenPayload = await apiPost<{ access_token: string; refresh_token: string }>("/auth/register", {
        body: { email, password },
      });
      localStorage.setItem("cc_access_token", tokenPayload.access_token);
      localStorage.setItem("cc_refresh_token", tokenPayload.refresh_token);
      notifyAuthChanged();
      router.push("/onboarding");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Sign up failed. Try again.");
      }
    }
  }

  if (guestForm === null) {
    return (
      <main className="container-page py-10">
        <p className="text-slate-600">Loading…</p>
      </main>
    );
  }

  if (guestForm === false) {
    return (
      <main className="container-page py-10">
        <p className="text-slate-600">Redirecting…</p>
      </main>
    );
  }

  return (
    <main className="container-page py-10">
      <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        <h1 className="text-2xl font-semibold">Create your CureCompass account</h1>
        <p className="mt-1 text-sm text-slate-600">Start with one condition (NF1 is preloaded).</p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <div>
            <input
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
              placeholder="Password"
              type="password"
              minLength={6}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">At least 6 characters.</p>
          </div>
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <button className="w-full rounded-lg bg-primary px-4 py-2 text-white">Sign up</button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-600">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
