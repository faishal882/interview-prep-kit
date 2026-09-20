"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ItemsApi } from "@/lib/api-client";
import { kitKeys, useKit } from "@/lib/kit-cache";
import { reorderWithin } from "@/lib/ordering";
import { LiveRegion } from "@/components/feedback";
import type { Category, Question } from "@/lib/types";

// Always-available Move menu (up, down, to another Category): the primary
// path on phones and for keyboard users. Drag and drop enhances it.
export function MoveMenu({
  kitId,
  question,
  siblings,
}: {
  kitId: string;
  question: Question;
  siblings: Question[];
}) {
  const qc = useQueryClient();
  const [live, setLive] = useState("");
  const cats: Category[] = ["technical", "behavioural", "system-design", "company-fit"];

  const apply = async (afterId: string | null, category?: Category) => {
    const prev = qc.getQueryData(kitKeys.detail(kitId));
    // Optimistic: compute locally, confirm with server, roll back on refusal.
    qc.setQueryData(kitKeys.detail(kitId), (old: unknown) => {
      const doc = old as { kit?: { questions?: Question[] } };
      if (!doc?.kit?.questions) return old;
      const items = doc.kit.questions.map((q) => ({ id: q.id, category: q.category, order: q._meta?.order ?? "a0" }));
      const moved = category && category !== question.category
        ? items.map((i) => (i.id === question.id ? { ...i, category } : i))
        : items;
      const targetCat = category ?? question.category;
      const reordered = reorderWithin(moved, targetCat, question.id, afterId);
      const byId = new Map(reordered.map((r) => [r.id, r]));
      return {
        ...doc,
        kit: {
          ...doc.kit,
          questions: doc.kit.questions!.map((q) => {
            const r = byId.get(q.id);
            return r ? { ...q, category: r.category as Category, _meta: { ...q._meta!, order: r.order, edited: r.category !== q.category ? true : q._meta?.edited } } : q;
          }),
        },
      };
    });
    try {
      await ItemsApi.reorder(kitId, { id: question.id, ...(category ? { category } : {}), after_id: afterId });
      setLive(`Moved Question ${question.id}.`);
      qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    } catch (e) {
      qc.setQueryData(kitKeys.detail(kitId), prev);
      setLive(`Move refused: ${e instanceof Error ? e.message : "server refused"}. Order restored.`);
    }
  };

  const idx = siblings.findIndex((s) => s.id === question.id);
  return (
    <span className="inline-flex items-center gap-1">
      <LiveRegion message={live} />
      <button aria-label={`Move ${question.id} up`} disabled={idx <= 0} onClick={() => void apply(idx > 1 ? siblings[idx - 2].id : null)} className="rounded border px-1.5 py-0.5 text-xs disabled:opacity-40">
        ↑
      </button>
      <button aria-label={`Move ${question.id} down`} disabled={idx < 0 || idx >= siblings.length - 1} onClick={() => void apply(siblings[idx + 1].id)} className="rounded border px-1.5 py-0.5 text-xs disabled:opacity-40">
        ↓
      </button>
      <label className="sr-only" htmlFor={`move-${question.id}`}>
        Move {question.id} to Category
      </label>
      <select
        id={`move-${question.id}`}
        aria-label={`Move ${question.id} to Category`}
        value={question.category}
        onChange={(e) => void apply(null, e.target.value as Category)}
        className="rounded border px-1 py-0.5 text-xs"
      >
        {cats.map((c) => (
          <option key={c} value={c}>
            → {c}
          </option>
        ))}
      </select>
    </span>
  );
}

export function MoveToDayMenu({ kitId, questionId }: { kitId: string; questionId: string }) {
  const qc = useQueryClient();
  const { data } = useKit(kitId);
  const [live, setLive] = useState("");
  const days = data?.kit?.schedule?.days ?? [];
  const move = async (toDay: number) => {
    const prev = qc.getQueryData(kitKeys.detail(kitId));
    try {
      const { SectionsApi } = await import("@/lib/api-client");
      await SectionsApi.patchScheduleDay(kitId, toDay, {}).catch(() => undefined);
      // Move via dedicated endpoint; fall back to day-patch with rebuilt lists.
      await fetch(`/api/kits/${kitId}/schedule/move`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: questionId, to_day: toDay }),
      });
      setLive(`Moved to day ${toDay}.`);
      qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    } catch (e) {
      qc.setQueryData(kitKeys.detail(kitId), prev);
      setLive(`Move refused: ${e instanceof Error ? e.message : "error"}.`);
    }
  };
  if (days.length === 0) return null;
  return (
    <span className="inline-flex items-center gap-1">
      <LiveRegion message={live} />
      <label className="sr-only" htmlFor={`moveday-${questionId}`}>
        Move to day
      </label>
      <select id={`moveday-${questionId}`} aria-label="Move to day" defaultValue="" onChange={(e) => e.target.value && void move(Number(e.target.value))} className="rounded border px-1 py-0.5 text-xs">
        <option value="">Move to day…</option>
        {days.map((d) => (
          <option key={d.day} value={d.day}>
            Day {d.day}
          </option>
        ))}
      </select>
    </span>
  );
}
