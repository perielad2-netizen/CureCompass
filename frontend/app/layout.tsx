import type { ReactNode } from "react";

/** Root segment required by Next.js; `html` / `body` / locale live in `[locale]/layout.tsx` (next-intl). */
export default function RootLayout({ children }: { children: ReactNode }) {
  return children;
}
