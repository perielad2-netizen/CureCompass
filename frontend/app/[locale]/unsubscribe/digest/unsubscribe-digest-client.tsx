"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { ApiError, apiPost } from "@/lib/api";

export function UnsubscribeDigestClient() {
  const t = useTranslations("DigestUnsubscribe");
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [phase, setPhase] = useState<"loading" | "ok" | "err">("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    if (!token || token.length < 10) {
      setPhase("err");
      setDetail(t("missingToken"));
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const res = await apiPost<{ message: string }>("/unsubscribe/digest", {
          body: { token },
          authRetry: false,
        });
        if (!cancelled) {
          setPhase("ok");
          setDetail(res.message);
        }
      } catch (e) {
        if (!cancelled) {
          setPhase("err");
          setDetail(e instanceof ApiError ? e.message : t("genericError"));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token, t]);

  return (
    <main className="container-page max-w-lg py-16">
      <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
      {phase === "loading" ? (
        <p className="mt-4 text-slate-600">{t("loading")}</p>
      ) : phase === "ok" ? (
        <p className="mt-4 text-slate-700">{detail}</p>
      ) : (
        <p className="mt-4 text-rose-700">{detail}</p>
      )}
      <p className="mt-6 text-sm text-slate-600">{t("settingsHint")}</p>
      <Link href="/settings/notifications" className="mt-3 inline-block text-sm font-medium text-primary">
        {t("openSettings")}
      </Link>
    </main>
  );
}
