// End-to-end journey against the real backend in scripted fake-LLM mode:
// register → create a Kit → watch progress → edit a Question → regenerate its
// Category → the edit survives. Needs no key or quota.
import { spawn } from "node:child_process";

const PORT = 8101;
const BASE = `http://127.0.0.1:${PORT}`;

let cookie = "";
async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(cookie ? { Cookie: cookie } : {}), ...(opts.headers ?? {}) },
  });
  const set = res.headers.get("set-cookie");
  if (set) cookie = set.split(";")[0];
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(`${opts.method ?? "GET"} ${path} → ${res.status} ${text.slice(0, 200)}`);
  return body;
}

async function waitFor(fn, timeoutMs, label) {
  const start = Date.now();
  for (;;) {
    try {
      const v = await fn();
      if (v) return v;
    } catch {
      /* retry */
    }
    if (Date.now() - start > timeoutMs) throw new Error(`timed out: ${label}`);
    await new Promise((r) => setTimeout(r, 1000));
  }
}

async function main() {
  const { fileURLToPath } = await import("node:url");
  const apiDir = fileURLToPath(new URL("../../api", import.meta.url));
  const path = await import("node:path");
  const py = path.join(apiDir, ".venv", "bin", "python");
  const server = spawn(py, ["-m", "uvicorn", "app.main:app", "--port", String(PORT)], {
    cwd: apiDir,
    env: { ...process.env, FAKE_LLM: "1" },
    stdio: "pipe",
  });
  const kill = () => server.kill();
  process.on("exit", kill);
  try {
    await waitFor(async () => {
      const r = await fetch(`${BASE}/api/health`).catch(() => null);
      return r?.ok ? true : null;
    }, 30000, "backend health");
    console.log("backend up");

    const email = `e2e${Date.now()}@example.com`;
    await req("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password: "password123" }) });
    console.log("registered");

    const jd = "Need Python. Required: Python.";
    const created = await req("/api/kits", { method: "POST", body: JSON.stringify({ jd, company_url: "", days: 2 }) });
    console.log("created kit", created.kit_id, "job", created.job_id);

    const kit = await waitFor(async () => {
      const k = await req(`/api/kits/${created.kit_id}`);
      if (k.status === "ready") return k;
      if (k.status === "failed") throw new Error(`kit failed: ${JSON.stringify(k.error)}`);
      return null;
    }, 180000, "kit ready");
    console.log(`ready: ${(kit.kit.questions ?? []).length} questions`);

    // Add a Question by hand (mirrors the builder flow), then edit it.
    const added = await req(`/api/kits/${created.kit_id}/questions`, {
      method: "POST",
      body: JSON.stringify({ prompt: "E2E question", answer_outline: "Outline.", requirement_ids: [], category: "technical", difficulty: 1 }),
    });
    if (added._meta.origin !== "user") throw new Error("hand-added question should be origin user");
    const editedPrompt = "E2E question [edited]";
    const patched = await req(`/api/kits/${created.kit_id}/questions/${added.id}`, {
      method: "PATCH",
      body: JSON.stringify({ prompt: editedPrompt, rev: added._meta.rev }),
    });
    if (patched._meta.edited !== true) throw new Error("edit flag not set");
    console.log("edited", added.id);

    const regen = await req(`/api/kits/${created.kit_id}/sections/questions:${added.category}/regenerate`, { method: "POST" });
    console.log("regenerated", added.category, JSON.stringify(regen).slice(0, 120));

    const after = await req(`/api/kits/${created.kit_id}`);
    const kept = after.kit.questions.find((x) => x.id === added.id);
    if (!kept) throw new Error("edited question missing after regeneration");
    if (kept.prompt !== editedPrompt) throw new Error("edit did not survive regeneration");
    console.log("edit survived regeneration");

    // Add a Requirement so the weak-spots report has something to rank.
    await req(`/api/kits/${created.kit_id}/requirements`, {
      method: "POST",
      body: JSON.stringify({ text: "Must know Python", kind: "technical", priority: "must" }),
    });
    const weak = await req(`/api/kits/${created.kit_id}/practice/weak-spots`);
    if (!Array.isArray(weak.spots) || weak.spots.length === 0) throw new Error("weak spots empty");
    console.log(`weak spots: ${weak.spots.length}`);
    console.log("E2E PASS");
  } finally {
    kill();
  }
}

main().catch((e) => {
  console.error("E2E FAIL:", e.message);
  process.exit(1);
});
