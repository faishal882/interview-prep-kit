import { notFound } from "next/navigation";

export default function NotFound() {
  return (
    <div>
      <h1 className="text-xl font-semibold">Not found</h1>
      <p className="mt-2 text-sm">That page does not exist.</p>
      <a href="/kits" className="mt-4 inline-block underline">
        Back to Kits
      </a>
    </div>
  );
}

export function KitNotFound() {
  notFound();
}
