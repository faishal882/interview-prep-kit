#!/usr/bin/env node
// Locate apps/api/.venv python cross-platform, forward args.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const venvPy = process.platform === "win32"
  ? path.join(root, "apps", "api", ".venv", "Scripts", "python.exe")
  : path.join(root, "apps", "api", ".venv", "bin", "python");
const py = existsSync(venvPy) ? venvPy : "python3";
const args = process.argv.slice(2);
const r = spawnSync(py, args, { cwd: root, stdio: "inherit", env: { ...process.env, PYTHONPATH: path.join(root, "apps", "api") } });
if (r.error) console.error(String(r.error));
process.exit(r.status ?? 1);
