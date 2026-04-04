"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ApiError, apiGet, apiPost } from "@/lib/api";

type ConditionRow = { id: string; canonical_name: string; slug: string };

export default function OnboardingPage() {
  const router = useRouter();
  const [conditions, setConditions] = useState<ConditionRow[]>([]);
  const [conditionId, setConditionId] = useState("");
  const [search, setSearch] = useState("");
  const [ageScope, setAgeScope] = useState<"pediatric" | "adult" | "both">("both");
  const [geography, setGeography] = useState("global");
  const [frequency, setFrequency] = useState<"real_time" | "daily" | "weekly" | "off">("daily");
  const [notifyTrials, setNotifyTrials] = useState(true);
  const [notifyRecruitingOnly, setNotifyRecruitingOnly] = useState(false);
  const [notifyPapers, setNotifyPapers] = useState(true);
  const [notifyRegulatory, setNotifyRegulatory] = useState(true);
  const [notifyFoundation, setNotifyFoundation] = useState(true);
  const [majorOnly, setMajorOnly] = useState(false);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [inAppEnabled, setInAppEnabled] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!localStorage.getItem("cc_access_token")) {
      router.replace("/login");
      return;
    }
    apiGet<ConditionRow[]>("/conditions")
      .then((rows) => {
        setConditions(rows);
        const nf1 = rows.find((r) => r.slug === "nf1");
        setConditionId((nf1 ?? rows[0])?.id ?? "");
      })
      .catch(() => setError("Could not load conditions."))
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => {
    if (!search.trim()) return;
    const t = setTimeout(() => {
      apiGet<ConditionRow[]>(`/conditions/search?q=${encodeURIComponent(search.trim())}`)
        .then(setConditions)
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [search]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!conditionId) {
      setError("Choose a condition to follow.");
      return;
    }
    try {
      await apiPost(`/conditions/${conditionId}/follow`, {
        body: {
          age_scope: ageScope,
          geography: geography.trim() || "global",
          frequency,
          notify_trials: notifyTrials,
          notify_recruiting_trials_only: notifyRecruitingOnly,
          notify_papers: notifyPapers,
          notify_regulatory: notifyRegulatory,
          notify_foundation_news: notifyFoundation,
          notify_major_only: majorOnly,
          quiet_hours_json: {},
          email_enabled: emailEnabled,
          push_enabled: false,
          in_app_enabled: inAppEnabled,
        },
      });
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Something went wrong.");
    }
  }

  if (loading) {
    return (
      <main className="container-page py-10">
        <p className="text-slate-600">Loading…</p>
      </main>
    );
  }

  return (
    <main className="container-page max-w-2xl py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Follow a condition</h1>
      <p className="mt-2 text-sm text-slate-600">
        Choose what to track. You can change this anytime. This app explains research only — not personal medical advice.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        <div>
          <label className="block text-sm font-medium text-slate-800">Search conditions</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder="e.g. NF1"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-800">Condition</label>
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={conditionId}
            onChange={(e) => setConditionId(e.target.value)}
          >
            {conditions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.canonical_name} ({c.slug})
              </option>
            ))}
          </select>
        </div>

        <fieldset className="space-y-3">
          <legend className="text-sm font-medium text-slate-800">Age relevance</legend>
          <p className="text-xs leading-relaxed text-slate-500">
            We use common research cutoffs: <strong className="font-medium text-slate-600">under 18</strong> vs{" "}
            <strong className="font-medium text-slate-600">18 and older</strong>. This helps filter updates and trials;
            it isn&apos;t a strict medical or legal definition everywhere.
          </p>
          <div className="space-y-2">
            <label className="flex cursor-pointer gap-3 rounded-lg border border-slate-200 p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
              <input
                type="radio"
                name="age"
                className="mt-1"
                checked={ageScope === "pediatric"}
                onChange={() => setAgeScope("pediatric")}
              />
              <span className="text-sm">
                <span className="font-medium text-slate-900">Pediatric</span>
                <span className="mt-0.5 block text-slate-600">Under 18 — prioritize child- and teen-focused research and trials.</span>
              </span>
            </label>
            <label className="flex cursor-pointer gap-3 rounded-lg border border-slate-200 p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
              <input
                type="radio"
                name="age"
                className="mt-1"
                checked={ageScope === "adult"}
                onChange={() => setAgeScope("adult")}
              />
              <span className="text-sm">
                <span className="font-medium text-slate-900">Adult</span>
                <span className="mt-0.5 block text-slate-600">18 and older — prioritize adult-focused research and trials.</span>
              </span>
            </label>
            <label className="flex cursor-pointer gap-3 rounded-lg border border-slate-200 p-3 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
              <input
                type="radio"
                name="age"
                className="mt-1"
                checked={ageScope === "both"}
                onChange={() => setAgeScope("both")}
              />
              <span className="text-sm">
                <span className="font-medium text-slate-900">Both</span>
                <span className="mt-0.5 block text-slate-600">All ages — don&apos;t narrow by age unless you change this later.</span>
              </span>
            </label>
          </div>
        </fieldset>

        <div>
          <label className="block text-sm font-medium text-slate-800">Country / region focus</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={geography}
            onChange={(e) => setGeography(e.target.value)}
            placeholder="global, US, EU, …"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-800">Research briefing frequency</label>
          <p className="mt-0.5 text-xs text-slate-500">
            Daily means a scheduled briefing about once per day per condition; with email on and SMTP configured, that
            can include a daily email. You can switch to weekly, turn briefings off, or disable email later under
            Notification settings.
          </p>
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value as typeof frequency)}
          >
            <option value="real_time">Real time (in-app when available)</option>
            <option value="daily">Daily briefing</option>
            <option value="weekly">Weekly briefing</option>
            <option value="off">Off</option>
          </select>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">What to notify me about</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyTrials} onChange={(e) => setNotifyTrials(e.target.checked)} />
            Clinical trials
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyRecruitingOnly} onChange={(e) => setNotifyRecruitingOnly(e.target.checked)} />
            Recruiting trials only
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyPapers} onChange={(e) => setNotifyPapers(e.target.checked)} />
            New published papers
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyRegulatory} onChange={(e) => setNotifyRegulatory(e.target.checked)} />
            FDA / regulatory updates
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyFoundation} onChange={(e) => setNotifyFoundation(e.target.checked)} />
            Foundation / trusted news
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={majorOnly} onChange={(e) => setMajorOnly(e.target.checked)} />
            Major meaningful changes only
          </label>
        </fieldset>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">Channels</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={inAppEnabled} onChange={(e) => setInAppEnabled(e.target.checked)} />
            In-app
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} />
            Email (when SMTP is configured)
          </label>
        </fieldset>

        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <div className="flex flex-wrap gap-3">
          <button type="submit" className="rounded-lg bg-primary px-5 py-2 text-white">
            Save & continue
          </button>
          <Link href="/dashboard" className="rounded-lg border border-slate-300 px-5 py-2 text-slate-800">
            Skip for now
          </Link>
        </div>
      </form>
    </main>
  );
}
