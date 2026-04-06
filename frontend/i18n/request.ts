import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;
  if (!locale || !routing.locales.includes(locale as "en" | "he")) {
    locale = routing.defaultLocale;
  }
  const [base, legal] = await Promise.all([
    import(`../messages/${locale}.json`),
    import(`../messages/legal.${locale}.json`),
  ]);
  return {
    locale,
    messages: { ...base.default, ...legal.default },
  };
});
