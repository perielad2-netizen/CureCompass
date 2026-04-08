"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useParams, useSearchParams } from "next/navigation";
import { UpdateCard } from "@/components/condition/update-card";
import { LtrIsland } from "@/components/ui/ltr-island";
import { AskAiStoredAssistantMessage } from "@/components/ask-ai/ask-ai-stored-assistant";
import { AskAiThreadThinking } from "@/components/ask-ai/ask-ai-thread-thinking";
import { ConditionHubSummary } from "@/components/condition/condition-hub-summary";
import { ApiError, apiDelete, apiGet, apiPost, apiPostFormData } from "@/lib/api";
import {
  trackAskAiEmptyStatePromptClick,
  trackAskAiHubCta,
  trackAskAiLimitBlocked,
  trackAskAiNewConversation,
} from "@/lib/product-analytics";

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

type AskThreadMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  structured_json: unknown;
  created_at: string;
};

type AskAiDailyUsage = {
  count: number;
  remaining: number | null;
  soft_limit: number;
  grace_limit: number;
  max_limit: number;
  is_limited: boolean;
  in_grace_zone: boolean;
  is_premium: boolean;
};

function isAskAiLimitPostResponse(res: unknown): res is { limit_reached: true; usage?: AskAiDailyUsage } {
  return typeof res === "object" && res !== null && (res as { limit_reached?: boolean }).limit_reached === true;
}

function pickAskAiUsage(res: unknown): AskAiDailyUsage | null {
  if (typeof res !== "object" || res === null || !("usage" in res)) return null;
  const u = (res as { usage: unknown }).usage;
  if (!u || typeof u !== "object") return null;
  return u as AskAiDailyUsage;
}

function formatAskThreadTime(iso: string, loc: string): string {
  try {
    return new Date(iso).toLocaleString(loc === "he" ? "he-IL" : "en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return "";
  }
}

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
  const searchParams = useSearchParams();
  const slug = typeof params.slug === "string" ? params.slug : params.slug?.[0] ?? "";
  const [tab, setTab] = useState<TabId>("updates");
  const [data, setData] = useState<ConditionDetail | null>(null);
  const [updates, setUpdates] = useState<FeedUpdate[]>([]);
  const [updatesTotal, setUpdatesTotal] = useState<number | null>(null);
  const [trials, setTrials] = useState<TrialRow[] | null>(null);
  const [trialsLoading, setTrialsLoading] = useState(false);
  const [error, setError] = useState("");
  const [askInput, setAskInput] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [threadMessages, setThreadMessages] = useState<AskThreadMessage[]>([]);
  const [threadLoading, setThreadLoading] = useState(false);
  const [threadLoadError, setThreadLoadError] = useState("");
  const askTextareaRef = useRef<HTMLTextAreaElement>(null);
  const threadListRef = useRef<HTMLUListElement>(null);
  /** User scrolled away from bottom — avoid auto-scroll on assistant updates. */
  const skipAutoScrollRef = useRef(false);
  /** After sending, always scroll to show thinking + new content. */
  const pendingSendScrollRef = useRef(false);
  const [askMode, setAskMode] = useState<AskMode>("research_only");
  const [privateDocs, setPrivateDocs] = useState<PrivateDocRow[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);
  const [consentUpload, setConsentUpload] = useState(false);
  const [askAiUsage, setAskAiUsage] = useState<AskAiDailyUsage | null>(null);

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
      .then((r) => {
        setUpdates(r.items);
        setUpdatesTotal(typeof r.total === "number" ? r.total : r.items.length);
      })
      .catch(() => {
        setUpdates([]);
        setUpdatesTotal(null);
      });
  }, [slug, locale]);

  useEffect(() => {
    if (!slug || !data) return;
    if (!data.followed) {
      setTrials([]);
      setTrialsLoading(false);
      return;
    }
    let cancelled = false;
    setTrialsLoading(true);
    setTrials(null);
    apiGet<TrialRow[]>(`/conditions/by-slug/${encodeURIComponent(slug)}/trials?limit=50`)
      .then((rows) => {
        if (!cancelled) setTrials(rows);
      })
      .catch(() => {
        if (!cancelled) setTrials([]);
      })
      .finally(() => {
        if (!cancelled) setTrialsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug, data]);

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

  const loadAskThread = useCallback(async () => {
    if (!slug || !data?.followed) return;
    setThreadLoading(true);
    setThreadLoadError("");
    try {
      const list = await apiGet<{ id: string }[]>(
        `/conditions/${encodeURIComponent(slug)}/ask-ai/conversations`
      );
      if (!list.length) {
        setConversationId(null);
        setThreadMessages([]);
        return;
      }
      const cid = list[0].id;
      setConversationId(cid);
      const conv = await apiGet<{ messages: AskThreadMessage[] }>(`/ask-ai/conversations/${cid}`);
      setThreadMessages(Array.isArray(conv.messages) ? conv.messages : []);
    } catch {
      setThreadLoadError(t("askThreadLoadError"));
      setThreadMessages([]);
    } finally {
      setThreadLoading(false);
    }
  }, [slug, data?.followed, t]);

  const loadAskAiUsage = useCallback(async () => {
    if (!data?.followed) {
      setAskAiUsage(null);
      return;
    }
    try {
      const r = await apiGet<{ usage: AskAiDailyUsage }>("/ask-ai/daily-usage");
      setAskAiUsage(r.usage);
    } catch {
      setAskAiUsage(null);
    }
  }, [data?.followed]);

  useEffect(() => {
    setConversationId(null);
    setThreadMessages([]);
    setThreadLoadError("");
    setAskAiUsage(null);
  }, [slug]);

  useEffect(() => {
    if (!data?.followed) {
      setThreadMessages([]);
      setConversationId(null);
      setAskAiUsage(null);
    }
  }, [data?.followed]);

  useEffect(() => {
    if (tab !== "ask") return;
    void loadPrivateDocs();
  }, [tab, loadPrivateDocs]);

  useEffect(() => {
    if (tab !== "ask" || !slug || !data?.followed) return;
    void loadAskThread();
    void loadAskAiUsage();
  }, [tab, slug, data?.followed, loadAskThread, loadAskAiUsage]);

  const startNewConversation = useCallback(() => {
    if (!data?.slug) return;
    trackAskAiNewConversation({ condition_slug: data.slug, locale });
    setConversationId(null);
    setThreadMessages([]);
    setAskError("");
    skipAutoScrollRef.current = false;
    void loadAskAiUsage();
  }, [data?.slug, locale, loadAskAiUsage]);

  const onThreadScroll = useCallback(() => {
    const el = threadListRef.current;
    if (!el) return;
    const gap = el.scrollHeight - el.scrollTop - el.clientHeight;
    skipAutoScrollRef.current = gap > 150;
  }, []);

  useLayoutEffect(() => {
    if (threadLoading) return;
    const hasThread = threadMessages.length > 0 || askLoading;
    if (!hasThread) return;
    const force = pendingSendScrollRef.current;
    if (skipAutoScrollRef.current && !force) return;
    const el = threadListRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
    if (force) pendingSendScrollRef.current = false;
  }, [threadMessages, askLoading, threadLoading]);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "updates" || tabParam === "trials" || tabParam === "ask" || tabParam === "more") {
      setTab(tabParam);
    }
  }, [searchParams]);

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

      <ConditionHubSummary
        conditionName={
          apiEnglish ? (
            <LtrIsland>
              <span>{data.canonical_name}</span>
            </LtrIsland>
          ) : (
            data.canonical_name
          )
        }
        followed={data.followed}
        updatesTotal={updatesTotal}
        updatesPreviewCount={updates.length}
        latestUpdateTitle={updates[0]?.title ?? null}
        recruitingTrialCount={
          trials == null ? null : trials.filter((tr) => /recruit/i.test(tr.status || "")).length
        }
        trialsLoaded={trials !== null}
        onAsk={() => {
          trackAskAiHubCta({ condition_slug: data.slug, locale, cta_name: "ask" });
          setTab("ask");
        }}
        onTrials={() => {
          trackAskAiHubCta({ condition_slug: data.slug, locale, cta_name: "trials" });
          setTab("trials");
        }}
        onUpdates={() => {
          trackAskAiHubCta({ condition_slug: data.slug, locale, cta_name: "updates" });
          setTab("updates");
        }}
      />

      <div
        className="mt-6 flex gap-2 overflow-x-auto overflow-y-hidden border-b border-slate-200 pb-3 [-webkit-overflow-scrolling:touch]"
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
            className={`${tabBtn} shrink-0 ${tab === id ? tabActive : tabIdle}`}
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

              {threadLoading ? (
                <p className="mt-4 text-sm text-slate-500">{t("askThreadLoading")}</p>
              ) : null}
              {threadLoadError ? (
                <p className="mt-4 text-sm text-rose-600">{threadLoadError}</p>
              ) : null}

              {!threadLoading && (threadMessages.length > 0 || askLoading) ? (
                <ul
                  ref={threadListRef}
                  onScroll={onThreadScroll}
                  className="mt-4 max-h-[min(70vh,32rem)] list-none space-y-5 overflow-y-auto overscroll-contain rounded-xl border border-slate-100 bg-slate-50/50 p-4 [-webkit-overflow-scrolling:touch]"
                >
                  {threadMessages.map((m) => (
                    <li key={m.id} className="text-sm">
                      {m.role === "user" ? (
                        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            {t("askYourQuestionLabel")}
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-slate-800">{m.content}</p>
                        </div>
                      ) : (
                        <AskAiStoredAssistantMessage
                          message={{
                            id: m.id,
                            content: m.content,
                            structured_json: m.structured_json,
                            created_at: m.created_at,
                          }}
                          answerLtr={answerLtr}
                          askTextareaRef={askTextareaRef}
                          onPickFollowUp={(q) => setAskInput(q)}
                          analyticsContext={{ conditionSlug: data.slug, locale }}
                        />
                      )}
                      <time className="mt-1 block text-xs text-slate-400" dateTime={m.created_at}>
                        {formatAskThreadTime(m.created_at, locale)}
                      </time>
                    </li>
                  ))}
                  {askLoading ? (
                    <AskAiThreadThinking label={t("askThinkingInThread")} sublabel={t("askThinkingInThreadSub")} />
                  ) : null}
                </ul>
              ) : null}

              {data.followed && !threadLoading && threadMessages.length > 0 ? (
                <div className="mt-2 flex justify-end">
                  <button
                    type="button"
                    title={t("askNewConversationHint")}
                    className="text-xs font-medium text-slate-600 underline decoration-slate-300 underline-offset-2 hover:text-primary"
                    onClick={startNewConversation}
                  >
                    {t("askNewConversation")}
                  </button>
                </div>
              ) : null}

              {data.followed && !threadLoading && !askLoading && threadMessages.length === 0 ? (
                <div className="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-4">
                  <p className="text-sm font-medium text-slate-800">{t("askEmptyStateTitle")}</p>
                  <p className="mt-2 text-xs text-slate-600">{t("askEmptyStateHint")}</p>
                  <div className="mt-3 flex flex-col gap-2">
                    {(
                      [
                        ["treatments", "askEmptyStarter1"],
                        ["trials", "askEmptyStarter2"],
                        ["warnings", "askEmptyStarter3"],
                      ] as const
                    ).map(([promptKey, msgKey]) => (
                      <button
                        key={promptKey}
                        type="button"
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-start text-sm text-slate-700 hover:border-primary/40 hover:bg-slate-50"
                        onClick={() => {
                          trackAskAiEmptyStatePromptClick({
                            condition_slug: data.slug,
                            locale,
                            prompt_key: promptKey,
                          });
                          setAskInput(t(msgKey));
                          askTextareaRef.current?.focus();
                        }}
                      >
                        {t(msgKey)}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {data.followed && askAiUsage?.is_premium ? (
                <p className="mt-4 text-xs text-slate-500">{t("askQuestionsRemainingPremium")}</p>
              ) : null}

              {data.followed && askAiUsage && !askAiUsage.is_premium ? (
                <div
                  className={`mt-4 rounded-lg border px-3 py-2.5 text-sm ${
                    askAiUsage.is_limited
                      ? "border-rose-200 bg-rose-50/90 text-rose-950"
                      : askAiUsage.remaining !== null && askAiUsage.remaining <= 2
                        ? "border-amber-200 bg-amber-50/70 text-amber-950"
                        : "border-slate-200 bg-slate-50 text-slate-700"
                  }`}
                >
                  {askAiUsage.is_limited ? (
                    apiEnglish ? (
                      <LtrIsland>
                        <span className="whitespace-pre-line">{t("askDailyLimitMessage")}</span>
                      </LtrIsland>
                    ) : (
                      <p className="whitespace-pre-line">{t("askDailyLimitMessage")}</p>
                    )
                  ) : (
                    <>
                      <p className="font-medium">
                        {t("askQuestionsRemaining", { count: askAiUsage.remaining ?? 0 })}
                      </p>
                      {askAiUsage.in_grace_zone ? (
                        <p className="mt-1 text-xs text-slate-600">{t("askDailyLimitLowHint")}</p>
                      ) : null}
                    </>
                  )}
                </div>
              ) : null}

              <textarea
                ref={askTextareaRef}
                className="mt-4 min-h-24 w-full rounded-lg border border-slate-300 p-3 text-sm"
                placeholder={t("askPlaceholder", { slug: data.slug.toUpperCase() })}
                value={askInput}
                onChange={(e) => setAskInput(e.target.value)}
              />
              <button
                type="button"
                className="mt-3 rounded-lg bg-primary px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={
                  !askInput.trim() ||
                  askLoading ||
                  Boolean(askAiUsage && !askAiUsage.is_premium && askAiUsage.is_limited)
                }
                onClick={async () => {
                  if (!askInput.trim()) return;
                  pendingSendScrollRef.current = true;
                  skipAutoScrollRef.current = false;
                  setAskLoading(true);
                  setAskError("");
                  try {
                    const body: Record<string, unknown> = {
                      prompt: askInput.trim(),
                      answer_locale: locale === "he" ? "he" : "en",
                      mode: askMode,
                      document_ids: [],
                    };
                    if (conversationId) body.conversation_id = conversationId;
                    const res = await apiPost<Record<string, unknown>>(`/conditions/${data.slug}/ask-ai`, { body });
                    if (isAskAiLimitPostResponse(res)) {
                      const u = res.usage;
                      if (u) setAskAiUsage(u);
                      trackAskAiLimitBlocked({ condition_slug: data.slug, locale });
                      return;
                    }
                    const u = pickAskAiUsage(res);
                    if (u) setAskAiUsage(u);
                    setAskInput("");
                    await loadAskThread();
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
