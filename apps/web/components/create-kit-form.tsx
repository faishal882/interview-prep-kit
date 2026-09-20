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
      <form onSubmit={handleSubmit((v) => void submit(v))} noValidate style={{ display: "grid", gap: 16 }}>
        <div>
          <label htmlFor="jd" className="field-label">
            Job description
          </label>
          <textarea id="jd" rows={8} {...field("jd")} className="inset-textarea" />
          {errors.jd ? (
            <p role="alert" className="field-error">
              {errors.jd.message}
            </p>
          ) : null}
        </div>
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
          <div>
            <label htmlFor="company_url" className="field-label">
              Company website
            </label>
            <input id="company_url" inputMode="url" placeholder="https://example.com" {...field("company_url")} className="inset-input" />
            {errors.company_url ? (
              <p role="alert" className="field-error">
                {errors.company_url.message}
              </p>
            ) : null}
          </div>
          <div>
            <label htmlFor="days" className="field-label">
              Days
            </label>
            <input id="days" type="number" min={1} max={60} {...field("days")} className="inset-input" style={{ maxWidth: 160 }} />
            {errors.days ? (
              <p role="alert" className="field-error">
                {errors.days.message}
              </p>
            ) : null}
          </div>
        </div>
        {serverError ? (
          <p role="alert" className="field-error">
            {serverError}
          </p>
        ) : null}
        <div>
          <button type="submit" disabled={isSubmitting} className="button">
            Create Kit
          </button>
        </div>
      </form>
      {duplicate ? (
        <div role="alert" className="banner banner-warn" style={{ marginTop: 20 }}>
          <p>You already have this Kit.</p>
          <div style={{ marginTop: 12, display: "flex", gap: 12 }}>
            <button onClick={() => router.push(`/kits/${duplicate.kit_id}`)} className="button button-small">
              Open existing
            </button>
            <button
              onClick={() => pending && void submit(pending, true)}
              className="button button-secondary button-small"
            >
              Create anyway
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
