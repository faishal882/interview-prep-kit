import { redirect } from "next/navigation";

// Registration is closed: this app is login-only. Old links land on login.
export default function RegisterPage() {
  redirect("/login");
}
