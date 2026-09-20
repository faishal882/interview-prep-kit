"use client";
import { use } from "react";
import { useKit } from "@/lib/kit-cache";
import { ErrorState, Skeleton } from "@/components/feedback";
import { formatWithRef } from "@/lib/errors";
import { EditableQuestions } from "@/components/editable-views";

export default function QuestionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { isLoading, isError, error, refetch } = useKit(id);
  if (isLoading) return <Skeleton label="Loading Questions" />;
  if (isError)
    return <ErrorState message={formatWithRef(error)} referenceId={(error as { referenceId?: string })?.referenceId} onRetry={() => void refetch()} />;
  return <EditableQuestions kitId={id} />;
}
