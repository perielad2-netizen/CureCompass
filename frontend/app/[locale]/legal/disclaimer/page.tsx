import type { Metadata } from "next";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "LegalDisclaimer" });
  return {
    title: `${t("metaTitle")} | CureCompass`,
    description: t("metaDescription"),
  };
}

export default async function MedicalDisclaimerPage({ params }: Props) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }
  setRequestLocale(locale);
  const t = await getTranslations("LegalDisclaimer");
  const strong = (chunks: ReactNode) => <strong>{chunks}</strong>;

  return (
    <main className="container-page max-w-3xl py-10">
      <p className="text-sm font-medium text-primary">
        <Link href="/" className="hover:underline">
          {t("backHome")}
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-semibold text-slate-900">{t("h1")}</h1>
      <p className="mt-2 text-sm text-slate-500">{t("lastUpdated")}</p>

      <div className="mt-8 max-w-none space-y-4 leading-relaxed text-slate-700">
        <p>{t.rich("p1", { strong })}</p>
        <p>{t.rich("p2", { strong })}</p>
        <p>{t("p3")}</p>
        <p>{t("p4")}</p>
      </div>
    </main>
  );
}
