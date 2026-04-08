import type { AskAiAnswerResponse, AskAiSourceRow, AskAiTrustedSourceRow } from "@/components/ask-ai/ask-ai-types";

function asRecord(v: unknown): Record<string, unknown> | null {
  if (v && typeof v === "object" && !Array.isArray(v)) return v as Record<string, unknown>;
  return null;
}

function strField(o: Record<string, unknown>, key: string, fallback = ""): string {
  const v = o[key];
  return typeof v === "string" ? v : fallback;
}

function stringList(o: Record<string, unknown>, key: string): string[] {
  const v = o[key];
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string");
}

function parseSources(raw: unknown): AskAiSourceRow[] {
  if (!Array.isArray(raw)) return [];
  const out: AskAiSourceRow[] = [];
  for (const item of raw) {
    const o = asRecord(item);
    if (!o) continue;
    const title = strField(o, "title");
    if (!title.trim()) continue;
    out.push({
      title,
      source_url: strField(o, "source_url"),
      research_item_id: strField(o, "research_item_id") || undefined,
      document_id: strField(o, "document_id") || undefined,
      item_type: strField(o, "item_type") || undefined,
    });
  }
  return out;
}

function parseTrustedSources(raw: unknown): AskAiTrustedSourceRow[] {
  if (!Array.isArray(raw)) return [];
  const out: AskAiTrustedSourceRow[] = [];
  for (const item of raw) {
    const o = asRecord(item);
    if (!o) continue;
    const title = strField(o, "title") || strField(o, "source_name");
    if (!title.trim()) continue;
    out.push({
      title: strField(o, "title") || strField(o, "source_name"),
      source_name: strField(o, "source_name"),
      source_url: strField(o, "source_url"),
      short_reason_used: strField(o, "short_reason_used"),
    });
  }
  return out;
}

/** User turn payload from API — not an assistant answer. */
export function isUserAskStructuredPayload(structured: unknown): boolean {
  const o = asRecord(structured);
  if (!o) return false;
  return "mode" in o && "document_ids" in o && typeof o.mode === "string" && !("direct_answer" in o);
}

/**
 * Build AskAiAnswerResponse from assistant `structured_json` + `content` fallback.
 * Returns null if there is nothing to show (should use plain content fallback only).
 */
export function hydrateAskAiAnswerFromStored(structuredJson: unknown, content: string): AskAiAnswerResponse | null {
  const contentTrim = (content || "").trim();
  const o = asRecord(structuredJson);

  if (!o) {
    if (!contentTrim) return null;
    return {
      direct_answer: contentTrim,
      what_changed_recently: "",
      evidence_strength: "",
      available_now_or_experimental: "",
      suggested_doctor_questions: [],
      sources: [],
    };
  }

  if (isUserAskStructuredPayload(o)) {
    return null;
  }

  const direct = strField(o, "direct_answer").trim() || contentTrim;
  if (!direct) return null;

  return {
    direct_answer: direct,
    what_changed_recently: strField(o, "what_changed_recently"),
    evidence_strength: strField(o, "evidence_strength"),
    available_now_or_experimental: strField(o, "available_now_or_experimental"),
    suggested_doctor_questions: stringList(o, "suggested_doctor_questions"),
    sources: parseSources(o.sources),
    simple_explanation: strField(o, "simple_explanation") || undefined,
    key_facts: stringList(o, "key_facts").length ? stringList(o, "key_facts") : undefined,
    approved_treatments: strField(o, "approved_treatments") || undefined,
    experimental_or_emerging_options: strField(o, "experimental_or_emerging_options") || undefined,
    relevant_clinical_trials: strField(o, "relevant_clinical_trials") || undefined,
    warning_signs_or_when_to_seek_care: strField(o, "warning_signs_or_when_to_seek_care") || undefined,
    what_is_uncertain: strField(o, "what_is_uncertain") || undefined,
    trusted_sources: (() => {
      const trusted = parseTrustedSources(o.trusted_sources);
      return trusted.length ? trusted : undefined;
    })(),
  };
}
