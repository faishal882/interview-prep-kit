"use client";
import { useState } from "react";

export function EmptyState({ title, body, action }: { title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="rounded border border-dashed p-8 text-center" role="status">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-300">{body}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, referenceId, onRetry }: { message: string; referenceId?: string; onRetry?: () => void }) {
  return (
    <div className="rounded border border-red-300 bg-red-50 p-4 dark:bg-red-950" role="alert">
      <p className="text-sm text-red-800 dark:text-red-200">{message}</p>
      {referenceId ? <p className="mt-1 text-xs text-red-600 dark:text-red-300">Reference id: {referenceId}</p> : null}
      {onRetry ? (
        <button onClick={onRetry} className="mt-2 rounded border px-3 py-1 text-sm">
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Skeleton({ label = "Loading…" }: { label?: string }) {
  return (
    <div aria-label={label} role="status" className="animate-pulse space-y-2">
      <div className="h-4 w-2/3 rounded bg-neutral-200 dark:bg-neutral-800" />
      <div className="h-4 w-1/2 rounded bg-neutral-200 dark:bg-neutral-800" />
      <div className="h-4 w-1/3 rounded bg-neutral-200 dark:bg-neutral-800" />
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
    <div role="alertdialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded bg-white p-6 dark:bg-neutral-900">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm">{body}</p>
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onCancel} className="rounded border px-3 py-1.5 text-sm">
            Cancel
          </button>
          <button onClick={onConfirm} autoFocus className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white dark:bg-white dark:text-black">
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
    <div role="status" className="fixed bottom-4 right-4 z-50 rounded bg-neutral-900 px-4 py-2 text-sm text-white dark:bg-white dark:text-black">
      {message}{" "}
      <button onClick={onClose} aria-label="Dismiss" className="ml-2 underline">
        Dismiss
      </button>
    </div>
  );
}

export function useToast(): { message: string; show: (m: string) => void; clear: () => void } {
  const [message, setMessage] = useState("");
  return { message, show: setMessage, clear: () => setMessage("") };
}
