"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { apiGet } from "@/lib/api";

type FollowedCondition = { id: string; slug: string; name: string };
type DashboardPeek = { followed_conditions: FollowedCondition[] };

export default function AskHubPage() {
  const t = useTranslations("AskHub");
  const [rows, setRows] = useState<FollowedCondition[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<DashboardPeek>("/dashboard")
      .then((d) => setRows(d.followed_conditions ?? []))
      .catch(() => {
        setRows([]);
        setError(t("loadError"));
      });
  }, [t]);

  return (
    <main className="container-page py-8">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      <p className="mt-1 text-sm text-slate-600">{t("intro")}</p>
      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}

      {rows === null ? (
        <p className="mt-6 text-sm text-slate-600">{t("loading")}</p>
      ) : rows.length === 0 ? (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-700">{t("noConditions")}</p>
          <Link href="/onboarding" className="mt-3 inline-block text-sm font-medium text-primary hover:underline">
            {t("followCondition")}
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {rows.map((c) => (
            <Link
              key={c.id}
              href={`/conditions/${encodeURIComponent(c.slug)}?tab=ask`}
              className="rounded-xl border border-slate-200 bg-white p-4 text-sm shadow-sm transition hover:border-primary/50 hover:bg-ice/40"
            >
              <p className="font-medium text-slate-900">{c.name}</p>
              <p className="mt-1 text-xs text-slate-500">{c.slug}</p>
              <p className="mt-2 text-primary">{t("openAsk")}</p>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}

