"use client";

import { FormEvent, Suspense, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { useSearchParams } from "next/navigation";
import { ApiError, apiPost } from "@/lib/api";

function ResetPasswordForm() {
  const router = useRouter();
  const t = useTranslations("AuthReset");
  const tc = useTranslations("Common");
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
      setError(t("missingToken"));
      return;
    }
    try {
      await apiPost("/auth/reset-password", {
        body: { token, password },
        authRetry: false,
      });
      setMessage(t("passwordUpdated"));
      setTimeout(() => router.replace("/login"), 1500);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError(t("resetFailed"));
    }
  }

  return (
    <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
      <h1 className="text-2xl font-semibold">{t("title")}</h1>
      <p className="mt-1 text-sm text-slate-600">{t("subtitle")}</p>
      <form className="mt-6 space-y-4" onSubmit={onSubmit}>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          type="password"
          placeholder={t("passwordPlaceholder")}
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        <button type="submit" className="w-full rounded-lg bg-primary px-4 py-2 text-white">
          {t("updatePassword")}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">
        <Link href="/login" className="font-medium text-primary">
          {t("signIn")}
        </Link>
      </p>
    </section>
  );
}

export default function ResetPasswordPage() {
  const t = useTranslations("AuthReset");
  return (
    <main className="container-page py-10">
      <Suspense fallback={<p className="text-slate-600">{t("suspenseLoading")}</p>}>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
