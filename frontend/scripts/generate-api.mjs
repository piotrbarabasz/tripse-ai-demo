import { createClient } from "@hey-api/openapi-ts";
import { mkdtemp, readdir, readFile, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const { values } = parseArgs({ options: { check: { type: "boolean" }, output: { type: "string" } } });
const destination = values.output ?? fileURLToPath(new URL("../src/shared/api/generated/", import.meta.url));
const temporary = await mkdtemp(join(tmpdir(), "tripse-client-"));
try {
  await createClient({
    input: fileURLToPath(new URL("../../docs/api/openapi.json", import.meta.url)),
    output: { path: temporary, postProcess: [] },
    plugins: ["@hey-api/typescript", { name: "zod", dates: { offset: true, local: true } }],
  });
  const names = (await readdir(temporary)).sort();
  if (values.check) {
    const committed = (await readdir(destination)).sort();
    if (JSON.stringify(names) !== JSON.stringify(committed)) throw new Error("Generated API file set drift");
    for (const name of names) {
      if (await readFile(join(temporary, name), "utf8") !== (await readFile(join(destination, name), "utf8")).replaceAll("\r\n", "\n")) {
        throw new Error(`Generated API drift: ${name}; run npm run api:generate`);
      }
    }
  } else {
    await mkdir(destination, { recursive: true });
    for (const name of await readdir(destination)) {
      if (!names.includes(name)) await rm(join(destination, name));
    }
    for (const name of names) await writeFile(join(destination, name), await readFile(join(temporary, name)));
  }
} finally {
  await rm(temporary, { recursive: true, force: true });
}
