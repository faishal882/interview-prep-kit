// Drift check: generated types match the committed OpenAPI document.
// Fails the test run on drift.
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webDir = resolve(here, "..");
const committedApi = resolve(webDir, "../api/openapi.json");
const mirrored = resolve(webDir, "openapi.json");
const generated = resolve(webDir, "lib/generated.ts");

let fail = false;
if (!existsSync(mirrored)) {
  console.error("DRIFT: apps/web/openapi.json missing — run npm run generate:types and copy the spec.");
  fail = true;
} else {
  const a = readFileSync(committedApi, "utf8");
  const b = readFileSync(mirrored, "utf8");
  if (a !== b) {
    console.error("DRIFT: apps/web/openapi.json differs from apps/api/openapi.json. Re-copy and regenerate.");
    fail = true;
  }
}
if (!existsSync(generated)) {
  console.error("DRIFT: apps/web/lib/generated.ts missing — run npm run generate:types.");
  fail = true;
} else {
  const spec = JSON.parse(readFileSync(committedApi, "utf8"));
  const paths = Object.keys(spec.paths ?? {}).sort();
  const gen = readFileSync(generated, "utf8");
  for (const p of paths) {
    if (!gen.includes(JSON.stringify(p))) {
      console.error(`DRIFT: generated types stale — missing path ${p}`);
      fail = true;
      break;
    }
  }
}
if (fail) process.exit(1);
console.log("drift check ok");
