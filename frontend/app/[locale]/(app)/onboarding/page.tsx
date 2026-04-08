"use client";

import { FormEvent, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { LtrIsland } from "@/components/ui/ltr-island";
import { ApiError, apiGet, apiPost } from "@/lib/api";

type ConditionRow = { id: string; canonical_name: string; slug: string };

type ConditionRequestResponse = {
  outcome: "existing" | "created";
  condition: { id: string; canonical_name: string; slug: string; description: string };
};

function mapAddConditionApiError(err: unknown, t: (key: string) => string): string {
  if (!(err instanceof ApiError)) return t("addConditionErrorGeneric");
  const m = err.message.toLowerCase();
  if (err.status === 503) return t("addConditionErrorService");
  if (err.status === 502) return t("addConditionErrorUpstream");
  if (err.status === 422) return t("addConditionErrorShort");
  if (err.status === 400) {
    if (m.includes("recognize") || m.includes("specific medical") || m.includes("clinician")) {
      return t("addConditionErrorNotMedical");
    }
    if (m.includes("short")) return t("addConditionErrorShort");
  }
  return t("addConditionErrorGeneric");
}

export default function OnboardingPage() {
  const t = useTranslations("Onboarding");
  const locale = useLocale();
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
  const [errorFromApi, setErrorFromApi] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showAddCondition, setShowAddCondition] = useState(false);
  const [addQuery, setAddQuery] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState("");
  const [addSuccess, setAddSuccess] = useState("");

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
      .catch(() => {
        setError(t("loadConditionsError"));
        setErrorFromApi(false);
      })
      .finally(() => setLoading(false));
  }, [router, t]);

  useEffect(() => {
    if (!search.trim()) return;
    const timer = setTimeout(() => {
      apiGet<ConditionRow[]>(`/conditions/search?q=${encodeURIComponent(search.trim())}`)
        .then(setConditions)
        .catch(() => {});
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  async function onAddCondition() {
    setAddError("");
    setAddSuccess("");
    const q = addQuery.trim();
    if (q.length < 2) {
      setAddError(t("addConditionErrorShort"));
      return;
    }
    setAddLoading(true);
    try {
      const res = await apiPost<ConditionRequestResponse>("/conditions/request", {
        body: { query: q, locale: locale === "he" ? "he" : "en" },
      });
      const rows = await apiGet<ConditionRow[]>("/conditions");
      setConditions(rows);
      setConditionId(res.condition.id);
      setSearch("");
      setAddSuccess(
        res.outcome === "created"
          ? t("addConditionSuccessCreated", { name: res.condition.canonical_name })
          : t("addConditionSuccessExisting", { name: res.condition.canonical_name })
      );
      setAddQuery("");
    } catch (err) {
      setAddError(mapAddConditionApiError(err, t));
    } finally {
      setAddLoading(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setErrorFromApi(false);
    if (!conditionId) {
      setError(t("chooseConditionError"));
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
      if (err instanceof ApiError) {
        setError(err.message);
        setErrorFromApi(true);
      } else {
        setError(t("genericError"));
        setErrorFromApi(false);
      }
    }
  }

  if (loading) {
    return (
      <main className="container-page py-10">
        <p className="text-slate-600">{t("loading")}</p>
      </main>
    );
  }

  const errorBody =
    error && locale === "he" && errorFromApi ? (
      <LtrIsland>
        <span>{error}</span>
      </LtrIsland>
    ) : (
      error
    );

  return (
    <main className="container-page max-w-2xl py-10">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      <p className="mt-2 text-sm text-slate-600">{t("intro")}</p>

      <form onSubmit={onSubmit} className="mt-8 space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-calm">
        <div>
          <label className="block text-sm font-medium text-slate-800">{t("searchLabel")}</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            placeholder={t("searchPlaceholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-800">{t("conditionLabel")}</label>
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

        <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4">
          <button
            type="button"
            className="text-sm font-medium text-primary hover:underline"
            onClick={() => {
              setShowAddCondition((v) => !v);
              setAddError("");
              setAddSuccess("");
            }}
          >
            {t("addConditionToggle")}
          </button>
          {showAddCondition ? (
            <div className="mt-3 space-y-3">
              <p className="text-xs text-slate-600">{t("addConditionIntro")}</p>
              <input
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
                placeholder={t("addConditionPlaceholder")}
                value={addQuery}
                onChange={(e) => setAddQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void onAddCondition();
                  }
                }}
                disabled={addLoading}
                dir="auto"
              />
              <button
                type="button"
                disabled={addLoading}
                className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-60"
                onClick={() => void onAddCondition()}
              >
                {addLoading ? t("addConditionLoading") : t("addConditionSubmit")}
              </button>
              {addSuccess ? (
                <p className="text-sm text-emerald-700">
                  {locale === "he" ? (
                    <LtrIsland>
                      <span>{addSuccess}</span>
                    </LtrIsland>
                  ) : (
                    addSuccess
                  )}
                </p>
              ) : null}
              {addError ? <p className="text-sm text-rose-600">{addError}</p> : null}
            </div>
          ) : null}
        </div>

        <fieldset className="space-y-3">
          <legend className="text-sm font-medium text-slate-800">{t("ageLegend")}</legend>
          <p className="text-xs leading-relaxed text-slate-500">
            {t.rich("ageHelp", {
              under18: (chunks) => <strong className="font-medium text-slate-600">{chunks}</strong>,
              adult: (chunks) => <strong className="font-medium text-slate-600">{chunks}</strong>,
            })}
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
                <span className="font-medium text-slate-900">{t("agePediatric")}</span>
                <span className="mt-0.5 block text-slate-600">{t("agePediatricDesc")}</span>
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
                <span className="font-medium text-slate-900">{t("ageAdult")}</span>
                <span className="mt-0.5 block text-slate-600">{t("ageAdultDesc")}</span>
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
                <span className="font-medium text-slate-900">{t("ageBoth")}</span>
                <span className="mt-0.5 block text-slate-600">{t("ageBothDesc")}</span>
              </span>
            </label>
          </div>
        </fieldset>

        <div>
          <label className="block text-sm font-medium text-slate-800">{t("geographyLabel")}</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={geography}
            onChange={(e) => setGeography(e.target.value)}
            placeholder={t("geographyPlaceholder")}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-800">{t("frequencyLabel")}</label>
          <p className="mt-0.5 text-xs text-slate-500">{t("frequencyHelp")}</p>
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value as typeof frequency)}
          >
            <option value="real_time">{t("freqRealtime")}</option>
            <option value="daily">{t("freqDaily")}</option>
            <option value="weekly">{t("freqWeekly")}</option>
            <option value="off">{t("freqOff")}</option>
          </select>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">{t("notifyLegend")}</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyTrials} onChange={(e) => setNotifyTrials(e.target.checked)} />
            {t("notifyTrials")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyRecruitingOnly} onChange={(e) => setNotifyRecruitingOnly(e.target.checked)} />
            {t("notifyRecruitingOnly")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyPapers} onChange={(e) => setNotifyPapers(e.target.checked)} />
            {t("notifyPapers")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyRegulatory} onChange={(e) => setNotifyRegulatory(e.target.checked)} />
            {t("notifyRegulatory")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={notifyFoundation} onChange={(e) => setNotifyFoundation(e.target.checked)} />
            {t("notifyFoundation")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={majorOnly} onChange={(e) => setMajorOnly(e.target.checked)} />
            {t("notifyMajorOnly")}
          </label>
        </fieldset>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-slate-800">{t("channelsLegend")}</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={inAppEnabled} onChange={(e) => setInAppEnabled(e.target.checked)} />
            {t("channelInApp")}
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} />
            {t("channelEmail")}
          </label>
        </fieldset>

        {error ? <p className="text-sm text-rose-600">{errorBody}</p> : null}

        <div className="flex flex-wrap gap-3">
          <button type="submit" className="rounded-lg bg-primary px-5 py-2 text-white">
            {t("saveContinue")}
          </button>
          <Link href="/dashboard" className="rounded-lg border border-slate-300 px-5 py-2 text-slate-800">
            {t("skipForNow")}
          </Link>
        </div>
      </form>
    </main>
  );
}
