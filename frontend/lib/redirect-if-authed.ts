import { apiGet } from "@/lib/api";

type RouterLike = { replace: (href: string) => void };

/** Send signed-in users away from auth-only pages (register / login). */
export async function redirectAuthenticatedUser(router: RouterLike): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("cc_access_token") : null;
  if (!token) return;
  try {
    const dash = await apiGet<{ followed_conditions: unknown[] }>("/dashboard");
    router.replace(dash.followed_conditions?.length ? "/dashboard" : "/onboarding");
  } catch {
    router.replace("/onboarding");
  }
}
