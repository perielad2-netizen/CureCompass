"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, apiDelete, apiGet, apiPost } from "@/lib/api";

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
  const [rows, setRows] = useState<DigestRow[]>([]);
  const [error, setError] = useState("");
  const [genType, setGenType] = useState<"daily" | "weekly" | "major">("daily");
  const [genSlug, setGenSlug] = useState("");
  const [genBusy, setGenBusy] = useState(false);
  const [genMsg, setGenMsg] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = () => {
    if (!localStorage.getItem("cc_access_token")) {
      setError("Please sign in to view research briefings.");
      return;
    }
    apiGet<DigestRow[]>("/digests?limit=50")
      .then(setRows)
      .catch(() => setError("Could not load briefings."));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="container-page py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Research briefings</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600">
            A <strong className="font-medium text-slate-800">briefing</strong> is one easy-to-read write-up of recent
            trusted research for conditions you follow (not a live list of every article). We build it from the same
            indexed sources as your dashboard, in plain language. You can create a briefing below anytime; in
            production, briefings can also be generated on a schedule or emailed when your settings allow.
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 text-sm font-medium">
          <Link href="/dashboard" className="text-primary">
            ← Dashboard
          </Link>
          <Link href="/settings/notifications" className="text-primary">
            Schedule &amp; email preferences
          </Link>
        </div>
      </div>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-calm">
        <h2 className="text-base font-semibold text-slate-900">Create a briefing now</h2>
        <p className="mt-1 text-sm text-slate-600">
          Builds a new briefing right away for all followed conditions, or for one condition if you enter its slug.
          Your notification settings still apply (e.g. email only if enabled).
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">Type</span>
            <select
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={genType}
              onChange={(e) => setGenType(e.target.value as typeof genType)}
            >
              <option value="daily">Daily window</option>
              <option value="weekly">Weekly window</option>
              <option value="major">Major milestones</option>
            </select>
          </label>
          <label className="flex min-w-[10rem] flex-col gap-1 text-sm">
            <span className="text-slate-600">Condition slug (optional)</span>
            <input
              className="rounded-lg border border-slate-300 px-3 py-2"
              placeholder="e.g. nf1"
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
              setGenMsg("");
              try {
                const res = await apiPost<{ generated: number; ids: string[] }>("/digests/generate", {
                  body: {
                    digest_type: genType,
                    condition_slug: genSlug.trim() || null,
                  },
                });
                setGenMsg(`Created ${res.generated} briefing(s).`);
                load();
              } catch (e) {
                if (e instanceof ApiError) setGenMsg(e.message);
                else setGenMsg("Generation failed.");
              } finally {
                setGenBusy(false);
              }
            }}
          >
            {genBusy ? "Working…" : "Create briefing"}
          </button>
        </div>
        {genMsg ? <p className="mt-3 text-sm text-slate-700">{genMsg}</p> : null}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">Your saved briefings</h2>
        <ul className="mt-4 space-y-3">
          {rows.length === 0 && !error ? (
            <li className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
              No briefings yet. Use “Create a briefing now” above once you have followed conditions and indexed
              updates—or wait for an automated job if your server runs one.
            </li>
          ) : null}
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex flex-wrap items-stretch gap-0 rounded-2xl border border-slate-200 bg-white shadow-calm transition hover:border-slate-300"
            >
              <Link href={`/digests/${r.id}`} className="min-w-0 flex-1 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-slate-900">{r.title}</p>
                  <span className="text-xs font-medium uppercase text-slate-500">
                    {r.digest_type === "daily"
                      ? "Daily-style"
                      : r.digest_type === "weekly"
                        ? "Weekly-style"
                        : r.digest_type === "major"
                          ? "Major milestones"
                          : r.digest_type}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {r.condition_name} · {new Date(r.created_at).toLocaleString()}
                  {r.email_delivered ? " · Emailed" : ""}
                </p>
              </Link>
              <div className="flex shrink-0 border-l border-slate-100">
                <button
                  type="button"
                  className="px-4 py-3 text-sm font-medium text-rose-600 hover:bg-rose-50 disabled:opacity-50"
                  disabled={deletingId === r.id}
                  title="Delete briefing"
                  onClick={async (e) => {
                    e.preventDefault();
                    if (!confirm(`Delete “${r.title.slice(0, 60)}${r.title.length > 60 ? "…" : ""}”?`)) return;
                    setDeletingId(r.id);
                    try {
                      await apiDelete(`/digests/${encodeURIComponent(r.id)}`);
                      setRows((prev) => prev.filter((x) => x.id !== r.id));
                    } catch (err) {
                      if (err instanceof ApiError) setError(err.message);
                      else setError("Could not delete briefing.");
                    } finally {
                      setDeletingId(null);
                    }
                  }}
                >
                  {deletingId === r.id ? "…" : "Delete"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
