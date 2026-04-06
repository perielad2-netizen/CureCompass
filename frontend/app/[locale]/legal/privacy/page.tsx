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
  const t = await getTranslations({ locale, namespace: "LegalPrivacy" });
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

export default async function PrivacyPage({ params }: Props) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }
  setRequestLocale(locale);
  const t = await getTranslations("LegalPrivacy");

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

        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-slate-900">{t("s1Title")}</h2>
          <p>{t("s1Intro")}</p>
          <div>
            <p className="font-medium text-slate-800">{t("s1aLabel")}</p>
            <ul className="mt-2 list-disc space-y-1 pl-6">
              <li>{t("s1a1")}</li>
              <li>{t("s1a2")}</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-slate-800">{t("s1bLabel")}</p>
            <ul className="mt-2 list-disc space-y-1 pl-6">
              <li>{t("s1b1")}</li>
              <li>{t("s1b2")}</li>
              <li>{t("s1b3")}</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-slate-800">{t("s1cLabel")}</p>
            <ul className="mt-2 list-disc space-y-1 pl-6">
              <li>{t("s1c1")}</li>
              <li>{t("s1c2")}</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-slate-800">{t("s1dLabel")}</p>
            <ul className="mt-2 list-disc space-y-1 pl-6">
              <li>{t("s1d1")}</li>
              <li>{t("s1d2")}</li>
            </ul>
          </div>
          <p className="font-medium text-slate-800">{t("s1Note")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s2Title")}</h2>
          <p>{t("s2Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s2u1")}</li>
            <li>{t("s2u2")}</li>
            <li>{t("s2u3")}</li>
            <li>{t("s2u4")}</li>
            <li>{t("s2u5")}</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s3Title")}</h2>
          <p>{t("s3p1")}</p>
          <p>{t("s3p2")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s3u1")}</li>
            <li>{t("s3u2")}</li>
            <li>{t("s3u3")}</li>
          </ul>
          <p>{t("s3p3")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s4Title")}</h2>
          <p>{t("s4Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s4u1")}</li>
            <li>{t("s4u2")}</li>
          </ul>
          <p>{t("s4p2")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s5Title")}</h2>
          <p>{t("s5Intro")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s5u1")}</li>
            <li>{t("s5u2")}</li>
            <li>{t("s5u3")}</li>
            <li>{t("s5u4")}</li>
          </ul>
          <p>{t("s5ContactIntro")}</p>
          <EmailLine />
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s6Title")}</h2>
          <p>{t("s6p1")}</p>
          <p>{t("s6p2")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s7Title")}</h2>
          <p>{t("s7p1")}</p>
          <p>{t("s7p2")}</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>{t("s7n1")}</li>
            <li>{t("s7n2")}</li>
            <li>{t("s7n3")}</li>
          </ul>
          <p>{t("s7p3")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s8Title")}</h2>
          <p>{t("s8p1")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s9Title")}</h2>
          <p>{t("s9p1")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s10Title")}</h2>
          <p>{t("s10p1")}</p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-slate-900">{t("s11Title")}</h2>
          <p>{t("s11ContactIntro")}</p>
          <EmailLine />
        </section>

        <p className="border-t border-slate-200 pt-8 text-sm">
          <Link href="/legal/terms" className="font-medium text-primary hover:underline">
            {t("seeTerms")}
          </Link>
        </p>
      </div>
    </main>
  );
}
