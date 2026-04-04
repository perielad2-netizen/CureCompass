import Link from "next/link";
import { BrandLogo } from "@/components/brand/brand-logo";

export default function LandingPage() {
  return (
    <main className="container-page py-12 md:py-20">
      <section className="relative overflow-hidden rounded-3xl border border-navy/10 bg-white/95 p-8 shadow-calm ring-1 ring-primary/15 md:p-14">
        <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-primary/10 blur-3xl" aria-hidden />
        <div className="pointer-events-none absolute -bottom-20 -left-16 h-56 w-56 rounded-full bg-navy/5 blur-3xl" aria-hidden />
        <div className="relative">
          <div className="mb-7 flex justify-center md:justify-start">
            <BrandLogo
              priority
              className="h-auto w-auto max-w-[min(248px,68vw)] object-contain object-center md:max-w-[284px] md:object-left"
            />
          </div>
          <p className="mb-3 text-center text-xs font-semibold uppercase tracking-[0.2em] text-navy-muted md:text-left">
            Condition-focused research intelligence
          </p>
          <h1 className="max-w-2xl text-center text-3xl font-semibold leading-tight tracking-tight text-navy md:text-left md:text-5xl">
            Track real progress for the conditions you care about.
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-center text-lg text-navy-muted md:mx-0 md:text-left">
            Trusted medical research updates, explained in simple language.
          </p>
          <p className="mx-auto mt-3 max-w-xl text-center text-sm font-medium text-primary md:mx-0 md:text-left">
            Clear answers. Real progress. Hope for the journey.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3 md:justify-start">
            <Link
              href="/register"
              className="rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-calm-teal transition-colors hover:bg-primary-dark"
            >
              Follow a condition
            </Link>
            <Link
              href="/dashboard"
              className="rounded-xl border border-navy/15 bg-white px-5 py-3 text-sm font-semibold text-navy transition-colors hover:border-primary/40 hover:bg-ice/50"
            >
              See latest progress
            </Link>
            <Link
              href="/conditions/nf1"
              className="rounded-xl border border-navy/15 bg-white px-5 py-3 text-sm font-semibold text-navy transition-colors hover:border-primary/40 hover:bg-ice/50"
            >
              Ask AI to explain
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
