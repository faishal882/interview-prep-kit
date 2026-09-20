// Weak-spots view model: presents the server ranking with reasons and links.
// Falls back to a client computation when the endpoint is unavailable.
import type { Flashcard, Question, Requirement } from "./types";

export interface WeakSpot {
  requirement_id: string;
  text: string;
  priority: string;
  reasons: string[];
  score: number;
  questionIds: string[];
  flashcardIds: string[];
}

export function reasonFor(opts: {
  practised: boolean;
  lowConfidence: boolean;
  noQuestion: boolean;
  noFlashcard: boolean;
}): string[] {
  const out: string[] = [];
  if (!opts.practised) out.push("never practised");
  if (opts.lowConfidence) out.push("low Confidence");
  if (opts.noQuestion) out.push("no Question");
  if (opts.noFlashcard) out.push("no Flashcard");
  return out;
}

/** Client-side ranking mirroring the backend formula (priority + coverage + practice). */
export function rankWeakSpots(
  requirements: Requirement[],
  questions: Question[],
  flashcards: Flashcard[],
  practiceByCard: Record<string, { last?: number; count?: number }>,
): WeakSpot[] {
  const spots: WeakSpot[] = requirements.map((r) => {
    const qs = questions.filter((q) => q.requirement_ids.includes(r.id));
    const fs = flashcards.filter((f) => (f.requirement_ids ?? []).includes(r.id));
    const practisedCards = fs.filter((f) => (practiceByCard[f.id]?.count ?? 0) > 0);
    const low = fs.some((f) => (practiceByCard[f.id]?.last ?? 3) <= 2);
    const reasons = reasonFor({
      practised: practisedCards.length > 0,
      lowConfidence: low,
      noQuestion: qs.length === 0,
      noFlashcard: fs.length === 0,
    });
    let score = 0;
    if (r.priority === "must") score += 3;
    if (qs.length === 0) score += 3;
    if (fs.length === 0) score += 1;
    if (practisedCards.length === 0) score += 2;
    if (low) score += 2;
    return {
      requirement_id: r.id,
      text: r.text,
      priority: r.priority,
      reasons,
      score,
      questionIds: qs.map((q) => q.id),
      flashcardIds: fs.map((f) => f.id),
    };
  });
  spots.sort((a, b) => b.score - a.score || (a.requirement_id < b.requirement_id ? -1 : 1));
  return spots;
}
