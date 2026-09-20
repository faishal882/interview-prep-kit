import Link from "next/link";

export default function Home() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Interview Prep Kit</h1>
      <p className="mt-2 text-sm">
        Turn a job description and a company website into a personalised, editable interview preparation Kit.
      </p>
      <div className="mt-4 flex gap-3">
        <Link href="/kits" className="rounded border px-3 py-1.5 text-sm underline">
          Go to Kits
        </Link>
        <Link href="/login" className="rounded border px-3 py-1.5 text-sm underline">
          Log in
        </Link>
      </div>
    </div>
  );
}
