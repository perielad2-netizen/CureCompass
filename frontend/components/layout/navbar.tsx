"use client";

import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { BrandLogo, brandLogoBarClassName } from "@/components/brand/brand-logo";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { useCallback, useEffect, useState } from "react";
import { AUTH_CHANGED_EVENT } from "@/lib/auth-events";
import { apiGet } from "@/lib/api";

type MeResponse = {
  id: string;
  email: string;
  is_admin: boolean;
  preferred_locale?: "en" | "he";
};

export function Navbar() {
  const t = useTranslations("Nav");
  const router = useRouter();
  const [user, setUser] = useState<MeResponse | null>(null);
  const [checked, setChecked] = useState(false);

  const loadSession = useCallback(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("cc_access_token") : null;
    if (!token) {
      setUser(null);
      setChecked(true);
      return;
    }
    apiGet<MeResponse>("/auth/me")
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("cc_access_token");
        localStorage.removeItem("cc_refresh_token");
        setUser(null);
      })
      .finally(() => setChecked(true));
  }, []);

  useEffect(() => {
    loadSession();
    window.addEventListener(AUTH_CHANGED_EVENT, loadSession);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, loadSession);
  }, [loadSession]);

  function logout() {
    localStorage.removeItem("cc_access_token");
    localStorage.removeItem("cc_refresh_token");
    setUser(null);
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
    router.push("/");
  }

  return (
    <header className="border-b border-navy/10 bg-white/85 backdrop-blur-md">
      <div className="container-page flex min-h-[5rem] flex-wrap items-center justify-between gap-x-2 gap-y-3 py-2.5 md:min-h-[5.5rem] md:gap-y-2 md:py-3">
        <Link href="/" className="shrink-0 rounded-md py-0.5 outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary">
          <BrandLogo priority className={brandLogoBarClassName} />
        </Link>
        <nav className="flex w-full flex-wrap items-center gap-2 text-sm text-navy-muted sm:w-auto md:gap-3">
          <Link href="/dashboard" className="rounded-md px-3 py-2 transition-colors hover:bg-ice/80 hover:text-navy">
            {t("dashboard")}
          </Link>
          <Link href="/digests" className="rounded-md px-3 py-2 transition-colors hover:bg-ice/80 hover:text-navy" title={t("briefingsTitle")}>
            {t("briefings")}
          </Link>
          {!checked ? (
            <span className="px-3 py-2 text-slate-400" aria-busy="true">
              {t("loading")}
            </span>
          ) : user ? (
            <>
              <Link href="/bookmarks" className="rounded-md px-3 py-2 transition-colors hover:bg-ice/80 hover:text-navy">
                {t("saved")}
              </Link>
              {user.is_admin ? (
                <Link href="/admin" className="rounded-md px-3 py-2 transition-colors hover:bg-ice/80 hover:text-navy">
                  {t("admin")}
                </Link>
              ) : null}
              <Link href="/profile" className="rounded-md px-3 py-2 transition-colors hover:bg-ice/80 hover:text-navy">
                {t("profile")}
              </Link>
              <span className="max-w-[200px] truncate rounded-md bg-ice/60 px-3 py-2 text-navy-muted md:max-w-[280px]" title={user.email}>
                {t("signedInAs")} <span className="font-medium text-navy">{user.email}</span>
              </span>
              <button
                type="button"
                onClick={logout}
                className="rounded-md border border-navy/15 px-3 py-2 text-navy transition-colors hover:bg-ice/80"
              >
                {t("logOut")}
              </button>
            </>
          ) : (
            <>
              <Link href="/register" className="rounded-md px-3 py-2 transition-colors hover:bg-ice/80 hover:text-navy">
                {t("createAccount")}
              </Link>
              <Link
                href="/login"
                className="rounded-md bg-primary px-3 py-2 font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary-dark"
              >
                {t("signIn")}
              </Link>
            </>
          )}
          <div className="ms-1 border-s border-navy/10 ps-2 md:ms-2 md:ps-3">
            <LanguageSwitcher />
          </div>
        </nav>
      </div>
    </header>
  );
}
