"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { BookmarkButton } from "@/components/condition/bookmark-button";
import { Badge } from "@/components/ui/badge";
import { LtrInline, LtrIsland } from "@/components/ui/ltr-island";
import { formatDateTimeMedium } from "@/lib/date-format";

type UpdateCardProps = {
  title: string;
  source: string;
  summary: string;
  whyItMatters: string;
  evidenceStage: string;
  /** When "he", summary/why are Hebrew from API (no LTR wrapper). */
  recapLocale?: "en" | "he";
  detailHref?: string;
  researchItemId?: string;
  bookmarked?: boolean;
  publishedAt?: string;
  itemType?: string;
  conditionName?: string;
  featured?: boolean;
  askHref?: string;
  askCtaLabel?: string;
  onAskClick?: () => void;
};

export function UpdateCard(props: UpdateCardProps) {
  const t = useTranslations("UpdateCard");

  function formatItemType(type: string): string {
    const m: Record<string, string> = {
      paper: t("typePaper"),
      trial: t("typeTrial"),
      regulatory: t("typeRegulatory"),
    };
    return m[type] ?? type.replace(/_/g, " ");
  }

  function formatPublishedLine(iso: string): { abs: string; relative: string | null } {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return { abs: iso, relative: null };
    const abs = formatDateTimeMedium(d);
    const now = Date.now();
    const ms = now - d.getTime();
    const days = Math.floor(ms / 86400000);
    let relative: string | null = null;
    if (days < 0) relative = t("relUpcoming");
    else if (days === 0) relative = t("relToday");
    else if (days === 1) relative = t("relYesterday");
    else if (days < 7) relative = t("relDaysAgo", { count: days });
    else if (days < 30) relative = t("relWeeksAgo", { count: Math.floor(days / 7) });
    return { abs, relative };
  }

  const titleEl = props.detailHref ? (
    <Link href={props.detailHref} className="text-primary hover:underline">
      {props.title}
    </Link>
  ) : (
    props.title
  );
  const showBookmark = Boolean(props.researchItemId);
  const dateLine =
    props.publishedAt != null && props.publishedAt !== "" ? formatPublishedLine(props.publishedAt) : null;
  const typeLabel = props.itemType ? formatItemType(props.itemType) : null;
  const rtlRecap = props.recapLocale === "he";

  return (
    <article
      className={`rounded-2xl border bg-white p-5 shadow-calm ${
        props.featured ? "border-primary/40 ring-1 ring-primary/20" : "border-slate-200"
      }`}
    >
      {props.featured ? (
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-primary">{t("mostRecent")}</p>
      ) : null}
      {props.conditionName || typeLabel || dateLine ? (
        <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
          {props.conditionName ? (
            <LtrIsland>
              <span className="font-medium text-slate-600">{props.conditionName}</span>
            </LtrIsland>
          ) : null}
          {props.conditionName && (typeLabel || dateLine) ? <span aria-hidden>·</span> : null}
          {typeLabel ? (
            <LtrIsland>
              <span>{typeLabel}</span>
            </LtrIsland>
          ) : null}
          {typeLabel && dateLine ? <span aria-hidden>·</span> : null}
          {dateLine ? (
            <time dateTime={props.publishedAt} title={dateLine.abs}>
              {dateLine.abs}
              {dateLine.relative ? ` (${dateLine.relative})` : ""}
            </time>
          ) : null}
        </div>
      ) : null}
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="min-w-0 flex-1 text-base font-semibold text-slate-900">
          <LtrIsland>{titleEl}</LtrIsland>
        </h3>
        <div className="flex shrink-0 items-start gap-2">
          {showBookmark ? (
            <BookmarkButton
              researchItemId={props.researchItemId!}
              initiallyBookmarked={props.bookmarked ?? false}
            />
          ) : null}
          {rtlRecap ? (
            <Badge>{props.evidenceStage}</Badge>
          ) : (
            <LtrIsland>
              <Badge>{props.evidenceStage}</Badge>
            </LtrIsland>
          )}
        </div>
      </div>
      {rtlRecap ? (
        <p className="text-sm text-slate-600">{props.summary}</p>
      ) : (
        <LtrIsland>
          <p className="text-sm text-slate-600">{props.summary}</p>
        </LtrIsland>
      )}
      <p className="mt-3 text-sm font-medium text-slate-800">
        {t("whyPrefix")}{" "}
        {rtlRecap ? <span>{props.whyItMatters}</span> : <LtrInline>{props.whyItMatters}</LtrInline>}
      </p>
      <div className="mt-4 text-xs text-slate-500">
        {t("sourcePrefix")} <LtrInline className="break-all">{props.source}</LtrInline>
      </div>
      {props.askHref ? (
        <div className="mt-3">
          <Link
            href={props.askHref}
            className="text-sm font-medium text-primary hover:underline"
            onClick={props.onAskClick}
          >
            {props.askCtaLabel ?? t("askAiAboutThis")}
          </Link>
        </div>
      ) : null}
    </article>
  );
}
