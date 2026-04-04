import Link from "next/link";
import type { Route } from "next";
import { BookmarkButton } from "@/components/condition/bookmark-button";
import { Badge } from "@/components/ui/badge";

type UpdateCardProps = {
  title: string;
  source: string;
  summary: string;
  whyItMatters: string;
  evidenceStage: string;
  /** When set, title links to the update detail page */
  detailHref?: string;
  /** When set with a real research item id, shows save control */
  researchItemId?: string;
  bookmarked?: boolean;
  /** ISO date string from API */
  publishedAt?: string;
  /** e.g. paper, trial, regulatory */
  itemType?: string;
  conditionName?: string;
  /** Highlight as the newest item in a list */
  featured?: boolean;
};

function formatItemType(t: string): string {
  const m: Record<string, string> = {
    paper: "Published paper",
    trial: "Clinical trial",
    regulatory: "Regulatory / FDA",
  };
  return m[t] ?? t.replace(/_/g, " ");
}

function formatPublishedLine(iso: string): { abs: string; relative: string | null } {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { abs: iso, relative: null };
  const abs = d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const now = Date.now();
  const ms = now - d.getTime();
  const days = Math.floor(ms / 86400000);
  let relative: string | null = null;
  if (days < 0) relative = "Upcoming date";
  else if (days === 0) relative = "Today";
  else if (days === 1) relative = "Yesterday";
  else if (days < 7) relative = `${days} days ago`;
  else if (days < 30) relative = `${Math.floor(days / 7)} weeks ago`;
  return { abs, relative };
}

export function UpdateCard(props: UpdateCardProps) {
  const titleEl = props.detailHref ? (
    <Link href={props.detailHref as Route} className="text-primary hover:underline">
      {props.title}
    </Link>
  ) : (
    props.title
  );
  const showBookmark = Boolean(props.researchItemId);
  const dateLine =
    props.publishedAt != null && props.publishedAt !== ""
      ? formatPublishedLine(props.publishedAt)
      : null;
  const typeLabel = props.itemType ? formatItemType(props.itemType) : null;

  return (
    <article
      className={`rounded-2xl border bg-white p-5 shadow-calm ${
        props.featured ? "border-primary/40 ring-1 ring-primary/20" : "border-slate-200"
      }`}
    >
      {props.featured ? (
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-primary">Most recent</p>
      ) : null}
      {props.conditionName || typeLabel || dateLine ? (
        <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
          {props.conditionName ? (
            <span className="font-medium text-slate-600">{props.conditionName}</span>
          ) : null}
          {props.conditionName && (typeLabel || dateLine) ? <span aria-hidden>·</span> : null}
          {typeLabel ? <span>{typeLabel}</span> : null}
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
        <h3 className="min-w-0 flex-1 text-base font-semibold text-slate-900">{titleEl}</h3>
        <div className="flex shrink-0 items-start gap-2">
          {showBookmark ? (
            <BookmarkButton
              researchItemId={props.researchItemId!}
              initiallyBookmarked={props.bookmarked ?? false}
            />
          ) : null}
          <Badge>{props.evidenceStage}</Badge>
        </div>
      </div>
      <p className="text-sm text-slate-600">{props.summary}</p>
      <p className="mt-3 text-sm font-medium text-slate-800">Why it matters: {props.whyItMatters}</p>
      <div className="mt-4 text-xs text-slate-500">Source: {props.source}</div>
    </article>
  );
}
