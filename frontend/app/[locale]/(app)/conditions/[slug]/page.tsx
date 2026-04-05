"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useParams } from "next/navigation";
import { UpdateCard } from "@/components/condition/update-card";
import { LtrIsland } from "@/components/ui/ltr-island";
import { ApiError, apiDelete, apiGet, apiPost, apiPostFormData } from "@/lib/api";

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
  recap_locale?: "en" | "he";
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

type PrivateDocRow = {
  id: string;
  original_filename: string;
  processing_status: string;
  patient_summary: string;
  doctor_questions: string[];
  created_at: string;
};

type AskMode = "research_only" | "documents_only" | "research_and_documents";

type AskSourceRow = {
  title: string;
  source_url: string;
  research_item_id?: string;
  document_id?: string;
  item_type?: string;
};

const tabBtn =
  "rounded-full px-3 py-1.5 text-sm font-medium transition-colors md:px-4 md:py-2";
const tabActive = "bg-primary text-white shadow-sm";
const tabIdle = "bg-slate-100 text-slate-700 hover:bg-slate-200";

export default function ConditionPage() {
  const locale = useLocale();
  const t = useTranslations("Condition");
  const apiEnglish = locale === "he";
  const answerLtr = locale !== "he";
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
    sources: AskSourceRow[];
  } | null>(null);
  const [askMode, setAskMode] = useState<AskMode>("research_only");
  const [privateDocs, setPrivateDocs] = useState<PrivateDocRow[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [consentUpload, setConsentUpload] = useState(false);

  useEffect(() => {
    if (!slug) return;
    apiGet<ConditionDetail>(`/conditions/by-slug/${encodeURIComponent(slug)}`)
      .then(setData)
      .catch(() => setError(t("notFound")));
  }, [slug, t]);

  useEffect(() => {
    if (!slug) return;
    apiGet<{ items: FeedUpdate[]; total: number }>(
      `/conditions/by-slug/${encodeURIComponent(slug)}/updates?limit=12`,
      { searchParams: { locale } }
    )
      .then((r) => setUpdates(r.items))
      .catch(() => setUpdates([]));
  }, [slug, locale]);

  useEffect(() => {
    if (tab !== "trials" || !slug || trials !== null) return;
    setTrialsLoading(true);
    apiGet<TrialRow[]>(`/conditions/by-slug/${encodeURIComponent(slug)}/trials?limit=50`)
      .then(setTrials)
      .catch(() => setTrials([]))
      .finally(() => setTrialsLoading(false));
  }, [tab, slug, trials]);

  const loadPrivateDocs = useCallback(() => {
    if (!slug || !data?.followed) return;
    setDocsLoading(true);
    setDocsError("");
    apiGet<PrivateDocRow[]>(`/conditions/${encodeURIComponent(slug)}/documents`)
      .then(setPrivateDocs)
      .catch((e) => {
        setPrivateDocs([]);
        if (e instanceof ApiError) setDocsError(e.message);
      })
      .finally(() => setDocsLoading(false));
  }, [slug, data?.followed]);

  useEffect(() => {
    if (tab !== "ask") return;
    void loadPrivateDocs();
  }, [tab, loadPrivateDocs]);

  const AnswerBody = ({ children }: { children: ReactNode }) =>
    answerLtr ? <LtrIsland>{children}</LtrIsland> : <>{children}</>;

  if (error) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error}</p>
        <Link href="/dashboard" className="mt-4 inline-block text-primary">
          {t("backDashboard")}
        </Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="container-page py-8">
        <p className="text-slate-600">{slug ? t("loading") : t("missing")}</p>
      </main>
    );
  }

  return (
    <main className="container-page py-8">
      <header className="rounded-2xl bg-white p-6 shadow-calm">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {data.followed ? t("following") : t("notFollowing")}
        </p>
        <h1 className="text-2xl font-semibold text-slate-900">
          {apiEnglish ? (
            <LtrIsland>
              <span>{data.canonical_name}</span>
            </LtrIsland>
          ) : (
            data.canonical_name
          )}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {apiEnglish ? (
            <LtrIsland>
              <span>{data.description || t("fallbackDescription")}</span>
            </LtrIsland>
          ) : (
            data.description || t("fallbackDescription")
          )}
        </p>
        <p className="mt-3 text-xs text-slate-500">{t("disclaimer")}</p>
        {!data.followed ? (
          <Link href="/onboarding" className="mt-4 inline-block text-sm font-medium text-primary">
            {t("followCta")}
          </Link>
        ) : null}
      </header>

      <div
        className="mt-6 flex flex-wrap gap-2 border-b border-slate-200 pb-3"
        role="tablist"
        aria-label={t("tablistAria")}
      >
        {(
          [
            ["updates", t("tabUpdates")],
            ["trials", t("tabTrials")],
            ["ask", t("tabAsk")],
            ["more", t("tabMore")],
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
            <h2 className="sr-only">{t("srUpdates")}</h2>
            <p className="text-sm text-slate-600">{t("updatesIntro")}</p>
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
                    recapLocale={u.recap_locale ?? "en"}
                    detailHref={`/updates/${u.id}`}
                  />
                ))
              ) : (
                <UpdateCard
                  title={t("emptyUpdatesTitle")}
                  source="CureCompass"
                  summary={t("emptyUpdatesSummary")}
                  whyItMatters={t("emptyUpdatesWhy")}
                  evidenceStage={t("emptyUpdatesBadge")}
                />
              )}
            </div>
          </section>
        ) : null}

        {tab === "trials" ? (
          <section>
            <h2 className="sr-only">{t("srTrials")}</h2>
            <p className="text-sm text-slate-600">{t("trialsIntro")}</p>
            {trialsLoading || trials === null ? (
              <p className="mt-4 text-sm text-slate-600">{t("trialsLoading")}</p>
            ) : (
              <ul className="mt-4 space-y-3">
                {trials.length ? (
                  trials.map((tr) => (
                    <li key={tr.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-calm">
                      {apiEnglish ? (
                        <LtrIsland>
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <p className="font-medium text-slate-900">{tr.title}</p>
                            <span className="text-xs font-medium uppercase text-slate-500">{tr.status}</span>
                          </div>
                          <p className="mt-1 text-xs text-slate-500">
                            {tr.nct_id} · {tr.phase || t("phaseUnknown")}
                          </p>
                          {tr.intervention ? (
                            <p className="mt-2 text-sm text-slate-600">
                              {t("intervention")} {tr.intervention}
                            </p>
                          ) : null}
                          {tr.primary_endpoint_plain_language ? (
                            <p className="mt-1 text-sm text-slate-600">
                              {t("goalPlain")} {tr.primary_endpoint_plain_language}
                            </p>
                          ) : null}
                        </LtrIsland>
                      ) : (
                        <>
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <p className="font-medium text-slate-900">{tr.title}</p>
                            <span className="text-xs font-medium uppercase text-slate-500">{tr.status}</span>
                          </div>
                          <p className="mt-1 text-xs text-slate-500">
                            {tr.nct_id} · {tr.phase || t("phaseUnknown")}
                          </p>
                          {tr.intervention ? (
                            <p className="mt-2 text-sm text-slate-600">
                              {t("intervention")} {tr.intervention}
                            </p>
                          ) : null}
                          {tr.primary_endpoint_plain_language ? (
                            <p className="mt-1 text-sm text-slate-600">
                              {t("goalPlain")} {tr.primary_endpoint_plain_language}
                            </p>
                          ) : null}
                        </>
                      )}
                      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                        <Link href={`/trials/${tr.id}`} className="text-sm font-medium text-primary hover:underline">
                          {t("fullDetails")}
                        </Link>
                        <a className="text-sm font-medium text-slate-600 hover:underline" href={tr.source_url} target="_blank" rel="noreferrer">
                          {t("trialRegistry")}
                        </a>
                      </div>
                    </li>
                  ))
                ) : (
                  <li className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                    {t("trialsEmpty")}
                  </li>
                )}
              </ul>
            )}
          </section>
        ) : null}

        {tab === "ask" ? (
          <section>
            <h2 className="sr-only">{t("srAsk")}</h2>
            <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-calm lg:max-w-2xl">
              <h3 className="text-base font-semibold">{t("askTitle")}</h3>
              <p className="mt-2 text-sm text-slate-600">{t("askIntroModes")}</p>
              <p className="mt-2 text-sm text-slate-600">
                {t("askIntroBefore")}
                <Link href="/dashboard" className="font-medium text-primary">
                  {t("checkUpdatesLink")}
                </Link>
                {t("askIntroAfter")}
              </p>

              {data.followed ? (
                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50/80 p-4">
                  <h4 className="text-sm font-semibold text-slate-900">{t("docsSectionTitle")}</h4>
                  <p className="mt-1 text-xs text-slate-600">{t("docsSectionHint")}</p>
                  <label className="mt-3 flex cursor-pointer items-start gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={consentUpload}
                      onChange={(e) => setConsentUpload(e.target.checked)}
                    />
                    <span>{t("docsConsentLabel")}</span>
                  </label>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <label className="text-sm text-slate-700">
                      <span className="sr-only">{t("docsPickFile")}</span>
                      <input
                        type="file"
                        accept="application/pdf,.pdf"
                        className="max-w-full text-sm"
                        disabled={uploadBusy || !consentUpload}
                        onChange={async (e) => {
                          const f = e.target.files?.[0];
                          e.target.value = "";
                          if (!f || !consentUpload || !data.slug) return;
                          setUploadBusy(true);
                          setDocsError("");
                          try {
                            const fd = new FormData();
                            fd.append("file", f);
                            fd.append("consent_accepted", "true");
                            fd.append("answer_locale", locale === "he" ? "he" : "en");
                            await apiPostFormData<PrivateDocRow>(`/conditions/${data.slug}/documents`, fd);
                            loadPrivateDocs();
                          } catch (err) {
                            if (err instanceof ApiError) setDocsError(err.message);
                          } finally {
                            setUploadBusy(false);
                          }
                        }}
                      />
                    </label>
                    {uploadBusy ? <span className="text-xs text-slate-500">{t("docsUploading")}</span> : null}
                  </div>
                  {docsError ? (
                    <p className="mt-2 text-xs text-rose-600">
                      {apiEnglish ? (
                        <LtrIsland>
                          <span>{docsError}</span>
                        </LtrIsland>
                      ) : (
                        docsError
                      )}
                    </p>
                  ) : null}
                  {docsLoading ? (
                    <p className="mt-3 text-sm text-slate-500">{t("docListLoading")}</p>
                  ) : privateDocs.length ? (
                    <ul className="mt-3 space-y-2 text-sm">
                      {privateDocs.map((d) => (
                        <li
                          key={d.id}
                          className="flex flex-col gap-1 rounded-lg border border-slate-200 bg-white p-3 sm:flex-row sm:items-start sm:justify-between"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-medium text-slate-900" title={d.original_filename}>
                              {d.original_filename}
                            </p>
                            <p className="text-xs text-slate-500">
                              {d.processing_status === "ready"
                                ? t("docsStatusReady")
                                : d.processing_status === "pending"
                                  ? t("docsStatusPending")
                                  : t("docsStatusFailed")}
                            </p>
                            {d.processing_status === "ready" && d.patient_summary ? (
                              <p className="mt-1 line-clamp-3 text-xs text-slate-600">{d.patient_summary}</p>
                            ) : null}
                          </div>
                          <button
                            type="button"
                            className="shrink-0 text-sm font-medium text-rose-700 hover:underline"
                            onClick={async () => {
                              if (!confirm(t("docsDeleteConfirm", { name: d.original_filename }))) return;
                              try {
                                await apiDelete(`/conditions/${data.slug}/documents/${d.id}`);
                                loadPrivateDocs();
                              } catch (err) {
                                if (err instanceof ApiError) setDocsError(err.message);
                              }
                            }}
                          >
                            {t("docsDelete")}
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-slate-500">{t("docsEmpty")}</p>
                  )}
                </div>
              ) : (
                <p className="mt-4 text-sm text-slate-600">{t("docsFollowToUpload")}</p>
              )}

              <div className="mt-5">
                <label htmlFor="ask-mode" className="text-sm font-medium text-slate-800">
                  {t("askModeLabel")}
                </label>
                <select
                  id="ask-mode"
                  className="mt-1 w-full max-w-md rounded-lg border border-slate-300 bg-white p-2 text-sm"
                  value={askMode}
                  onChange={(e) => setAskMode(e.target.value as AskMode)}
                >
                  <option value="research_only">{t("askModeResearch")}</option>
                  <option value="documents_only">{t("askModeDocuments")}</option>
                  <option value="research_and_documents">{t("askModeBoth")}</option>
                </select>
              </div>

              <textarea
                className="mt-4 min-h-24 w-full rounded-lg border border-slate-300 p-3 text-sm"
                placeholder={t("askPlaceholder", { slug: data.slug.toUpperCase() })}
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
                      sources: AskSourceRow[];
                    }>(`/conditions/${data.slug}/ask-ai`, {
                      body: {
                        prompt: askInput.trim(),
                        answer_locale: locale === "he" ? "he" : "en",
                        mode: askMode,
                        document_ids: [],
                      },
                    });
                    setAskAnswer(res);
                  } catch (err) {
                    if (err instanceof ApiError) {
                      setAskError(err.message);
                    } else setAskError(t("askFailed"));
                  } finally {
                    setAskLoading(false);
                  }
                }}
              >
                {askLoading ? t("thinking") : t("ask")}
              </button>
              {askError ? (
                <p className="mt-3 text-sm text-rose-600">
                  {apiEnglish && askError !== t("askFailed") ? (
                    <LtrIsland>
                      <span>{askError}</span>
                    </LtrIsland>
                  ) : (
                    askError
                  )}
                </p>
              ) : null}
              {askAnswer ? (
                <div className="mt-4 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <div>
                    <p className="font-medium text-slate-900">{t("directAnswer")}</p>
                    <AnswerBody>
                      <p className="text-slate-700">{askAnswer.direct_answer}</p>
                    </AnswerBody>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">{t("whatChanged")}</p>
                    <AnswerBody>
                      <p className="text-slate-700">{askAnswer.what_changed_recently}</p>
                    </AnswerBody>
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <AnswerBody>
                      <p className="text-slate-700">
                        <span className="font-medium text-slate-900">{t("evidence")}</span> {askAnswer.evidence_strength}
                      </p>
                    </AnswerBody>
                    <AnswerBody>
                      <p className="text-slate-700">
                        <span className="font-medium text-slate-900">{t("availability")}</span>{" "}
                        {askAnswer.available_now_or_experimental}
                      </p>
                    </AnswerBody>
                  </div>
                  {!!askAnswer.suggested_doctor_questions?.length && (
                    <div>
                      <p className="font-medium text-slate-900">{t("doctorQuestions")}</p>
                      <AnswerBody>
                        <ul className="mt-1 list-disc space-y-1 ps-5 text-slate-700">
                          {askAnswer.suggested_doctor_questions.map((q) => (
                            <li key={q}>{q}</li>
                          ))}
                        </ul>
                      </AnswerBody>
                    </div>
                  )}
                  {!!askAnswer.sources?.length && (
                    <div>
                      <p className="font-medium text-slate-900">{t("sources")}</p>
                      <AnswerBody>
                        <ul className="mt-1 space-y-1">
                          {askAnswer.sources.map((s) => (
                            <li key={`${s.title}-${s.source_url || s.document_id || ""}`}>
                              {s.source_url ? (
                                <a className="text-primary underline" href={s.source_url} target="_blank" rel="noreferrer">
                                  {s.title}
                                </a>
                              ) : (
                                <span className="text-slate-800">
                                  {t("sourceYourDocument")}: {s.title}
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </AnswerBody>
                    </div>
                  )}
                </div>
              ) : null}
            </article>
          </section>
        ) : null}

        {tab === "more" ? (
          <section className="max-w-xl space-y-4 text-sm text-slate-700">
            <h2 className="sr-only">{t("srMore")}</h2>
            <p>
              <Link href="/settings/notifications" className="font-medium text-primary hover:underline">
                {t("moreLine1a")}
              </Link>{" "}
              {t("moreLine1b")}
            </p>
            <p>
              <Link href="/legal/disclaimer" className="font-medium text-primary hover:underline">
                {t("moreLine2a")}
              </Link>{" "}
              {t("moreLine2b")}
            </p>
            <p>
              {t("moreLine3a")}
              <strong>{t("tabUpdates")}</strong>
              {t("moreLine3b")}
              <button type="button" className="font-medium text-primary hover:underline" onClick={() => setTab("updates")}>
                {t("tabUpdates")}
              </button>
              {t("moreLine3c")}
            </p>
          </section>
        ) : null}
      </div>
    </main>
  );
}
