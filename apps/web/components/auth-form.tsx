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

function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { login, register } = useAuth();
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
      if (mode === "login") await login(v.email, v.password);
      else await register(v.email, v.password);
      router.push(returnTo);
    } catch (e) {
      const err = e as ApiError;
      setServerError(`${err.message ?? "Failed."}${err.referenceId ? ` (ref ${err.referenceId})` : ""}`);
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-xl font-semibold">{mode === "login" ? "Log in" : "Register"}</h1>
      {expired ? (
        <p role="alert" className="mt-2 rounded border border-amber-300 bg-amber-50 p-2 text-sm">
          Your login session expired. Sign in again.
        </p>
      ) : null}
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-4 space-y-3">
        <div>
          <label htmlFor="email" className="text-sm font-medium">
            Email
          </label>
          <input id="email" type="email" autoComplete="email" {...field("email")} className="mt-1 w-full rounded border px-2 py-1.5" />
          {errors.email ? (
            <p role="alert" className="mt-1 text-sm text-red-700">
              {errors.email.message}
            </p>
          ) : null}
        </div>
        <div>
          <label htmlFor="password" className="text-sm font-medium">
            Password
          </label>
          <input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} {...field("password")} className="mt-1 w-full rounded border px-2 py-1.5" />
          {errors.password ? (
            <p role="alert" className="mt-1 text-sm text-red-700">
              {errors.password.message}
            </p>
          ) : null}
        </div>
        {serverError ? (
          <p role="alert" className="mt-1 text-sm text-red-700">
            {serverError}
          </p>
        ) : null}
        <button type="submit" disabled={isSubmitting} className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-black">
          {mode === "login" ? "Log in" : "Create account"}
        </button>
      </form>
    </div>
  );
}

export function LoginForm() {
  return <AuthForm mode="login" />;
}

export function RegisterForm() {
  return <AuthForm mode="register" />;
}
