/** English month/day so dates match the rest of the UI regardless of browser locale. */
export const DISPLAY_DATE_LOCALE = "en-US";

export function formatDateTimeMedium(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  if (Number.isNaN(d.getTime())) return typeof iso === "string" ? iso : "";
  return d.toLocaleString(DISPLAY_DATE_LOCALE, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
