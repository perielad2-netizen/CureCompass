"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ApiError, apiPost } from "@/lib/api";

export default function ForgotPasswordPage() {
  const t = useTranslations("AuthForgot");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await apiPost("/auth/forgot-password", { body: { email }, authRetry: false });
      setMessage(t("messageSent"));
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError(t("requestFailed"));
    }
  }

  return (
    <main className="container-page py-10">
      <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-1 text-sm text-slate-600">{t("subtitle")}</p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            type="email"
            placeholder={t("emailPlaceholder")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <button type="submit" className="w-full rounded-lg bg-primary px-4 py-2 text-white">
            {t("sendResetLink")}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-600">
          <Link href="/login" className="font-medium text-primary">
            {t("backToSignIn")}
          </Link>
        </p>
      </section>
    </main>
  );
}
