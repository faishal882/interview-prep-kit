"use client";
import Link from "next/link";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div role="alert" className="rounded border border-red-300 p-6">
      <h1 className="text-xl font-semibold">Something broke on this page</h1>
      <p className="mt-2 text-sm">{error.message || "Unexpected error."}</p>
      <div className="mt-4 flex gap-2">
        <button onClick={() => reset()} className="rounded border px-3 py-1.5 text-sm">
          Try again
        </button>
        <Link href="/kits" className="rounded border px-3 py-1.5 text-sm underline">
          Back to Kits
        </Link>
      </div>
    </div>
  );
}
