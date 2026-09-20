"use client";
import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { KitsApi } from "@/lib/api-client";
import { kitKeys } from "@/lib/kit-cache";
import { ConfirmDialog, EmptyState, ErrorState, LiveRegion, Skeleton } from "@/components/feedback";
import { formatWithRef } from "@/lib/errors";
import { useKitsList } from "@/lib/kit-cache";

export function KitList() {
  const { data, isLoading, isError, error, refetch } = useKitsList();
  const qc = useQueryClient();
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [live, setLive] = useState("");
  const del = useMutation({
    mutationFn: (id: string) => KitsApi.remove(id),
    onSuccess: (_v, id) => {
      qc.setQueryData(kitKeys.list, (old: { kits: Array<Record<string, unknown>> } | undefined) => ({
        kits: (old?.kits ?? []).filter((k) => k.id !== id),
      }));
      setLive("Kit deleted.");
      setPendingDelete(null);
    },
  });

  if (isLoading) return <Skeleton label="Loading Kits" />;
  if (isError)
    return (
      <ErrorState
        message={formatWithRef(error)}
        referenceId={(error as { referenceId?: string })?.referenceId}
        onRetry={() => void refetch()}
      />
    );
  const kits = (data ?? []) as Array<Record<string, unknown>>;
  if (kits.length === 0)
    return (
      <EmptyState
        title="No Kits yet"
        body="A Kit turns a job description and a company website into interview Questions, Flashcards and a day-by-day Schedule."
        action={
          <Link href="/kits/new" className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white dark:bg-white dark:text-black">
            Create your first Kit
          </Link>
        }
      />
    );
  return (
    <div>
      <LiveRegion message={live} />
      <ul className="space-y-3">
        {kits.map((k) => (
          <li key={String(k.id)} className="rounded border p-4">
            <div className="flex items-center gap-2">
              <Link href={`/kits/${String(k.id)}`} className="font-medium underline">
                {String(k.company || k.role || k.id)}
              </Link>
              {String(k.status) === "generating" ? (
                <span aria-label="generating" className="rounded bg-amber-100 px-2 py-0.5 text-xs dark:bg-amber-900">
                  Generating…
                </span>
              ) : (
                <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs dark:bg-neutral-800">{String(k.status)}</span>
              )}
              <span className="ml-auto text-xs text-neutral-500">
                {String(k.requirement_count ?? "")} Requirements · {String(k.question_count ?? "")} Questions · {String(k.days ?? "")} days
              </span>
              <button onClick={() => setPendingDelete(String(k.id))} aria-label={`Delete Kit ${String(k.id)}`} className="rounded border px-2 py-0.5 text-xs">
                Delete
              </button>
            </div>
            <p className="mt-1 text-xs text-neutral-500">
              {String(k.role || "")} · updated {k.updated_at ? new Date(Number(k.updated_at) * 1000).toLocaleString() : "—"}
            </p>
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete this Kit?"
        body="This removes the Kit, its jobs and practice data. This cannot be undone."
        confirmLabel="Delete"
        onConfirm={() => pendingDelete && del.mutate(pendingDelete)}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
