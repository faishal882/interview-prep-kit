// Ordering mirrors backend fractional ordering (key_between) so reorder/move
// can be computed locally, shown instantly, then confirmed by the server.
const DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz";

function midpoint(a: string, b: string): string {
  let i = 0;
  let out = "";
  while (true) {
    const ca = i < a.length ? DIGITS.indexOf(a[i]) : 0;
    const cb = i < b.length ? DIGITS.indexOf(b[i]) : DIGITS.length - 1;
    if (cb - ca > 1) {
      out += DIGITS[(ca + cb) >> 1];
      return out;
    }
    out += a[i] ?? "0";
    i += 1;
    if (i > 64) return out + "n";
  }
}

export function keyBetween(prev?: string | null, next?: string | null): string {
  const p = prev ?? "";
  const n = next ?? "";
  if (!p && !n) return "a0";
  if (!p) return "a0" === n ? "a0" : midpoint("", n.replace(/^a/, ""));
  if (!n) return p + "n";
  const pp = p.replace(/^a/, "");
  const nn = n.replace(/^a/, "");
  return "a" + midpoint(pp, nn);
}

export interface OrderedItem {
  id: string;
  category: string;
  order: string;
}

/** Compute new order key for moving `id` after `afterId` (null = front) within a category. */
export function reorderWithin(items: OrderedItem[], category: string, id: string, afterId: string | null): OrderedItem[] {
  const siblings = items
    .filter((q) => q.category === category && q.id !== id)
    .sort((a, b) => (a.order < b.order ? -1 : 1));
  let newOrder: string;
  if (siblings.length === 0) newOrder = "a0";
  else if (afterId === null) newOrder = keyBetween(null, siblings[0].order);
  else {
    const idx = siblings.findIndex((s) => s.id === afterId);
    const at = idx === -1 ? siblings.length - 1 : idx;
    const prevK = siblings[at]?.order ?? null;
    const nextK = siblings[at + 1]?.order ?? null;
    newOrder = keyBetween(prevK, nextK);
  }
  return items.map((q) => (q.id === id ? { ...q, order: newOrder } : q));
}

/** Move across Category: caller sets category then reorders; counts as edit. */
export function moveToCategory(items: OrderedItem[], id: string, toCategory: string, afterId: string | null = null): OrderedItem[] {
  const moved = items.map((q) => (q.id === id ? { ...q, category: toCategory } : q));
  return reorderWithin(moved, toCategory, id, afterId);
}
