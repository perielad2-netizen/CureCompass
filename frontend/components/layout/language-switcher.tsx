"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";
import { apiPatch } from "@/lib/api";
import type { AppLocale } from "@/i18n/routing";

export function LanguageSwitcher() {
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const pathname = usePathname();

  function go(next: AppLocale) {
    if (next === locale) return;
    router.replace(pathname, { locale: next });
    const token = typeof window !== "undefined" ? localStorage.getItem("cc_access_token") : null;
    if (token) {
      void apiPatch("/auth/me", { body: { preferred_locale: next } }).catch(() => {});
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1 text-sm" role="group" aria-label="Language">
      {routing.locales.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => go(l)}
          className={`rounded-md px-2 py-1 font-medium transition-colors ${
            l === locale ? "bg-primary/15 text-primary" : "text-navy-muted hover:bg-ice/80 hover:text-navy"
          }`}
        >
          {l === "he" ? "עברית" : "English"}
        </button>
      ))}
    </div>
  );
}
