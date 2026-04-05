"use client";

import { useLocale } from "next-intl";

/**
 * English research text inside an RTL (Hebrew) page: fixes bidi so periods and links read correctly.
 */
export function LtrIsland({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const locale = useLocale();
  if (locale !== "he") {
    return <>{children}</>;
  }
  return (
    <div dir="ltr" lang="en" className={`isolate text-left [text-align:left] ${className}`.trim()}>
      {children}
    </div>
  );
}

/** Inline English inside Hebrew paragraphs (summaries, titles). */
export function LtrInline({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const locale = useLocale();
  if (locale !== "he") {
    return <>{children}</>;
  }
  return (
    <span dir="ltr" lang="en" className={`inline-block max-w-full text-left align-top ${className}`.trim()}>
      {children}
    </span>
  );
}
