"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { LtrInline, LtrIsland } from "@/components/ui/ltr-island";
import { ApiError, apiDelete, apiGet, apiPost } from "@/lib/api";
import { formatDateTimeMedium } from "@/lib/date-format";

type DigestRow = {
  id: string;
  digest_type: string;
  title: string;
  condition_slug: string;
  condition_name: string;
  created_at: string;
  email_delivered: boolean;
};

type FollowedCond = { id: string; slug: string; name: string };

type DashboardPeek = { followed_conditions: FollowedCond[] };

export default function DigestsPage() {
  const t = useTranslations("Digests");
  const locale = useLocale();
  const [rows, setRows] = useState<DigestRow[]>([]);
  const [followed, setFollowed] = useState<FollowedCond[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [genType, setGenType] = useState<"daily" | "weekly" | "major">("daily");
  const [genBusy, setGenBusy] = useState(false);
  const [genMsg, setGenMsg] = useState<{ text: string; apiEnglish: boolean } | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [bootstrapDone, setBootstrapDone] = useState(false);

  const refreshDigests = useCallback(() => {
    if (!localStorage.getItem("cc_access_token")) return;
    apiGet<DigestRow[]>("/digests?limit=50")
      .then(setRows)
      .catch(() => setError(t("loadError")));
  }, [t]);

  useEffect(() => {
    if (!localStorage.getItem("cc_access_token")) {
      setError(t("signIn"));
      setBootstrapDone(true);
      return;
    }
    setError("");
    Promise.all([
      apiGet<DigestRow[]>("/digests?limit=50"),
      apiGet<DashboardPeek>("/dashboard"),
    ])
      .then(([digests, dash]) => {
        setRows(digests);
        const fc = dash.followed_conditions ?? [];
        setFollowed(fc);
        setSelectedSlug((prev) => {
          const next: Record<string, boolean> = {};
          for (const c of fc) {
            next[c.slug] = prev[c.slug] !== undefined ? Boolean(prev[c.slug]) : true;
          }
          return next;
        });
      })
      .catch(() => setError(t("loadError")))
      .finally(() => setBootstrapDone(true));
  }, [t]);

  const typeLabel = (digestType: string) => {
    if (digestType === "daily") return t("typeLabelDaily");
    if (digestType === "weekly") return t("typeLabelWeekly");
    if (digestType === "major") return t("typeLabelMajor");
    return digestType;
  };

  const selectedCount = followed.filter((c) => selectedSlug[c.slug]).length;
  const canCreate =
    bootstrapDone && followed.length > 0 && selectedCount > 0 && !genBusy;

  const conditionSlugsForApi = (): string[] => {
    if (followed.length === 0) return [];
    const picked = followed.filter((c) => selectedSlug[c.slug]).map((c) => c.slug);
    if (picked.length === 0 || picked.length === followed.length) return [];
    return picked;
  };

  const selectAllSlugs = () => {
    const next: Record<string, boolean> = {};
    for (const c of followed) next[c.slug] = true;
    setSelectedSlug(next);
  };

  const clearAllSlugs = () => {
    const next: Record<string, boolean> = {};
    for (const c of followed) next[c.slug] = false;
    setSelectedSlug(next);
  };

  return (
    <main className="container-page py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600">{t.rich("intro", { bold: (chunks) => <strong className="font-medium text-slate-800">{chunks}</strong> })}</p>
        </div>
        <div className="flex flex-col gap-1 text-sm font-medium ms-auto sm:items-end">
          <Link href="/dashboard" className="text-primary">
            {t("backToDashboard")}
          </Link>
          <Link href="/settings/notifications" className="text-primary">
            {t("notifPrefs")}
          </Link>
        </div>
      </div>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-calm">
        <h2 className="text-base font-semibold text-slate-900">{t("createSectionTitle")}</h2>
        <p className="mt-1 text-sm text-slate-600">{t("createSectionBody")}</p>
        <div className="mt-4">
          <label className="flex w-full max-w-xs flex-col gap-1 text-sm">
            <span className="text-slate-600">{t("type")}</span>
            <select
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={genType}
              onChange={(e) => setGenType(e.target.value as typeof genType)}
            >
              <option value="daily">{t("typeDaily")}</option>
              <option value="weekly">{t("typeWeekly")}</option>
              <option value="major">{t("typeMajor")}</option>
            </select>
          </label>
        </div>

        <div className="mt-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-medium text-slate-800">{t("conditionsLabel")}</span>
            {followed.length > 0 ? (
              <div className="flex flex-wrap gap-2 text-sm">
                <button type="button" className="font-medium text-primary hover:underline" onClick={selectAllSlugs}>
                  {t("selectAll")}
                </button>
                <span className="text-slate-300" aria-hidden>
                  |
                </span>
                <button type="button" className="font-medium text-primary hover:underline" onClick={clearAllSlugs}>
                  {t("selectNone")}
                </button>
              </div>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-slate-500">{t("conditionsHint")}</p>
          {bootstrapDone && followed.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600">{t("noFollowedConditions")}</p>
          ) : null}
          {followed.length > 0 ? (
            <ul className="mt-3 max-h-56 space-y-2 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50/80 p-3">
              {followed.map((c) => (
                <li key={c.id}>
                  <label className="flex cursor-pointer items-start gap-3 text-sm">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={Boolean(selectedSlug[c.slug])}
                      onChange={() =>
                        setSelectedSlug((prev) => ({
                          ...prev,
                          [c.slug]: !prev[c.slug],
                        }))
                      }
                    />
                    <span className="min-w-0">
                      <span className="font-medium text-slate-900">{c.name}</span>
                      <span className="mt-0.5 block text-xs text-slate-500">
                        <LtrInline>
                          <span>{c.slug}</span>
                        </LtrInline>
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          ) : null}
          {followed.length > 0 && selectedCount === 0 ? (
            <p className="mt-2 text-sm text-amber-800">{t("selectAtLeastOne")}</p>
          ) : null}
        </div>

        <button
          type="button"
          className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={!canCreate}
          onClick={async () => {
            setGenBusy(true);
            setGenMsg(null);
            try {
              const res = await apiPost<{ generated: number; ids: string[] }>("/digests/generate", {
                body: {
                  digest_type: genType,
                  condition_slugs: conditionSlugsForApi(),
                },
              });
              setGenMsg({ text: t("createdCount", { count: res.generated }), apiEnglish: false });
              refreshDigests();
            } catch (e) {
              if (e instanceof ApiError) {
                setGenMsg({ text: e.message, apiEnglish: locale === "he" });
              } else setGenMsg({ text: t("genFailed"), apiEnglish: false });
            } finally {
              setGenBusy(false);
            }
          }}
        >
          {genBusy ? t("working") : t("createBtn")}
        </button>

        {genMsg ? (
          <p className="mt-3 text-sm text-slate-700">
            {genMsg.apiEnglish ? (
              <LtrInline>
                <span>{genMsg.text}</span>
              </LtrInline>
            ) : (
              genMsg.text
            )}
          </p>
        ) : null}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">{t("listTitle")}</h2>
        <ul className="mt-4 space-y-3">
          {rows.length === 0 && !error ? (
            <li className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
              {t("listEmpty")}
            </li>
          ) : null}
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex flex-wrap items-stretch gap-0 rounded-2xl border border-slate-200 bg-white shadow-calm transition hover:border-slate-300"
            >
              <Link href={`/digests/${r.id}`} className="min-w-0 flex-1 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    {locale === "he" ? (
                      <>
                        <p className="font-medium text-slate-900">
                          {t("rowBriefingSummary", {
                            date: formatDateTimeMedium(r.created_at),
                          })}
                        </p>
                        <details className="mt-1.5 text-sm">
                          <summary className="cursor-pointer text-primary hover:underline">{t("rowShowAiHeadline")}</summary>
                          <div className="mt-1">
                            <LtrIsland>
                              <span className="text-slate-700">{r.title}</span>
                            </LtrIsland>
                          </div>
                        </details>
                      </>
                    ) : (
                      <p className="font-medium text-slate-900">{r.title}</p>
                    )}
                  </div>
                  <span className="shrink-0 text-xs font-medium uppercase text-slate-500">{typeLabel(r.digest_type)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  <LtrInline>
                    <span>
                      {r.condition_name} · {formatDateTimeMedium(r.created_at)}
                      {r.email_delivered ? ` · ${t("emailed")}` : ""}
                    </span>
                  </LtrInline>
                </p>
              </Link>
              <div className="flex shrink-0 border-s border-slate-100">
                <button
                  type="button"
                  className="px-4 py-3 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                  disabled={deletingId === r.id}
                  title={t("deleteTitle")}
                  onClick={async (e) => {
                    e.preventDefault();
                    const short = r.title.length > 60 ? `${r.title.slice(0, 60)}…` : r.title;
                    if (!confirm(t("deleteConfirm", { title: short }))) return;
                    setDeletingId(r.id);
                    try {
                      await apiDelete(`/digests/${encodeURIComponent(r.id)}`);
                      setRows((prev) => prev.filter((x) => x.id !== r.id));
                    } catch (err) {
                      if (err instanceof ApiError) {
                        setError(err.message);
                      } else setError(t("deleteError"));
                    } finally {
                      setDeletingId(null);
                    }
                  }}
                >
                  {deletingId === r.id ? "…" : t("delete")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
