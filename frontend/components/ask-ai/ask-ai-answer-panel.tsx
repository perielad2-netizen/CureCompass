"use client";

import type { ReactNode, RefObject } from "react";
import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Beaker,
  BookOpen,
  ChevronDown,
  ClipboardList,
  HelpCircle,
  ListChecks,
  ShieldCheck,
} from "lucide-react";
import { LtrIsland } from "@/components/ui/ltr-island";
import {
  type AskAiAnswerResponse,
  askAnswerHasStructuredFields,
  hasMeaningfulText,
} from "@/components/ask-ai/ask-ai-types";
import { inferSourceKind, SourceKindBadge, type SourceKind } from "@/components/ask-ai/source-kind-badge";
import {
  trackAskAiFollowupChip,
  trackAskAiSectionExpand,
  trackAskAiToggleView,
  trackAskAiTrustedSourceClick,
} from "@/lib/product-analytics";

type DetailMode = "simple" | "detailed";

export type AskAiAnalyticsContext = {
  conditionSlug: string;
  locale: string;
};

type Props = {
  answer: AskAiAnswerResponse;
  /** When true, wrap answer prose in LtrIsland (e.g. Hebrew UI with English API text). */
  answerLtr: boolean;
  onPickFollowUp: (question: string) => void;
  askTextareaRef: RefObject<HTMLTextAreaElement | null>;
  /** Optional: product analytics (never throws). */
  analyticsContext?: AskAiAnalyticsContext;
  /** Reset Simple/Detailed when switching messages (e.g. thread history). */
  instanceKey?: string;
  /** Tighter top spacing when stacked in a thread. */
  embeddedInThread?: boolean;
};

function Wrap({ answerLtr, children }: { answerLtr: boolean; children: ReactNode }) {
  return answerLtr ? <LtrIsland>{children}</LtrIsland> : <>{children}</>;
}

function CollapsibleBlock({
  id,
  icon: Icon,
  title,
  defaultOpen,
  children,
  sectionName,
  analytics,
}: {
  id: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
  sectionName: string;
  analytics?: AskAiAnalyticsContext;
}) {
  return (
    <details
      id={id}
      className="group rounded-lg border border-slate-200 bg-white"
      open={defaultOpen}
      onToggle={(e) => {
        const el = e.currentTarget;
        if (el.open && analytics) {
          trackAskAiSectionExpand({
            condition_slug: analytics.conditionSlug,
            locale: analytics.locale,
            section_name: sectionName,
          });
        }
      }}
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-3 text-start text-sm font-medium text-slate-900 [&::-webkit-details-marker]:hidden">
        <Icon className="h-4 w-4 shrink-0 text-slate-500" aria-hidden />
        <span className="min-w-0 flex-1">{title}</span>
        <ChevronDown
          className="h-4 w-4 shrink-0 text-slate-400 transition-transform group-open:rotate-180"
          aria-hidden
        />
      </summary>
      <div className="border-t border-slate-100 px-3 pb-3 pt-2 text-sm leading-relaxed text-slate-700">{children}</div>
    </details>
  );
}

function ProseBlocks({ text }: { text: string }) {
  const parts = text.split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
  if (!parts.length) return null;
  return (
    <div className="space-y-2">
      {parts.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </div>
  );
}

function badgeLabelForKind(kind: SourceKind, t: (k: string) => string): string {
  switch (kind) {
    case "pubmed":
      return t("askBadgePubmed");
    case "clinicaltrials":
      return t("askBadgeTrialsGov");
    case "fda":
      return t("askBadgeFda");
    case "orphanet":
      return t("askBadgeOrphanet");
    case "medlineplus":
      return t("askBadgeMedlinePlus");
    case "document":
      return t("askBadgeDocument");
    default:
      return t("askBadgeSource");
  }
}

export function AskAiAnswerPanel({
  answer,
  answerLtr,
  onPickFollowUp,
  askTextareaRef,
  analyticsContext,
  instanceKey,
  embeddedInThread,
}: Props) {
  const topCls = embeddedInThread ? "mt-0" : "mt-4";
  const t = useTranslations("Condition");
  const [mode, setMode] = useState<DetailMode>("simple");
  const structured = askAnswerHasStructuredFields(answer);

  useEffect(() => {
    setMode("simple");
  }, [
    instanceKey,
    answer.direct_answer,
    answer.what_changed_recently,
    answer.evidence_strength,
    answer.available_now_or_experimental,
  ]);

  const followUps = useMemo(() => {
    const keys = [
      "askFollowUpTreatments",
      "askFollowUpTrials",
      "askFollowUpWarnings",
      "askFollowUpRecent",
      "askFollowUpApprovedVsExperimental",
    ] as const;
    const out: { key: (typeof keys)[number]; text: string }[] = [];
    const da = `${answer.direct_answer} ${answer.simple_explanation ?? ""}`.toLowerCase();
    if (/\btrial\b|clinical|nct|ניסוי/.test(da)) {
      out.push({ key: "askFollowUpTrials", text: t("askFollowUpTrials") });
    }
    if (/warn|emergency|seek care|side effect|תופע|מצב חירום/.test(da)) {
      out.push({ key: "askFollowUpWarnings", text: t("askFollowUpWarnings") });
    }
    for (const k of keys) {
      if (out.length >= 5) break;
      if (!out.some((x) => x.key === k)) out.push({ key: k, text: t(k) });
    }
    return out.slice(0, 5).map((x) => ({ id: x.key, text: x.text }));
  }, [answer.direct_answer, answer.simple_explanation, t]);

  const showDetailedBlocks = mode === "detailed";

  const warningText = answer.warning_signs_or_when_to_seek_care;
  const hasWarning = structured && hasMeaningfulText(warningText);

  if (!structured) {
    return (
      <div className={`${topCls} space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm`}>
        <div>
          <p className="font-medium text-slate-900">{t("directAnswer")}</p>
          <Wrap answerLtr={answerLtr}>
            <p className="text-slate-700">{answer.direct_answer}</p>
          </Wrap>
        </div>
        <div>
          <p className="font-medium text-slate-900">{t("whatChanged")}</p>
          <Wrap answerLtr={answerLtr}>
            <p className="text-slate-700">{answer.what_changed_recently}</p>
          </Wrap>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Wrap answerLtr={answerLtr}>
            <p className="text-slate-700">
              <span className="font-medium text-slate-900">{t("evidence")}</span> {answer.evidence_strength}
            </p>
          </Wrap>
          <Wrap answerLtr={answerLtr}>
            <p className="text-slate-700">
              <span className="font-medium text-slate-900">{t("availability")}</span>{" "}
              {answer.available_now_or_experimental}
            </p>
          </Wrap>
        </div>
        {!!answer.suggested_doctor_questions?.length && (
          <div>
            <p className="font-medium text-slate-900">{t("doctorQuestions")}</p>
            <Wrap answerLtr={answerLtr}>
              <ul className="mt-1 list-disc space-y-1 ps-5 text-slate-700">
                {answer.suggested_doctor_questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </Wrap>
          </div>
        )}
        {!!answer.sources?.length && (
          <div>
            <p className="font-medium text-slate-900">{t("sources")}</p>
            <p className="mt-1 text-xs text-slate-600">{t("askTrustedFraming")}</p>
            <Wrap answerLtr={answerLtr}>
              <ul className="mt-1 space-y-2">
                {answer.sources.map((s) => (
                  <li key={`${s.title}-${s.source_url || s.document_id || ""}`} className="flex flex-wrap items-center gap-2">
                    {(() => {
                      const kind = inferSourceKind(s.item_type || "", s.source_url || "");
                      return <SourceKindBadge kind={kind} label={badgeLabelForKind(kind, t)} />;
                    })()}
                    {s.source_url ? (
                      <a
                        className="text-primary underline"
                        href={s.source_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={() => {
                          if (!analyticsContext) return;
                          const kind = inferSourceKind(s.item_type || "", s.source_url || "");
                          trackAskAiTrustedSourceClick({
                            condition_slug: analyticsContext.conditionSlug,
                            locale: analyticsContext.locale,
                            source_name: s.title,
                            source_kind: kind,
                          });
                        }}
                      >
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
            </Wrap>
          </div>
        )}
        <FollowUpChips
          chips={followUps}
          hasStructuredFields={structured}
          analyticsContext={analyticsContext}
          onPick={(q) => {
            onPickFollowUp(q);
            askTextareaRef.current?.focus();
            askTextareaRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
          }}
          t={t}
        />
      </div>
    );
  }

  return (
    <div className={`${topCls} space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm`}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs font-medium text-slate-600">{t("askTrustedFraming")}</p>
        <div
          className="inline-flex rounded-full border border-slate-200 bg-white p-0.5 text-xs font-medium"
          role="group"
          aria-label={t("askViewModeAria")}
        >
          <button
            type="button"
            className={`rounded-full px-3 py-1.5 transition-colors ${mode === "simple" ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-50"}`}
            onClick={() => {
              if (analyticsContext && mode !== "simple") {
                trackAskAiToggleView({
                  condition_slug: analyticsContext.conditionSlug,
                  locale: analyticsContext.locale,
                  selected_view: "simple",
                  has_structured_fields: structured,
                });
              }
              setMode("simple");
            }}
          >
            {t("askViewSimple")}
          </button>
          <button
            type="button"
            className={`rounded-full px-3 py-1.5 transition-colors ${mode === "detailed" ? "bg-slate-800 text-white" : "text-slate-600 hover:bg-slate-50"}`}
            onClick={() => {
              if (analyticsContext && mode !== "detailed") {
                trackAskAiToggleView({
                  condition_slug: analyticsContext.conditionSlug,
                  locale: analyticsContext.locale,
                  selected_view: "detailed",
                  has_structured_fields: structured,
                });
              }
              setMode("detailed");
            }}
          >
            {t("askViewDetailed")}
          </button>
        </div>
      </div>

      <div>
        <p className="font-medium text-slate-900">{t("directAnswer")}</p>
        <Wrap answerLtr={answerLtr}>
          <ProseBlocks text={answer.direct_answer} />
        </Wrap>
      </div>

      {hasMeaningfulText(answer.simple_explanation) ? (
        <div>
          <p className="font-medium text-slate-900">{t("askSimpleExplanation")}</p>
          <Wrap answerLtr={answerLtr}>
            <ProseBlocks text={answer.simple_explanation!} />
          </Wrap>
        </div>
      ) : null}

      {hasWarning && (mode === "simple" || mode === "detailed") ? (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50/90 px-3 py-3 text-slate-900"
          role="status"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-amber-950">{t("askWarningSignsTitle")}</p>
              <Wrap answerLtr={answerLtr}>
                <div className="mt-1 text-sm text-amber-950/95">
                  <ProseBlocks text={warningText!} />
                </div>
              </Wrap>
            </div>
          </div>
        </div>
      ) : null}

      {showDetailedBlocks && (
        <div className="space-y-2">
          {answer.key_facts?.some((f) => hasMeaningfulText(f)) ? (
            <CollapsibleBlock
              id="cc-key-facts"
              icon={ListChecks}
              title={t("askKeyFacts")}
              defaultOpen={false}
              sectionName="key_facts"
              analytics={analyticsContext}
            >
              <Wrap answerLtr={answerLtr}>
                <ul className="list-disc space-y-1 ps-5">
                  {answer.key_facts!.filter((f) => hasMeaningfulText(f)).map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </Wrap>
            </CollapsibleBlock>
          ) : null}

          {hasMeaningfulText(answer.approved_treatments) ? (
            <CollapsibleBlock
              id="cc-approved"
              icon={ShieldCheck}
              title={t("askApprovedTreatments")}
              defaultOpen={false}
              sectionName="approved_treatments"
              analytics={analyticsContext}
            >
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">{t("askSectionApprovedHint")}</p>
              <Wrap answerLtr={answerLtr}>
                <ProseBlocks text={answer.approved_treatments!} />
              </Wrap>
            </CollapsibleBlock>
          ) : null}

          {hasMeaningfulText(answer.experimental_or_emerging_options) ? (
            <CollapsibleBlock
              id="cc-experimental"
              icon={Beaker}
              title={t("askExperimental")}
              defaultOpen={false}
              sectionName="experimental_or_emerging"
              analytics={analyticsContext}
            >
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">{t("askSectionExperimentalHint")}</p>
              <Wrap answerLtr={answerLtr}>
                <ProseBlocks text={answer.experimental_or_emerging_options!} />
              </Wrap>
            </CollapsibleBlock>
          ) : null}

          {hasMeaningfulText(answer.relevant_clinical_trials) ? (
            <CollapsibleBlock
              id="cc-trials"
              icon={ClipboardList}
              title={t("askClinicalTrialsSection")}
              defaultOpen={false}
              sectionName="relevant_clinical_trials"
              analytics={analyticsContext}
            >
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">{t("askSectionTrialsHint")}</p>
              <Wrap answerLtr={answerLtr}>
                <ProseBlocks text={answer.relevant_clinical_trials!} />
              </Wrap>
            </CollapsibleBlock>
          ) : null}

          {hasMeaningfulText(answer.what_is_uncertain) ? (
            <CollapsibleBlock
              id="cc-uncertain"
              icon={HelpCircle}
              title={t("askUncertain")}
              defaultOpen={false}
              sectionName="what_is_uncertain"
              analytics={analyticsContext}
            >
              <Wrap answerLtr={answerLtr}>
                <ProseBlocks text={answer.what_is_uncertain!} />
              </Wrap>
            </CollapsibleBlock>
          ) : null}

          <div>
            <p className="font-medium text-slate-900">{t("whatChanged")}</p>
            <Wrap answerLtr={answerLtr}>
              <p className="text-slate-700">{answer.what_changed_recently}</p>
            </Wrap>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Wrap answerLtr={answerLtr}>
              <p className="text-slate-700">
                <span className="font-medium text-slate-900">{t("evidence")}</span> {answer.evidence_strength}
              </p>
            </Wrap>
            <Wrap answerLtr={answerLtr}>
              <p className="text-slate-700">
                <span className="font-medium text-slate-900">{t("availability")}</span>{" "}
                {answer.available_now_or_experimental}
              </p>
            </Wrap>
          </div>
          <p className="text-xs text-slate-500">{t("askEvidenceContextNote")}</p>
          {!!answer.suggested_doctor_questions?.length && (
            <div>
              <p className="font-medium text-slate-900">{t("doctorQuestions")}</p>
              <Wrap answerLtr={answerLtr}>
                <ul className="mt-1 list-disc space-y-1 ps-5 text-slate-700">
                  {answer.suggested_doctor_questions.map((q) => (
                    <li key={q}>{q}</li>
                  ))}
                </ul>
              </Wrap>
            </div>
          )}
          {!!answer.sources?.length && (
            <div>
              <p className="font-medium text-slate-900">{t("sources")}</p>
              <Wrap answerLtr={answerLtr}>
                <ul className="mt-1 space-y-2">
                  {answer.sources.map((s) => (
                    <li key={`${s.title}-${s.source_url || s.document_id || ""}`} className="flex flex-wrap items-center gap-2">
                      {(() => {
                        const kind = inferSourceKind(s.item_type || "", s.source_url || "");
                        return <SourceKindBadge kind={kind} label={badgeLabelForKind(kind, t)} />;
                      })()}
                      {s.source_url ? (
                        <a
                          className="text-primary underline"
                          href={s.source_url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={() => {
                            if (!analyticsContext) return;
                            const kind = inferSourceKind(s.item_type || "", s.source_url || "");
                            trackAskAiTrustedSourceClick({
                              condition_slug: analyticsContext.conditionSlug,
                              locale: analyticsContext.locale,
                              source_name: s.title,
                              source_kind: kind,
                            });
                          }}
                        >
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
              </Wrap>
            </div>
          )}
        </div>
      )}

      {answer.trusted_sources && answer.trusted_sources.length > 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-slate-500" aria-hidden />
            <p className="font-medium text-slate-900">{t("askTrustedSourcesTitle")}</p>
          </div>
          <p className="mt-1 text-xs text-slate-600">{t("askTrustedSourcesSub")}</p>
          <ul className="mt-3 space-y-3">
            {answer.trusted_sources.map((src) => {
              const kind = inferSourceKind(src.source_name, src.source_url);
              return (
                <li key={`${src.title}-${src.source_url}`} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <SourceKindBadge kind={kind} label={badgeLabelForKind(kind, t)} />
                    {src.source_url ? (
                      <a
                        href={src.source_url}
                        className="font-medium text-primary hover:underline"
                        target="_blank"
                        rel="noreferrer"
                        onClick={() => {
                          if (!analyticsContext) return;
                          const kind = inferSourceKind(src.source_name, src.source_url);
                          trackAskAiTrustedSourceClick({
                            condition_slug: analyticsContext.conditionSlug,
                            locale: analyticsContext.locale,
                            source_name: src.source_name || src.title,
                            source_kind: kind,
                          });
                        }}
                      >
                        {src.title || src.source_name}
                      </a>
                    ) : (
                      <span className="font-medium text-slate-900">{src.title || src.source_name}</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{src.source_name}</p>
                  <Wrap answerLtr={answerLtr}>
                    <p className="mt-1 text-xs text-slate-600">{src.short_reason_used}</p>
                  </Wrap>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      <FollowUpChips
        chips={followUps}
        hasStructuredFields={structured}
        analyticsContext={analyticsContext}
        onPick={(q) => {
          onPickFollowUp(q);
          askTextareaRef.current?.focus();
          askTextareaRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
        }}
        t={t}
      />
    </div>
  );
}

type FollowUpChipItem = { id: string; text: string };

function FollowUpChips({
  chips,
  onPick,
  t,
  analyticsContext,
  hasStructuredFields,
}: {
  chips: FollowUpChipItem[];
  onPick: (q: string) => void;
  t: (k: string) => string;
  analyticsContext?: AskAiAnalyticsContext;
  hasStructuredFields: boolean;
}) {
  return (
    <div className="pt-1">
      <p className="text-xs font-medium text-slate-600">{t("askFollowUpTitle")}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {chips.map((c, i) => (
          <button
            key={c.id}
            type="button"
            className="min-h-[44px] max-w-full rounded-full border border-slate-200 bg-white px-3 py-2 text-left text-xs font-medium text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
            onClick={() => {
              if (analyticsContext) {
                trackAskAiFollowupChip({
                  condition_slug: analyticsContext.conditionSlug,
                  locale: analyticsContext.locale,
                  chip_key: c.id,
                  position_index: i,
                  has_structured_fields: hasStructuredFields,
                });
              }
              onPick(c.text);
            }}
          >
            {c.text}
          </button>
        ))}
      </div>
    </div>
  );
}
