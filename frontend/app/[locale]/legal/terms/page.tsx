import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

const SUPPORT_EMAIL = "support@curecompass.app";

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "LegalTerms" });
  return {
    title: `${t("metaTitle")} | CureCompass`,
    description: t("metaDescription"),
  };
}

function EmailLine() {
  return (
    <p className="mt-1">
      <a
        href={`mailto:${SUPPORT_EMAIL}`}
        dir="ltr"
        className="inline-block font-medium text-primary hover:underline"
        translate="no"
      >
        {SUPPORT_EMAIL}
      </a>
    </p>
  );
}

export default async function TermsPage({ params }: Props) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }
  setRequestLocale(locale);
  const t = await getTranslations("LegalTerms");

  return (
    <main className="container-page max-w-3xl py-10">
      <p className="text-sm font-medium text-primary">
        <Link href="/" className="hover:underline">
          {t("backHome")}
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-semibold text-slate-900">{t("h1")}</h1>
      <p className="mt-1 text-lg text-slate-600">{t("subtitle")}</p>
      <p className="mt-2 text-sm text-slate-500">{t("lastUpdated")}</p>

      <div className="mt-10 max-w-none space-y-10 leading-relaxed text-slate-700">
        <p>{t("intro")}</p>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s1Title")}</h2>
          <p>{t("s1Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s1u1")}</li>
            <li>{t("s1u2")}</li>
            <li>{t("s1u3")}</li>
          </ul>
          <p>{t("s1p2")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s2Title")}</h2>
          <p>{t("s2Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s2n1")}</li>
            <li>{t("s2n2")}</li>
            <li>{t("s2n3")}</li>
          </ul>
          <p>{t("s2p2")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s3Title")}</h2>
          <p>{t("s3p1")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s4Title")}</h2>
          <p>{t("s4Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s4u1")}</li>
            <li>{t("s4u2")}</li>
            <li>{t("s4u3")}</li>
            <li>{t("s4u4")}</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s5Title")}</h2>
          <p>{t("s5p1")}</p>
          <p>{t("s5p2")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s6Title")}</h2>
          <p>{t("s6p1")}</p>
          <p>{t("s6p2")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s7Title")}</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s7u1")}</li>
            <li>{t("s7u2")}</li>
            <li>{t("s7u3")}</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s8Title")}</h2>
          <p>{t("s8Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s8u1")}</li>
            <li>{t("s8u2")}</li>
            <li>{t("s8u3")}</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s9Title")}</h2>
          <p>{t("s9Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s9u1")}</li>
            <li>{t("s9u2")}</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s10Title")}</h2>
          <p>{t("s10p1")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s11Title")}</h2>
          <p>{t("s11p1")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s12Title")}</h2>
          <EmailLine />
        </section>

        <div className="flex flex-col gap-2 border-t border-slate-200 pt-8 text-sm sm:flex-row sm:gap-6">
          <Link href="/legal/disclaimer" className="font-medium text-primary hover:underline">
            {t("seeDisclaimer")}
          </Link>
          <Link href="/legal/privacy" className="font-medium text-primary hover:underline">
            {t("seePrivacy")}
          </Link>
        </div>
      </div>
    </main>
  );
}
