"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useParams } from "next/navigation";
import { ApiError, apiGet } from "@/lib/api";
import { formatDateTimeMedium } from "@/lib/date-format";

type TrialDetail = {
  id: string;
  nct_id: string;
  status: string;
  phase: string;
  title: string;
  intervention: string;
  eligibility_summary: string;
  age_min: number | null;
  age_max: number | null;
  sex: string;
  countries: unknown[];
  primary_endpoint_plain_language: string;
  primary_endpoint: string;
  source_url: string;
  last_verified_at: string;
  condition_slug: string;
  condition_name: string;
  locations: unknown[];
};

export default function TrialDetailPage() {
  const t = useTranslations("TrialDetail");
  const tc = useTranslations("Common");
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : params.id?.[0] ?? "";
  const [data, setData] = useState<TrialDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    apiGet<TrialDetail>(`/trials/${encodeURIComponent(id)}`)
      .then(setData)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) setError(t("notFound"));
        else setError(t("loadError"));
      });
  }, [id, t]);

  if (error) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error}</p>
        <Link href="/dashboard" className="mt-4 inline-block text-primary">
          {tc("backToDashboard")}
        </Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="container-page py-8">
        <p className="text-slate-600">{id ? t("loading") : t("missingId")}</p>
      </main>
    );
  }

  const ages =
    data.age_min != null || data.age_max != null
      ? t("ageRange", { min: data.age_min ?? "?", max: data.age_max ?? "?" })
      : t("ageUnknown");

  return (
    <main className="container-page max-w-3xl py-8">
      <p className="text-sm text-slate-500">
        {data.condition_slug ? (
          <Link href={`/conditions/${data.condition_slug}`} className="font-medium text-primary hover:underline">
            ← {data.condition_name || data.condition_slug}
          </Link>
        ) : (
          <Link href="/dashboard" className="font-medium text-primary hover:underline">
            ← {tc("dashboard")}
          </Link>
        )}
      </p>
      <p className="mt-3 text-xs font-medium uppercase tracking-wide text-slate-500">{data.status}</p>
      <h1 className="mt-1 text-2xl font-semibold text-slate-900">{data.title}</h1>
      <p className="mt-2 text-sm text-slate-600">
        {data.nct_id}
        {data.phase ? ` · ${data.phase}` : ""}
      </p>

      <div className="mt-8 space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        {data.intervention ? (
          <section>
            <h2 className="text-sm font-semibold text-slate-900">{t("intervention")}</h2>
            <p className="mt-1 text-sm text-slate-700">{data.intervention}</p>
          </section>
        ) : null}
        <section>
          <h2 className="text-sm font-semibold text-slate-900">{t("whoCanJoin")}</h2>
          <p className="mt-1 text-sm text-slate-700">{data.eligibility_summary || t("eligibilityNotSummarized")}</p>
          <p className="mt-2 text-xs text-slate-500">
            {t("sex")} {data.sex} · {ages}
          </p>
        </section>
        {data.primary_endpoint_plain_language ? (
          <section>
            <h2 className="text-sm font-semibold text-slate-900">{t("studyGoalPlain")}</h2>
            <p className="mt-1 text-sm text-slate-700">{data.primary_endpoint_plain_language}</p>
          </section>
        ) : null}
        {data.primary_endpoint ? (
          <section>
            <h2 className="text-sm font-semibold text-slate-900">{t("primaryEndpointListed")}</h2>
            <p className="mt-1 text-sm text-slate-700">{data.primary_endpoint}</p>
          </section>
        ) : null}
        {data.countries != null && (Array.isArray(data.countries) ? data.countries.length > 0 : true) ? (
          <section>
            <h2 className="text-sm font-semibold text-slate-900">{t("countries")}</h2>
            <p className="mt-1 text-sm text-slate-700">
              {Array.isArray(data.countries) ? data.countries.map(String).join(", ") : JSON.stringify(data.countries)}
            </p>
          </section>
        ) : null}
        {data.locations?.length ? (
          <section>
            <h2 className="text-sm font-semibold text-slate-900">{t("locations")}</h2>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {data.locations.slice(0, 20).map((loc, i) => (
                <li key={i}>{typeof loc === "object" && loc !== null ? JSON.stringify(loc) : String(loc)}</li>
              ))}
            </ul>
            {data.locations.length > 20 ? (
              <p className="mt-2 text-xs text-slate-500">{t("locationsTruncated", { total: data.locations.length })}</p>
            ) : null}
          </section>
        ) : null}
        <p className="text-xs text-slate-500">
          {t("lastVerified")} {formatDateTimeMedium(data.last_verified_at)}
        </p>
        <a
          href={data.source_url}
          target="_blank"
          rel="noreferrer"
          className="inline-block rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white"
        >
          {t("openRegistry")}
        </a>
      </div>

      <p className="mt-6 text-xs text-slate-500">{t("footerDisclaimer")}</p>
    </main>
  );
}
