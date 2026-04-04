"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api";

type Me = { id: string; email: string; is_admin: boolean };

export default function ProfilePage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("cc_access_token")) {
      router.replace("/login");
      return;
    }
    apiGet<Me>("/auth/me")
      .then(setMe)
      .catch(() => setError("Could not load profile."));
  }, [router]);

  return (
    <main className="container-page max-w-2xl py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Profile</h1>
      <p className="mt-2 text-sm text-slate-600">Account and preferences (research information only — not medical advice).</p>
      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
      {me ? (
        <ul className="mt-6 space-y-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
          <li className="text-sm">
            <span className="font-medium text-slate-800">Email</span>
            <p className="text-slate-600">{me.email}</p>
          </li>
          <li>
            <Link href="/settings/notifications" className="text-sm font-medium text-primary">
              Research briefings &amp; notification settings
            </Link>
          </li>
          <li>
            <Link href="/onboarding" className="text-sm font-medium text-primary">
              Add or adjust followed conditions
            </Link>
          </li>
          <li>
            <Link href="/forgot-password" className="text-sm font-medium text-primary">
              Change password (reset link)
            </Link>
          </li>
        </ul>
      ) : !error ? (
        <p className="mt-6 text-slate-600">Loading…</p>
      ) : null}
    </main>
  );
}
