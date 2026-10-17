import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const root = fileURLToPath(new URL("../../", import.meta.url));
const file =
  process.argv[2] ||
  path.join(root, "frontend/src/mocks/recordings/golden_s1.json");
const recording = JSON.parse(await fs.readFile(file, "utf8"));
const schema = JSON.parse(
  await fs.readFile(path.join(root, "contracts/ws-events.schema.json"), "utf8"),
);
const version = (
  await fs.readFile(path.join(root, "contracts/VERSION"), "utf8")
).trim();
if (!recording.ok || recording.version !== version)
  throw new Error("Recording must be successful and match contracts/VERSION.");
const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
const validate = ajv.compile(schema);
const failures = [];
for (const [index, event] of recording.events.entries()) {
  if (!validate(event.envelope))
    failures.push({
      index,
      type: event.envelope?.type,
      errors: validate.errors,
    });
}
if (failures.length) {
  console.error(JSON.stringify(failures.slice(0, 3), null, 2));
  throw new Error(
    `${failures.length}/${recording.events.length} recorded envelopes violate the frozen contract.`,
  );
}
console.log(
  `Validated ${recording.events.length} real envelopes against contracts ${version}.`,
);
