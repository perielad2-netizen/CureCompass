import Link from "next/link";
import { BrandLogo, brandLogoBarClassName } from "@/components/brand/brand-logo";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-navy/10 bg-white/90 backdrop-blur-sm">
      <div className="container-page flex flex-col gap-6 py-10 text-sm text-navy-muted md:flex-row md:flex-wrap md:items-start md:justify-between md:gap-8">
        <div className="flex max-w-xl flex-col gap-4">
          <Link href="/" className="inline-block w-fit rounded-md outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
            <BrandLogo className={brandLogoBarClassName} />
          </Link>
          <p className="leading-relaxed">
            CureCompass explains trusted research in plain language. It is{" "}
            <strong className="font-medium text-navy">not</strong> personal medical advice. Always talk to a qualified
            clinician about your care.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-5 gap-y-2" aria-label="Legal">
          <Link href="/legal/disclaimer" className="font-medium text-primary hover:underline">
            Medical disclaimer
          </Link>
          <Link href="/legal/privacy" className="font-medium text-primary hover:underline">
            Privacy
          </Link>
          <Link href="/legal/terms" className="font-medium text-primary hover:underline">
            Terms
          </Link>
        </nav>
      </div>
    </footer>
  );
}
