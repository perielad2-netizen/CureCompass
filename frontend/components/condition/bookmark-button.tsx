"use client";

import { useCallback, useEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { AUTH_CHANGED_EVENT } from "@/lib/auth-events";
import { ApiError, apiDelete, apiPost } from "@/lib/api";

type BookmarkButtonProps = {
  researchItemId: string;
  initiallyBookmarked: boolean;
  /** Compact icon-only control for cards */
  compact?: boolean;
};

function BookmarkGlyph({ filled }: { filled: boolean }) {
  if (filled) {
    return (
      <svg className="h-5 w-5 fill-primary text-primary" viewBox="0 0 24 24" aria-hidden>
        <path d="M6 2h12a1 1 0 011 1v17l-7-4-7 4V3a1 1 0 011-1z" />
      </svg>
    );
  }
  return (
    <svg
      className="h-5 w-5 text-slate-500"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path d="M6 2h12a1 1 0 011 1v17l-7-4-7 4V3a1 1 0 011-1z" />
    </svg>
  );
}

export function BookmarkButton({ researchItemId, initiallyBookmarked, compact = true }: BookmarkButtonProps) {
  const [bookmarked, setBookmarked] = useState(initiallyBookmarked);
  const [hasToken, setHasToken] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    setBookmarked(initiallyBookmarked);
  }, [researchItemId, initiallyBookmarked]);

  useEffect(() => {
    const sync = () => setHasToken(!!localStorage.getItem("cc_access_token"));
    sync();
    window.addEventListener(AUTH_CHANGED_EVENT, sync);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, sync);
  }, []);

  const toggle = useCallback(async () => {
    if (busy) return;
    setErr("");
    setBusy(true);
    const path = `/bookmarks/${encodeURIComponent(researchItemId)}`;
    const prev = bookmarked;
    setBookmarked(!prev);
    try {
      if (prev) {
        await apiDelete(path);
      } else {
        await apiPost(path, { body: {} });
      }
    } catch (e) {
      setBookmarked(prev);
      if (e instanceof ApiError) setErr(e.message);
      else setErr("Could not update bookmark.");
    } finally {
      setBusy(false);
    }
  }, [busy, bookmarked, researchItemId]);

  const baseClass = compact
    ? "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 disabled:opacity-50"
    : "inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50";

  if (!hasToken) {
    return (
      <Link
        href="/login"
        className={baseClass}
        title="Sign in to save updates"
        aria-label="Sign in to save updates"
      >
        <BookmarkGlyph filled={false} />
        {!compact ? <span>Save</span> : null}
      </Link>
    );
  }

  return (
    <span className="inline-flex flex-col items-end gap-0.5">
      <button
        type="button"
        className={baseClass}
        onClick={toggle}
        disabled={busy}
        title={bookmarked ? "Remove bookmark" : "Save update"}
        aria-label={bookmarked ? "Remove bookmark" : "Save update"}
        aria-pressed={bookmarked}
      >
        <BookmarkGlyph filled={bookmarked} />
        {!compact ? <span>{bookmarked ? "Saved" : "Save"}</span> : null}
      </button>
      {err ? <span className="max-w-[12rem] text-right text-xs text-rose-600">{err}</span> : null}
    </span>
  );
}
