import type { Metadata } from "next";
import { Link } from "@/i18n/navigation";

export const metadata: Metadata = {
  title: "Terms of use | CureCompass",
  description: "Terms of use for CureCompass (placeholder).",
};

export default function TermsPage() {
  return (
    <main className="container-page max-w-3xl py-10">
      <p className="text-sm font-medium text-primary">
        <Link href="/" className="hover:underline">
          ← Home
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-semibold text-slate-900">Terms of use</h1>
      <p className="mt-2 text-sm text-amber-800">
        <strong>Placeholder.</strong> Replace with counsel-reviewed terms before production or public launch.
      </p>

      <div className="mt-8 max-w-none space-y-4 leading-relaxed text-slate-700">
        <p>
          These <strong>placeholder terms</strong> are not a substitute for legal review. Your final terms should
          reflect your entity, product, acceptable use, liability limits allowed in your jurisdiction, and account
          rules.
        </p>
        <p>Common sections to include:</p>
        <ul className="list-disc space-y-2 pl-6">
          <li>Description of the service and eligibility.</li>
          <li>User responsibilities and prohibited uses.</li>
          <li>Intellectual property and content licensing.</li>
          <li>Disclaimer of warranties and limitation of liability.</li>
          <li>Termination and changes to the terms.</li>
          <li>Governing law and dispute resolution.</li>
        </ul>
        <p>
          CureCompass is an educational research-tracking tool, not a medical device and not a substitute for
          professional care. See also the{" "}
          <Link href="/legal/disclaimer" className="font-medium text-primary hover:underline">
            medical disclaimer
          </Link>
          .
        </p>
      </div>
    </main>
  );
}
