"use client";
import { useEffect, useRef, useState } from "react";
import { useEditing, useItemState } from "@/lib/editing";
import { ItemsApi } from "@/lib/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { kitKeys } from "@/lib/kit-cache";
import { ConfirmDialog, LiveRegion } from "@/components/feedback";
import { OriginBadge } from "@/components/badges";

// Autosave per field on blur or ~600 ms idle; writes serialised per item.
export function EditableField({
  collection,
  itemId,
  field,
  value,
  label,
  multiline = false,
}: {
  collection: string;
  itemId: string;
  field: string;
  value: string;
  label: string;
  multiline?: boolean;
}) {
  const { queue } = useEditing();
  const key = `${collection}:${itemId}:${field}`;
  const state = useItemState(key);
  const [draft, setDraft] = useState(value);
  const [live, setLive] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => setDraft(value), [value]);

  const schedule = (v: string) => {
    setDraft(v);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      queue.enqueue(key, v);
      setLive("Saving.");
    }, 600);
  };

  const commitNow = () => {
    if (timer.current) clearTimeout(timer.current);
    if (draft !== value) {
      queue.enqueue(key, draft, { immediate: true });
      setLive("Saving.");
    }
  };

  useEffect(() => {
    if (state === "saved") setLive("Saved.");
    if (state === "failed") setLive("Save failed. Retry available.");
    if (state === "conflict") setLive("Changed elsewhere. Choose Keep mine or Use latest.");
  }, [state]);

  const retry = () => void queue.retry(key);
  const keepMine = () => void queue.resolve(key, "mine");
  const useLatest = () =>
    void queue.resolve(key, "latest", async () => {
      // Refetch latest from cache invalidation path is handled by parent;
      // here we simply drop the draft back to the last known value.
      return { value, rev: undefined };
    });

  const statusLabel = state === "saving" ? "Saving" : state === "saved" ? "Saved" : state === "failed" ? "Failed" : state === "conflict" ? "Conflict" : "";
  const id = `${collection}-${itemId}-${field}`;
  return (
    <div className="mt-1">
      <LiveRegion message={live} />
      <label htmlFor={id} className="text-xs font-medium text-neutral-500">
        {label} {statusLabel ? <span aria-label={`Save status: ${statusLabel}`}>· {statusLabel}</span> : null}
      </label>
      {multiline ? (
        <textarea id={id} value={draft} onChange={(e) => schedule(e.target.value)} onBlur={commitNow} rows={3} className="mt-1 w-full rounded border px-2 py-1 text-sm" />
      ) : (
        <input id={id} value={draft} onChange={(e) => schedule(e.target.value)} onBlur={commitNow} className="mt-1 w-full rounded border px-2 py-1 text-sm" />
      )}
      {state === "failed" ? (
        <button onClick={retry} className="mt-1 rounded border px-2 py-0.5 text-xs">
          Retry
        </button>
      ) : null}
      {state === "conflict" ? (
        <div role="alert" className="mt-1 flex gap-2 text-xs">
          <button onClick={keepMine} className="rounded border px-2 py-0.5">
            Keep mine
          </button>
          <button onClick={useLatest} className="rounded border px-2 py-0.5">
            Use latest
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function DeleteItemButton({ kitId, collection, itemId, label }: { kitId: string; collection: string; itemId: string; label: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const confirm = async () => {
    setBusy(true);
    try {
      await ItemsApi.remove(kitId, collection, itemId);
      await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
      await qc.invalidateQueries({ queryKey: kitKeys.list });
    } finally {
      setBusy(false);
      setOpen(false);
    }
  };
  return (
    <>
      <button onClick={() => setOpen(true)} aria-label={label} className="rounded border px-2 py-0.5 text-xs">
        Delete
      </button>
      <ConfirmDialog open={open} title="Delete this item?" body="Deletion needs confirmation and cannot be undone." confirmLabel={busy ? "Deleting…" : "Delete"} onConfirm={() => void confirm()} onCancel={() => setOpen(false)} />
    </>
  );
}

export function PinToggle({ kitId, collection, itemId, pinned }: { kitId: string; collection: string; itemId: string; pinned?: boolean }) {
  const qc = useQueryClient();
  const toggle = async () => {
    await ItemsApi.patch(kitId, collection, itemId, { pinned: !pinned });
    await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
  };
  return (
    <button onClick={() => void toggle()} aria-pressed={!!pinned} aria-label={pinned ? "Unpin item" : "Pin item"} className="rounded border px-2 py-0.5 text-xs">
      {pinned ? "Pinned" : "Pin"}
    </button>
  );
}

export function GapBanner({ uncovered, kitId }: { uncovered: string[]; kitId: string }) {
  if (uncovered.length === 0) return null;
  return (
    <div role="alert" className="rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950">
      {uncovered.length} Gap{uncovered.length === 1 ? "" : "s"}: {uncovered.join(", ")}.{" "}
      <a href={`/kits/${kitId}/role`} className="underline">
        Review Requirements
      </a>
    </div>
  );
}

export function StaleBanner() {
  return (
    <div role="alert" className="rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950">
      Questions or Requirements changed after the Schedule was built — the Schedule may be out of date.
    </div>
  );
}

export function ItemBadges({ origin, edited, pinned }: { origin?: string; edited?: boolean; pinned?: boolean }) {
  return <OriginBadge meta={{ origin: (origin as "generated" | "user") ?? "generated", edited: !!edited, pinned: !!pinned, rev: 1, order: "" }} />;
}
