"use client";
import Link from "next/link";
import { useKit } from "@/lib/kit-cache";
import { KitNav } from "@/components/kit-overview";
import { ExportButton } from "@/components/export-button";
import { EmptyState } from "@/components/feedback";
import { OriginBadge } from "@/components/badges";

// Full read-only views. Each has its own address and survives reload.
export function OverviewView({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const kit = data?.kit;
  const brief = kit?.company_brief;
  const warnings = kit?.warnings ?? [];
  const uncovered = kit?.coverage?.uncovered_requirement_ids ?? [];
  const hasHiring = Boolean(brief?.summary || brief?.what_they_do || brief?.hiring_process);
  return (
    <div className="space-y-4">
      <KitNav kitId={kitId} />
      <div className="flex items-center gap-2">
        <h1 className="text-xl font-semibold">Overview</h1>
        <span className="ml-auto" />
        <ExportButton kitId={kitId} />
      </div>
      {warnings.length > 0 ? (
        <div role="alert" className="rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950">
          Warnings: {warnings.join("; ")}
        </div>
      ) : null}
      {!hasHiring ? (
        <div role="status" className="rounded border p-4 text-sm">
          We could not retrieve hiring information for this company. The brief below is honest about what was found — see the research log.
        </div>
      ) : null}
      <section aria-label="Company brief">
        <h2 className="font-medium">Company brief</h2>
        <p className="mt-1 text-sm">{brief?.summary || "No summary."}</p>
        {brief?.what_they_do ? <p className="mt-1 text-sm">What they do: {brief.what_they_do}</p> : null}
        {brief?.hiring_process ? <p className="mt-1 text-sm">How they hire: {brief.hiring_process}</p> : null}
      </section>
      <section aria-label="Sources">
        <h2 className="font-medium">Sources</h2>
        {(brief?.sources ?? []).length === 0 ? (
          <p className="text-sm text-neutral-500">No sources retrieved.</p>
        ) : (
          <ul className="list-disc pl-5 text-sm">
            {(brief?.sources ?? []).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
      </section>
      <section aria-label="Coverage">
        <h2 className="font-medium">Coverage</h2>
        <p className="text-sm">
          {uncovered.length === 0 ? "All Requirements covered." : `${uncovered.length} Gap${uncovered.length === 1 ? "" : "s"}: ${uncovered.join(", ")}`}
        </p>
        <Link href={`/kits/${kitId}/role`} className="text-sm underline">
          See Role view
        </Link>
      </section>
    </div>
  );
}

export function RoleView({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const role = data?.kit?.role;
  const questions = data?.kit?.questions ?? [];
  const uncovered = new Set(data?.kit?.coverage?.uncovered_requirement_ids ?? []);
  const coverCount = (rid: string) => questions.filter((q) => q.requirement_ids.includes(rid)).length;
  const reqs = role?.requirements ?? [];
  return (
    <div className="space-y-4">
      <KitNav kitId={kitId} />
      <h1 className="text-xl font-semibold">Role</h1>
      {(role?.responsibilities ?? []).length > 0 ? (
        <section aria-label="Responsibilities">
          <h2 className="font-medium">Responsibilities</h2>
          <ul className="list-disc pl-5 text-sm">
            {role!.responsibilities!.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {reqs.length === 0 ? (
        <EmptyState title="No Requirements" body="The generator found no interviewable claims in this job description." />
      ) : (
        <ul className="space-y-2">
          {reqs.map((r) => {
            const n = coverCount(r.id);
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
                </div>
                <p className="mt-1">{r.text}</p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function QuestionsView({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const questions = data?.kit?.questions ?? [];
  const cats = ["technical", "behavioural", "system-design", "company-fit"] as const;
  return (
    <div className="space-y-4">
      <KitNav kitId={kitId} />
      <h1 className="text-xl font-semibold">Questions</h1>
      <div className="grid gap-4 md:grid-cols-2">
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
                <ul className="mt-2 space-y-2">
                  {list.map((q) => (
                    <li key={q.id} className="rounded border p-2 text-sm">
                      <p className="font-medium">{q.prompt}</p>
                      <p className="mt-1 flex items-center gap-1 text-xs text-neutral-500">
                        Difficulty {q.difficulty} · covers {(q.requirement_ids ?? []).join(", ") || "—"} <OriginBadge meta={q._meta} />
                      </p>
                      <p className="mt-1 text-sm">{q.answer_outline}</p>
                    </li>
                  ))}
                </ul>
              )}
            </details>
          );
        })}
      </div>
    </div>
  );
}

export function FlashcardsView({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const cards = data?.kit?.flashcards ?? [];
  return (
    <div className="space-y-4">
      <KitNav kitId={kitId} />
      <h1 className="text-xl font-semibold">Flashcards</h1>
      {cards.length === 0 ? (
        <EmptyState title="No Flashcards yet" body="Flashcards are generated from must Requirements and technical Questions. Add some by hand or regenerate." />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {cards.map((f) => (
            <li key={f.id} className="rounded border p-3 text-sm">
              <p className="font-medium">{f.front}</p>
              <p className="mt-1 text-neutral-600 dark:text-neutral-300">{f.back}</p>
              <p className="mt-1">
                <OriginBadge meta={f._meta} />
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function reviewDays(days: Array<{ day: number; question_ids: string[] }>): Set<number> {
  const seen = new Set<string>();
  const out = new Set<number>();
  for (const d of days) {
    if (d.question_ids.length > 0 && d.question_ids.every((q) => seen.has(q))) out.add(d.day);
    for (const q of d.question_ids) seen.add(q);
  }
  return out;
}

export function ScheduleView({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const days = data?.kit?.schedule?.days ?? [];
  const review = reviewDays(days);
  const avg = days.length === 0 ? 0 : days.reduce((a, d) => a + d.minutes, 0) / days.length;
  const stale = Boolean(data?.schedule_stale);
  return (
    <div className="space-y-4">
      <KitNav kitId={kitId} />
      <h1 className="text-xl font-semibold">Schedule</h1>
      {stale ? (
        <div role="alert" className="rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950">
          Questions or Requirements changed after this Schedule was built — it may be out of date.
        </div>
      ) : null}
      {avg > 180 ? (
        <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-sm dark:bg-red-950">
          Overload warning: about {Math.round(avg)} min/day average is above the 180 min guideline.
        </div>
      ) : null}
      {days.length === 0 ? (
        <EmptyState title="No Schedule" body="This Kit has no scheduled days yet." />
      ) : (
        <ol className="space-y-2">
          {days.map((d) => (
            <li key={d.day} className="rounded border p-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">Day {d.day}</span>
                {review.has(d.day) ? <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs dark:bg-blue-900">Review day</span> : null}
                <span className="ml-auto text-xs text-neutral-500">{d.minutes} min</span>
              </div>
              <p className="mt-1">{d.focus}</p>
              <p className="mt-1 text-xs text-neutral-500">Questions: {d.question_ids.join(", ") || "—"}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
