"use client";
import { use } from "react";
import { useKit } from "@/lib/kit-cache";
import { ErrorState, Skeleton } from "@/components/feedback";
import { formatWithRef } from "@/lib/errors";
import { RoleView } from "@/components/kit-views";

export default function RolePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { isLoading, isError, error, refetch } = useKit(id);
  if (isLoading) return <Skeleton label="Loading Role" />;
  if (isError)
    return <ErrorState message={formatWithRef(error)} referenceId={(error as { referenceId?: string })?.referenceId} onRetry={() => void refetch()} />;
  return <RoleView kitId={id} />;
}
