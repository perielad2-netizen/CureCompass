"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useParams } from "next/navigation";
import { BookmarkButton } from "@/components/condition/bookmark-button";
import { Badge } from "@/components/ui/badge";
import { LtrInline, LtrIsland } from "@/components/ui/ltr-island";
import { ApiError, apiGet } from "@/lib/api";

type UpdateDetail = {
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
  confidence_level: string;
  applicability_age_group: string;
  hype_risk: string;
  abstract_or_body: string;
  bookmarked: boolean;
};

export default function UpdateDetailPage() {
  const locale = useLocale();
  const tCard = useTranslations("UpdateCard");
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : params.id?.[0] ?? "";
  const [data, setData] = useState<UpdateDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    apiGet<UpdateDetail>(`/updates/${encodeURIComponent(id)}`, { searchParams: { locale } })
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setError("This update was not found.");
        else setError("Could not load this update.");
      });
  }, [id, locale]);

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
        <p className="text-slate-600">{id ? "Loading…" : "Missing update."}</p>
      </main>
    );
  }

  const rtlRecap = data.recap_locale === "he";

  return (
    <main className="container-page max-w-3xl py-8">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {data.item_type.replace(/_/g, " ")} · {data.source_name}
      </p>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <h1 className="min-w-0 flex-1 text-2xl font-semibold text-slate-900">
          <LtrIsland>
            <span>{data.title}</span>
          </LtrIsland>
        </h1>
        <BookmarkButton researchItemId={data.id} initiallyBookmarked={data.bookmarked} compact={false} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
        {rtlRecap ? (
          <Badge>{data.evidence_stage_label}</Badge>
        ) : (
          <LtrIsland>
            <Badge>{data.evidence_stage_label}</Badge>
          </LtrIsland>
        )}
        <span>Confidence: {data.confidence_level}</span>
        <span>Applies to: {data.applicability_age_group}</span>
        <time dateTime={data.published_at}>{new Date(data.published_at).toLocaleDateString()}</time>
      </div>
      <p className="mt-2 text-xs text-slate-500">Hype / risk note: {data.hype_risk.replace(/_/g, " ")}</p>
      {rtlRecap ? (
        <p className="mt-6 text-sm text-slate-600">{data.summary}</p>
      ) : (
        <LtrIsland>
          <p className="mt-6 text-sm text-slate-600">{data.summary}</p>
        </LtrIsland>
      )}
      <p className="mt-4 text-sm font-medium text-slate-800">
        {tCard("whyPrefix")}{" "}
        {rtlRecap ? <span>{data.why_it_matters}</span> : <LtrInline>{data.why_it_matters}</LtrInline>}
      </p>
      <section className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <h2 className="text-sm font-semibold text-slate-900">From the source</h2>
        <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words font-sans text-sm text-slate-700">
          {data.abstract_or_body}
        </pre>
      </section>
      <div className="mt-8 flex flex-wrap gap-3">
        <a
          href={data.source_url}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white"
        >
          Open original source
        </a>
        <Link href="/dashboard" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800">
          Dashboard
        </Link>
      </div>
      <p className="mt-8 text-xs text-slate-500">
        Educational research information only. Not personal medical advice. Discuss questions with your clinician.
      </p>
    </main>
  );
}
