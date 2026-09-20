"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { KitsApi } from "@/lib/api-client";
import { ApiError } from "@/lib/errors";

const schema = z.object({
  jd: z.string().min(20, "Paste at least a few lines of the job description."),
  company_url: z.string().refine((v) => v === "" || /^https?:\/\/.+\..+/.test(v), "Enter a valid http(s) URL or leave blank."),
  days: z.coerce.number().int().min(1, "At least 1 day.").max(60, "At most 60 days."),
});

type Fields = z.infer<typeof schema>;

export function CreateKitForm() {
  const router = useRouter();
  const [duplicate, setDuplicate] = useState<{ kit_id: string } | null>(null);
  const [serverError, setServerError] = useState("");
  const [pending, setPending] = useState<Fields | null>(null);
  const {
    register: field,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Fields>({ resolver: zodResolver(schema), defaultValues: { jd: "", company_url: "", days: 5 } });

  const submit = async (v: Fields, force = false) => {
    setServerError("");
    setDuplicate(null);
    try {
      const res = await KitsApi.create(v.jd, v.company_url, v.days, force);
      if (res.duplicate) {
        setDuplicate({ kit_id: res.kit_id });
        setPending(v);
        return;
      }
      router.push(`/kits/${res.kit_id}`);
    } catch (e) {
      const err = e as ApiError;
      setServerError(`${err.message}${err.referenceId ? ` (ref ${err.referenceId})` : ""}`);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit((v) => void submit(v))} noValidate className="space-y-3">
        <div>
          <label htmlFor="jd" className="text-sm font-medium">
            Job description
          </label>
          <textarea id="jd" rows={8} {...field("jd")} className="mt-1 w-full rounded border px-2 py-1.5" />
          {errors.jd ? (
            <p role="alert" className="text-sm text-red-700">
              {errors.jd.message}
            </p>
          ) : null}
        </div>
        <div>
          <label htmlFor="company_url" className="text-sm font-medium">
            Company website
          </label>
          <input id="company_url" inputMode="url" placeholder="https://example.com" {...field("company_url")} className="mt-1 w-full rounded border px-2 py-1.5" />
          {errors.company_url ? (
            <p role="alert" className="text-sm text-red-700">
              {errors.company_url.message}
            </p>
          ) : null}
        </div>
        <div>
          <label htmlFor="days" className="text-sm font-medium">
            Days
          </label>
          <input id="days" type="number" min={1} max={60} {...field("days")} className="mt-1 w-32 rounded border px-2 py-1.5" />
          {errors.days ? (
            <p role="alert" className="text-sm text-red-700">
              {errors.days.message}
            </p>
          ) : null}
        </div>
        {serverError ? (
          <p role="alert" className="text-sm text-red-700">
            {serverError}
          </p>
        ) : null}
        <button type="submit" disabled={isSubmitting} className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-black">
          Create Kit
        </button>
      </form>
      {duplicate ? (
        <div role="alert" className="mt-4 rounded border border-amber-300 bg-amber-50 p-4 dark:bg-amber-950">
          <p className="text-sm">You already have this Kit.</p>
          <div className="mt-2 flex gap-2">
            <button onClick={() => router.push(`/kits/${duplicate.kit_id}`)} className="rounded border px-3 py-1.5 text-sm underline">
              Open existing
            </button>
            <button
              onClick={() => pending && void submit(pending, true)}
              className="rounded border px-3 py-1.5 text-sm"
            >
              Create anyway
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
