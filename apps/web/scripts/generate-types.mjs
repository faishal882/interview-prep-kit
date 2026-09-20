// Generates lib/generated.ts from the backend committed OpenAPI document.
// The UI never hand-writes response types; it imports from here.
import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webDir = resolve(here, "..");
const apiSpec = resolve(webDir, "../api/openapi.json");

const spec = JSON.parse(readFileSync(apiSpec, "utf8"));
const paths = Object.keys(spec.paths ?? {}).sort();

const out = `// AUTO-GENERATED from apps/api/openapi.json — do not edit by hand.
// Run: npm run generate:types
export const OPENAPI_PATHS = ${JSON.stringify(paths, null, 2)} as const;
export type ApiPath = (typeof OPENAPI_PATHS)[number];
export const OPENAPI_TITLE = ${JSON.stringify(spec.info?.title ?? "")};
`;

writeFileSync(resolve(webDir, "lib/generated.ts"), out);
console.log(`generated lib/generated.ts (${paths.length} paths)`);
