"use client";

import { FormEvent, useLayoutEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { notifyAuthChanged } from "@/lib/auth-events";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import { redirectAuthenticatedUser } from "@/lib/redirect-if-authed";

type MeLocale = { preferred_locale: "en" | "he" };

export default function LoginPage() {
  const router = useRouter();
  const t = useTranslations("AuthLogin");
  const tc = useTranslations("Common");
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
      const tokenPayload = await apiPost<{ access_token: string; refresh_token: string }>("/auth/login", {
        body: { email, password },
      });
      localStorage.setItem("cc_access_token", tokenPayload.access_token);
      localStorage.setItem("cc_refresh_token", tokenPayload.refresh_token);
      const [dash, me] = await Promise.all([
        apiGet<{ followed_conditions: unknown[] }>("/dashboard"),
        apiGet<MeLocale>("/auth/me"),
      ]);
      notifyAuthChanged();
      const locale = me.preferred_locale === "he" ? "he" : "en";
      if (!dash.followed_conditions?.length) {
        router.push("/onboarding", { locale });
      } else {
        router.push("/dashboard", { locale });
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t("loginFailedGeneric"));
      }
    }
  }

  if (guestForm === null) {
    return (
      <main className="container-page py-10">
        <p className="text-slate-600">{tc("loading")}</p>
      </main>
    );
  }

  if (guestForm === false) {
    return (
      <main className="container-page py-10">
        <p className="text-slate-600">{tc("redirecting")}</p>
      </main>
    );
  }

  return (
    <main className="container-page py-10">
      <section className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-1 text-sm text-slate-600">{t("subtitle")}</p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder={t("emailPlaceholder")}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder={t("passwordPlaceholder")}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          <button className="w-full rounded-lg bg-primary px-4 py-2 text-white">{t("loginButton")}</button>
        </form>
        <p className="mt-2 text-center text-sm">
          <Link href="/forgot-password" className="font-medium text-primary">
            {t("forgotPassword")}
          </Link>
        </p>
        <p className="mt-4 text-center text-sm text-slate-600">
          {t("newTo")}{" "}
          <Link href="/register" className="font-medium text-primary">
            {t("createAccount")}
          </Link>
        </p>
      </section>
    </main>
  );
}
