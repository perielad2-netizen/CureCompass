"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { notifyAuthChanged } from "@/lib/auth-events";
import { ApiError, apiGet, apiPost } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const tokenPayload = await apiPost<{ access_token: string; refresh_token: string }>("/auth/login", {
        body: { email, password },
      });
      localStorage.setItem("cc_access_token", tokenPayload.access_token);
      localStorage.setItem("cc_refresh_token", tokenPayload.refresh_token);
      notifyAuthChanged();
      const dash = await apiGet<{ followed_conditions: unknown[] }>("/dashboard");
      if (!dash.followed_conditions?.length) {
        router.push("/onboarding");
      } else {
        router.push("/dashboard");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Login failed. Check your credentials.");
      }
    }
  }

  return (
    <main className="container-page py-10">
      <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        <h1 className="text-2xl font-semibold">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-600">Sign in to continue following condition updates.</p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <button className="w-full rounded-lg bg-primary px-4 py-2 text-white">Login</button>
        </form>
        <p className="mt-2 text-center text-sm">
          <Link href="/forgot-password" className="font-medium text-primary">
            Forgot password?
          </Link>
        </p>
        <p className="mt-4 text-center text-sm text-slate-600">
          New to CureCompass?{" "}
          <Link href="/register" className="font-medium text-primary">
            Create account
          </Link>
        </p>
      </section>
    </main>
  );
}
