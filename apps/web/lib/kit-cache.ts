"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { KitsApi, JobsApi } from "./api-client";
import type { Job, KitDoc, KitSummary } from "./types";

export const kitKeys = {
  list: ["kits"] as const,
  detail: (id: string) => ["kits", id] as const,
  job: (id: string) => ["jobs", id] as const,
};

export function useKitsList() {
  return useQuery({
    queryKey: kitKeys.list,
    queryFn: async (): Promise<KitSummary[]> => {
      const res = await KitsApi.list();
      return res.kits;
    },
  });
}

export function useKit(id: string, enabled = true) {
  return useQuery({
    queryKey: kitKeys.detail(id),
    queryFn: async (): Promise<KitDoc> => KitsApi.get(id),
    enabled,
    refetchOnWindowFocus: false,
  });
}

export function useJob(jobId: string | null, enabled = true) {
  return useQuery({
    queryKey: kitKeys.job(jobId ?? "none"),
    queryFn: async (): Promise<Job> => JobsApi.get(jobId!),
    enabled: enabled && !!jobId,
    refetchInterval: false,
  });
}

export function useInvalidateKit() {
  const qc = useQueryClient();
  return (id: string) => {
    qc.invalidateQueries({ queryKey: kitKeys.detail(id) });
    qc.invalidateQueries({ queryKey: kitKeys.list });
  };
}

export function kitFromCache(qc: { getQueryData: (k: unknown) => unknown }, id: string): KitDoc | undefined {
  return qc.getQueryData(kitKeys.detail(id)) as KitDoc | undefined;
}
