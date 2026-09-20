"use client";
import { use } from "react";
import { useSearchParams } from "next/navigation";
import { useKit } from "@/lib/kit-cache";
import { ProgressScreen } from "@/components/progress-screen";
import { ErrorState, Skeleton } from "@/components/feedback";
import { formatWithRef } from "@/lib/errors";
import { KitOverview } from "@/components/kit-overview";

export default function KitDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const search = useSearchParams();
  const jobId = search.get("job_id");
  const { data, isLoading, isError, error, refetch } = useKit(id);

  if (isLoading) return <Skeleton label="Loading Kit" />;
  if (isError)
    return (
      <ErrorState
        message={formatWithRef(error)}
        referenceId={(error as { referenceId?: string })?.referenceId}
        onRetry={() => void refetch()}
      />
    );
  if (!data) return <Skeleton label="Loading Kit" />;
  if (data.status === "generating") return <ProgressScreen kitId={id} jobId={jobId} />;
  if (data.status === "failed")
    return <ProgressScreen kitId={id} jobId={jobId} />;
  return <KitOverview kitId={id} />;
}
