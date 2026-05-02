import { Suspense } from "react";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import { UnsubscribeDigestClient } from "./unsubscribe-digest-client";

type Props = { params: Promise<{ locale: string }> };

export default async function UnsubscribeDigestPage({ params }: Props) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "DigestUnsubscribe" });

  return (
    <Suspense
      fallback={
        <main className="container-page max-w-lg py-16">
          <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
          <p className="mt-4 text-slate-600">{t("loading")}</p>
        </main>
      }
    >
      <UnsubscribeDigestClient />
    </Suspense>
  );
}
