"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { ApiError, apiDelete, apiGet, apiPost } from "@/lib/api";
import { formatDateTimeMedium } from "@/lib/date-format";

type DigestDetail = {
  id: string;
  digest_type: string;
  title: string;
  condition_slug: string;
  condition_name: string;
  created_at: string;
  email_delivered: boolean;
  body_markdown: string;
  structured_json: Record<string, unknown>;
};

function digestGenerationFailed(structured: Record<string, unknown> | undefined): structured is { error: string } {
  return Boolean(structured && typeof structured.error === "string");
}

export default function DigestDetailPage() {
  const t = useTranslations("DigestDetail");
  const tList = useTranslations("Digests");
  const params = useParams();
  const router = useRouter();
  const id = typeof params.id === "string" ? params.id : params.id?.[0] ?? "";
  const [data, setData] = useState<DigestDetail | null>(null);
  const [error, setError] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteErr, setDeleteErr] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailMsg, setEmailMsg] = useState("");

  useEffect(() => {
    if (!id) return;
    apiGet<DigestDetail>(`/digests/${encodeURIComponent(id)}`)
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setError(t("notFound"));
        else setError(t("loadError"));
      });
  }, [id, t]);

  if (error) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error}</p>
        <Link href="/digests" className="mt-4 inline-block text-primary">
          {t("backToList")}
        </Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="container-page py-8">
        <p className="text-slate-600">{id ? t("loading") : t("missingId")}</p>
      </main>
    );
  }

  const failed = digestGenerationFailed(data.structured_json);
  const rawErr = failed ? String(data.structured_json.error) : "";
  const errDetail = rawErr.length > 280 ? `${rawErr.slice(0, 280)}…` : rawErr;

  const typeLabel =
    data.digest_type === "daily"
      ? t("dailyStyle")
      : data.digest_type === "weekly"
        ? t("weeklyStyle")
        : data.digest_type === "major"
          ? tList("typeLabelMajor")
          : data.digest_type;

  return (
    <main className="container-page max-w-3xl py-8">
      <Link href="/digests" className="text-sm font-medium text-primary">
        {t("allBriefings")}
      </Link>
      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-500">
        {typeLabel} · {data.condition_name}
        {data.email_delivered ? t("sentByEmail") : ""}
      </p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">{data.title}</h1>
      <time className="mt-2 block text-sm text-slate-500" dateTime={data.created_at}>
        {formatDateTimeMedium(data.created_at)}
      </time>
      <div className="mt-3 flex flex-wrap items-center gap-4">
        {data.condition_slug ? (
          <Link className="text-sm text-primary" href={`/conditions/${data.condition_slug}`}>
            {t("openCondition")}
          </Link>
        ) : null}
        <button
          type="button"
          className="text-sm font-medium text-primary hover:underline disabled:opacity-50"
          disabled={emailBusy}
          onClick={async () => {
            setEmailBusy(true);
            setEmailMsg("");
            try {
              await apiPost<{ sent: boolean }>(`/digests/${encodeURIComponent(id)}/email`, { body: {} });
              setEmailMsg(t("emailSentToast"));
              setData((d) => (d ? { ...d, email_delivered: true } : d));
            } catch (e) {
              if (e instanceof ApiError) setEmailMsg(e.message);
              else setEmailMsg(t("emailSendFailed"));
            } finally {
              setEmailBusy(false);
            }
          }}
        >
          {emailBusy ? t("sending") : t("emailButton")}
        </button>
        <button
          type="button"
          className="text-sm font-medium text-rose-600 hover:text-rose-700 disabled:opacity-50"
          disabled={deleteBusy}
          onClick={async () => {
            if (!confirm(t("deleteConfirm"))) return;
            setDeleteBusy(true);
            setDeleteErr("");
            try {
              await apiDelete(`/digests/${encodeURIComponent(id)}`);
              router.push("/digests");
            } catch (e) {
              if (e instanceof ApiError) setDeleteErr(e.message);
              else setDeleteErr(t("deleteFailed"));
            } finally {
              setDeleteBusy(false);
            }
          }}
        >
          {deleteBusy ? t("deleting") : t("deleteButton")}
        </button>
      </div>
      {emailMsg ? (
        <p
          className={`mt-2 text-sm ${emailMsg === t("emailSentToast") ? "text-emerald-700" : "text-rose-600"}`}
        >
          {emailMsg}
        </p>
      ) : null}
      {deleteErr ? <p className="mt-2 text-sm text-rose-600">{deleteErr}</p> : null}

      <article className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        {failed ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <p className="font-semibold">{t("generationFailedTitle")}</p>
              <p className="mt-2 text-amber-900/90">
                {t.rich("generationFailedBody", {
                  dashboard: (chunks) => (
                    <Link href="/dashboard" className="font-medium underline">
                      {chunks}
                    </Link>
                  ),
                })}
              </p>
              <p className="mt-3">
                <Link href="/digests" className="font-medium text-primary">
                  {t("createNewBriefing")}
                </Link>{" "}
                {t.rich("generationFailedAfterKey", {
                  code: (chunks) => <code className="rounded bg-amber-100/80 px-1">{chunks}</code>,
                })}
              </p>
            </div>
            {errDetail ? (
              <p className="text-xs text-slate-500">
                <span className="font-medium text-slate-600">{t("detailLabel")} </span>
                <span className="font-mono">{errDetail}</span>
              </p>
            ) : null}
          </div>
        ) : (
          <div className="digest-markdown text-sm leading-relaxed text-slate-800 [&_h2]:mt-6 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-slate-900 [&_h2:first-child]:mt-0 [&_h3]:mt-4 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:text-slate-900 [&_p]:mt-2 [&_ul]:mt-2 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_strong]:font-semibold [&_em]:italic">
            <ReactMarkdown>{data.body_markdown}</ReactMarkdown>
          </div>
        )}
      </article>
      <p className="mt-6 text-xs text-slate-500">{t("footerDisclaimer")}</p>
    </main>
  );
}
