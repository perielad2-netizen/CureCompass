"use client";

import { useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { ApiError, apiGet, apiPatch, apiPost } from "@/lib/api";
import { formatDateTimeMedium } from "@/lib/date-format";

type Me = { id: string; email: string; is_admin: boolean };

type JobRow = {
  id: string;
  job_type: string;
  status: string;
  payload_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  error_text: string;
  started_at: string;
  finished_at: string | null;
};

type SourceRow = {
  id: string;
  name: string;
  source_type: string;
  base_url: string;
  trust_score: number;
  enabled: boolean;
};

type ReportTotals = {
  users_total: number;
  admins_total: number;
  users_created_30d: number;
  users_locale_he: number;
  users_locale_en: number;
  users_with_follows: number;
  follows_total: number;
  users_with_email_briefings_enabled: number;
  users_with_in_app_briefings_enabled: number;
  digests_total: number;
  digests_delivered_total: number;
  digest_users_total: number;
  ask_ai_messages_total: number;
  ask_ai_conversations_total: number;
  ask_ai_users_total: number;
  private_docs_total: number;
  private_docs_processed: number;
};

type ReportUser = {
  user_id: string;
  email: string;
  preferred_locale: string;
  created_at: string;
  followed_conditions: number;
  ask_ai_messages: number;
  ask_ai_conversations: number;
  digests_created: number;
  digests_delivered: number;
  has_email_briefings_enabled: boolean;
  has_in_app_briefings_enabled: boolean;
  last_ai_message_at: string | null;
  last_digest_at: string | null;
};

type Reports = {
  generated_at: string;
  totals: ReportTotals;
  top_ai_users: ReportUser[];
  recent_users: ReportUser[];
};

export default function AdminPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [jobs, setJobs] = useState<JobRow[] | null>(null);
  const [sources, setSources] = useState<SourceRow[] | null>(null);
  const [reports, setReports] = useState<Reports | null>(null);
  const [error, setError] = useState("");
  const [sourceSaving, setSourceSaving] = useState<string | null>(null);
  const [backfillSlug, setBackfillSlug] = useState("");
  const [backfillBusy, setBackfillBusy] = useState(false);
  const [backfillMsg, setBackfillMsg] = useState("");


  useEffect(() => {
    const token = localStorage.getItem("cc_access_token");
    if (!token) {
      setError("Sign in required.");
      return;
    }
    apiGet<Me>("/auth/me")
      .then((u) => {
        setMe(u);
        if (!u.is_admin) {
          setError("You do not have admin access.");
          return null;
        }
        return Promise.all([
          apiGet<JobRow[]>("/admin/jobs"),
          apiGet<SourceRow[]>("/admin/sources"),
          apiGet<Reports>("/admin/reports"),
        ]);
      })
      .then((pair) => {
        if (!pair) return;
        setJobs(pair[0]);
        setSources(pair[1]);
        setReports(pair[2]);
      })
      .catch((e) => {
        if (e instanceof ApiError) setError(e.message);
        else setError("Could not load admin data.");
      });
  }, []);

  if (error && !me) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error}</p>
        <Link href="/login" className="mt-4 inline-block text-primary">
          Sign in
        </Link>
      </main>
    );
  }

  if (me && !me.is_admin) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error || "Admin access required."}</p>
        <Link href="/dashboard" className="mt-4 inline-block text-primary">
          ← Dashboard
        </Link>
      </main>
    );
  }

  return (
    <main className="container-page py-8">
      <h1 className="text-2xl font-semibold text-slate-900">Admin</h1>
      <p className="mt-1 text-sm text-slate-600">Job runs, source registry, and ingestion backfill.</p>
      <Link href="/dashboard" className="mt-2 inline-block text-sm text-primary">
        ← Dashboard
      </Link>

      {error && me?.is_admin ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      <section className="mt-10 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Owner reports</h2>
        {!reports ? (
          <p className="mt-2 text-sm text-slate-600">Loading report metrics…</p>
        ) : (
          <>
            <p className="mt-1 text-xs text-slate-500">Generated: {formatDateTimeMedium(reports.generated_at)}</p>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Registered users</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.users_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">New users (30d)</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.users_created_30d}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Users with AI usage</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.ask_ai_users_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">AI messages total</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.ask_ai_messages_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Digest users</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.digest_users_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Digests sent</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.digests_delivered_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Email briefings enabled</p>
                <p className="text-xl font-semibold text-slate-900">
                  {reports.totals.users_with_email_briefings_enabled}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Private docs processed</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.private_docs_processed}</p>
              </div>
            </div>

            <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Top AI users (email)</th>
                    <th className="px-3 py-2">AI msgs</th>
                    <th className="px-3 py-2">AI convos</th>
                    <th className="px-3 py-2">Digests</th>
                    <th className="px-3 py-2">Delivered</th>
                    <th className="px-3 py-2">Locale</th>
                    <th className="px-3 py-2">Last AI</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.top_ai_users.map((u) => (
                    <tr key={u.user_id} className="border-b border-slate-100">
                      <td className="px-3 py-2 font-medium text-slate-900">{u.email}</td>
                      <td className="px-3 py-2">{u.ask_ai_messages}</td>
                      <td className="px-3 py-2">{u.ask_ai_conversations}</td>
                      <td className="px-3 py-2">{u.digests_created}</td>
                      <td className="px-3 py-2">{u.digests_delivered}</td>
                      <td className="px-3 py-2">{u.preferred_locale}</td>
                      <td className="px-3 py-2 text-slate-600">
                        {u.last_ai_message_at ? formatDateTimeMedium(u.last_ai_message_at) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Recent users</th>
                    <th className="px-3 py-2">Created</th>
                    <th className="px-3 py-2">Follows</th>
                    <th className="px-3 py-2">Email briefings</th>
                    <th className="px-3 py-2">In-app briefings</th>
                    <th className="px-3 py-2">AI msgs</th>
                    <th className="px-3 py-2">Digests</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.recent_users.map((u) => (
                    <tr key={u.user_id} className="border-b border-slate-100">
                      <td className="px-3 py-2 font-medium text-slate-900">{u.email}</td>
                      <td className="px-3 py-2 text-slate-600">{formatDateTimeMedium(u.created_at)}</td>
                      <td className="px-3 py-2">{u.followed_conditions}</td>
                      <td className="px-3 py-2">{u.has_email_briefings_enabled ? "Yes" : "No"}</td>
                      <td className="px-3 py-2">{u.has_in_app_briefings_enabled ? "Yes" : "No"}</td>
                      <td className="px-3 py-2">{u.ask_ai_messages}</td>
                      <td className="px-3 py-2">{u.digests_created}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="mt-10 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Run ingestion backfill</h2>
        <p className="mt-1 text-sm text-slate-600">
          Queues Celery job <span className="font-mono text-xs">ingestion.backfill</span> for a condition slug (same as{" "}
          <span className="font-mono text-xs">POST /api/ingestion/backfill</span> — admins skip the follow check).
        </p>
        <form
          className="mt-4 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            const slug = backfillSlug.trim();
            if (!slug) return;
            setBackfillBusy(true);
            setBackfillMsg("");
            apiPost<Record<string, unknown>>("/ingestion/backfill", { body: { condition_slug: slug } })
              .then((out) => {
                setBackfillMsg(typeof out.status === "string" ? `Status: ${out.status}` : JSON.stringify(out));
                setBackfillSlug("");
              })
              .catch((err) => {
                setBackfillMsg(err instanceof ApiError ? err.message : "Backfill request failed.");
              })
              .finally(() => setBackfillBusy(false));
          }}
        >
          <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Condition slug</span>
            <input
              value={backfillSlug}
              onChange={(e) => setBackfillSlug(e.target.value)}
              placeholder="e.g. nf1"
              className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              autoComplete="off"
            />
          </label>
          <button
            type="submit"
            disabled={backfillBusy || !backfillSlug.trim()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {backfillBusy ? "Queueing…" : "Queue backfill"}
          </button>
        </form>
        {backfillMsg ? <p className="mt-3 text-sm text-slate-700">{backfillMsg}</p> : null}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">Recent jobs</h2>
        {!jobs ? (
          <p className="mt-2 text-sm text-slate-600">Loading…</p>
        ) : jobs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">No job rows yet.</p>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Started</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Payload</th>
                  <th className="px-3 py-2">Error</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id} className="border-b border-slate-100">
                    <td className="whitespace-nowrap px-3 py-2 text-slate-600">
                      {formatDateTimeMedium(j.started_at)}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-800">{j.job_type}</td>
                    <td className="px-3 py-2">{j.status}</td>
                    <td className="max-w-xs truncate px-3 py-2 font-mono text-xs text-slate-600" title={JSON.stringify(j.payload_json)}>
                      {JSON.stringify(j.payload_json)}
                    </td>
                    <td className="max-w-xs truncate px-3 py-2 text-xs text-rose-700" title={j.error_text}>
                      {j.error_text || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">Sources</h2>
        {!sources ? (
          <p className="mt-2 text-sm text-slate-600">Loading…</p>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Trust</th>
                  <th className="px-3 py-2">Enabled</th>
                  <th className="px-3 py-2">URL</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={s.id} className="border-b border-slate-100">
                    <td className="px-3 py-2 font-medium text-slate-900">{s.name}</td>
                    <td className="px-3 py-2 text-slate-600">{s.source_type}</td>
                    <td className="px-3 py-2">{s.trust_score}</td>
                    <td className="px-3 py-2">
                      <label className="inline-flex cursor-pointer items-center gap-2">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-slate-300"
                          checked={s.enabled}
                          disabled={sourceSaving === s.id}
                          onChange={(e) => {
                            const next = e.target.checked;
                            setSourceSaving(s.id);
                            setSources((prev) =>
                              prev
                                ? prev.map((row) => (row.id === s.id ? { ...row, enabled: next } : row))
                                : prev
                            );
                            apiPatch<SourceRow>(`/admin/sources/${encodeURIComponent(s.id)}`, {
                              body: { enabled: next },
                            })
                              .then((updated) => {
                                setSources((prev) =>
                                  prev ? prev.map((row) => (row.id === s.id ? updated : row)) : prev
                                );
                              })
                              .catch(() => {
                                setSources((prev) =>
                                  prev
                                    ? prev.map((row) => (row.id === s.id ? { ...row, enabled: s.enabled } : row))
                                    : prev
                                );
                                setError("Could not update source.");
                              })
                              .finally(() => setSourceSaving(null));
                          }}
                        />
                        <span className="text-slate-600">{s.enabled ? "On" : "Off"}</span>
                      </label>
                    </td>
                    <td className="max-w-xs truncate px-3 py-2 text-primary">
                      <a href={s.base_url} target="_blank" rel="noreferrer" className="hover:underline">
                        {s.base_url}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
