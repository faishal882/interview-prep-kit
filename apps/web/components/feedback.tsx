"use client";
import { useState } from "react";

export function EmptyState({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="inset-well" role="status" style={{ textAlign: "center", padding: "48px 32px" }}>
      <h2 className="kit-display" style={{ fontSize: 20 }}>{title}</h2>
      <p style={{ marginTop: 8, color: "var(--copy)", fontSize: 15 }}>{body}</p>
      {action ? <div style={{ marginTop: 20 }}>{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, referenceId, onRetry }: { message: string; referenceId?: string; onRetry?: () => void }) {
  return (
    <div className="banner banner-error" role="alert">
      <p>{message}</p>
      {referenceId ? <p style={{ marginTop: 4, fontSize: 13 }}>Reference id: {referenceId}</p> : null}
      {onRetry ? (
        <button onClick={onRetry} className="button button-secondary button-small" style={{ marginTop: 12 }}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Skeleton({ label = "Loading…" }: { label?: string }) {
  return (
    <div aria-label={label} role="status" style={{ display: "grid", gap: 12 }} className="animate-pulse">
      <div className="skeleton-bar" style={{ width: "66%" }} />
      <div className="skeleton-bar" style={{ width: "50%" }} />
      <div className="skeleton-bar" style={{ width: "33%" }} />
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div role="alertdialog" aria-modal="true" aria-label={title} className="dialog-backdrop">
      <div className="dialog-panel">
        <span className="eyebrow">Confirm</span>
        <h2 className="kit-display" style={{ fontSize: 22, marginTop: 12 }}>{title}</h2>
        <p style={{ marginTop: 8, color: "var(--copy)", fontSize: 15 }}>{body}</p>
        <div style={{ marginTop: 20, display: "flex", justifyContent: "flex-end", gap: 12 }}>
          <button onClick={onCancel} className="button button-secondary button-small">
            Cancel
          </button>
          <button onClick={onConfirm} autoFocus className="button button-small">
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function LiveRegion({ message }: { message: string }) {
  return (
    <div aria-live="polite" role="status" className="sr-only">
      {message}
    </div>
  );
}

export function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  return (
    <div role="status" className="toast">
      {message}{" "}
      <button onClick={onClose} aria-label="Dismiss" style={{ marginLeft: 8, textDecoration: "underline" }}>
        Dismiss
      </button>
    </div>
  );
}

export function useToast(): { message: string; show: (m: string) => void; clear: () => void } {
  const [message, setMessage] = useState("");
  return { message, show: setMessage, clear: () => setMessage("") };
}
