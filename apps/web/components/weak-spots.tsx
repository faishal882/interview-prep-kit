"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { PracticeApi } from "@/lib/api-client";
import { useKit } from "@/lib/kit-cache";
import { rankWeakSpots, type WeakSpot } from "@/lib/weak-spots";
import { EmptyState, LiveRegion } from "@/components/feedback";

// Weak-spots report: Requirements ranked by readiness with reasons and links.
export function WeakSpotsReport({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const [server, setServer] = useState<WeakSpot[] | null>(null);
  const [live, setLive] = useState("");
  const reqs = data?.kit?.role?.requirements ?? [];
  const questions = data?.kit?.questions ?? [];
  const cards = data?.kit?.flashcards ?? [];

  useEffect(() => {
    PracticeApi.weakSpots(kitId)
      .then((res) => {
        const byId = new Map(reqs.map((r) => [r.id, r]));
        setServer(
          res.spots.map((s) => ({
            requirement_id: s.requirement_id,
            text: byId.get(s.requirement_id)?.text ?? s.requirement_id,
            priority: byId.get(s.requirement_id)?.priority ?? "",
            reasons: s.reasons,
            score: s.score,
            questionIds: (s as { question_ids?: string[] }).question_ids ?? [],
            flashcardIds: (s as { flashcard_ids?: string[] }).flashcard_ids ?? [],
          })),
        );
      })
      .catch(() => setServer(null));
  }, [kitId, reqs]);

  const spots = server ?? rankWeakSpots(reqs, questions, cards, {});
  useEffect(() => {
    if (spots.length > 0) setLive(`Weak spots ranked. Top: ${spots[0].requirement_id}.`);
  }, [spots.length]); // eslint-disable-line react-hooks/exhaustive-deps

  if (reqs.length === 0) {
    return <EmptyState title="No weak spots yet" body="Nothing practised yet, or no Requirements to rank. Start a Drill to generate practice data." />;
  }

  return (
    <section aria-label="Weak spots" id="weak-spots" className="neu-card-flat">
      <LiveRegion message={live} />
      <span className="eyebrow">Weak spots</span>
      <ol className="ruled-list" style={{ marginTop: 8 }}>
        {spots.map((s, i) => (
          <li key={s.requirement_id} style={{ padding: "14px 4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="proof-icon" aria-label={`Rank ${i + 1}`} style={{ width: 32, height: 32, flexBasis: 32, fontSize: 14 }}>
                {i + 1}
              </span>
              <span className="kit-display" style={{ fontWeight: 600 }}>{s.requirement_id}</span>
              <span className="pill pill-neutral">{s.priority}</span>
            </div>
            <p style={{ marginTop: 8 }}>{s.text}</p>
            <p style={{ marginTop: 4, fontSize: 13, color: "var(--copy)" }}>Why: {s.reasons.length > 0 ? s.reasons.join("; ") : "well covered"}</p>
            <p style={{ marginTop: 4, fontSize: 13 }}>
              <Link href={`/kits/${kitId}/questions`} style={{ color: "var(--primary)", fontWeight: 600 }}>
                {s.questionIds.length} Questions
              </Link>{" "}
              ·{" "}
              <Link href={`/kits/${kitId}/practice`} style={{ color: "var(--primary)", fontWeight: 600 }}>
                {s.flashcardIds.length} Flashcards
              </Link>
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
