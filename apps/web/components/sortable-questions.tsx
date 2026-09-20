"use client";
import { useState } from "react";
import { DndContext, KeyboardSensor, PointerSensor, TouchSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useQueryClient } from "@tanstack/react-query";
import { ItemsApi } from "@/lib/api-client";
import { kitKeys } from "@/lib/kit-cache";
import { reorderWithin } from "@/lib/ordering";
import { LiveRegion } from "@/components/feedback";
import type { Question } from "@/lib/types";

function SortableItem({ id, children }: { id: string; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id });
  return (
    <li ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition, listStyle: "none" }} {...attributes}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
        <button {...listeners} aria-label={`Drag Question ${id} to reorder`} title="Drag to reorder (long-press on touch)" className="button button-secondary button-small no-print" style={{ minWidth: 34, padding: "4px 8px", cursor: "grab" }}>
          ⠿
        </button>
        <div style={{ minWidth: 0, flex: 1 }}>{children}</div>
      </div>
    </li>
  );
}

// Drag within a Category with pointer, touch (long-press) and keyboard;
// the Move menu on every Question is always available as the alternative.
export function SortableCategory({ kitId, category, items, render }: { kitId: string; category: string; items: Question[]; render: (q: Question, siblings: Question[]) => React.ReactNode }) {
  const qc = useQueryClient();
  const [live, setLive] = useState("");
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(TouchSensor, { activationConstraint: { delay: 300, tolerance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const sorted = [...items].sort((a, b) => ((a._meta?.order ?? "") < (b._meta?.order ?? "") ? -1 : 1));

  const onDragEnd = async (e: DragEndEvent) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const ids = sorted.map((q) => q.id);
    const from = ids.indexOf(String(active.id));
    const to = ids.indexOf(String(over.id));
    const afterId = from < to ? String(over.id) : to > 0 ? ids[to - 1] : null;
    const prev = qc.getQueryData(kitKeys.detail(kitId));
    qc.setQueryData(kitKeys.detail(kitId), (old: unknown) => {
      const doc = old as { kit?: { questions?: Question[] } };
      if (!doc?.kit?.questions) return old;
      const flat = doc.kit.questions.map((q) => ({ id: q.id, category: q.category, order: q._meta?.order ?? "a0" }));
      const reordered = reorderWithin(flat, category, String(active.id), afterId);
      const byId = new Map(reordered.map((r) => [r.id, r]));
      return { ...doc, kit: { ...doc.kit, questions: doc.kit.questions!.map((q) => { const r = byId.get(q.id); return r && q.id === String(active.id) ? { ...q, _meta: { ...q._meta!, order: r.order } } : q; }) } };
    });
    try {
      await ItemsApi.reorder(kitId, { id: String(active.id), after_id: afterId });
      setLive(`Reordered Question ${String(active.id)}.`);
      qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    } catch (err) {
      qc.setQueryData(kitKeys.detail(kitId), prev);
      setLive(`Reorder refused: ${err instanceof Error ? err.message : "error"}. Previous order restored.`);
    }
  };

  return (
    <div>
      <LiveRegion message={live} />
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(e) => void onDragEnd(e)}>
        <SortableContext items={sorted.map((q) => q.id)} strategy={verticalListSortingStrategy}>
          <ul style={{ marginTop: 12, display: "grid", gap: 12, padding: 0 }}>
            {sorted.map((q) => (
              <SortableItem key={q.id} id={q.id}>
                {render(q, sorted)}
              </SortableItem>
            ))}
          </ul>
        </SortableContext>
      </DndContext>
    </div>
  );
}
