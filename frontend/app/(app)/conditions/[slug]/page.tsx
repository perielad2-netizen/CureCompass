"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { UpdateCard } from "@/components/condition/update-card";
import { ApiError, apiGet, apiPost } from "@/lib/api";

type ConditionDetail = {
  id: string;
  canonical_name: string;
  slug: string;
  description: string;
  rare_disease_flag: boolean;
  followed: boolean;
};

type FeedUpdate = {
  id: string;
  title: string;
  source_name: string;
  source_url: string;
  published_at: string;
  item_type: string;
  evidence_stage_label: string;
  summary: string;
  why_it_matters: string;
  bookmarked?: boolean;
};

type TrialRow = {
  id: string;
  nct_id: string;
  status: string;
  phase: string;
  title: string;
  intervention: string;
  primary_endpoint_plain_language: string;
  source_url: string;
};

type TabId = "updates" | "trials" | "ask" | "more";

const tabBtn =
  "rounded-full px-3 py-1.5 text-sm font-medium transition-colors md:px-4 md:py-2";
const tabActive = "bg-primary text-white shadow-sm";
const tabIdle = "bg-slate-100 text-slate-700 hover:bg-slate-200";

export default function ConditionPage() {
  const params = useParams();
  const slug = typeof params.slug === "string" ? params.slug : params.slug?.[0] ?? "";
  const [tab, setTab] = useState<TabId>("updates");
  const [data, setData] = useState<ConditionDetail | null>(null);
  const [updates, setUpdates] = useState<FeedUpdate[]>([]);
  const [trials, setTrials] = useState<TrialRow[] | null>(null);
  const [trialsLoading, setTrialsLoading] = useState(false);
  const [error, setError] = useState("");
  const [askInput, setAskInput] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState("");
  const [askAnswer, setAskAnswer] = useState<{
    direct_answer: string;
    what_changed_recently: string;
    evidence_strength: string;
    available_now_or_experimental: string;
    suggested_doctor_questions: string[];
    sources: { title: string; source_url: string }[];
  } | null>(null);

  useEffect(() => {
    if (!slug) return;
    apiGet<ConditionDetail>(`/conditions/by-slug/${encodeURIComponent(slug)}`)
      .then(setData)
      .catch(() => setError("Condition not found."));
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    apiGet<{ items: FeedUpdate[]; total: number }>(
      `/conditions/by-slug/${encodeURIComponent(slug)}/updates?limit=12`
    )
      .then((r) => setUpdates(r.items))
      .catch(() => setUpdates([]));
  }, [slug]);

  useEffect(() => {
    if (tab !== "trials" || !slug || trials !== null) return;
    setTrialsLoading(true);
    apiGet<TrialRow[]>(`/conditions/by-slug/${encodeURIComponent(slug)}/trials?limit=50`)
      .then(setTrials)
      .catch(() => setTrials([]))
      .finally(() => setTrialsLoading(false));
  }, [tab, slug, trials]);

  if (error) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error}</p>
        <Link href="/dashboard" className="mt-4 inline-block text-primary">
          Back to dashboard
        </Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="container-page py-8">
        <p className="text-slate-600">{slug ? "Loading…" : "Missing condition."}</p>
      </main>
    );
  }

  return (
    <main className="container-page py-8">
      <header className="rounded-2xl bg-white p-6 shadow-calm">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {data.followed ? "Following" : "Not following yet"}
        </p>
        <h1 className="text-2xl font-semibold text-slate-900">{data.canonical_name}</h1>
        <p className="mt-2 text-sm text-slate-600">{data.description || "Trusted research updates for this condition."}</p>
        <p className="mt-3 text-xs text-slate-500">
          Educational research tracking only. Not diagnosis or treatment advice.
        </p>
        {!data.followed ? (
          <Link href="/onboarding" className="mt-4 inline-block text-sm font-medium text-primary">
            Follow this condition
          </Link>
        ) : null}
      </header>

      <div
        className="mt-6 flex flex-wrap gap-2 border-b border-slate-200 pb-3"
        role="tablist"
        aria-label="Condition sections"
      >
        {(
          [
            ["updates", "Updates"],
            ["trials", "Trials"],
            ["ask", "Ask AI"],
            ["more", "More"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={`${tabBtn} ${tab === id ? tabActive : tabIdle}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-8" role="tabpanel">
        {tab === "updates" ? (
          <section>
            <h2 className="sr-only">Latest updates</h2>
            <p className="text-sm text-slate-600">
              Plain-language summaries from trusted indexed sources. Run ingestion from the dashboard if this list is empty.
            </p>
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              {updates.length ? (
                updates.map((u) => (
                  <UpdateCard
                    key={u.id}
                    researchItemId={u.id}
                    bookmarked={u.bookmarked}
                    title={u.title}
                    source={`${u.source_name} · ${u.source_url}`}
                    summary={u.summary}
                    whyItMatters={u.why_it_matters}
                    evidenceStage={u.evidence_stage_label}
                    detailHref={`/updates/${u.id}`}
                  />
                ))
              ) : (
                <UpdateCard
                  title="No indexed updates yet"
                  source="CureCompass"
                  summary="After you follow this condition, an admin or automated job can run ingestion to pull PubMed, ClinicalTrials.gov, and openFDA records."
                  whyItMatters="Once data is ingested and enriched, updates appear here with evidence badges and summaries."
                  evidenceStage="Monitoring"
                />
              )}
            </div>
          </section>
        ) : null}

        {tab === "trials" ? (
          <section>
            <h2 className="sr-only">Trials</h2>
            <p className="text-sm text-slate-600">
              Studies indexed from ClinicalTrials.gov for this condition (newest verified first). Not all are recruiting.
            </p>
            {trialsLoading || trials === null ? (
              <p className="mt-4 text-sm text-slate-600">Loading trials…</p>
            ) : (
              <ul className="mt-4 space-y-3">
                {trials.length ? (
                  trials.map((t) => (
                    <li key={t.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-calm">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <p className="font-medium text-slate-900">{t.title}</p>
                        <span className="text-xs font-medium uppercase text-slate-500">{t.status}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {t.nct_id} · {t.phase || "Phase not listed"}
                      </p>
                      {t.intervention ? <p className="mt-2 text-sm text-slate-600">Intervention: {t.intervention}</p> : null}
                      {t.primary_endpoint_plain_language ? (
                        <p className="mt-1 text-sm text-slate-600">Goal (plain language): {t.primary_endpoint_plain_language}</p>
                      ) : null}
                      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                        <Link href={`/trials/${t.id}`} className="text-sm font-medium text-primary hover:underline">
                          Full details
                        </Link>
                        <a className="text-sm font-medium text-slate-600 hover:underline" href={t.source_url} target="_blank" rel="noreferrer">
                          ClinicalTrials.gov
                        </a>
                      </div>
                    </li>
                  ))
                ) : (
                  <li className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    No trials in the index yet. Ingestion will populate trial records for this condition.
                  </li>
                )}
              </ul>
            )}
          </section>
        ) : null}

        {tab === "ask" ? (
          <section>
            <h2 className="sr-only">Ask AI</h2>
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-calm lg:max-w-2xl">
              <h3 className="text-base font-semibold">Ask AI (condition-limited)</h3>
              <p className="mt-2 text-sm text-slate-600">
                Answers use only this condition and items already indexed from trusted feeds (PubMed, ClinicalTrials.gov,
                openFDA). If nothing is ingested yet, use{" "}
                <Link href="/dashboard" className="font-medium text-primary">
                  Check for updates
                </Link>{" "}
                on the dashboard first.
              </p>
              <textarea
                className="mt-4 min-h-24 w-full rounded-lg border border-slate-300 p-3 text-sm"
                placeholder={`Anything new for ${data.slug.toUpperCase()} kids?`}
                value={askInput}
                onChange={(e) => setAskInput(e.target.value)}
              />
              <button
                type="button"
                className="mt-3 rounded-lg bg-primary px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={!askInput.trim() || askLoading}
                onClick={async () => {
                  if (!askInput.trim()) return;
                  setAskLoading(true);
                  setAskError("");
                  try {
                    const res = await apiPost<{
                      direct_answer: string;
                      what_changed_recently: string;
                      evidence_strength: string;
                      available_now_or_experimental: string;
                      suggested_doctor_questions: string[];
                      sources: { title: string; source_url: string }[];
                    }>(`/conditions/${data.slug}/ask-ai`, {
                      body: { prompt: askInput.trim() },
                    });
                    setAskAnswer(res);
                  } catch (err) {
                    if (err instanceof ApiError) setAskError(err.message);
                    else setAskError("Ask AI request failed.");
                  } finally {
                    setAskLoading(false);
                  }
                }}
              >
                {askLoading ? "Thinking..." : "Ask"}
              </button>
              {askError ? <p className="mt-3 text-sm text-rose-600">{askError}</p> : null}
              {askAnswer ? (
                <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <div>
                    <p className="font-medium text-slate-900">Direct answer</p>
                    <p className="text-slate-700">{askAnswer.direct_answer}</p>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">What changed recently</p>
                    <p className="text-slate-700">{askAnswer.what_changed_recently}</p>
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <p className="text-slate-700">
                      <span className="font-medium text-slate-900">Evidence:</span> {askAnswer.evidence_strength}
                    </p>
                    <p className="text-slate-700">
                      <span className="font-medium text-slate-900">Availability:</span> {askAnswer.available_now_or_experimental}
                    </p>
                  </div>
                  {!!askAnswer.suggested_doctor_questions?.length && (
                    <div>
                      <p className="font-medium text-slate-900">Questions to ask your doctor</p>
                      <ul className="mt-1 list-disc space-y-1 pl-5 text-slate-700">
                        {askAnswer.suggested_doctor_questions.map((q) => (
                          <li key={q}>{q}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {!!askAnswer.sources?.length && (
                    <div>
                      <p className="font-medium text-slate-900">Sources</p>
                      <ul className="mt-1 space-y-1">
                        {askAnswer.sources.map((s) => (
                          <li key={`${s.title}-${s.source_url}`}>
                            <a className="text-primary underline" href={s.source_url} target="_blank" rel="noreferrer">
                              {s.title}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : null}
            </article>
          </section>
        ) : null}

        {tab === "more" ? (
          <section className="max-w-xl space-y-4 text-sm text-slate-700">
            <h2 className="sr-only">More</h2>
            <p>
              <Link href="/settings/notifications" className="font-medium text-primary hover:underline">
                Notification settings
              </Link>{" "}
              — defaults for new follows and per-condition email / digest preferences.
            </p>
            <p>
              <Link href="/legal/disclaimer" className="font-medium text-primary hover:underline">
                Medical disclaimer
              </Link>{" "}
              — how to use CureCompass safely alongside your clinician.
            </p>
            <p>
              Regulatory and trial updates appear in the <strong>Updates</strong> tab when indexed as separate items. Open the{" "}
              <button type="button" className="font-medium text-primary hover:underline" onClick={() => setTab("updates")}>
                Updates
              </button>{" "}
              tab for source links and evidence badges.
            </p>
          </section>
        ) : null}
      </div>
    </main>
  );
}
