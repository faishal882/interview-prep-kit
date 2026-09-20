"use client";
import { useState } from "react";
import { CreateKitForm } from "@/components/create-kit-form";
import { BatchUpload } from "@/components/batch-upload";

export default function NewKitPage() {
  const [tab, setTab] = useState<"single" | "batch">("single");
  return (
    <div>
      <h1 className="text-xl font-semibold">New Kit</h1>
      <div role="tablist" aria-label="Create mode" className="mt-3 flex gap-2">
        <button role="tab" aria-selected={tab === "single"} onClick={() => setTab("single")} className="rounded border px-3 py-1.5 text-sm">
          Single
        </button>
        <button role="tab" aria-selected={tab === "batch"} onClick={() => setTab("batch")} className="rounded border px-3 py-1.5 text-sm">
          Batch
        </button>
      </div>
      <div className="mt-4">{tab === "single" ? <CreateKitForm /> : <BatchUpload />}</div>
    </div>
  );
}
