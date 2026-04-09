export function buildAskPrefillPrompt(params: {
  locale: string;
  researchTitle?: string | null;
  conditionName?: string | null;
}): string {
  const { locale, researchTitle, conditionName } = params;
  const title = (researchTitle || "").trim();
  const condition = (conditionName || "").trim();
  if (locale === "he") {
    if (title) {
      return `תסביר לי יותר על המחקר הזה ומה המשמעות שלו בשפה פשוטה:\n${title}`;
    }
    if (condition) {
      return `מה המשמעות של המחקר הזה עבור מטופלים עם ${condition}?`;
    }
    return "תסביר לי מה המשמעות של העדכון הזה בשפה פשוטה.";
  }
  if (title) {
    return `Tell me more about this research and what it means in simple language:\n${title}`;
  }
  if (condition) {
    return `What does this research mean for patients with ${condition}?`;
  }
  return "Tell me more about this research and what it means in simple language.";
}

export function buildConditionAskHref(params: {
  slug: string;
  prefill?: string | null;
}): string {
  const { slug, prefill } = params;
  const base = `/conditions/${encodeURIComponent(slug)}?tab=ask`;
  const q = (prefill || "").trim();
  if (!q) return base;
  return `${base}&ask_prefill=${encodeURIComponent(q)}`;
}

