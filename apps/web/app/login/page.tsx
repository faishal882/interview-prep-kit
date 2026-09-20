import { Suspense } from "react";
import { LoginForm } from "@/components/auth-form";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
