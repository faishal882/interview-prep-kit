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
import { MoveMenu, MoveToDayMenu } from "@/components/move-menu";
import { SortableCategory } from "@/components/sortable-questions";
import { RegenCategoryButton, RegenScheduleButton, BriefRegen, GenerateForGapButton } from "@/components/regen";
import { CheckAnswer } from "@/components/check-answer";
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
      <div className="section">
        <KitNav kitId={kitId} />
        <div className="section-head" style={{ marginBottom: 16 }}>
          <span className="eyebrow">Questions</span>
        </div>
        <GapBanner uncovered={uncovered} kitId={kitId} />
        {data?.schedule_stale ? <div style={{ marginTop: 12 }}><StaleBanner /></div> : null}
        <div style={{ marginTop: 16 }}>
          <button onClick={() => setAdding((a) => !a)} className="button button-secondary button-small">
            {adding ? "Cancel" : "Add a Question"}
          </button>
        </div>
        {adding ? (
          <div className="neu-card-flat" style={{ marginTop: 12 }}>
            <label htmlFor="new-q" className="field-label">
              Question
            </label>
            <input id="new-q" value={prompt} onChange={(e) => setPrompt(e.target.value)} className="inset-input" />
            <label htmlFor="new-q-cat" className="field-label" style={{ marginTop: 12 }}>
              Category
            </label>
            <select id="new-q-cat" value={category} onChange={(e) => setCategory(e.target.value as Category)} className="inset-select">
              {cats.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <button onClick={() => void add()} disabled={!prompt.trim()} className="button button-small" style={{ marginTop: 12 }}>
              Add
            </button>
          </div>
        ) : null}
        <div style={{ marginTop: 8 }}>
          {cats.map((c) => {
            const list = questions.filter((q) => q.category === c);
            return (
              <details key={c} open className="disclosure">
                <summary>
                  {c} ({list.length})
                  <span className="plus" aria-hidden="true">+</span>
                </summary>
                <div style={{ marginTop: 8 }}>
                  <RegenCategoryButton kitId={kitId} category={c} />
                </div>
                {list.length === 0 ? (
                  <p style={{ marginTop: 12, color: "var(--copy)", paddingRight: 42 }}>No Questions in this Category — no Requirements routed here, so nothing was padded.</p>
                ) : (
                  <SortableCategory
                    kitId={kitId}
                    category={c}
                    items={list}
                    render={(q, siblings) => (
                      <div className="neu-card" style={{ padding: 18 }}>
                        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}>
                          <OriginBadge meta={q._meta} />
                          <MoveMenu kitId={kitId} question={q} siblings={siblings} />
                          <span style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
                            <PinToggle kitId={kitId} collection="questions" itemId={q.id} pinned={q._meta?.pinned} />
                            <DeleteItemButton kitId={kitId} collection="questions" itemId={q.id} label={`Delete Question ${q.id}`} />
                          </span>
                        </div>
                        <EditableField collection="questions" itemId={q.id} field="prompt" value={q.prompt} label="Prompt" multiline />
                        <EditableField collection="questions" itemId={q.id} field="answer_outline" value={q.answer_outline} label="Answer outline" multiline />
                        <CheckAnswer kitId={kitId} questionId={q.id} />
                      </div>
                    )}
                  />
                )}
              </details>
            );
          })}
        </div>
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
      <div className="section">
        <KitNav kitId={kitId} />
        <div className="section-head" style={{ marginBottom: 16 }}>
          <span className="eyebrow">Role</span>
        </div>
        <div className="neu-card-flat" style={{ display: "flex", gap: 12 }}>
          <input aria-label="New Requirement text" value={text} onChange={(e) => setText(e.target.value)} placeholder="New Requirement…" className="inset-input" />
          <button onClick={() => void add()} disabled={!text.trim()} className="button button-small" style={{ flexShrink: 0 }}>
            Add
          </button>
        </div>
        <div style={{ marginTop: 16 }}>
          {reqs.length === 0 ? (
            <EmptyState title="No Requirements" body="The generator found no interviewable claims in this job description." />
          ) : (
            <ul className="ruled-list">
              {reqs.map((r) => {
                const n = questions.filter((q) => q.requirement_ids.includes(r.id)).length;
                const gap = uncovered.has(r.id) || n === 0;
                return (
                  <li key={r.id}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ fontFamily: "var(--font-display)", fontSize: 12, color: "var(--copy)" }}>{r.id}</span>
                      <span className="pill pill-neutral">{r.kind}</span>
                      <span className="pill pill-neutral">{r.priority}</span>
                      <OriginBadge meta={r._meta} />
                      {gap ? (
                        <span role="status" className="pill pill-red">
                          Gap
                        </span>
                      ) : (
                        <span className="pill pill-teal">{n} Questions</span>
                      )}
                      {gap ? <GenerateForGapButton kitId={kitId} requirementId={r.id} /> : null}
                      <span style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
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
      <div className="section">
        <KitNav kitId={kitId} />
        <div className="section-head" style={{ marginBottom: 16 }}>
          <span className="eyebrow">Flashcards</span>
        </div>
        <div className="neu-card-flat">
          <label htmlFor="fc-front" className="field-label">
            Front
          </label>
          <input id="fc-front" value={front} onChange={(e) => setFront(e.target.value)} className="inset-input" />
          <label htmlFor="fc-back" className="field-label" style={{ marginTop: 12 }}>
            Back
          </label>
          <input id="fc-back" value={back} onChange={(e) => setBack(e.target.value)} className="inset-input" />
          <button onClick={() => void add()} disabled={!front.trim() || !back.trim()} className="button button-small" style={{ marginTop: 12 }}>
            Add Flashcard
          </button>
        </div>
        <div style={{ marginTop: 16 }}>
          {cards.length === 0 ? (
            <EmptyState title="No Flashcards yet" body="Flashcards are generated from must Requirements and technical Questions. Add some by hand or regenerate." />
          ) : (
            <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
              {cards.map((f) => (
                <li key={f.id} className="neu-card">
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <OriginBadge meta={f._meta} />
                    <span style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
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
      </div>
    </EditingProvider>
  );
}

export function EditableSchedule({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const days = data?.kit?.schedule?.days ?? [];
  return (
    <EditingProvider kitId={kitId}>
      <div className="section">
        <KitNav kitId={kitId} />
        <div className="section-head" style={{ marginBottom: 16 }}>
          <span className="eyebrow">Schedule</span>
        </div>
        {data?.schedule_stale ? <StaleBanner /> : null}
        <div style={{ marginTop: 12 }}>
          <RegenScheduleButton kitId={kitId} />
        </div>
        <ol className="ruled-list" style={{ listStyle: "none", marginTop: 8 }}>
          {days.map((d) => (
            <li key={d.day}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="proof-icon" aria-hidden="true" style={{ width: 36, height: 36, flexBasis: 36, fontSize: 15 }}>
                  {d.day}
                </span>
                <span className="kit-display" style={{ fontWeight: 600 }}>Day {d.day}</span>
                <span style={{ marginLeft: "auto", fontSize: 13, color: "var(--copy)" }}>{d.minutes} min</span>
              </div>
              <EditableField collection="day" itemId={String(d.day)} field="focus" value={d.focus} label="Day focus" />
              <p style={{ marginTop: 8, fontSize: 13, color: "var(--copy)" }}>Questions: {d.question_ids.join(", ") || "—"}</p>
              <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 8 }}>
                {d.question_ids.map((qid) => (
                  <span key={qid} className="pill pill-neutral">
                    {qid} <MoveToDayMenu kitId={kitId} questionId={qid} />
                  </span>
                ))}
              </div>
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
      <section aria-label="Company brief" className="neu-card-flat">
        <h2 className="kit-display" style={{ fontSize: 17 }}>Company brief (editable)</h2>
        <EditableField collection="brief" itemId="brief" field="summary" value={brief.summary ?? ""} label="Summary" multiline />
        <EditableField collection="brief" itemId="brief" field="what_they_do" value={brief.what_they_do ?? ""} label="What they do" multiline />
        <EditableField collection="brief" itemId="brief" field="hiring_process" value={brief.hiring_process ?? ""} label="Hiring process" multiline />
        <div style={{ marginTop: 12 }}>
          <BriefRegen kitId={kitId} />
        </div>
      </section>
    </EditingProvider>
  );
}
