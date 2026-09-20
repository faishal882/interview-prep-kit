"use client";
import { KitsApi } from "@/lib/api-client";
import { useState } from "react";

export function ExportButton({ kitId }: { kitId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const download = async () => {
    setBusy(true);
    setError("");
    try {
      const data = await KitsApi.exportJson(kitId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `kit-${kitId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <span>
      <button onClick={() => void download()} disabled={busy} className="rounded border px-2 py-1 text-sm">
        {busy ? "Exporting…" : "Download JSON"}
      </button>
      {error ? (
        <span role="alert" className="ml-2 text-sm text-red-700">
          {error}
        </span>
      ) : null}
    </span>
  );
}
