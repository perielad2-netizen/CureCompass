"use client";

import { FormEvent, useEffect, useState } from "react";
import { Link, useRouter } from "@/i18n/navigation";
import { ApiError, apiGet, apiPut } from "@/lib/api";

type Defaults = {
  notify_trials: boolean;
  notify_recruiting_trials_only: boolean;
  notify_papers: boolean;
  notify_regulatory: boolean;
  notify_foundation_news: boolean;
  notify_major_only: boolean;
  frequency: string;
  quiet_hours_json: Record<string, unknown>;
  email_enabled: boolean;
  push_enabled: boolean;
  in_app_enabled: boolean;
};

type PerConditionRow = Defaults & {
  condition_id: string;
  slug: string;
  canonical_name: string;
};

type NotificationSettingsResponse = {
  defaults: Defaults;
  per_condition: PerConditionRow[];
};

function rowToPayload(row: Defaults): Defaults {
  return {
    notify_trials: row.notify_trials,
    notify_recruiting_trials_only: row.notify_recruiting_trials_only,
    notify_papers: row.notify_papers,
    notify_regulatory: row.notify_regulatory,
    notify_foundation_news: row.notify_foundation_news,
    notify_major_only: row.notify_major_only,
    frequency: row.frequency,
    quiet_hours_json: row.quiet_hours_json,
    email_enabled: row.email_enabled,
    push_enabled: row.push_enabled,
    in_app_enabled: row.in_app_enabled,
  };
}

export default function NotificationSettingsPage() {
  const router = useRouter();
  const [data, setData] = useState<NotificationSettingsResponse | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [form, setForm] = useState<Defaults | null>(null);
  const [applyToFollowed, setApplyToFollowed] = useState(false);
  const [perRowBusy, setPerRowBusy] = useState<string | null>(null);
  const [perRowMsg, setPerRowMsg] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!localStorage.getItem("cc_access_token")) {
      router.replace("/login");
      return;
    }
    apiGet<NotificationSettingsResponse>("/notification-settings")
      .then((r) => {
        setData(r);
        setForm(r.defaults);
      })
      .catch(() => setError("Could not load settings."));
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setError("");
    setSaved("");
    try {
      await apiPut("/notification-settings", {
        body: { ...form, apply_to_followed_conditions: applyToFollowed },
      });
      setSaved(
        applyToFollowed
          ? "Saved defaults and applied them to all conditions you follow."
          : "Saved defaults for new follows only. Use the checkbox to push these settings to conditions you already follow, or edit each condition below."
      );
      setApplyToFollowed(false);
      const r = await apiGet<NotificationSettingsResponse>("/notification-settings");
      setData(r);
      setForm(r.defaults);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Save failed.");
    }
  }

  async function savePerCondition(slug: string, row: PerConditionRow) {
    setPerRowBusy(slug);
    setPerRowMsg((m) => ({ ...m, [slug]: "" }));
    setError("");
    try {
      await apiPut(`/conditions/by-slug/${encodeURIComponent(slug)}/notification-settings`, {
        body: rowToPayload(row),
      });
      setPerRowMsg((m) => ({ ...m, [slug]: "Saved." }));
      const r = await apiGet<NotificationSettingsResponse>("/notification-settings");
      setData(r);
      if (form) setForm(r.defaults);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Save failed.";
      setPerRowMsg((m) => ({ ...m, [slug]: msg }));
    } finally {
      setPerRowBusy(null);
    }
  }

  function updatePerRow(slug: string, patch: Partial<Defaults>) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        per_condition: prev.per_condition.map((p) => (p.slug === slug ? { ...p, ...patch } : p)),
      };
    });
  }

  if (!form) {
    return (
      <main className="container-page max-w-2xl py-10">
        {error ? <p className="text-rose-600">{error}</p> : <p className="text-slate-600">Loading…</p>}
      </main>
    );
  }

  return (
    <main className="container-page max-w-2xl py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Research briefings &amp; notifications</h1>
      <p className="mt-2 text-sm text-slate-600">
        Scheduled <strong className="font-medium text-slate-800">research briefings</strong> are generated automatically
        when the server runs its digest jobs. If <strong className="font-medium text-slate-800">email</strong> is on and
        the server has SMTP configured, we send that briefing to your account email—so{" "}
        <strong className="font-medium text-slate-800">daily</strong> can mean roughly one email per day{" "}
        <em>per followed condition</em> (when there is content to summarize). Choose{" "}
        <strong className="font-medium text-slate-800">weekly</strong> for a lighter schedule,{" "}
        <strong className="font-medium text-slate-800">off</strong> to stop automatic briefings (you can still create
        briefings manually from the Research briefings page), or turn off email only to keep in-app briefings.
      </p>
      <Link href="/profile" className="mt-4 inline-block text-sm text-primary">
        ← Profile
      </Link>
      <Link href="/digests" className="mt-4 ml-4 inline-block text-sm text-primary">
        Research briefings
      </Link>

      <form onSubmit={onSubmit} className="mt-8 space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        <h2 className="text-base font-semibold text-slate-900">Default preferences</h2>
        <p className="text-xs text-slate-500">
          Defaults are used when you follow a new condition. Existing follows keep their own settings until you apply
          defaults below or edit each condition.
        </p>

        <div>
          <label className="text-sm font-medium text-slate-800">Research briefing schedule</label>
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={form.frequency}
            onChange={(e) => setForm({ ...form, frequency: e.target.value })}
          >
            <option value="real_time">Real time (major / in-app when available; not a daily email digest)</option>
            <option value="daily">Daily (scheduled briefing; email too if email is on)</option>
            <option value="weekly">Weekly (scheduled briefing; email too if email is on)</option>
            <option value="off">Off (no scheduled automatic briefings)</option>
          </select>
        </div>

        <fieldset className="space-y-2 border-t border-slate-100 pt-4">
          <legend className="text-sm font-medium text-slate-800">What to include</legend>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.notify_trials}
              onChange={(e) => setForm({ ...form, notify_trials: e.target.checked })}
            />
            Trials
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.notify_recruiting_trials_only}
              onChange={(e) => setForm({ ...form, notify_recruiting_trials_only: e.target.checked })}
            />
            Recruiting trials only
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.notify_papers}
              onChange={(e) => setForm({ ...form, notify_papers: e.target.checked })}
            />
            Papers
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.notify_regulatory}
              onChange={(e) => setForm({ ...form, notify_regulatory: e.target.checked })}
            />
            Regulatory
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.notify_foundation_news}
              onChange={(e) => setForm({ ...form, notify_foundation_news: e.target.checked })}
            />
            Foundation / news
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.notify_major_only}
              onChange={(e) => setForm({ ...form, notify_major_only: e.target.checked })}
            />
            Major updates only
          </label>
        </fieldset>

        <fieldset className="space-y-2 border-t border-slate-100 pt-4">
          <legend className="text-sm font-medium text-slate-800">Channels</legend>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.in_app_enabled}
              onChange={(e) => setForm({ ...form, in_app_enabled: e.target.checked })}
            />
            In-app briefings
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.email_enabled}
              onChange={(e) => setForm({ ...form, email_enabled: e.target.checked })}
            />
            Email briefings (requires SMTP on the server)
          </label>
        </fieldset>

        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={applyToFollowed}
            onChange={(e) => setApplyToFollowed(e.target.checked)}
          />
          <span>
            Also apply these defaults to <strong className="font-medium text-slate-800">every condition I already follow</strong>{" "}
            (overwrites per-condition settings with the choices above).
          </span>
        </label>

        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        {saved ? <p className="text-sm text-emerald-700">{saved}</p> : null}
        <button type="submit" className="rounded-lg bg-primary px-5 py-2 text-white">
          Save defaults
        </button>
      </form>

      {data?.per_condition?.length ? (
        <section className="mt-10">
          <h2 className="text-lg font-semibold text-slate-900">Per condition</h2>
          <p className="mt-1 text-sm text-slate-600">
            Adjust schedule or email for one condition without changing your global defaults.
          </p>
          <ul className="mt-4 space-y-4">
            {data.per_condition.map((p) => (
              <li key={p.condition_id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-calm">
                <div className="font-medium text-slate-900">{p.canonical_name}</div>
                <div className="text-xs text-slate-500">{p.slug}</div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="flex flex-col gap-1 text-sm">
                    <span className="text-slate-600">Briefing schedule</span>
                    <select
                      className="rounded-lg border border-slate-300 px-3 py-2"
                      value={p.frequency}
                      onChange={(e) => updatePerRow(p.slug, { frequency: e.target.value })}
                      disabled={perRowBusy === p.slug}
                    >
                      <option value="real_time">Real time</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="off">Off</option>
                    </select>
                  </label>
                  <div className="flex flex-col justify-end gap-2 text-sm">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={p.email_enabled}
                        onChange={(e) => updatePerRow(p.slug, { email_enabled: e.target.checked })}
                        disabled={perRowBusy === p.slug}
                      />
                      Email
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={p.in_app_enabled}
                        onChange={(e) => updatePerRow(p.slug, { in_app_enabled: e.target.checked })}
                        disabled={perRowBusy === p.slug}
                      />
                      In-app
                    </label>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                    disabled={perRowBusy === p.slug}
                    onClick={() => savePerCondition(p.slug, p)}
                  >
                    {perRowBusy === p.slug ? "Saving…" : "Save this condition"}
                  </button>
                  <Link href={`/conditions/${encodeURIComponent(p.slug)}`} className="text-sm text-primary">
                    Open condition page
                  </Link>
                  {perRowMsg[p.slug] ? (
                    <span
                      className={`text-sm ${perRowMsg[p.slug] === "Saved." ? "text-emerald-700" : "text-rose-600"}`}
                    >
                      {perRowMsg[p.slug]}
                    </span>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
