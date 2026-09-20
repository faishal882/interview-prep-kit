"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { SectionsApi } from "@/lib/api-client";
import { kitKeys, useKit } from "@/lib/kit-cache";
import { planRegeneration } from "@/lib/regen-controller";
import { ConfirmDialog, LiveRegion } from "@/components/feedback";
import { formatWithRef } from "@/lib/errors";
import { OriginBadge } from "@/components/badges";
import type { Category } from "@/lib/types";

// Regenerate a Section: confirmation with replaced/protected counts, dimming
// of replaceable items while running, new-item badges after completion.
export function RegenCategoryButton({ kitId, category }: { kitId: string; category: Category }) {
  const qc = useQueryClient();
  const { data } = useKit(kitId);
  const [open, setOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [live, setLive] = useState("");
  const [error, setError] = useState("");
  const [freshIds, setFreshIds] = useState<string[]>([]);
  const questions = data?.kit?.questions ?? [];
  const plan = planRegeneration("questions", questions, category);

  const run = async () => {
    setOpen(false);
    setRunning(true);
    setError("");
    const before = new Set(questions.map((q) => q.id));
    try {
      await SectionsApi.regenerate(kitId, `questions:${category}`);
      await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
      const fresh = (qc.getQueryData(kitKeys.detail(kitId)) as { kit?: { questions?: Array<{ id: string }> } } | undefined)
        ?.kit?.questions?.filter((q) => !before.has(q.id)).map((q) => q.id) ?? [];
      setFreshIds(fresh);
      setLive(`Regenerated ${category}. ${fresh.length} new Questions.`);
    } catch (e) {
      setError(formatWithRef(e));
      setLive("Regeneration failed. Your Kit is unchanged.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <span>
      <LiveRegion message={live} />
      <button onClick={() => setOpen(true)} disabled={running} className="button button-secondary button-small no-print" aria-label={`Regenerate ${category}`}>
        {running ? "Regenerating…" : `Regenerate ${category}`}
      </button>
      {freshIds.length > 0 ? <span className="pill pill-teal" style={{ marginLeft: 8 }}>{freshIds.length} new</span> : null}
      {error ? (
        <span role="alert" className="field-error" style={{ marginLeft: 8 }}>
          {error}
        </span>
      ) : null}
      <ConfirmDialog
        open={open}
        title={`Regenerate ${category}?`}
        body={`${plan.summary}. Protected items stay editable during the run; edits made mid-run survive.`}
        confirmLabel="Regenerate"
        onConfirm={() => void run()}
        onCancel={() => setOpen(false)}
      />
      {running ? (
        <span aria-label="Regeneration in progress" className="pill" style={{ marginLeft: 8 }}>
          Replacing {plan.replacedCount}…
        </span>
      ) : null}
    </span>
  );
}

export function NewBadge({ ids, id }: { ids: string[]; id: string }) {
  if (!ids.includes(id)) return null;
  return (
    <span aria-label="New after regeneration" className="pill pill-teal">
      New
    </span>
  );
}

export function RegenScheduleButton({ kitId }: { kitId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [live, setLive] = useState("");
  const run = async () => {
    setOpen(false);
    await SectionsApi.regenerate(kitId, "schedule");
    await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    setLive("Schedule rebuilt. Manual edits were replaced; the stale flag is cleared.");
  };
  return (
    <span>
      <LiveRegion message={live} />
      <button onClick={() => setOpen(true)} className="button button-secondary button-small no-print">
        Rebuild Schedule
      </button>
      <ConfirmDialog
        open={open}
        title="Rebuild the Schedule?"
        body="This replaces the whole Schedule, including your manual focus edits and moved Questions. Questions and Requirements are untouched."
        confirmLabel="Rebuild"
        onConfirm={() => void run()}
        onCancel={() => setOpen(false)}
      />
    </span>
  );
}

export function BriefRegen({ kitId }: { kitId: string }) {
  const qc = useQueryClient();
  const { data } = useKit(kitId);
  const [live, setLive] = useState("");
  const proposal = data?.proposals?.brief;
  const run = async () => {
    const res = await SectionsApi.regenerate(kitId, "brief");
    await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    setLive(res.proposal ? "A Proposal is ready below. Your current text is unchanged." : "Brief refreshed.");
  };
  const accept = async () => {
    await SectionsApi.acceptBrief(kitId);
    await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    setLive("Proposal accepted.");
  };
  const reject = async () => {
    await SectionsApi.rejectBrief(kitId);
    await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    setLive("Proposal rejected. Your text is unchanged.");
  };
  return (
    <div className="no-print">
      <LiveRegion message={live} />
      <button onClick={() => void run()} className="button button-secondary button-small">
        Regenerate brief
      </button>
      {proposal ? (
        <div role="group" aria-label="Brief Proposal" className="neu-card-flat" style={{ marginTop: 12 }}>
          <span className="eyebrow">Proposal</span>
          <h3 className="kit-display" style={{ fontSize: 16, marginTop: 8 }}>Proposed brief</h3>
          <p style={{ marginTop: 8 }}>{proposal.summary}</p>
          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            <button onClick={() => void accept()} className="button button-small">
              Accept
            </button>
            <button onClick={() => void reject()} className="button button-secondary button-small">
              Reject
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function GenerateForGapButton({ kitId, requirementId }: { kitId: string; requirementId: string }) {
  const qc = useQueryClient();
  const [live, setLive] = useState("");
  const run = async () => {
    await SectionsApi.generateForRequirement(kitId, requirementId);
    await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
    setLive(`Generated a Question for ${requirementId}. Nothing else changed.`);
  };
  return (
    <span>
      <LiveRegion message={live} />
      <button onClick={() => void run()} className="button button-secondary button-small">
        Generate a Question for this
      </button>
    </span>
  );
}

export function ProtectedNote({ origin, edited, pinned }: { origin?: string; edited?: boolean; pinned?: boolean }) {
  return <OriginBadge meta={{ origin: (origin as "generated" | "user") ?? "generated", edited: !!edited, pinned: !!pinned, rev: 1, order: "" }} />;
}
