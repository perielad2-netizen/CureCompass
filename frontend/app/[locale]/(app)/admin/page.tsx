"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
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
  conditions_total: number;
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
  const t = useTranslations("Admin");
  const tc = useTranslations("Common");
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
      setError(t("signInRequired"));
      return;
    }
    apiGet<Me>("/auth/me")
      .then((u) => {
        setMe(u);
        if (!u.is_admin) {
          setError(t("noAccess"));
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
        else setError(t("loadFailed"));
      });
  }, [t]);

  if (error && !me) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error}</p>
        <Link href="/login" className="mt-4 inline-block text-primary">
          {tc("signIn")}
        </Link>
      </main>
    );
  }

  if (me && !me.is_admin) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error || t("accessRequired")}</p>
        <Link href="/dashboard" className="mt-4 inline-block text-primary">
          ← {tc("dashboard")}
        </Link>
      </main>
    );
  }

  return (
    <main className="container-page py-8">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      <p className="mt-1 text-sm text-slate-600">{t("subtitle")}</p>
      <Link href="/dashboard" className="mt-2 inline-block text-sm text-primary">
        ← {tc("dashboard")}
      </Link>

      {error && me?.is_admin ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      <section className="mt-10 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">{t("reportsTitle")}</h2>
        {!reports ? (
          <p className="mt-2 text-sm text-slate-600">{t("loadingMetrics")}</p>
        ) : (
          <>
            <p className="mt-1 text-xs text-slate-500">
              {t("generated")} {formatDateTimeMedium(reports.generated_at)}
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricRegisteredUsers")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.users_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricNewUsers30d")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.users_created_30d}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricCatalogConditions")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.conditions_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricUsersWithAi")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.ask_ai_users_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricAiMessagesTotal")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.ask_ai_messages_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricDigestUsers")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.digest_users_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricDigestsSent")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.digests_delivered_total}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricEmailBriefings")}</p>
                <p className="text-xl font-semibold text-slate-900">
                  {reports.totals.users_with_email_briefings_enabled}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{t("metricPrivateDocs")}</p>
                <p className="text-xl font-semibold text-slate-900">{reports.totals.private_docs_processed}</p>
              </div>
            </div>

            <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">{t("tableTopAiUsers")}</th>
                    <th className="px-3 py-2">{t("tableAiMsgs")}</th>
                    <th className="px-3 py-2">{t("tableAiConvos")}</th>
                    <th className="px-3 py-2">{t("tableDigests")}</th>
                    <th className="px-3 py-2">{t("tableDelivered")}</th>
                    <th className="px-3 py-2">{t("tableLocale")}</th>
                    <th className="px-3 py-2">{t("tableLastAi")}</th>
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
                        {u.last_ai_message_at ? formatDateTimeMedium(u.last_ai_message_at) : t("dash")}
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
                    <th className="px-3 py-2">{t("tableRecentUsers")}</th>
                    <th className="px-3 py-2">{t("tableCreated")}</th>
                    <th className="px-3 py-2">{t("tableFollows")}</th>
                    <th className="px-3 py-2">{t("tableEmailBriefings")}</th>
                    <th className="px-3 py-2">{t("tableInAppBriefings")}</th>
                    <th className="px-3 py-2">{t("tableAiMsgs")}</th>
                    <th className="px-3 py-2">{t("tableDigests")}</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.recent_users.map((u) => (
                    <tr key={u.user_id} className="border-b border-slate-100">
                      <td className="px-3 py-2 font-medium text-slate-900">{u.email}</td>
                      <td className="px-3 py-2 text-slate-600">{formatDateTimeMedium(u.created_at)}</td>
                      <td className="px-3 py-2">{u.followed_conditions}</td>
                      <td className="px-3 py-2">{u.has_email_briefings_enabled ? tc("yes") : tc("no")}</td>
                      <td className="px-3 py-2">{u.has_in_app_briefings_enabled ? tc("yes") : tc("no")}</td>
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
        <h2 className="text-lg font-semibold text-slate-900">{t("backfillTitle")}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {t.rich("backfillIntro", {
            code: (chunks) => <code className="font-mono text-xs">{chunks}</code>,
          })}
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
                setBackfillMsg(err instanceof ApiError ? err.message : t("backfillFailed"));
              })
              .finally(() => setBackfillBusy(false));
          }}
        >
          <label className="flex min-w-[200px] flex-1 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t("conditionSlug")}</span>
            <input
              value={backfillSlug}
              onChange={(e) => setBackfillSlug(e.target.value)}
              placeholder={t("slugPlaceholder")}
              className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              autoComplete="off"
            />
          </label>
          <button
            type="submit"
            disabled={backfillBusy || !backfillSlug.trim()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            {backfillBusy ? t("queueing") : t("queueBackfill")}
          </button>
        </form>
        {backfillMsg ? <p className="mt-3 text-sm text-slate-700">{backfillMsg}</p> : null}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">{t("recentJobs")}</h2>
        {!jobs ? (
          <p className="mt-2 text-sm text-slate-600">{tc("loading")}</p>
        ) : jobs.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">{t("noJobs")}</p>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">{t("jobsStarted")}</th>
                  <th className="px-3 py-2">{t("jobsType")}</th>
                  <th className="px-3 py-2">{t("jobsStatus")}</th>
                  <th className="px-3 py-2">{t("jobsPayload")}</th>
                  <th className="px-3 py-2">{t("jobsError")}</th>
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
                      {j.error_text || t("dash")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-slate-900">{t("sourcesTitle")}</h2>
        {!sources ? (
          <p className="mt-2 text-sm text-slate-600">{tc("loading")}</p>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">{t("sourcesName")}</th>
                  <th className="px-3 py-2">{t("sourcesType")}</th>
                  <th className="px-3 py-2">{t("sourcesTrust")}</th>
                  <th className="px-3 py-2">{t("sourcesEnabled")}</th>
                  <th className="px-3 py-2">{t("sourcesUrl")}</th>
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
                                setError(t("sourceUpdateFailed"));
                              })
                              .finally(() => setSourceSaving(null));
                          }}
                        />
                        <span className="text-slate-600">{s.enabled ? t("sourceOn") : t("sourceOff")}</span>
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
