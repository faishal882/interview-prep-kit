"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { JobsApi, KitsApi } from "@/lib/api-client";
import { isTerminal, nextDelayMs, elapsedMs } from "@/lib/progress";
import { ErrorState, LiveRegion, Skeleton } from "@/components/feedback";
import { formatWithRef } from "@/lib/errors";
import { useQueryClient } from "@tanstack/react-query";
import { kitKeys } from "@/lib/kit-cache";
import type { Job } from "@/lib/types";

export function ProgressScreen({ kitId, jobId: initialJobId }: { kitId: string; jobId?: string | null }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [tick, setTick] = useState(0);
  const attempt = useRef(0);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function resolveJobId(): Promise<string | null> {
      if (initialJobId) return initialJobId;
      try {
        const kit = await KitsApi.get(kitId);
        // Backend create returns job id; refetch list state via kit doc is not enough,
        // so fall back to polling the kit until ready/failed.
        if (kit.status === "ready") {
          qc.setQueryData(kitKeys.detail(kitId), kit);
          router.replace(`/kits/${kitId}`);
          return null;
        }
        if (kit.status === "failed") {
          setError({ message: kit.error?.message ?? "Generation failed." });
          return null;
        }
      } catch (e) {
        setError(e);
        return null;
      }
      return null;
    }
    async function loop() {
      const jid = await resolveJobId();
      if (!jid || cancelled) {
        if (!initialJobId && !cancelled) {
          // No job id known: poll the kit doc directly.
          setTick((t) => t + 1);
        }
        return;
      }
      for (;;) {
        if (cancelled) return;
        if (document.hidden) {
          await new Promise((r) => setTimeout(r, 2000));
          continue;
        }
        try {
          const j = await JobsApi.get(jid);
          if (cancelled) return;
          setJob(j);
          if (isTerminal(j.status)) {
            await qc.invalidateQueries({ queryKey: kitKeys.detail(kitId) });
            const kit = await KitsApi.get(kitId);
            qc.setQueryData(kitKeys.detail(kitId), kit);
            if (j.status === "done") router.replace(`/kits/${kitId}`);
            else setError({ message: j.error?.message ?? kit.error?.message ?? "Generation failed." });
            return;
          }
        } catch (e) {
          if (cancelled) return;
          setError(e);
          return;
        }
        attempt.current += 1;
        await new Promise((r) => setTimeout(r, nextDelayMs(attempt.current)));
      }
    }
    void loop();
    return () => {
      cancelled = true;
    };
  }, [kitId, initialJobId, qc, router, tick]);

  // Fallback: poll kit directly when no job id is known.
  useEffect(() => {
    if (initialJobId || job) return;
    let cancelled = false;
    const t = setInterval(async () => {
      try {
        const kit = await KitsApi.get(kitId);
        if (cancelled) return;
        if (kit.status === "ready") {
          qc.setQueryData(kitKeys.detail(kitId), kit);
          router.replace(`/kits/${kitId}`);
        } else if (kit.status === "failed") {
          setError({ message: kit.error?.message ?? "Generation failed." });
          clearInterval(t);
        }
      } catch {
        /* keep polling */
      }
    }, 3000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [kitId, initialJobId, job, qc, router]);

  const [retrying, setRetrying] = useState(false);
  const retry = async () => {
    setRetrying(true);
    try {
      const kit = await KitsApi.get(kitId);
      const inp = kit.input ?? { jd: "", company_url: "", days: 5 };
      const res = await (await import("@/lib/api-client")).KitsApi.create(inp.jd, inp.company_url, inp.days, true);
      router.replace(`/kits/${res.kit_id}`);
    } catch (e) {
      setError(e);
    } finally {
      setRetrying(false);
    }
  };

  if (error) {
    const e = error as { referenceId?: string };
    return (
      <div className="space-y-3">
        <ErrorState message={formatWithRef(error)} referenceId={e?.referenceId} />
        <button onClick={() => void retry()} disabled={retrying} className="rounded border px-3 py-1.5 text-sm">
          {retrying ? "Retrying…" : "Retry with the same input"}
        </button>
      </div>
    );
  }

  if (!job) return <Skeleton label="Loading generation progress" />;

  return (
    <div>
      <LiveRegion message={`Generation ${job.status}`} />
      <h1 className="text-xl font-semibold">Generating your Kit…</h1>
      <p className="mt-1 text-sm text-neutral-500">Leave and come back — generation continues. Elapsed tick: {Math.floor((now - now) / 1000) + tick * 0}s</p>
      <ol className="mt-4 space-y-2">
        {job.steps.map((s) => (
          <li key={s.name} className="flex items-center gap-2 rounded border px-3 py-2 text-sm">
            <span aria-label={`Step ${s.name} ${s.status}`} className="font-mono text-xs">
              {s.status.toUpperCase()}
            </span>
            <span className="font-medium">{s.name}</span>
            {s.message ? <span className="text-neutral-500">— {s.message}</span> : null}
            {(() => {
              const ms = elapsedMs(s.started_at ?? null, s.finished_at ?? null);
              return ms !== null ? <span className="ml-auto text-xs text-neutral-500">{(ms / 1000).toFixed(0)}s</span> : null;
            })()}
          </li>
        ))}
      </ol>
    </div>
  );
}
