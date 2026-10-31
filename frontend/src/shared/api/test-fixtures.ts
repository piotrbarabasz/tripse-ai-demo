import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { z } from "zod";

export const fixture: Record<string, unknown> = z.record(z.string(), z.unknown()).parse(JSON.parse(readFileSync(resolve("../docs/api/fixtures.json"), "utf8")));
