import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import openapiTS, { astToString } from "openapi-typescript";
import { compile } from "json-schema-to-typescript";

const root = fileURLToPath(new URL("../../", import.meta.url));
const output = path.join(root, "frontend/src/api/generated");
await fs.mkdir(output, { recursive: true });
const ast = await openapiTS(
  new URL("../../contracts/openapi.json", import.meta.url),
);
await fs.writeFile(path.join(output, "rest.ts"), astToString(ast));
for (const [file, name] of [
  ["ws-events.schema.json", "WsEvent"],
  ["cards.schema.json", "Card"],
]) {
  const schema = JSON.parse(
    await fs.readFile(path.join(root, "contracts", file), "utf8"),
  );
  await fs.writeFile(
    path.join(output, `${name}.ts`),
    await compile(schema, name, {
      additionalProperties: false,
      cwd: path.join(root, "contracts"),
    }),
  );
}
const version = (
  await fs.readFile(path.join(root, "contracts/VERSION"), "utf8")
).trim();
await fs.writeFile(
  path.join(output, "version.ts"),
  `export const CONTRACT_VERSION = ${JSON.stringify(version)};\n`,
);
// Copy examples, never mutate the Engine's contract files.
await fs.cp(
  path.join(root, "contracts/examples"),
  path.join(root, "frontend/src/mocks/fixtures"),
  { recursive: true },
);
console.log(
  `Generated REST, WebSocket and card types; copied fixtures for contracts ${version}.`,
);
