// Generates lib/api-types.ts from the single committed OpenAPI source
// (apps/api/openapi.json). The UI consumes these types; hand-written
// response duplicates are not allowed.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webDir = resolve(here, "..");
const apiSpec = resolve(webDir, "../api/openapi.json");
const outFile = process.argv[2] ?? resolve(webDir, "lib/api-types.ts");

const PRIMS = { string: "string", integer: "number", number: "number", boolean: "boolean" };

function refName(ref) {
  return ref.split("/").pop();
}

function tsType(schema, comps) {
  if (!schema || typeof schema !== "object") return "unknown";
  if (schema.$ref) return refName(schema.$ref);
  if (schema.enum) return schema.enum.map((v) => JSON.stringify(v)).join(" | ");
  if (schema.anyOf) {
    const parts = schema.anyOf.filter((s) => s.type !== "null" && !s.$null);
    const hasNull = schema.anyOf.some((s) => s.type === "null");
    const inner = parts.map((s) => tsType(s, comps)).join(" | ");
    return hasNull ? `(${inner}) | null` : inner;
  }
  if (schema.oneOf) return schema.oneOf.map((s) => tsType(s, comps)).join(" | ");
  if (schema.allOf) return schema.allOf.map((s) => tsType(s, comps)).join(" & ");
  const t = schema.type;
  if (t === "array") return `Array<${tsType(schema.items ?? {}, comps)}>`;
  if (t === "object" || schema.properties) {
    const required = new Set(schema.required ?? []);
    const props = Object.entries(schema.properties ?? {}).map(([k, v]) => {
      const safe = /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(k) ? k : JSON.stringify(k);
      return `${safe}${required.has(k) ? "" : "?"}: ${tsType(v, comps)};`;
    });
    let extra = "";
    if (schema.additionalProperties === true) extra = "[key: string]: unknown;";
    else if (schema.additionalProperties && typeof schema.additionalProperties === "object")
      extra = `[key: string]: ${tsType(schema.additionalProperties, comps)};`;
    return `{ ${[...props, extra].filter(Boolean).join(" ")} }`;
  }
  if (PRIMS[t]) return PRIMS[t];
  return "unknown";
}

const spec = JSON.parse(readFileSync(apiSpec, "utf8"));
const comps = spec.components?.schemas ?? {};
const names = Object.keys(comps).sort();
const chunks = [
  "// AUTO-GENERATED from apps/api/openapi.json — do not edit by hand.",
  "// Run: npm run generate:types",
  "",
];
for (const name of names) {
  const schema = comps[name];
  if (schema.type === "object" || schema.properties || schema.allOf) {
    if (schema.allOf && schema.allOf.every((s) => s.$ref || Object.keys(s).length === 0)) {
      const refs = schema.allOf.filter((s) => s.$ref).map((s) => refName(s.$ref));
      chunks.push(`export type ${name} = ${refs.join(" & ") || "Record<string, unknown>"};`);
    } else if (schema.properties) {
      const required = new Set(schema.required ?? []);
      const props = Object.entries(schema.properties).map(([k, v]) => {
        const safe = /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(k) ? k : JSON.stringify(k);
        return `  ${safe}${required.has(k) ? "" : "?"}: ${tsType(v, comps)};`;
      });
      let extra = "";
      if (schema.additionalProperties === true) extra = "  [key: string]: unknown;";
      else if (schema.additionalProperties && typeof schema.additionalProperties === "object")
        extra = `  [key: string]: ${tsType(schema.additionalProperties, comps)};`;
      chunks.push(`export interface ${name} {\n${props.join("\n")}${extra ? `\n${extra}` : ""}\n}`);
    } else if (schema.additionalProperties && typeof schema.additionalProperties === "object") {
      chunks.push(`export type ${name} = Record<string, ${tsType(schema.additionalProperties, comps)}>;`);
    } else {
      chunks.push(`export type ${name} = Record<string, unknown>;`);
    }
  } else {
    chunks.push(`export type ${name} = ${tsType(schema, comps)};`);
  }
}
chunks.push("");
mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, chunks.join("\n"));
const paths = Object.keys(spec.paths ?? {}).length;
console.log(`generated ${outFile} (${names.length} schemas, ${paths} paths)`);
