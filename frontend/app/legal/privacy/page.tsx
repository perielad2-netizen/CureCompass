import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy policy | CureCompass",
  description: "How CureCompass handles your information (placeholder).",
};

export default function PrivacyPage() {
  return (
    <main className="container-page max-w-3xl py-10">
      <p className="text-sm font-medium text-primary">
        <Link href="/" className="hover:underline">
          ← Home
        </Link>
      </p>
      <h1 className="mt-4 text-3xl font-semibold text-slate-900">Privacy policy</h1>
      <p className="mt-2 text-sm text-amber-800">
        <strong>Placeholder.</strong> Replace with counsel-reviewed text before production or public launch.
      </p>

      <div className="mt-8 max-w-none space-y-4 leading-relaxed text-slate-700">
        <p>
          This is a <strong>placeholder privacy policy</strong>. It is not legal advice. Before you invite real users,
          work with qualified counsel to draft a policy that matches your data practices, jurisdictions, and hosting
          setup.
        </p>
        <p>Topics your final policy should cover typically include:</p>
        <ul className="list-disc space-y-2 pl-6">
          <li>What personal data you collect (e.g. account email, usage logs, AI prompts if stored).</li>
          <li>Legal bases and purposes for processing.</li>
          <li>How long you retain data and who you share it with (e.g. email provider, model API).</li>
          <li>User rights (access, deletion, export) and how to contact you.</li>
          <li>Cookies and analytics, if any.</li>
          <li>International transfers, if applicable.</li>
        </ul>
        <p>
          Contact: use the support channel you define for your deployment (not listed here in the template).
        </p>
      </div>
    </main>
  );
}
