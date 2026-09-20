"use client";
import { useState } from "react";
import { CreateKitForm } from "@/components/create-kit-form";
import { BatchUpload } from "@/components/batch-upload";

export default function NewKitPage() {
  const [tab, setTab] = useState<"single" | "batch">("single");
  return (
    <div className="section">
      <div className="section-head" style={{ marginBottom: 20 }}>
        <span className="eyebrow">Create</span>
        <h2>New Kit</h2>
      </div>
      <div role="tablist" aria-label="Create mode" className="tabs">
        <button role="tab" aria-selected={tab === "single"} onClick={() => setTab("single")}>
          Single
        </button>
        <button role="tab" aria-selected={tab === "batch"} onClick={() => setTab("batch")}>
          Batch
        </button>
      </div>
      <div style={{ marginTop: 24 }}>{tab === "single" ? <CreateKitForm /> : <BatchUpload />}</div>
    </div>
  );
}
