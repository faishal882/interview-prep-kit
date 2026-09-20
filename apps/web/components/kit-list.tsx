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
          <Link href="/kits/new" className="button">
            Create your first Kit
          </Link>
        }
      />
    );
  return (
    <div>
      <LiveRegion message={live} />
      <ul className="ruled-list">
        {kits.map((k) => (
          <li key={String(k.id)}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <span className="proof-icon" aria-hidden="true">
                {(String(k.company || k.role || k.id) as string).slice(0, 1).toUpperCase()}
              </span>
              <Link href={`/kits/${String(k.id)}`} className="kit-display" style={{ fontSize: 17, textDecoration: "none" }}>
                {String(k.company || k.role || k.id)}
              </Link>
              {String(k.status) === "generating" ? (
                <span aria-label="generating" className="pill">
                  Generating…
                </span>
              ) : (
                <span className="pill pill-neutral">{String(k.status)}</span>
              )}
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 13, color: "var(--copy)" }}>
                  {String(k.requirement_count ?? "")} Requirements · {String(k.question_count ?? "")} Questions · {String(k.days ?? "")} days
                </span>
                <button onClick={() => setPendingDelete(String(k.id))} aria-label={`Delete Kit ${String(k.id)}`} className="button button-danger button-small">
                  Delete
                </button>
              </span>
            </div>
            <p style={{ marginTop: 6, fontSize: 13, color: "var(--copy)" }}>
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
