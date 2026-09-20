"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/errors";

const schema = z.object({
  email: z.string().email("Enter a valid email."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

type Fields = z.infer<typeof schema>;

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const expired = params.get("expired") === "1";
  const returnTo = params.get("returnTo") || "/kits";
  const [serverError, setServerError] = useState("");
  const {
    register: field,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Fields>({ resolver: zodResolver(schema) });

  const onSubmit = async (v: Fields) => {
    setServerError("");
    try {
      await login(v.email, v.password);
      router.push(returnTo);
    } catch (e) {
      const err = e as ApiError;
      setServerError(`${err.message ?? "Failed."}${err.referenceId ? ` (ref ${err.referenceId})` : ""}`);
    }
  };

  return (
    <div className="hero-panel">
      <div className="hero-copy" style={{ padding: "48px 40px" }}>
        <span className="eyebrow">Welcome back</span>
        <h1 style={{ fontSize: "clamp(32px, 3vw, 44px)" }}>Log in</h1>
        {expired ? (
          <p role="alert" className="banner banner-warn" style={{ marginTop: 16 }}>
            Your login session expired. Sign in again.
          </p>
        ) : null}
        <form onSubmit={handleSubmit(onSubmit)} noValidate style={{ marginTop: 24, display: "grid", gap: 16, width: "100%", maxWidth: 440 }}>
          <div>
            <label htmlFor="email" className="field-label">
              Email
            </label>
            <input id="email" type="email" autoComplete="email" {...field("email")} className="inset-input" />
            {errors.email ? (
              <p role="alert" className="field-error">
                {errors.email.message}
              </p>
            ) : null}
          </div>
          <div>
            <label htmlFor="password" className="field-label">
              Password
            </label>
            <input id="password" type="password" autoComplete="current-password" {...field("password")} className="inset-input" />
            {errors.password ? (
              <p role="alert" className="field-error">
                {errors.password.message}
              </p>
            ) : null}
          </div>
          {serverError ? (
            <p role="alert" className="field-error">
              {serverError}
            </p>
          ) : null}
          <button type="submit" disabled={isSubmitting} className="button">
            Log in
          </button>
        </form>
      </div>
    </div>
  );
}
