"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { BrandLogo, brandLogoBarClassName } from "@/components/brand/brand-logo";

export function SiteFooter() {
  const t = useTranslations("Footer");

  return (
    <footer className="mt-auto border-t border-navy/10 bg-white/90 backdrop-blur-sm">
      <div className="container-page flex flex-col gap-6 py-10 text-sm text-navy-muted md:flex-row md:flex-wrap md:items-start md:justify-between md:gap-8">
        <div className="flex max-w-xl flex-col gap-4">
          <Link href="/" className="inline-block w-fit rounded-md outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
            <BrandLogo className={brandLogoBarClassName} />
          </Link>
          <p className="leading-relaxed">
            {t.rich("blurb", {
              bold: (chunks) => <strong className="font-medium text-navy">{chunks}</strong>,
            })}
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-5 gap-y-2" aria-label="Legal">
          <Link href="/legal/disclaimer" className="font-medium text-primary hover:underline">
            {t("disclaimer")}
          </Link>
          <Link href="/legal/privacy" className="font-medium text-primary hover:underline">
            {t("privacy")}
          </Link>
          <Link href="/legal/terms" className="font-medium text-primary hover:underline">
            {t("terms")}
          </Link>
        </nav>
      </div>
    </footer>
  );
}
