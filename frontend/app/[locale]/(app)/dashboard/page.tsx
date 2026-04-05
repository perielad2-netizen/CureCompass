"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { UpdateCard } from "@/components/condition/update-card";
import { LtrIsland } from "@/components/ui/ltr-island";
import { ApiError, apiGet, apiPost } from "@/lib/api";

type RecruitingTrialBrief = {
  id: string;
  nct_id: string;
  title: string;
  status: string;
  phase: string;
  condition_slug: string;
  condition_name: string;
  source_url: string;
};

const DASH_EN_FALLBACK_EMPTY = "No major changes in the last 24 hours.";
const DASH_EN_FALLBACK_UPDATES = "You have new trusted updates available.";

type DashboardPayload = {
  followed_conditions: { id: string; slug: string; name: string }[];
  latest_important_updates: {
    id: string;
    title: string;
    source_url: string;
    published_at: string;
    item_type: string;
    evidence_stage: string;
    evidence_stage_label: string;
    summary: string;
    why_it_matters: string;
    bookmarked?: boolean;
    condition_slug?: string;
    condition_name?: string;
    recap_locale?: "en" | "he";
  }[];
  unread_updates: number;
  digest_preview: string;
  digest_preview_kind?: "latest_digest" | "empty_feed" | "has_updates";
  upcoming_recruiting_trials: RecruitingTrialBrief[];
};

export default function DashboardPage() {
  const t = useTranslations("Dashboard");
  const locale = useLocale();
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState("");
  const [scanSlug, setScanSlug] = useState("");
  const [scanBusy, setScanBusy] = useState(false);
  const [scanNotice, setScanNotice] = useState("");
  const [scanError, setScanError] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("cc_access_token")) {
      setError(t("signInFirst"));
      return;
    }
    apiGet<DashboardPayload>("/dashboard", { searchParams: { locale } })
      .then(setData)
      .catch(() => setError(t("loadError")));
  }, [t, locale]);

  useEffect(() => {
    if (!data?.followed_conditions.length) {
      setScanSlug("");
      return;
    }
    setScanSlug((prev) => {
      if (prev && data.followed_conditions.some((c) => c.slug === prev)) return prev;
      return data.followed_conditions[0].slug;
    });
  }, [data?.followed_conditions]);

  return (
    <main className="container-page py-8">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      <p className="mt-1 text-sm text-slate-600">
        {data?.digest_preview ? (
          locale === "he" ? (
            (() => {
              const text = data.digest_preview;
              const kind = data.digest_preview_kind;
              if (kind === "empty_feed" || (!kind && text === DASH_EN_FALLBACK_EMPTY)) {
                return kind === "empty_feed" ? text : t("digestPreviewNoMajor");
              }
              if (kind === "has_updates" || (!kind && text === DASH_EN_FALLBACK_UPDATES)) {
                return kind === "has_updates" ? text : t("digestPreviewHasUpdates");
              }
              return (
                <>
                  <span>{t("digestPreviewBriefingTeaser")}</span>
                  <details className="mt-2 text-xs text-slate-500">
                    <summary className="cursor-pointer select-none text-slate-600">{t("digestPreviewShowEnglishHeadline")}</summary>
                    <div className="mt-1">
                      <LtrIsland>
                        <span>{text}</span>
                      </LtrIsland>
                    </div>
                  </details>
                </>
              );
            })()
          ) : (
            data.digest_preview
          )
        ) : (
          t("loadingFeed")
        )}
      </p>
      <Link href="/digests" className="mt-2 inline-block text-sm font-medium text-primary">
        {t("openBriefings")}
      </Link>

      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_min(100%,320px)] lg:items-start">
        <div className="space-y-4">
          {data && data.followed_conditions.length > 0 ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-calm sm:p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between lg:gap-6">
                <div className="min-w-0 flex-1">
                  <p className="text-base font-semibold text-slate-900">{t("checkUpdatesTitle")}</p>
                  <p className="mt-1 text-sm text-slate-600">{t("checkUpdatesBody")}</p>
                </div>
                <div className="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-end">
                  {data.followed_conditions.length > 1 ? (
                    <label className="flex min-w-[11rem] flex-col gap-1 text-sm">
                      <span className="text-slate-600">{t("condition")}</span>
                      <select
                        className="rounded-lg border border-slate-300 px-3 py-2"
                        value={scanSlug}
                        onChange={(e) => setScanSlug(e.target.value)}
                        disabled={scanBusy}
                      >
                        {data.followed_conditions.map((c) => (
                          <option key={c.id} value={c.slug}>
                            {c.name} ({c.slug})
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                  <button
                    type="button"
                    className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-[42px]"
                    disabled={scanBusy || !scanSlug}
                    onClick={async () => {
                      if (!scanSlug) return;
                      setScanBusy(true);
                      setScanNotice("");
                      setScanError("");
                      try {
                        const out = await apiPost<{
                          status?: string;
                          condition_slug?: string;
                          job_id?: string;
                          result?: unknown;
                          error?: string;
                          enrichment_scheduled?: boolean;
                        }>("/ingestion/backfill", { body: { condition_slug: scanSlug } });
                        if (out.status === "failed") {
                          setScanError(typeof out.error === "string" ? out.error : t("scanFail"));
                        } else {
                          let tail =
                            out.status === "queued" ? t("scanQueued") : t("scanDone");
                          if (out.status !== "queued" && out.enrichment_scheduled) {
                            tail += t("scanEnrich");
                          }
                          setScanNotice(tail);
                          const next = await apiGet<DashboardPayload>("/dashboard", {
                            searchParams: { locale },
                          });
                          setData(next);
                        }
                      } catch (e) {
                        if (e instanceof ApiError) setScanError(e.message);
                        else setScanError(t("scanCouldNot"));
                      } finally {
                        setScanBusy(false);
                      }
                    }}
                  >
                    {scanBusy ? t("checking") : t("checkUpdates")}
                  </button>
                </div>
              </div>
              {scanError ? <p className="mt-3 text-sm text-rose-600">{scanError}</p> : null}
              {scanNotice ? (
                <p className="mt-3 text-sm text-emerald-800">
                  <LtrIsland>
                    <span>{scanNotice}</span>
                  </LtrIsland>
                </p>
              ) : null}
            </section>
          ) : null}
          {!data ? (
            <p className="text-sm text-slate-600">{t("loadingUpdates")}</p>
          ) : data.latest_important_updates.length ? (
            <>
              <h2 className="text-lg font-semibold text-slate-900">{t("latestHeading")}</h2>
              <p className="-mt-2 text-sm text-slate-600">{t("latestSub")}</p>
              {data.latest_important_updates.map((u, i) => (
                <UpdateCard
                  key={u.id}
                  researchItemId={u.id}
                  bookmarked={u.bookmarked}
                  title={u.title}
                  source={u.source_url}
                  summary={u.summary}
                  whyItMatters={u.why_it_matters}
                  evidenceStage={u.evidence_stage_label}
                  detailHref={`/updates/${u.id}`}
                  publishedAt={u.published_at}
                  itemType={u.item_type}
                  conditionName={u.condition_name}
                  recapLocale={u.recap_locale ?? "en"}
                  featured={i === 0 && data.latest_important_updates.length > 1}
                />
              ))}
            </>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-slate-900">{t("latestHeading")}</h2>
              {data.followed_conditions.length === 0 ? (
                <UpdateCard
                  title={t("emptyFollowTitle")}
                  source="CureCompass"
                  summary={t("emptyFollowSummary")}
                  whyItMatters={t("emptyFollowWhy")}
                  evidenceStage={t("emptyFollowBadge")}
                />
              ) : (
                <UpdateCard
                  title={t("emptyIngestTitle")}
                  source="CureCompass"
                  summary={t("emptyIngestSummary")}
                  whyItMatters={t("emptyIngestWhy")}
                  evidenceStage={t("emptyIngestBadge")}
                />
              )}
            </>
          )}
        </div>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-calm">
          <h3 className="text-base font-semibold">{t("trialsTitle")}</h3>
          <p className="mt-2 text-sm text-slate-600">
            {data
              ? data.followed_conditions.length
                ? t("trialsIntro")
                : t("trialsNoFollow")
              : t("trialsLoading")}
          </p>
          {data && data.upcoming_recruiting_trials.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {data.upcoming_recruiting_trials.map((tr) => (
                <li key={tr.id} className="rounded-xl border border-slate-100 bg-slate-50/80 p-3 text-sm">
                  <LtrIsland>
                    <p className="font-medium leading-snug text-slate-900">{tr.title}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {tr.nct_id}
                      {tr.phase ? ` · ${tr.phase}` : ""}
                      {tr.condition_name ? ` · ${tr.condition_name}` : ""}
                    </p>
                  </LtrIsland>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                    <Link href={`/trials/${encodeURIComponent(tr.id)}`} className="font-medium text-primary hover:underline">
                      {t("trialDetails")}
                    </Link>
                    <a
                      className="font-medium text-slate-600 hover:underline"
                      href={tr.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t("trialRegistry")}
                    </a>
                    {tr.condition_slug ? (
                      <Link href={`/conditions/${tr.condition_slug}`} className="font-medium text-slate-600 hover:underline">
                        {t("trialCondition")}
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : data && data.followed_conditions.length > 0 ? (
            <p className="mt-4 text-sm text-slate-600">{t("trialsEmpty")}</p>
          ) : null}
          {data?.followed_conditions[0] ? (
            <Link
              href={`/conditions/${data.followed_conditions[0].slug}`}
              className="mt-4 inline-block text-sm font-medium text-primary"
            >
              {t("openCondition")}
            </Link>
          ) : data && !data.followed_conditions.length ? (
            <Link href="/onboarding" className="mt-4 inline-block text-sm font-medium text-primary">
              {t("followCondition")}
            </Link>
          ) : null}
        </article>
      </div>
    </main>
  );
}
