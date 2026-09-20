"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { OverviewView } from "@/components/kit-views";
import { EditableBrief } from "@/components/editable-views";

const VIEWS = [
  { slug: "", label: "Overview" },
  { slug: "role", label: "Role" },
  { slug: "questions", label: "Questions" },
  { slug: "flashcards", label: "Flashcards" },
  { slug: "schedule", label: "Schedule" },
  { slug: "practice", label: "Practice" },
  { slug: "print", label: "Print" },
];

export function KitNav({ kitId }: { kitId: string }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Kit views" className="tabs">
      {VIEWS.map((v) => {
        const href = v.slug ? `/kits/${kitId}/${v.slug}` : `/kits/${kitId}`;
        return (
          <Link key={v.slug} href={href} aria-current={pathname === href ? "page" : undefined}>
            {v.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function KitOverview({ kitId }: { kitId: string }) {
  return (
    <div className="section">
      <OverviewView kitId={kitId} />
      <div style={{ marginTop: 24 }}>
        <EditableBrief kitId={kitId} />
      </div>
    </div>
  );
}
