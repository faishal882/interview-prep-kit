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
      <button onClick={() => setOpen(true)} disabled={running} className="rounded border px-2 py-1 text-xs no-print" aria-label={`Regenerate ${category}`}>
        {running ? "Regenerating…" : `Regenerate ${category}`}
      </button>
      {freshIds.length > 0 ? <span className="ml-1 text-xs text-green-700">{freshIds.length} new</span> : null}
      {error ? (
        <span role="alert" className="ml-1 text-xs text-red-700">
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
        <span aria-label="Regeneration in progress" className="ml-2 text-xs text-neutral-500">
          Replacing {plan.replacedCount}…
        </span>
      ) : null}
    </span>
  );
}

export function NewBadge({ ids, id }: { ids: string[]; id: string }) {
  if (!ids.includes(id)) return null;
  return (
    <span aria-label="New after regeneration" className="rounded bg-green-100 px-1.5 py-0.5 text-xs dark:bg-green-900">
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
      <button onClick={() => setOpen(true)} className="rounded border px-2 py-1 text-xs no-print">
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
      <button onClick={() => void run()} className="rounded border px-2 py-1 text-xs">
        Regenerate brief
      </button>
      {proposal ? (
        <div role="group" aria-label="Brief Proposal" className="mt-2 rounded border p-3 text-sm">
          <h3 className="font-medium">Proposed brief</h3>
          <p className="mt-1">{proposal.summary}</p>
          <div className="mt-2 flex gap-2">
            <button onClick={() => void accept()} className="rounded border px-2 py-1 text-xs">
              Accept
            </button>
            <button onClick={() => void reject()} className="rounded border px-2 py-1 text-xs">
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
      <button onClick={() => void run()} className="rounded border px-2 py-0.5 text-xs">
        Generate a Question for this
      </button>
    </span>
  );
}

export function ProtectedNote({ origin, edited, pinned }: { origin?: string; edited?: boolean; pinned?: boolean }) {
  return <OriginBadge meta={{ origin: (origin as "generated" | "user") ?? "generated", edited: !!edited, pinned: !!pinned, rev: 1, order: "" }} />;
}
