// Drift check: regenerates types from the single committed OpenAPI source
// and fails the test run when the committed lib/api-types.ts differs.
// A response-shape change without regenerating types fails the build.
import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, unlinkSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import os from "node:os";

const here = dirname(fileURLToPath(import.meta.url));
const webDir = resolve(here, "..");
const committed = resolve(webDir, "lib/api-types.ts");
const apiSpec = resolve(webDir, "../api/openapi.json");

let fail = false;
if (!existsSync(apiSpec)) {
  console.error("DRIFT: apps/api/openapi.json missing.");
  process.exit(1);
}
if (!existsSync(committed)) {
  console.error("DRIFT: apps/web/lib/api-types.ts missing — run npm run generate:types.");
  process.exit(1);
}
const tmp = join(os.tmpdir(), `api-types-drift-${process.pid}.ts`);
execFileSync(process.execPath, [resolve(here, "generate-types.mjs"), tmp], { stdio: "inherit" });
const a = readFileSync(committed, "utf8");
const b = readFileSync(tmp, "utf8");
try {
  unlinkSync(tmp);
} catch {
  /* ignore */
}
if (a !== b) {
  console.error("DRIFT: lib/api-types.ts is stale — run npm run generate:types and commit.");
  process.exit(1);
}
console.log("drift check ok (schemas match committed types)");
