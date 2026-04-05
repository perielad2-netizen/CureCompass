"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { apiGet } from "@/lib/api";

type Me = { id: string; email: string; is_admin: boolean; preferred_locale: "en" | "he" };

export default function ProfilePage() {
  const t = useTranslations("Profile");
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
      .catch(() => setError(t("loadError")));
  }, [router, t]);

  return (
    <main className="container-page max-w-2xl py-10">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("intro")}</p>
      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
      {me ? (
        <ul className="mt-6 space-y-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
          <li className="text-sm">
            <span className="font-medium text-slate-800">{t("email")}</span>
            <p className="text-slate-600">{me.email}</p>
          </li>
          <li className="space-y-1 border-t border-slate-100 pt-3">
            <p className="text-sm font-medium text-slate-800">{t("language")}</p>
            <p className="text-xs text-slate-500">{t("languageHelp")}</p>
          </li>
          <li>
            <Link href="/settings/notifications" className="text-sm font-medium text-primary">
              {t("briefingSettings")}
            </Link>
          </li>
          <li>
            <Link href="/onboarding" className="text-sm font-medium text-primary">
              {t("adjustConditions")}
            </Link>
          </li>
          <li>
            <Link href="/forgot-password" className="text-sm font-medium text-primary">
              {t("changePassword")}
            </Link>
          </li>
        </ul>
      ) : !error ? (
        <p className="mt-6 text-slate-600">{t("loading")}</p>
      ) : null}
    </main>
  );
}
