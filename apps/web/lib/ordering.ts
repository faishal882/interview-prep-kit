// Ordering mirrors the backend's fractional ordering (app/domain/ordering.py)
// so a reorder or move can be computed locally and shown instantly, then
// confirmed by the server.
export function keyBetween(a: string | null | undefined, b: string | null | undefined): string {
  if ((a ?? null) === null && (b ?? null) === null) return "a0";
  if ((a ?? null) === null) return decrement(b!);
  if ((b ?? null) === null) return increment(a!);
  const aa = a!;
  const bb = b!;
  if (aa >= bb) return increment(aa);
  let i = 0;
  while (i < aa.length && i < bb.length && aa[i] === bb[i]) i += 1;
  if (i < aa.length && i < bb.length) {
    const ca = aa.charCodeAt(i);
    const cb = bb.charCodeAt(i);
    if (cb - ca > 1) return aa.slice(0, i) + String.fromCharCode((ca + cb) >> 1);
    return aa.slice(0, i + 1) + "0";
  }
  return aa + "0";
}

function increment(k: string): string {
  const last = k[k.length - 1];
  if (last === "z") return k + "0";
  if (last === "9") return k.slice(0, -1) ? k.slice(0, -1) + "a" : "a";
  return k.slice(0, -1) + String.fromCharCode(last.charCodeAt(0) + 1);
}

function decrement(k: string): string {
  const first = k[0];
  if (first > "0") return (String.fromCharCode(first.charCodeAt(0) - 1) + k.slice(1)) as string;
  return "0" + k;
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
