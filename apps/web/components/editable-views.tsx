"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ItemsApi } from "@/lib/api-client";
import { kitKeys, useKit } from "@/lib/kit-cache";
import { EditingProvider } from "@/lib/editing";
import { KitNav } from "@/components/kit-overview";
import { EditableField, DeleteItemButton, PinToggle, GapBanner, StaleBanner } from "@/components/editable";
import { OriginBadge } from "@/components/badges";
import { EmptyState } from "@/components/feedback";
import type { Category } from "@/lib/types";

function useRefresh(kitId: string) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    qc.invalidateQueries({ queryKey: kitKeys.list });
  };
}

export function EditableQuestions({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const refresh = useRefresh(kitId);
  const questions = data?.kit?.questions ?? [];
  const uncovered = data?.kit?.coverage?.uncovered_requirement_ids ?? [];
  const [adding, setAdding] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [category, setCategory] = useState<Category>("technical");
  const cats: Category[] = ["technical", "behavioural", "system-design", "company-fit"];
  const add = async () => {
    await ItemsApi.create(kitId, "questions", { prompt, category, requirement_ids: [], answer_outline: "", difficulty: 1 });
    setPrompt("");
    setAdding(false);
    refresh();
  };
  return (
    <EditingProvider kitId={kitId}>
      <div className="space-y-4">
        <KitNav kitId={kitId} />
        <h1 className="text-xl font-semibold">Questions</h1>
        <GapBanner uncovered={uncovered} kitId={kitId} />
        {data?.schedule_stale ? <StaleBanner /> : null}
        <button onClick={() => setAdding((a) => !a)} className="rounded border px-2 py-1 text-sm">
          {adding ? "Cancel" : "Add a Question"}
        </button>
        {adding ? (
          <div className="rounded border p-3 text-sm">
            <label htmlFor="new-q" className="font-medium">
              Question
            </label>
            <input id="new-q" value={prompt} onChange={(e) => setPrompt(e.target.value)} className="mt-1 w-full rounded border px-2 py-1" />
            <label htmlFor="new-q-cat" className="mt-2 block font-medium">
              Category
            </label>
            <select id="new-q-cat" value={category} onChange={(e) => setCategory(e.target.value as Category)} className="mt-1 rounded border px-2 py-1">
              {cats.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <button onClick={() => void add()} disabled={!prompt.trim()} className="mt-2 rounded bg-neutral-900 px-3 py-1 text-white disabled:opacity-50 dark:bg-white dark:text-black">
              Add
            </button>
          </div>
        ) : null}
        {cats.map((c) => {
          const list = questions.filter((q) => q.category === c);
          return (
            <details key={c} open className="rounded border p-3">
              <summary className="cursor-pointer font-medium">
                {c} ({list.length})
              </summary>
              {list.length === 0 ? (
                <p className="mt-2 text-sm text-neutral-500">No Questions in this Category — no Requirements routed here, so nothing was padded.</p>
              ) : (
                <ul className="mt-2 space-y-3">
                  {list.map((q) => (
                    <li key={q.id} className="rounded border p-2 text-sm">
                      <div className="flex items-center gap-2">
                        <OriginBadge meta={q._meta} />
                        <span className="ml-auto flex gap-1">
                          <PinToggle kitId={kitId} collection="questions" itemId={q.id} pinned={q._meta?.pinned} />
                          <DeleteItemButton kitId={kitId} collection="questions" itemId={q.id} label={`Delete Question ${q.id}`} />
                        </span>
                      </div>
                      <EditableField collection="questions" itemId={q.id} field="prompt" value={q.prompt} label="Prompt" multiline />
                      <EditableField collection="questions" itemId={q.id} field="answer_outline" value={q.answer_outline} label="Answer outline" multiline />
                    </li>
                  ))}
                </ul>
              )}
            </details>
          );
        })}
      </div>
    </EditingProvider>
  );
}

export function EditableRole({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const refresh = useRefresh(kitId);
  const role = data?.kit?.role;
  const reqs = role?.requirements ?? [];
  const questions = data?.kit?.questions ?? [];
  const uncovered = new Set(data?.kit?.coverage?.uncovered_requirement_ids ?? []);
  const [text, setText] = useState("");
  const add = async () => {
    await ItemsApi.create(kitId, "requirements", { text, kind: "technical", priority: "must" });
    setText("");
    refresh();
  };
  return (
    <EditingProvider kitId={kitId}>
      <div className="space-y-4">
        <KitNav kitId={kitId} />
        <h1 className="text-xl font-semibold">Role</h1>
        <div className="flex gap-2 text-sm">
          <input aria-label="New Requirement text" value={text} onChange={(e) => setText(e.target.value)} placeholder="New Requirement…" className="w-full rounded border px-2 py-1" />
          <button onClick={() => void add()} disabled={!text.trim()} className="rounded border px-3 py-1 disabled:opacity-50">
            Add
          </button>
        </div>
        {reqs.length === 0 ? (
          <EmptyState title="No Requirements" body="The generator found no interviewable claims in this job description." />
        ) : (
          <ul className="space-y-2">
            {reqs.map((r) => {
              const n = questions.filter((q) => q.requirement_ids.includes(r.id)).length;
              const gap = uncovered.has(r.id) || n === 0;
              return (
                <li key={r.id} className="rounded border p-3 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs">{r.id}</span>
                    <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs dark:bg-neutral-800">{r.kind}</span>
                    <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs dark:bg-neutral-800">{r.priority}</span>
                    <OriginBadge meta={r._meta} />
                    {gap ? (
                      <span role="status" className="rounded bg-red-100 px-1.5 py-0.5 text-xs dark:bg-red-900">
                        Gap
                      </span>
                    ) : (
                      <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs dark:bg-green-900">{n} Questions</span>
                    )}
                    <span className="ml-auto flex gap-1">
                      <PinToggle kitId={kitId} collection="requirements" itemId={r.id} pinned={r._meta?.pinned} />
                      <DeleteItemButton kitId={kitId} collection="requirements" itemId={r.id} label={`Delete Requirement ${r.id}`} />
                    </span>
                  </div>
                  <EditableField collection="requirements" itemId={r.id} field="text" value={r.text} label="Requirement" multiline />
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </EditingProvider>
  );
}

export function EditableFlashcards({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const refresh = useRefresh(kitId);
  const cards = data?.kit?.flashcards ?? [];
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const add = async () => {
    await ItemsApi.create(kitId, "flashcards", { front, back, requirement_ids: [] });
    setFront("");
    setBack("");
    refresh();
  };
  return (
    <EditingProvider kitId={kitId}>
      <div className="space-y-4">
        <KitNav kitId={kitId} />
        <h1 className="text-xl font-semibold">Flashcards</h1>
        <div className="rounded border p-3 text-sm">
          <label htmlFor="fc-front" className="font-medium">
            Front
          </label>
          <input id="fc-front" value={front} onChange={(e) => setFront(e.target.value)} className="mt-1 w-full rounded border px-2 py-1" />
          <label htmlFor="fc-back" className="mt-2 block font-medium">
            Back
          </label>
          <input id="fc-back" value={back} onChange={(e) => setBack(e.target.value)} className="mt-1 w-full rounded border px-2 py-1" />
          <button onClick={() => void add()} disabled={!front.trim() || !back.trim()} className="mt-2 rounded border px-3 py-1 disabled:opacity-50">
            Add Flashcard
          </button>
        </div>
        {cards.length === 0 ? (
          <EmptyState title="No Flashcards yet" body="Flashcards are generated from must Requirements and technical Questions. Add some by hand or regenerate." />
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {cards.map((f) => (
              <li key={f.id} className="rounded border p-3 text-sm">
                <div className="flex items-center gap-2">
                  <OriginBadge meta={f._meta} />
                  <span className="ml-auto flex gap-1">
                    <PinToggle kitId={kitId} collection="flashcards" itemId={f.id} pinned={f._meta?.pinned} />
                    <DeleteItemButton kitId={kitId} collection="flashcards" itemId={f.id} label={`Delete Flashcard ${f.id}`} />
                  </span>
                </div>
                <EditableField collection="flashcards" itemId={f.id} field="front" value={f.front} label="Front" multiline />
                <EditableField collection="flashcards" itemId={f.id} field="back" value={f.back} label="Back" multiline />
              </li>
            ))}
          </ul>
        )}
      </div>
    </EditingProvider>
  );
}

export function EditableSchedule({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const days = data?.kit?.schedule?.days ?? [];
  return (
    <EditingProvider kitId={kitId}>
      <div className="space-y-4">
        <KitNav kitId={kitId} />
        <h1 className="text-xl font-semibold">Schedule</h1>
        {data?.schedule_stale ? <StaleBanner /> : null}
        <ol className="space-y-2">
          {days.map((d) => (
            <li key={d.day} className="rounded border p-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">Day {d.day}</span>
                <span className="ml-auto text-xs text-neutral-500">{d.minutes} min</span>
              </div>
              <EditableField collection="day" itemId={String(d.day)} field="focus" value={d.focus} label="Day focus" />
              <p className="mt-1 text-xs text-neutral-500">Questions: {d.question_ids.join(", ") || "—"}</p>
            </li>
          ))}
        </ol>
      </div>
    </EditingProvider>
  );
}

export function EditableBrief({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const brief = data?.kit?.company_brief;
  if (!brief) return null;
  return (
    <EditingProvider kitId={kitId}>
      <section aria-label="Company brief" className="rounded border p-3">
        <h2 className="font-medium">Company brief (editable)</h2>
        <EditableField collection="brief" itemId="brief" field="summary" value={brief.summary ?? ""} label="Summary" multiline />
        <EditableField collection="brief" itemId="brief" field="what_they_do" value={brief.what_they_do ?? ""} label="What they do" multiline />
        <EditableField collection="brief" itemId="brief" field="hiring_process" value={brief.hiring_process ?? ""} label="Hiring process" multiline />
      </section>
    </EditingProvider>
  );
}
