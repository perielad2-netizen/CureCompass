"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { UpdateCard } from "@/components/condition/update-card";
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
  }[];
  unread_updates: number;
  digest_preview: string;
  upcoming_recruiting_trials: RecruitingTrialBrief[];
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState("");
  const [scanSlug, setScanSlug] = useState("");
  const [scanBusy, setScanBusy] = useState(false);
  const [scanNotice, setScanNotice] = useState("");
  const [scanError, setScanError] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("cc_access_token")) {
      setError("Please sign in first.");
      return;
    }
    apiGet<DashboardPayload>("/dashboard")
      .then(setData)
      .catch(() => setError("Could not load dashboard. Please sign in again."));
  }, []);

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
      <h1 className="text-2xl font-semibold text-slate-900">Your dashboard</h1>
      <p className="mt-1 text-sm text-slate-600">{data?.digest_preview || "Loading your research feed..."}</p>
      <Link href="/digests" className="mt-2 inline-block text-sm font-medium text-primary">
        Open research briefings
      </Link>

      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_min(100%,320px)] lg:items-start">
        <div className="space-y-4">
          {data && data.followed_conditions.length > 0 ? (
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-calm sm:p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between lg:gap-6">
                <div className="min-w-0 flex-1">
                  <p className="text-base font-semibold text-slate-900">Check for updates</p>
                  <p className="mt-1 text-sm text-slate-600">
                    Pull the latest from PubMed, ClinicalTrials.gov, and openFDA. When new items are found, we
                    automatically start plain-language summaries (needs OpenAI key on the server). Refresh after a short
                    wait to see them.
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-3 sm:flex-row sm:items-end">
                  {data.followed_conditions.length > 1 ? (
                    <label className="flex min-w-[11rem] flex-col gap-1 text-sm">
                      <span className="text-slate-600">Condition</span>
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
                          setScanError(typeof out.error === "string" ? out.error : "Update check failed.");
                        } else {
                          let tail =
                            out.status === "queued"
                              ? "Job queued — ensure Redis and a Celery worker are running for background completion."
                              : "Done — new items appear below.";
                          if (out.status !== "queued" && out.enrichment_scheduled) {
                            tail +=
                              " Simple-language summaries are generating in the background—refresh in a minute or two for easier explanations.";
                          }
                          setScanNotice(tail);
                          const next = await apiGet<DashboardPayload>("/dashboard");
                          setData(next);
                        }
                      } catch (e) {
                        if (e instanceof ApiError) setScanError(e.message);
                        else setScanError("Could not check for updates.");
                      } finally {
                        setScanBusy(false);
                      }
                    }}
                  >
                    {scanBusy ? "Checking…" : "Check for updates"}
                  </button>
                </div>
              </div>
              {scanError ? <p className="mt-3 text-sm text-rose-600">{scanError}</p> : null}
              {scanNotice ? <p className="mt-3 text-sm text-emerald-800">{scanNotice}</p> : null}
            </section>
          ) : null}
          {!data ? (
            <p className="text-sm text-slate-600">Loading your latest updates…</p>
          ) : data.latest_important_updates.length ? (
            <>
              <h2 className="text-lg font-semibold text-slate-900">Latest from your conditions</h2>
              <p className="-mt-2 text-sm text-slate-600">
                Newest trusted items we&apos;ve indexed, with source date. Run ingestion if this list is empty.
              </p>
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
                  featured={i === 0 && data.latest_important_updates.length > 1}
                />
              ))}
            </>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-slate-900">Latest from your conditions</h2>
              {data.followed_conditions.length === 0 ? (
                <UpdateCard
                  title="Follow a condition to see updates"
                  source="CureCompass"
                  summary="Choose a condition to track so we can show the newest trusted research, trials, and regulatory items here with dates."
                  whyItMatters="A focused feed helps you spot meaningful changes without wading through unrelated news."
                  evidenceStage="Get started"
                />
              ) : (
                <UpdateCard
                  title="No major changes showing yet"
                  source="CureCompass monitoring"
                  summary="We don’t have indexed items for your followed conditions right now. After ingestion runs, the latest updates will appear here with source dates."
                  whyItMatters="Regular monitoring helps you catch meaningful progress while avoiding information overload."
                  evidenceStage="Basic research"
                />
              )}
            </>
          )}
        </div>
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-calm">
          <h3 className="text-base font-semibold">Recruiting trials</h3>
          <p className="mt-2 text-sm text-slate-600">
            {data
              ? data.followed_conditions.length
                ? "Open studies on ClinicalTrials.gov for your followed conditions (newest verified first)."
                : "Follow a condition to see recruiting trials here."
              : "Loading…"}
          </p>
          {data && data.upcoming_recruiting_trials.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {data.upcoming_recruiting_trials.map((t) => (
                <li key={t.id} className="rounded-xl border border-slate-100 bg-slate-50/80 p-3 text-sm">
                  <p className="font-medium leading-snug text-slate-900">{t.title}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {t.nct_id}
                    {t.phase ? ` · ${t.phase}` : ""}
                    {t.condition_name ? ` · ${t.condition_name}` : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                    <Link href={`/trials/${encodeURIComponent(t.id)}`} className="font-medium text-primary hover:underline">
                      Details
                    </Link>
                    <a
                      className="font-medium text-slate-600 hover:underline"
                      href={t.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      ClinicalTrials.gov
                    </a>
                    {t.condition_slug ? (
                      <Link href={`/conditions/${t.condition_slug}`} className="font-medium text-slate-600 hover:underline">
                        Condition
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : data && data.followed_conditions.length > 0 ? (
            <p className="mt-4 text-sm text-slate-600">
              No recruiting trials in the index yet for your conditions. After ingestion, they will appear here.
            </p>
          ) : null}
          {data?.followed_conditions[0] ? (
            <Link
              href={`/conditions/${data.followed_conditions[0].slug}`}
              className="mt-4 inline-block text-sm font-medium text-primary"
            >
              Open condition page
            </Link>
          ) : data && !data.followed_conditions.length ? (
            <Link href="/onboarding" className="mt-4 inline-block text-sm font-medium text-primary">
              Follow a condition
            </Link>
          ) : null}
        </article>
      </div>
    </main>
  );
}
