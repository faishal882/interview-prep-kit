"use client";
import { useState } from "react";
import Link from "next/link";
import { KitsApi } from "@/lib/api-client";
import { LiveRegion } from "@/components/feedback";

type Entry = { id?: string; jd: string; company_url?: string; days: number };

type Status = "idle" | "uploading" | "report" | "error";

export function parseBatchFile(text: string): { entries?: Entry[]; error?: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { error: "Invalid JSON: the file must be a JSON array of Cases." };
  }
  if (!Array.isArray(parsed)) return { error: "Invalid shape: expected a JSON array." };
  if (parsed.length > 10) return { error: "Too many entries: at most 10 per upload." };
  return { entries: parsed as Entry[] };
}

export function BatchUpload() {
  const [status, setStatus] = useState<Status>("idle");
  const [preview, setPreview] = useState<Entry[] | null>(null);
  const [message, setMessage] = useState("");
  const [report, setReport] = useState<{ accepted: Array<{ id: string; kit_id: string }>; rejected: Array<{ id: string; reason: string }> } | null>(null);

  const onFile = async (f: File | undefined) => {
    if (!f) return;
    setReport(null);
    const text = await f.text();
    const { entries, error } = parseBatchFile(text);
    if (error) {
      setStatus("error");
      setMessage(error);
      setPreview(null);
      return;
    }
    setStatus("idle");
    setMessage("");
    setPreview(entries!);
  };

  const submit = async () => {
    if (!preview) return;
    setStatus("uploading");
    setMessage("Uploading…");
    try {
      const res = await KitsApi.batch(preview.map((e, i) => ({ id: e.id ?? `entry-${i}`, jd: e.jd, company_url: e.company_url ?? "", days: e.days })));
      setReport(res);
      setStatus("report");
      setMessage(`Accepted ${res.accepted.length}, rejected ${res.rejected.length}.`);
    } catch (e) {
      setStatus("error");
      setMessage(e instanceof Error ? e.message : "Upload failed.");
    }
  };

  return (
    <div>
      <LiveRegion message={`Batch upload: ${status}. ${message}`} />
      <label htmlFor="batch-file" className="field-label">
        JSON file (up to 10 Cases: id, jd, company_url, days)
      </label>
      <input
        id="batch-file"
        type="file"
        accept="application/json,.json"
        onChange={(e) => void onFile(e.target.files?.[0])}
        className="inset-input"
      />
      {preview ? (
        <p style={{ marginTop: 12 }} role="status">
          <span className="pill">{preview.length} {preview.length === 1 ? "entry" : "entries"} ready</span>
        </p>
      ) : null}
      {status === "error" ? (
        <p role="alert" className="field-error">
          {message}
        </p>
      ) : null}
      <div style={{ marginTop: 16 }}>
        <button
          onClick={() => void submit()}
          disabled={!preview || status === "uploading"}
          className="button"
        >
          {status === "uploading" ? "Uploading…" : "Submit batch"}
        </button>
      </div>
      {status === "report" && report ? (
        <div className="neu-card-flat" style={{ marginTop: 20 }} role="status">
          <span className="eyebrow">Report</span>
          <section aria-label="Accepted" style={{ marginTop: 12 }}>
            <h3 className="kit-display" style={{ fontSize: 16 }}>Accepted ({report.accepted.length})</h3>
            <ul className="ruled-list" style={{ marginTop: 8 }}>
              {report.accepted.map((a) => (
                <li key={a.id} style={{ padding: "10px 4px" }}>
                  {a.id} →{" "}
                  <Link href={`/kits/${a.kit_id}`} style={{ color: "var(--primary)", fontWeight: 600 }}>
                    Open Kit
                  </Link>
                </li>
              ))}
            </ul>
          </section>
          <section aria-label="Rejected" style={{ marginTop: 12 }}>
            <h3 className="kit-display" style={{ fontSize: 16 }}>Rejected ({report.rejected.length})</h3>
            <ul className="ruled-list" style={{ marginTop: 8 }}>
              {report.rejected.map((r) => (
                <li key={r.id} style={{ padding: "10px 4px" }}>
                  {r.id}: {r.reason}
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}
    </div>
  );
}
