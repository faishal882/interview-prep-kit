// Drill engine: queue fixed at Drill start, position, reveal/rating, undo,
// end summary; reviews recorded through the optimistic path.
export type Confidence = 1 | 2 | 3;

export interface DrillCard {
  id: string;
  front: string;
  back: string;
}

export interface DrillState {
  cards: DrillCard[];
  position: number;
  revealed: boolean;
  ratings: Array<{ id: string; confidence: Confidence }>;
  undone: Array<{ id: string; confidence: Confidence }>;
}

export function startDrill(all: DrillCard[], queueOrder: string[], limit = 10): DrillState {
  const byId = new Map(all.map((c) => [c.id, c]));
  const cards = queueOrder.filter((id) => byId.has(id)).slice(0, limit).map((id) => byId.get(id)!);
  return { cards, position: 0, revealed: false, ratings: [], undone: [] };
}

export function reveal(state: DrillState): DrillState {
  return { ...state, revealed: true };
}

export function rate(state: DrillState, confidence: Confidence): DrillState {
  if (state.position >= state.cards.length) return state;
  const cur = state.cards[state.position];
  return {
    ...state,
    position: state.position + 1,
    revealed: false,
    ratings: [...state.ratings, { id: cur.id, confidence }],
    undone: [],
  };
}

export function undoLast(state: DrillState): DrillState {
  if (state.ratings.length === 0) return state;
  const last = state.ratings[state.ratings.length - 1];
  return {
    ...state,
    position: Math.max(0, state.position - 1),
    revealed: false,
    ratings: state.ratings.slice(0, -1),
    undone: [...state.undone, last],
  };
}

export function isFinished(state: DrillState): boolean {
  return state.position >= state.cards.length;
}

export function weakCardIds(state: DrillState): string[] {
  return state.ratings.filter((r) => r.confidence <= 2).map((r) => r.id);
}

export function coverageOf(total: number, rated: number): { rated: number; total: number; pct: number } {
  return { rated, total, pct: total === 0 ? 0 : Math.round((rated / total) * 100) };
}
