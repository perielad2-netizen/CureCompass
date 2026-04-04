export type Condition = {
  id: string;
  canonical_name: string;
  slug: string;
  description?: string;
};

export type AskAIRequest = {
  prompt: string;
  conditionSlug: string;
};
