"use client";

import type { RefObject } from "react";
import { useTranslations } from "next-intl";
import { AskAiAnswerPanel } from "@/components/ask-ai/ask-ai-answer-panel";
import { hydrateAskAiAnswerFromStored } from "@/components/ask-ai/hydrate-stored-answer";
import { LtrIsland } from "@/components/ui/ltr-island";

export type ThreadAssistantMessage = {
  id: string;
  content: string;
  structured_json: unknown;
  created_at: string;
};

type Props = {
  message: ThreadAssistantMessage;
  answerLtr: boolean;
  askTextareaRef: RefObject<HTMLTextAreaElement | null>;
  onPickFollowUp: (question: string) => void;
  analyticsContext?: { conditionSlug: string; locale: string };
};

export function AskAiStoredAssistantMessage({
  message,
  answerLtr,
  askTextareaRef,
  onPickFollowUp,
  analyticsContext,
}: Props) {
  const t = useTranslations("Condition");
  const hydrated = hydrateAskAiAnswerFromStored(message.structured_json, message.content);

  if (!hydrated) {
    const text = (message.content || "").trim();
    if (!text) return null;
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{t("askHistoryLegacyLabel")}</p>
        {answerLtr ? (
          <LtrIsland>
            <p className="mt-2 whitespace-pre-wrap">{text}</p>
          </LtrIsland>
        ) : (
          <p className="mt-2 whitespace-pre-wrap">{text}</p>
        )}
      </div>
    );
  }

  return (
    <AskAiAnswerPanel
      answer={hydrated}
      answerLtr={answerLtr}
      askTextareaRef={askTextareaRef}
      onPickFollowUp={onPickFollowUp}
      analyticsContext={analyticsContext}
      instanceKey={message.id}
      embeddedInThread
    />
  );
}
