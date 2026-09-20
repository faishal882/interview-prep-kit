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
    <div>
      <KitNav kitId={kitId} />
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 20 }}>
        <span className="eyebrow">Overview</span>
        <span style={{ marginLeft: "auto" }}>
          <ExportButton kitId={kitId} />
        </span>
      </div>
      {warnings.length > 0 ? (
        <div role="alert" className="banner banner-warn" style={{ marginTop: 16 }}>
          Warnings: {warnings.join("; ")}
        </div>
      ) : null}
      {!hasHiring ? (
        <div role="status" className="inset-well" style={{ marginTop: 16 }}>
          We could not retrieve hiring information for this company. The brief below is honest about what was found — see the research log.
        </div>
      ) : null}
      <div style={{ display: "grid", gap: 16, marginTop: 20, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        <section aria-label="Company brief" className="neu-card">
          <h2 className="kit-display" style={{ fontSize: 17 }}>Company brief</h2>
          <p style={{ marginTop: 8, fontSize: 15 }}>{brief?.summary || "No summary."}</p>
          {brief?.what_they_do ? <p style={{ marginTop: 8, fontSize: 15 }}>What they do: {brief.what_they_do}</p> : null}
          {brief?.hiring_process ? <p style={{ marginTop: 8, fontSize: 15 }}>How they hire: {brief.hiring_process}</p> : null}
        </section>
        <section aria-label="Sources" className="neu-card">
          <h2 className="kit-display" style={{ fontSize: 17 }}>Sources</h2>
          {(brief?.sources ?? []).length === 0 ? (
            <p style={{ color: "var(--copy)", fontSize: 15, marginTop: 8 }}>No sources retrieved.</p>
          ) : (
            <ul style={{ paddingLeft: 20, fontSize: 15, marginTop: 8 }}>
              {(brief?.sources ?? []).map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          )}
        </section>
        <section aria-label="Coverage" className="neu-card">
          <h2 className="kit-display" style={{ fontSize: 17 }}>Coverage</h2>
          <p style={{ fontSize: 15, marginTop: 8 }}>
            {uncovered.length === 0 ? "All Requirements covered." : `${uncovered.length} Gap${uncovered.length === 1 ? "" : "s"}: ${uncovered.join(", ")}`}
          </p>
          <Link href={`/kits/${kitId}/role`} style={{ fontSize: 14, color: "var(--primary)", fontWeight: 600 }}>
            See Role view
          </Link>
        </section>
      </div>
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
    <div>
      <KitNav kitId={kitId} />
      <span className="eyebrow" style={{ marginTop: 20 }}>Role</span>
      {(role?.responsibilities ?? []).length > 0 ? (
        <section aria-label="Responsibilities" className="neu-card" style={{ marginTop: 16 }}>
          <h2 className="kit-display" style={{ fontSize: 17 }}>Responsibilities</h2>
          <ul style={{ paddingLeft: 20, fontSize: 15, marginTop: 8 }}>
            {role!.responsibilities!.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <div style={{ marginTop: 16 }}>
        {reqs.length === 0 ? (
          <EmptyState title="No Requirements" body="The generator found no interviewable claims in this job description." />
        ) : (
          <ul className="ruled-list">
            {reqs.map((r) => {
              const n = coverCount(r.id);
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
                  </div>
                  <p style={{ marginTop: 8 }}>{r.text}</p>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

export function QuestionsView({ kitId }: { kitId: string }) {
  const { data } = useKit(kitId);
  const questions = data?.kit?.questions ?? [];
  const cats = ["technical", "behavioural", "system-design", "company-fit"] as const;
  return (
    <div>
      <KitNav kitId={kitId} />
      <span className="eyebrow" style={{ marginTop: 20 }}>Questions</span>
      <div style={{ marginTop: 8 }}>
        {cats.map((c) => {
          const list = questions.filter((q) => q.category === c);
          return (
            <details key={c} open className="disclosure">
              <summary>
                {c} ({list.length})
                <span className="plus" aria-hidden="true">+</span>
              </summary>
              {list.length === 0 ? (
                <p style={{ marginTop: 12, color: "var(--copy)", fontSize: 15, paddingRight: 42 }}>No Questions in this Category — no Requirements routed here, so nothing was padded.</p>
              ) : (
                <ul className="ruled-list" style={{ marginTop: 8 }}>
                  {list.map((q) => (
                    <li key={q.id}>
                      <p style={{ fontWeight: 600 }}>{q.prompt}</p>
                      <p style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--copy)" }}>
                        Difficulty {q.difficulty} · covers {(q.requirement_ids ?? []).join(", ") || "—"} <OriginBadge meta={q._meta} />
                      </p>
                      <p style={{ marginTop: 6, fontSize: 15 }}>{q.answer_outline}</p>
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
    <div>
      <KitNav kitId={kitId} />
      <span className="eyebrow" style={{ marginTop: 20 }}>Flashcards</span>
      <div style={{ marginTop: 16 }}>
        {cards.length === 0 ? (
          <EmptyState title="No Flashcards yet" body="Flashcards are generated from must Requirements and technical Questions. Add some by hand or regenerate." />
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
            {cards.map((f) => (
              <li key={f.id} className="neu-card">
                <p style={{ fontWeight: 600 }}>{f.front}</p>
                <p style={{ marginTop: 8, color: "var(--copy)" }}>{f.back}</p>
                <p style={{ marginTop: 8 }}>
                  <OriginBadge meta={f._meta} />
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
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
    <div>
      <KitNav kitId={kitId} />
      <span className="eyebrow" style={{ marginTop: 20 }}>Schedule</span>
      {stale ? (
        <div role="alert" className="banner banner-warn" style={{ marginTop: 16 }}>
          Questions or Requirements changed after this Schedule was built — it may be out of date.
        </div>
      ) : null}
      {avg > 180 ? (
        <div role="alert" className="banner banner-error" style={{ marginTop: 16 }}>
          Overload warning: about {Math.round(avg)} min/day average is above the 180 min guideline.
        </div>
      ) : null}
      <div style={{ marginTop: 16 }}>
        {days.length === 0 ? (
          <EmptyState title="No Schedule" body="This Kit has no scheduled days yet." />
        ) : (
          <ol className="ruled-list" style={{ listStyle: "none" }}>
            {days.map((d) => (
              <li key={d.day}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="proof-icon" aria-hidden="true" style={{ width: 36, height: 36, flexBasis: 36, fontSize: 15 }}>
                    {d.day}
                  </span>
                  <span className="kit-display" style={{ fontWeight: 600 }}>Day {d.day}</span>
                  {review.has(d.day) ? <span className="pill">Review day</span> : null}
                  <span style={{ marginLeft: "auto", fontSize: 13, color: "var(--copy)" }}>{d.minutes} min</span>
                </div>
                <p style={{ marginTop: 8 }}>{d.focus}</p>
                <p style={{ marginTop: 4, fontSize: 13, color: "var(--copy)" }}>Questions: {d.question_ids.join(", ") || "—"}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
