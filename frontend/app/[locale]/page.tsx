import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { BrandLogo } from "@/components/brand/brand-logo";
import { FollowConditionCtaLink } from "@/components/marketing/follow-condition-cta-link";

export default async function LandingPage() {
  const t = await getTranslations("Home");

  return (
    <main className="container-page py-12 md:py-20">
      <section className="relative overflow-hidden rounded-3xl border border-navy/10 bg-white/95 p-8 shadow-calm ring-1 ring-primary/15 md:p-14">
        <div
          className="pointer-events-none absolute -top-24 -end-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl max-md:-end-8"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-20 -start-16 h-56 w-56 rounded-full bg-navy/5 blur-3xl max-md:-start-8"
          aria-hidden
        />
        <div className="relative">
          <div className="mb-7 flex justify-center md:justify-start">
            <BrandLogo
              priority
              className="h-auto w-auto max-w-[min(248px,68vw)] object-contain object-center md:max-w-[284px] md:object-start"
            />
          </div>
          <p className="mb-3 text-center text-xs font-semibold uppercase tracking-[0.2em] text-navy-muted md:text-start">
            {t("kicker")}
          </p>
          <h1 className="mx-auto max-w-2xl text-center text-3xl font-semibold leading-tight tracking-tight text-navy md:mx-0 md:text-start md:text-5xl">
            {t("headline")}
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-center text-lg text-navy-muted md:mx-0 md:text-start">{t("sub")}</p>
          <p className="mx-auto mt-3 max-w-xl text-center text-sm font-medium text-primary md:mx-0 md:text-start">
            {t("tagline")}
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3 md:justify-start">
            <FollowConditionCtaLink className="rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-calm-teal transition-colors hover:bg-primary-dark">
              {t("ctaFollow")}
            </FollowConditionCtaLink>
            <Link
              href="/dashboard"
              className="rounded-xl border border-navy/15 bg-white px-5 py-3 text-sm font-semibold text-navy transition-colors hover:border-primary/40 hover:bg-ice/50"
            >
              {t("ctaDashboard")}
            </Link>
            <Link
              href="/conditions/nf1"
              className="rounded-xl border border-navy/15 bg-white px-5 py-3 text-sm font-semibold text-navy transition-colors hover:border-primary/40 hover:bg-ice/50"
            >
              {t("ctaAsk")}
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
