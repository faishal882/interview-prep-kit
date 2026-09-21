// Ordering mirrors the backend fractional indexing (app/domain/ordering.py)
// exactly: base36 fraction strings with rational-exact midpoints, so a local
// reorder matches what the server stores. Shared vectors in
// fixtures/ordering-vectors.json are executed by both implementations.
const DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz";
const BASE = 36n;
const FIRST_KEY = "h";
export const KEY_LENGTH_LIMIT = 32;
const ENCODE_CAP = 64;

interface Frac {
  n: bigint;
  d: bigint;
}

function gcd(a: bigint, b: bigint): bigint {
  const x = a < 0n ? -a : a;
  const y = b < 0n ? -b : b;
  return y === 0n ? x : gcd(y, x % y);
}

function frac(n: bigint, d: bigint): Frac {
  const g = gcd(n, d);
  return { n: n / g, d: d / g };
}

function parse(key: string): Frac {
  let n = 0n;
  let d = 1n;
  for (const ch of key) {
    n = n * BASE + BigInt(DIGITS.indexOf(ch));
    d = d * BASE;
  }
  return frac(n, d);
}

function digitsValue(digits: number[]): Frac {
  let n = 0n;
  let d = 1n;
  for (const x of digits) {
    n = n * BASE + BigInt(x);
    d = d * BASE;
  }
  return frac(n, d);
}

function le(a: Frac, b: Frac): boolean {
  return a.n * b.d <= b.n * a.d;
}

function encodeBetween(lo: Frac, hi: Frac): string {
  const mid = frac(lo.n * hi.d + hi.n * lo.d, 2n * lo.d * hi.d);
  const digits: number[] = [];
  let rem: Frac = mid;
  for (let i = 0; i < ENCODE_CAP; i++) {
    const scaled = frac(rem.n * BASE, rem.d);
    let digit = Number(scaled.n / scaled.d);
    if (digit > 35) digit = 35;
    digits.push(digit);
    rem = frac(scaled.n - BigInt(digit) * scaled.d, scaled.d);
    if (rem.n === 0n) break;
  }
  while (le(digitsValue(digits), lo)) {
    const scaled = frac(rem.n * BASE, rem.d);
    let digit = Number(scaled.n / scaled.d);
    if (digit > 35) digit = 35;
    digits.push(digit);
    rem = frac(scaled.n - BigInt(digit) * scaled.d, scaled.d);
  }
  return digits.map((x) => DIGITS[x]).join("");
}

export function keyBetween(a: string | null | undefined, b: string | null | undefined): string {
  if ((a ?? null) === null && (b ?? null) === null) return FIRST_KEY;
  if ((a ?? null) === null) return encodeBetween(frac(0n, 1n), parse(b!));
  if ((b ?? null) === null) return encodeBetween(parse(a!), frac(1n, 1n));
  const va = parse(a!);
  const vb = parse(b!);
  if (va.n * vb.d >= vb.n * va.d) return encodeBetween(vb, frac(1n, 1n));
  return encodeBetween(va, vb);
}

export function needsRebalance(key: string): boolean {
  return key.length > KEY_LENGTH_LIMIT;
}

function toBase36Padded(value: bigint, width: number): string {
  let out = "";
  let v = value;
  for (let i = 0; i < width; i++) {
    out = DIGITS[Number(v % BASE)] + out;
    v = v / BASE;
  }
  return out;
}

export function rebalanceKeys(n: number): string[] {
  let width = 1;
  let span = BASE;
  while (span < BigInt(n + 2)) {
    width += 1;
    span = span * BASE;
  }
  const out: string[] = [];
  for (let i = 0; i < n; i++) {
    out.push(toBase36Padded((span * BigInt(i + 1)) / BigInt(n + 1), width));
  }
  return out;
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
  if (siblings.length === 0) newOrder = keyBetween(null, null);
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
