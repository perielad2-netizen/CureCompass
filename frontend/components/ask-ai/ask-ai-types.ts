/** Ask AI POST response: legacy fields + optional Phase 4 structured fields (additive). */

export type AskAiSourceRow = {
  title: string;
  source_url: string;
  research_item_id?: string;
  document_id?: string;
  item_type?: string;
};

export type AskAiTrustedSourceRow = {
  title: string;
  source_name: string;
  source_url: string;
  short_reason_used: string;
};

export type AskAiAnswerResponse = {
  conversation_id?: string;
  direct_answer: string;
  what_changed_recently: string;
  evidence_strength: string;
  available_now_or_experimental: string;
  suggested_doctor_questions: string[];
  sources: AskAiSourceRow[];
  simple_explanation?: string;
  key_facts?: string[];
  approved_treatments?: string;
  experimental_or_emerging_options?: string;
  relevant_clinical_trials?: string;
  warning_signs_or_when_to_seek_care?: string;
  what_is_uncertain?: string;
  trusted_sources?: AskAiTrustedSourceRow[];
};

export function askAnswerHasStructuredFields(a: AskAiAnswerResponse): boolean {
  if (Array.isArray(a.trusted_sources) && a.trusted_sources.length > 0) return true;
  if (typeof a.simple_explanation === "string" && a.simple_explanation.trim().length > 0) return true;
  if (Array.isArray(a.key_facts) && a.key_facts.length > 0) return true;
  if (typeof a.approved_treatments === "string" && a.approved_treatments.trim().length > 0) return true;
  if (typeof a.experimental_or_emerging_options === "string" && a.experimental_or_emerging_options.trim().length > 0)
    return true;
  if (typeof a.relevant_clinical_trials === "string" && a.relevant_clinical_trials.trim().length > 0) return true;
  if (typeof a.warning_signs_or_when_to_seek_care === "string" && a.warning_signs_or_when_to_seek_care.trim().length > 0)
    return true;
  if (typeof a.what_is_uncertain === "string" && a.what_is_uncertain.trim().length > 0) return true;
  return false;
}

export function hasMeaningfulText(s: string | undefined): boolean {
  if (s == null || !s.trim()) return false;
  const t = s.trim().toLowerCase();
  const placeholders = [
    "not applicable",
    "not covered in the supplied evidence",
    "לא רלוונטי",
    "לא מכוסה",
  ];
  return !placeholders.some((p) => t === p || t.startsWith(p + ".") || t.startsWith(p + ","));
}
