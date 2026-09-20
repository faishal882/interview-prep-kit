import { KitList } from "@/components/kit-list";
import Link from "next/link";

export default function KitsPage() {
  return (
    <div>
      <div className="mb-4 flex items-center">
        <h1 className="text-xl font-semibold">Kits</h1>
        <Link href="/kits/new" className="ml-auto rounded border px-3 py-1.5 text-sm underline">
          New Kit
        </Link>
      </div>
      <KitList />
    </div>
  );
}
