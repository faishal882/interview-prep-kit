import Link from "next/link";

export default function Home() {
  return (
    <div>
      <div className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">Interview preparation, operating system</span>
          <h1>
            Turn a job description into an <span>interview-ready Kit</span>
          </h1>
          <p className="lede">
            Paste the role, add the company website, pick your days. Watch generation step by step, reshape every
            Question, drill Flashcards, and see exactly where you are weakest.
          </p>
          <div className="hero-actions">
            <Link href="/kits/new" className="button">
              Create a Kit
            </Link>
            <Link href="/kits" className="button button-secondary">
              Go to Kits
            </Link>
          </div>
        </div>
      </div>
      <div className="section">
        <div className="section-head">
          <span className="eyebrow">How it operates</span>
          <h2>Generate, reshape, practise</h2>
          <p>Each stage is inspectable: progress is visible, edits survive regeneration, practice ranks your weak spots.</p>
        </div>
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
          <article className="neu-card">
            <div className="proof-icon" aria-hidden="true">
              1
            </div>
            <h3 className="kit-display" style={{ fontSize: 17, marginTop: 16 }}>
              Generate with evidence
            </h3>
            <p style={{ color: "var(--copy)", fontSize: 14, marginTop: 8 }}>
              Requirements, Questions, Flashcards and a day-by-day Schedule — with the research log to show what was found.
            </p>
          </article>
          <article className="neu-card">
            <div className="proof-icon" aria-hidden="true">
              2
            </div>
            <h3 className="kit-display" style={{ fontSize: 17, marginTop: 16 }}>
              Reshape without loss
            </h3>
            <p style={{ color: "var(--copy)", fontSize: 14, marginTop: 8 }}>
              Edit, reorder, pin and regenerate by Section. Your work is protected and never silently discarded.
            </p>
          </article>
          <article className="neu-card">
            <div className="proof-icon" aria-hidden="true">
              3
            </div>
            <h3 className="kit-display" style={{ fontSize: 17, marginTop: 16 }}>
              Practise deliberately
            </h3>
            <p style={{ color: "var(--copy)", fontSize: 14, marginTop: 8 }}>
              Drills ordered by least confidence, coverage per Requirement, and a ranked weak-spots report.
            </p>
          </article>
        </div>
      </div>
    </div>
  );
}
