"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { LtrIsland } from "@/components/ui/ltr-island";
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

export default function DigestsPage() {
  const t = useTranslations("Digests");
  const locale = useLocale();
  const [rows, setRows] = useState<DigestRow[]>([]);
  const [error, setError] = useState("");
  const [genType, setGenType] = useState<"daily" | "weekly" | "major">("daily");
  const [genSlug, setGenSlug] = useState("");
  const [genBusy, setGenBusy] = useState(false);
  const [genMsg, setGenMsg] = useState<{ text: string; apiEnglish: boolean } | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = () => {
    if (!localStorage.getItem("cc_access_token")) {
      setError(t("signIn"));
      return;
    }
    apiGet<DigestRow[]>("/digests?limit=50")
      .then(setRows)
      .catch(() => setError(t("loadError")));
  };

  useEffect(() => {
    load();
  }, []);

  const typeLabel = (digestType: string) => {
    if (digestType === "daily") return t("typeLabelDaily");
    if (digestType === "weekly") return t("typeLabelWeekly");
    if (digestType === "major") return t("typeLabelMajor");
    return digestType;
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
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
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
          <label className="flex min-w-[10rem] flex-col gap-1 text-sm">
            <span className="text-slate-600">{t("slugOptional")}</span>
            <input
              className="rounded-lg border border-slate-300 px-3 py-2"
              placeholder={t("slugPlaceholder")}
              value={genSlug}
              onChange={(e) => setGenSlug(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            disabled={genBusy}
            onClick={async () => {
              setGenBusy(true);
              setGenMsg(null);
              try {
                const res = await apiPost<{ generated: number; ids: string[] }>("/digests/generate", {
                  body: {
                    digest_type: genType,
                    condition_slug: genSlug.trim() || null,
                  },
                });
                setGenMsg({ text: t("createdCount", { count: res.generated }), apiEnglish: false });
                load();
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
        </div>
        {genMsg ? (
          <p className="mt-3 text-sm text-slate-700">
            {genMsg.apiEnglish ? (
              <LtrIsland>
                <span>{genMsg.text}</span>
              </LtrIsland>
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
                  <LtrIsland>
                    <span>
                      {r.condition_name} · {formatDateTimeMedium(r.created_at)}
                      {r.email_delivered ? ` · ${t("emailed")}` : ""}
                    </span>
                  </LtrIsland>
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
