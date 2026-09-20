"use client";
import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { PracticeApi } from "@/lib/api-client";
import { useKit } from "@/lib/kit-cache";
import { KitNav } from "@/components/kit-overview";
import { EmptyState, LiveRegion } from "@/components/feedback";
import { startDrill, reveal, rate, undoLast, isFinished, weakCardIds, type Confidence, type DrillState } from "@/lib/drill";
import { WeakSpotsReport } from "@/components/weak-spots";

// Drill: queue snapshot at start; space reveals; 1/2/3 rate and advance;
// Backspace undoes; end summary offers weak-card re-drill; reviews save optimistically.
export function PracticeView({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const qc = useQueryClient();
  const cards = data?.kit?.flashcards ?? [];
  const [queue, setQueue] = useState<string[] | null>(null);
  const [drill, setDrill] = useState<DrillState | null>(null);
  const [live, setLive] = useState("");
  const [summary, setSummary] = useState<{ total: number; covered: number; uncovered: number } | null>(null);

  useEffect(() => {
    PracticeApi.queue(kitId).then((q) => setQueue(q.queue)).catch(() => setQueue([]));
    PracticeApi.summary(kitId).then(setSummary).catch(() => undefined);
  }, [kitId]);

  const begin = useCallback(
    (order: string[]) => {
      setDrill(startDrill(cards.map((c) => ({ id: c.id, front: c.front, back: c.back })), order, 10));
      setLive("Drill started. Card 1.");
    },
    [cards],
  );

  const record = useCallback(
    (id: string, confidence: Confidence) => {
      // Optimistic: announce at once; the server write happens in the background.
      setLive(`Rated ${confidence}.`);
      PracticeApi.review(kitId, id, confidence)
        .then(() => PracticeApi.summary(kitId).then(setSummary).catch(() => undefined))
        .catch(() => setLive("Rating failed to save — it will retry when you rate again."));
      void qc;
    },
    [kitId, qc],
  );

  useEffect(() => {
    if (!drill || isFinished(drill)) return;
    const onKey = (e: KeyboardEvent) => {
      const cur = drill.cards[drill.position];
      if (e.code === "Space") {
        e.preventDefault();
        setDrill((d) => (d ? reveal(d) : d));
      } else if (["1", "2", "3"].includes(e.key) && drill.revealed) {
        const c = Number(e.key) as Confidence;
        record(cur.id, c);
        setDrill((d) => {
          if (!d) return d;
          const next = rate(d, c);
          setLive(`Card ${Math.min(next.position + 1, next.cards.length)} of ${next.cards.length}.`);
          return next;
        });
      } else if (e.key === "Backspace") {
        e.preventDefault();
        setDrill((d) => (d ? undoLast(d) : d));
        setLive("Undid the last rating.");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drill, record]);

  if (cards.length === 0) {
    return (
      <div className="section">
        <KitNav kitId={kitId} />
        <div className="section-head" style={{ marginBottom: 16 }}>
          <span className="eyebrow">Practice</span>
        </div>
        <EmptyState title="Nothing to practise yet" body="Add Flashcards or regenerate the Kit, then start a Drill." />
      </div>
    );
  }

  if (!drill) {
    return (
      <div className="section">
        <KitNav kitId={kitId} />
        <div className="section-head" style={{ marginBottom: 16 }}>
          <span className="eyebrow">Practice</span>
        </div>
        <LiveRegion message={live} />
        {summary ? (
          <p role="status" style={{ marginBottom: 12 }}>
            <span className="pill pill-teal">Covered {summary.covered} of {summary.total} Flashcards</span>
          </p>
        ) : null}
        <button onClick={() => begin(queue ?? cards.map((c) => c.id))} className="button">
          Start Drill (10 cards, least sure first)
        </button>
        <div style={{ marginTop: 20 }}>
          <CoveragePanel kitId={kitId} />
        </div>
        <div style={{ marginTop: 16 }}>
          <WeakSpotsReport kitId={kitId} />
        </div>
      </div>
    );
  }

  if (isFinished(drill)) {
    const weak = weakCardIds(drill);
    return (
      <div className="section">
        <KitNav kitId={kitId} />
        <span className="eyebrow">Drill summary</span>
        <LiveRegion message={live} />
        <p role="status" style={{ marginTop: 12 }}>
          Rated {drill.ratings.length} cards. {weak.length} weak.
        </p>
        <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
          {weak.length > 0 ? (
            <button onClick={() => begin(weak)} className="button">
              Drill weak cards again
            </button>
          ) : null}
          <button onClick={() => begin(queue ?? cards.map((c) => c.id))} className="button button-secondary">
            New Drill
          </button>
        </div>
      </div>
    );
  }

  const cur = drill.cards[drill.position];
  return (
    <div className="section">
      <KitNav kitId={kitId} />
      <span className="eyebrow">Drill</span>
      <LiveRegion message={live} />
      <p role="status" aria-label={`Card ${drill.position + 1} of ${drill.cards.length}`} style={{ marginTop: 12 }}>
        <span className="pill">Card {drill.position + 1} of {drill.cards.length}</span>
      </p>
      <div className="drill-frame" style={{ marginTop: 16 }} tabIndex={0} aria-label="Flashcard">
        <p className="kit-display" style={{ fontSize: 22 }}>{cur.front}</p>
        {drill.revealed ? <div className="drill-answer">{cur.back}</div> : <p style={{ marginTop: 16, color: "var(--copy)" }}>Press Space to reveal.</p>}
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
        {!drill.revealed ? (
          <button onClick={() => setDrill(reveal(drill))} className="button">
            Reveal (Space)
          </button>
        ) : (
          ([1, 2, 3] as Confidence[]).map((c) => (
            <button
              key={c}
              onClick={() => {
                record(cur.id, c);
                setDrill(rate(drill, c));
              }}
              className="button button-secondary"
              aria-label={`Rate Confidence ${c}`}
            >
              {c}
            </button>
          ))
        )}
        <button onClick={() => setDrill(undoLast(drill))} disabled={drill.ratings.length === 0} className="button button-secondary">
          Undo (Backspace)
        </button>
      </div>
      <div style={{ marginTop: 20 }}>
        <CoveragePanel kitId={kitId} />
      </div>
    </div>
  );
}

export function CoveragePanel({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const reqs = data?.kit?.role?.requirements ?? [];
  const questions = data?.kit?.questions ?? [];
  const cards = data?.kit?.flashcards ?? [];
  return (
    <section aria-label="Coverage" className="neu-card-flat">
      <h2 className="kit-display" style={{ fontSize: 16 }}>Coverage</h2>
      <ul className="ruled-list" style={{ marginTop: 8 }}>
        {reqs.map((r) => {
          const nq = questions.filter((q) => q.requirement_ids.includes(r.id)).length;
          const nf = cards.filter((f) => (f.requirement_ids ?? []).includes(r.id)).length;
          return (
            <li key={r.id} style={{ padding: "10px 4px" }}>
              {r.id}: {nq} Questions, {nf} Flashcards
            </li>
          );
        })}
      </ul>
    </section>
  );
}
