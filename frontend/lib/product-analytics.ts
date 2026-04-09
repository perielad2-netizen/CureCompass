/**
 * Lightweight, privacy-conscious product analytics. Never blocks UI.
 * Enable by setting NEXT_PUBLIC_CC_ANALYTICS_URL to an endpoint that accepts JSON POST.
 * Optional: window.__CC_ANALYTICS_DEBUG__ = true for console logging in development.
 */

export type ProductAnalyticsPayload = Record<string, unknown>;

function isDebug(): boolean {
  return (
    typeof window !== "undefined" &&
    (window as unknown as { __CC_ANALYTICS_DEBUG__?: boolean }).__CC_ANALYTICS_DEBUG__ === true
  );
}

export function trackProductEvent(event: string, properties: ProductAnalyticsPayload = {}): void {
  try {
    const payload = {
      event,
      properties: { ...properties, ts: new Date().toISOString() },
    };
    if (isDebug() && process.env.NODE_ENV === "development") {
      // eslint-disable-next-line no-console
      console.debug("[cc-analytics]", event, properties);
    }
    const url = process.env.NEXT_PUBLIC_CC_ANALYTICS_URL;
    if (!url || typeof window === "undefined") return;
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      navigator.sendBeacon(url, blob);
      return;
    }
    void fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* never throw */
  }
}

export function trackAskAiToggleView(props: {
  condition_slug: string;
  locale: string;
  selected_view: "simple" | "detailed";
  has_structured_fields: boolean;
}): void {
  trackProductEvent("ask_ai_toggle_view", props);
}

export function trackAskAiFollowupChip(props: {
  condition_slug: string;
  locale: string;
  chip_key: string;
  position_index: number;
  has_structured_fields: boolean;
}): void {
  trackProductEvent("ask_ai_followup_chip_click", props);
}

export function trackAskAiSectionExpand(props: {
  condition_slug: string;
  locale: string;
  section_name: string;
}): void {
  trackProductEvent("ask_ai_section_expand", props);
}

export function trackAskAiHubCta(props: {
  condition_slug: string;
  locale: string;
  cta_name: "ask" | "trials" | "updates";
}): void {
  trackProductEvent("ask_ai_hub_cta_click", props);
}

export function trackAskAiTrustedSourceClick(props: {
  condition_slug: string;
  locale: string;
  source_name: string;
  source_kind: string;
}): void {
  trackProductEvent("ask_ai_trusted_source_click", props);
}

export function trackAskAiNewConversation(props: { condition_slug: string; locale: string }): void {
  trackProductEvent("ask_ai_new_conversation", props);
}

export function trackAskAiEmptyStatePromptClick(props: {
  condition_slug: string;
  locale: string;
  prompt_key: string;
}): void {
  trackProductEvent("ask_ai_empty_state_prompt_click", props);
}

export function trackAskAiLimitBlocked(props: { condition_slug: string; locale: string }): void {
  trackProductEvent("ask_ai_limit_blocked", props);
}

export function trackAskAiDashboardCtaClick(props: {
  condition_slug: string;
  locale: string;
  entry_point: "dashboard_primary";
}): void {
  trackProductEvent("ask_ai_dashboard_cta_click", props);
}

export function trackAskAiResearchCardCtaClick(props: {
  condition_slug: string;
  locale: string;
  source_name?: string;
  item_type?: string;
  entry_point: "dashboard_card" | "condition_card";
}): void {
  trackProductEvent("ask_ai_research_card_cta_click", props);
}
