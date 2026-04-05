"use client";

import { useLayoutEffect, useState } from "react";
import { Link } from "@/i18n/navigation";
import { AUTH_CHANGED_EVENT } from "@/lib/auth-events";

function followHrefFromStorage(): "/onboarding" | "/register" {
  if (typeof window === "undefined") return "/register";
  return localStorage.getItem("cc_access_token") ? "/onboarding" : "/register";
}

/** Primary “follow a condition” CTA: register when signed out, onboarding when signed in. */
export function FollowConditionCtaLink({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  const [href, setHref] = useState<"/onboarding" | "/register">("/register");

  useLayoutEffect(() => {
    const sync = () => setHref(followHrefFromStorage());
    sync();
    window.addEventListener(AUTH_CHANGED_EVENT, sync);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, sync);
  }, []);

  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}
