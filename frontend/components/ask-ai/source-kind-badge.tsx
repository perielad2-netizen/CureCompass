import { clsx } from "clsx";

export type SourceKind = "pubmed" | "clinicaltrials" | "fda" | "orphanet" | "medlineplus" | "document" | "other";

export function inferSourceKind(sourceName: string, sourceUrl: string): SourceKind {
  const blob = `${sourceName} ${sourceUrl}`.toLowerCase();
  if (blob.includes("pubmed")) return "pubmed";
  if (blob.includes("clinicaltrials.gov") || blob.includes("clinicaltrials") || blob.includes("nct"))
    return "clinicaltrials";
  if (blob.includes("openfda") || /\bfda\b/.test(blob)) return "fda";
  if (blob.includes("orphanet") || blob.includes("orpha")) return "orphanet";
  if (blob.includes("medlineplus") || blob.includes("medline")) return "medlineplus";
  if (
    sourceName.toLowerCase().includes("upload") ||
    sourceName.includes("המסמך") ||
    (!sourceUrl.trim() && sourceName.toLowerCase().includes("document"))
  )
    return "document";
  return "other";
}

const STYLES: Record<SourceKind, string> = {
  pubmed: "bg-sky-100 text-sky-900",
  clinicaltrials: "bg-violet-100 text-violet-900",
  fda: "bg-amber-100 text-amber-900",
  orphanet: "bg-emerald-100 text-emerald-900",
  medlineplus: "bg-teal-100 text-teal-900",
  document: "bg-slate-200 text-slate-800",
  other: "bg-slate-100 text-slate-700",
};

type Props = {
  kind: SourceKind;
  label: string;
};

export function SourceKindBadge({ kind, label }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex max-w-full items-center truncate rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
        STYLES[kind]
      )}
      title={label}
    >
      {label}
    </span>
  );
}
