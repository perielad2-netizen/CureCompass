"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
};

export default function BookmarksPage() {
  const [rows, setRows] = useState<BookmarkRow[] | null>(null);
  const [error, setError] = useState("");
  const [removing, setRemoving] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!localStorage.getItem("cc_access_token")) {
      setError("Please sign in to view bookmarks.");
      setRows([]);
      return;
    }
    apiGet<BookmarkRow[]>("/bookmarks")
      .then(setRows)
      .catch(() => {
        setError("Could not load bookmarks.");
        setRows([]);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="container-page py-8">
      <h1 className="text-2xl font-semibold text-slate-900">Saved updates</h1>
      <p className="mt-1 text-sm text-slate-600">
        Bookmarks from your research feed. Open an update to remove it from here or use Remove.
      </p>
      <Link href="/dashboard" className="mt-2 inline-block text-sm font-medium text-primary">
        ← Dashboard
      </Link>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      {!error && rows === null ? (
        <p className="mt-6 text-sm text-slate-600">Loading…</p>
      ) : !error && rows?.length === 0 ? (
        <p className="mt-6 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
          No bookmarks yet. Use “Save” on an update card on the dashboard or condition page.
        </p>
      ) : !error && rows && rows.length > 0 ? (
        <ul className="mt-6 space-y-4">
          {rows.map((b) => (
            <li key={b.research_item_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-calm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium uppercase text-slate-500">{b.evidence_stage_label}</p>
                  <Link
                    href={`/updates/${encodeURIComponent(b.research_item_id)}`}
                    className="mt-1 block text-lg font-semibold text-slate-900 hover:text-primary"
                  >
                    {b.title}
                  </Link>
                  <p className="mt-2 text-sm text-slate-600">{b.summary}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {b.source_name}
                    {b.condition_slug ? (
                      <>
                        {" · "}
                        <Link href={`/conditions/${b.condition_slug}`} className="text-primary hover:underline">
                          {b.condition_slug}
                        </Link>
                      </>
                    ) : null}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center">
                  <a
                    href={b.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    Original source
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
                        else setError("Could not remove bookmark.");
                      } finally {
                        setRemoving(null);
                      }
                    }}
                  >
                    {removing === b.research_item_id ? "…" : "Remove"}
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
