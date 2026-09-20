"use client";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ItemsApi, SectionsApi } from "./api-client";
import { kitKeys } from "./kit-cache";
import { MutationQueue, type ItemState } from "./mutation-queue";
import type { KitDoc } from "./types";

// Binds one MutationQueue per Kit to the query cache: optimistic apply updates
// the cache at once; writes go to the items API with revision checks.
const Ctx = createContext<{ queue: MutationQueue; kitId: string } | null>(null);

function getItem(cache: KitDoc | undefined, collection: string, itemId: string): Record<string, unknown> | undefined {
  const kit = cache?.kit;
  if (!kit) return undefined;
  if (collection === "questions") return (kit.questions ?? []).find((q) => q.id === itemId) as unknown as Record<string, unknown>;
  if (collection === "flashcards") return (kit.flashcards ?? []).find((f) => f.id === itemId) as unknown as Record<string, unknown>;
  if (collection === "requirements") return (kit.role?.requirements ?? []).find((r) => r.id === itemId) as unknown as Record<string, unknown>;
  return undefined;
}

export function EditingProvider({ kitId, children }: { kitId: string; children: React.ReactNode }) {
  const qc = useQueryClient();
  const queue = useMemo(
    () =>
      new MutationQueue(
        (key, value) => {
          // key: `${collection}:${itemId}:${field}`
          const [collection, itemId, field] = key.split(":");
          qc.setQueryData(kitKeys.detail(kitId), (old: KitDoc | undefined) => {
            if (!old?.kit) return old;
            const clone: KitDoc = JSON.parse(JSON.stringify(old));
            if (collection === "brief" && clone.kit) {
              (clone.kit.company_brief as Record<string, unknown>)[field] = value;
              return clone;
            }
            if (collection === "day" && clone.kit?.schedule?.days) {
              const day = clone.kit.schedule.days.find((d) => String(d.day) === itemId);
              if (day) (day as unknown as Record<string, unknown>)[field] = value;
              return clone;
            }
            const item = getItem(clone, collection, itemId);
            if (item) (item as Record<string, unknown>)[field] = value;
            return clone;
          });
        },
        async (key, value, baseRev) => {
          const [collection, itemId, field] = key.split(":");
          if (collection === "brief") {
            await ItemsApi.patch(kitId, "brief", "brief", { [field]: value });
            return {};
          }
          if (collection === "day") {
            await SectionsApi.patchScheduleDay(kitId, Number(itemId), { [field]: value });
            return {};
          }
          const current = getItem(qc.getQueryData(kitKeys.detail(kitId)) as KitDoc | undefined, collection, itemId) as { _meta?: { rev?: number } } | undefined;
          const rev = current?._meta?.rev ?? baseRev;
          const res = (await ItemsApi.patch(kitId, collection, itemId, { [field]: value, ...(rev !== undefined ? { rev } : {}) })) as { _meta?: { rev?: number } };
          return { rev: res?._meta?.rev };
        },
      ),
    [qc, kitId],
  );
  return <Ctx.Provider value={{ queue, kitId }}>{children}</Ctx.Provider>;
}

export function useEditing(): { queue: MutationQueue; kitId: string } {
  const v = useContext(Ctx);
  if (!v) throw new Error("useEditing outside EditingProvider");
  return v;
}

export function useItemState(itemKey: string): ItemState {
  const { queue } = useEditing();
  const [state, setState] = useState<ItemState>(() => queue.stateOf(itemKey));
  useEffect(() => {
    setState(queue.stateOf(itemKey));
    return queue.subscribe((snap) => setState(snap[itemKey]?.state ?? "idle"));
  }, [queue, itemKey]);
  return state;
}
