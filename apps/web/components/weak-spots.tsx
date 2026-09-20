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
    <section aria-label="Weak spots" id="weak-spots" className="rounded border p-3">
      <LiveRegion message={live} />
      <h2 className="font-medium">Weak spots</h2>
      <ol className="mt-2 space-y-2">
        {spots.map((s, i) => (
          <li key={s.requirement_id} className="rounded border p-2 text-sm">
            <div className="flex items-center gap-2">
              <span aria-label={`Rank ${i + 1}`} className="font-mono text-xs">
                #{i + 1}
              </span>
              <span className="font-medium">{s.requirement_id}</span>
              <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs dark:bg-neutral-800">{s.priority}</span>
            </div>
            <p className="mt-1">{s.text}</p>
            <p className="mt-1 text-xs text-neutral-500">Why: {s.reasons.length > 0 ? s.reasons.join("; ") : "well covered"}</p>
            <p className="mt-1 text-xs">
              <Link href={`/kits/${kitId}/questions`} className="underline">
                {s.questionIds.length} Questions
              </Link>{" "}
              ·{" "}
              <Link href={`/kits/${kitId}/practice`} className="underline">
                {s.flashcardIds.length} Flashcards
              </Link>
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
