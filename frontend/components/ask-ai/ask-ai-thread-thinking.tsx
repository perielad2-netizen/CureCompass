"use client";

type Props = {
  /** Localized main line (calm, not a final answer). */
  label: string;
  /** Optional second line, e.g. subtitle. */
  sublabel?: string;
};

/**
 * Temporary in-thread placeholder while the assistant response is loading.
 * Distinct from real answer panels — dashed border, muted copy, pulse dots.
 */
export function AskAiThreadThinking({ label, sublabel }: Props) {
  return (
    <li className="list-none text-sm" aria-live="polite" role="status">
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-3 text-slate-600">
        <p className="font-medium text-slate-700">{label}</p>
        {sublabel ? <p className="mt-1 text-xs text-slate-500">{sublabel}</p> : null}
        <div className="mt-3 flex gap-1.5" aria-hidden>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400"
              style={{ animationDelay: `${i * 160}ms` }}
            />
          ))}
        </div>
      </div>
    </li>
  );
}
