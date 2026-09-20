import { KitList } from "@/components/kit-list";
import Link from "next/link";

export default function KitsPage() {
  return (
    <div className="section">
      <div className="section-head" style={{ marginBottom: 20 }}>
        <span className="eyebrow">Your Kits</span>
        <div style={{ display: "flex", alignItems: "center", gap: 16, width: "100%", marginTop: 16 }}>
          <h2 style={{ marginTop: 0 }}>Kits</h2>
          <Link href="/kits/new" className="button button-small" style={{ marginLeft: "auto" }}>
            New Kit
          </Link>
        </div>
      </div>
      <KitList />
    </div>
  );
}
