#!/usr/bin/env node
/**
 * One local quality gate: optional ruff lint, API tests, web typecheck + tests
 * (includes OpenAPI drift), and high-severity dependency audits.
 * Exit non-zero on the first failure.
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const py = resolve(root, "apps/api/.venv/bin/python");
const ruff = resolve(root, "apps/api/.venv/bin/ruff");

function run(label, command, args, opts = {}) {
  console.log(`\n==> ${label}`);
  const r = spawnSync(command, args, { stdio: "inherit", cwd: root, env: process.env, ...opts });
  if (r.status !== 0) {
    console.error(`verify failed: ${label}`);
    process.exit(r.status ?? 1);
  }
}

if (!existsSync(py)) {
  console.error("apps/api/.venv missing — run npm run setup first");
  process.exit(1);
}

if (existsSync(ruff)) {
  run("ruff (api)", ruff, ["check", "apps/api/app", "apps/api/tests"]);
} else {
  console.log("\n==> ruff not installed — skipping lint (optional)");
}

run("pytest", py, ["-m", "pytest", "apps/api/tests", "-q"]);
run("web typecheck", "npm", ["--prefix", "apps/web", "run", "typecheck"]);
run("web tests + drift", "npm", ["--prefix", "apps/web", "test"]);

console.log("\n==> pip audit (high)");
{
  const check = spawnSync(py, ["-c", "import pip_audit"], { cwd: root });
  if (check.status === 0) {
    run("pip audit", py, [
      "-m",
      "pip_audit",
      "-r",
      "apps/api/requirements.lock",
      "--severity-level",
      "high",
      "--progress-spinner",
      "off",
    ]);
  } else {
    console.log("pip-audit not installed — skipping (pip install pip-audit to enable)");
  }
}

run("npm audit (web production, high)", "npm", [
  "--prefix",
  "apps/web",
  "audit",
  "--omit=dev",
  "--audit-level=high",
]);

console.log("\nverify ok");
