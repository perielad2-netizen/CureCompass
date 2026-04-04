import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Medical disclaimer | CureCompass",
  description: "Educational use only — not personal medical advice.",
};

export default function MedicalDisclaimerPage() {
  return (
    <main className="container-page max-w-3xl py-10">
      <p className="text-sm font-medium text-primary">
        <Link href="/" className="hover:underline">
          ← Home
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-semibold text-slate-900">Medical disclaimer</h1>
      <p className="mt-2 text-sm text-slate-500">Last updated for CureCompass v1 (placeholder date — replace before production).</p>

      <div className="mt-8 max-w-none space-y-4 leading-relaxed text-slate-700">
        <p>
          CureCompass provides <strong>general educational information</strong> about medical research, clinical trials,
          and regulatory news related to conditions you choose to follow. It does not provide medical diagnosis,
          treatment recommendations, or emergency guidance.
        </p>
        <p>
          Content is synthesized from public sources and AI-assisted summaries. It may be incomplete, outdated, or not
          applicable to your situation. <strong>Always consult a qualified healthcare professional</strong> for
          decisions about diagnosis, medications, procedures, or any change to your care.
        </p>
        <p>
          Do not use CureCompass in place of professional advice or delay seeking care because of something you read
          here. If you think you may have a medical emergency, contact emergency services immediately.
        </p>
        <p>
          By using CureCompass, you agree that the service is provided &quot;as is&quot; for informational purposes only
          and that we are not liable for actions taken based on the content.
        </p>
      </div>
    </main>
  );
}
