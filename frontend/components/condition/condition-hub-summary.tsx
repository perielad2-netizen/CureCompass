"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

type Props = {
  conditionName: ReactNode;
  followed: boolean;
  updatesTotal: number | null;
  updatesPreviewCount: number;
  latestUpdateTitle: string | null;
  recruitingTrialCount: number | null;
  trialsLoaded: boolean;
  onAsk: () => void;
  onTrials: () => void;
  onUpdates: () => void;
};

export function ConditionHubSummary({
  conditionName,
  followed,
  updatesTotal,
  updatesPreviewCount,
  latestUpdateTitle,
  recruitingTrialCount,
  trialsLoaded,
  onAsk,
  onTrials,
  onUpdates,
}: Props) {
  const t = useTranslations("Condition");

  if (!followed) {
    return (
      <section
        aria-label={t("hubSummaryAria")}
        className="mt-6 rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-700"
      >
        <p className="font-medium text-slate-900">{t("hubFollowPromptTitle")}</p>
        <p className="mt-1 text-slate-600">{t("hubFollowPromptBody")}</p>
      </section>
    );
  }

  const totalLine =
    updatesTotal != null && updatesTotal > 0
      ? t("hubUpdatesCount", { count: updatesTotal })
      : updatesPreviewCount > 0
        ? t("hubUpdatesShowing", { count: updatesPreviewCount })
        : t("hubUpdatesNone");

  const trialsLine = !trialsLoaded
    ? t("hubTrialsLoading")
    : recruitingTrialCount != null && recruitingTrialCount > 0
      ? t("hubRecruitingCount", { count: recruitingTrialCount })
      : t("hubRecruitingNone");

  return (
    <section
      aria-label={t("hubSummaryAria")}
      className="mt-6 rounded-xl border border-slate-200 bg-white p-4 text-sm shadow-sm"
    >
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4">
        <h2 className="text-base font-semibold text-slate-900">{t("hubTitle")}</h2>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t("hubSubtitle")}</p>
      </div>
      <p className="mt-2 text-xs text-slate-600">{t("hubTrustedLine")}</p>

      <dl className="mt-3 space-y-2 text-slate-700">
        <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
          <dt className="shrink-0 font-medium text-slate-800">{t("hubConditionLabel")}</dt>
          <dd className="min-w-0 text-slate-700">{conditionName}</dd>
        </div>
        <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
          <dt className="shrink-0 font-medium text-slate-800">{t("hubUpdatesLabel")}</dt>
          <dd className="min-w-0">{totalLine}</dd>
        </div>
        {latestUpdateTitle ? (
          <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
            <dt className="shrink-0 font-medium text-slate-800">{t("hubLatestLabel")}</dt>
            <dd className="line-clamp-2 min-w-0 text-slate-600">{latestUpdateTitle}</dd>
          </div>
        ) : null}
        <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-2">
          <dt className="shrink-0 font-medium text-slate-800">{t("hubTrialsLabel")}</dt>
          <dd className="min-w-0">{trialsLine}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="min-h-[44px] rounded-full bg-primary px-4 py-2 text-sm font-medium text-white shadow-sm hover:opacity-95"
          onClick={onAsk}
        >
          {t("hubCtaAsk")}
        </button>
        <button
          type="button"
          className="min-h-[44px] rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          onClick={onTrials}
        >
          {t("hubCtaTrials")}
        </button>
        <button
          type="button"
          className="min-h-[44px] rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          onClick={onUpdates}
        >
          {t("hubCtaUpdates")}
        </button>
      </div>
    </section>
  );
}
