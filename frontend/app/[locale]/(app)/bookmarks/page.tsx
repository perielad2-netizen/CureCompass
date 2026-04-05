"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { LtrIsland } from "@/components/ui/ltr-island";
import { ApiError, apiDelete, apiGet } from "@/lib/api";

type BookmarkRow = {
  research_item_id: string;
  created_at: string;
  condition_slug: string;
  title: string;
  source_name: string;
  source_url: string;
  evidence_stage_label: string;
  summary: string;
  recap_locale?: "en" | "he";
};

export default function BookmarksPage() {
  const t = useTranslations("Bookmarks");
  const locale = useLocale();
  const apiEnglish = locale === "he";
  const [rows, setRows] = useState<BookmarkRow[] | null>(null);
  const [error, setError] = useState("");
  const [removing, setRemoving] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!localStorage.getItem("cc_access_token")) {
      setError(t("signIn"));
      setRows([]);
      return;
    }
    apiGet<BookmarkRow[]>("/bookmarks", { searchParams: { locale } })
      .then(setRows)
      .catch(() => {
        setError(t("loadError"));
        setRows([]);
      });
  }, [t, locale]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="container-page py-8">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      <p className="mt-1 text-sm text-slate-600">{t("intro")}</p>
      <Link href="/dashboard" className="mt-2 inline-block text-sm font-medium text-primary">
        {t("backToDashboard")}
      </Link>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      {!error && rows === null ? (
        <p className="mt-6 text-sm text-slate-600">{t("loading")}</p>
      ) : !error && rows?.length === 0 ? (
        <p className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
          {t("empty")}
        </p>
      ) : !error && rows && rows.length > 0 ? (
        <ul className="mt-6 space-y-4">
          {rows.map((b) => (
            <li key={b.research_item_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-calm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  {apiEnglish && b.recap_locale !== "he" ? (
                    <LtrIsland>
                      <p className="text-xs font-medium uppercase text-slate-500">{b.evidence_stage_label}</p>
                    </LtrIsland>
                  ) : (
                    <p className="text-xs font-medium uppercase text-slate-500">{b.evidence_stage_label}</p>
                  )}
                  <Link
                    href={`/updates/${encodeURIComponent(b.research_item_id)}`}
                    className="mt-1 block text-lg font-semibold text-slate-900 hover:text-primary"
                  >
                    {apiEnglish ? (
                      <LtrIsland>
                        <span>{b.title}</span>
                      </LtrIsland>
                    ) : (
                      b.title
                    )}
                  </Link>
                  <p className="mt-2 text-sm text-slate-600">
                    {apiEnglish && b.recap_locale !== "he" ? (
                      <LtrIsland>
                        <span>{b.summary}</span>
                      </LtrIsland>
                    ) : (
                      b.summary
                    )}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    {apiEnglish ? (
                      <LtrIsland>
                        <span>
                          {b.source_name}
                          {b.condition_slug ? (
                            <>
                              {" · "}
                              <Link href={`/conditions/${b.condition_slug}`} className="text-primary hover:underline">
                                {b.condition_slug}
                              </Link>
                            </>
                          ) : null}
                        </span>
                      </LtrIsland>
                    ) : (
                      <>
                        {b.source_name}
                        {b.condition_slug ? (
                          <>
                            {" · "}
                            <Link href={`/conditions/${b.condition_slug}`} className="text-primary hover:underline">
                              {b.condition_slug}
                            </Link>
                          </>
                        ) : null}
                      </>
                    )}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">
                  <a
                    href={b.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    {t("originalSource")}
                  </a>
                  <button
                    type="button"
                    className="text-sm font-medium text-rose-600 hover:text-rose-700 disabled:opacity-50"
                    disabled={removing === b.research_item_id}
                    onClick={async () => {
                      setRemoving(b.research_item_id);
                      try {
                        await apiDelete(`/bookmarks/${encodeURIComponent(b.research_item_id)}`);
                        setRows((prev) => prev?.filter((x) => x.research_item_id !== b.research_item_id) ?? []);
                      } catch (e) {
                        if (e instanceof ApiError) setError(e.message);
                        else setError(t("removeError"));
                      } finally {
                        setRemoving(null);
                      }
                    }}
                  >
                    {removing === b.research_item_id ? "…" : t("remove")}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
