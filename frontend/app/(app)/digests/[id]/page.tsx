"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { ApiError, apiDelete, apiGet, apiPost } from "@/lib/api";

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
        if (err instanceof ApiError && err.status === 404) setError("Briefing not found.");
        else setError("Could not load briefing.");
      });
  }, [id]);

  if (error) {
    return (
      <main className="container-page py-8">
        <p className="text-rose-600">{error}</p>
        <Link href="/digests" className="mt-4 inline-block text-primary">
          Back to research briefings
        </Link>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="container-page py-8">
        <p className="text-slate-600">{id ? "Loading…" : "Missing briefing."}</p>
      </main>
    );
  }

  const failed = digestGenerationFailed(data.structured_json);
  const rawErr = failed ? String(data.structured_json.error) : "";
  const errDetail = rawErr.length > 280 ? `${rawErr.slice(0, 280)}…` : rawErr;

  return (
    <main className="container-page max-w-3xl py-8">
      <Link href="/digests" className="text-sm font-medium text-primary">
        ← All research briefings
      </Link>
      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-500">
        {data.digest_type === "daily"
          ? "Daily-style"
          : data.digest_type === "weekly"
            ? "Weekly-style"
            : data.digest_type === "major"
              ? "Major milestones"
              : data.digest_type}{" "}
        · {data.condition_name}
        {data.email_delivered ? " · Sent by email" : ""}
      </p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">{data.title}</h1>
      <time className="mt-2 block text-sm text-slate-500" dateTime={data.created_at}>
        {new Date(data.created_at).toLocaleString()}
      </time>
      <div className="mt-3 flex flex-wrap items-center gap-4">
        {data.condition_slug ? (
          <Link className="text-sm text-primary" href={`/conditions/${data.condition_slug}`}>
            Open condition
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
              setEmailMsg("Sent — check your inbox.");
              setData((d) => (d ? { ...d, email_delivered: true } : d));
            } catch (e) {
              if (e instanceof ApiError) setEmailMsg(e.message);
              else setEmailMsg("Could not send email.");
            } finally {
              setEmailBusy(false);
            }
          }}
        >
          {emailBusy ? "Sending…" : "Email this briefing to me"}
        </button>
        <button
          type="button"
          className="text-sm font-medium text-rose-600 hover:text-rose-700 disabled:opacity-50"
          disabled={deleteBusy}
          onClick={async () => {
            if (!confirm("Delete this research briefing? This cannot be undone.")) return;
            setDeleteBusy(true);
            setDeleteErr("");
            try {
              await apiDelete(`/digests/${encodeURIComponent(id)}`);
              router.push("/digests");
            } catch (e) {
              if (e instanceof ApiError) setDeleteErr(e.message);
              else setDeleteErr("Could not delete.");
            } finally {
              setDeleteBusy(false);
            }
          }}
        >
          {deleteBusy ? "Deleting…" : "Delete briefing"}
        </button>
      </div>
      {emailMsg ? (
        <p
          className={`mt-2 text-sm ${emailMsg.startsWith("Sent") ? "text-emerald-700" : "text-rose-600"}`}
        >
          {emailMsg}
        </p>
      ) : null}
      {deleteErr ? <p className="mt-2 text-sm text-rose-600">{deleteErr}</p> : null}

      <article className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        {failed ? (
          <div className="space-y-4">
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <p className="font-semibold">This briefing didn&apos;t finish generating</p>
              <p className="mt-2 text-amber-900/90">
                The server couldn&apos;t produce the AI summary when this was created (for example missing or invalid
                OpenAI settings, a timeout, or a temporary API error). Your indexed updates on the{" "}
                <Link href="/dashboard" className="font-medium underline">
                  dashboard
                </Link>{" "}
                are unchanged.
              </p>
              <p className="mt-3">
                <Link href="/digests" className="font-medium text-primary">
                  Create a new research briefing
                </Link>{" "}
                from the list page after confirming <code className="rounded bg-amber-100/80 px-1">OPENAI_API_KEY</code>{" "}
                is set and the API has been restarted.
              </p>
            </div>
            {errDetail ? (
              <p className="text-xs text-slate-500">
                <span className="font-medium text-slate-600">Detail: </span>
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
      <p className="mt-6 text-xs text-slate-500">
        Educational research summaries only — not personal medical advice. Discuss with your clinician.
      </p>
    </main>
  );
}
