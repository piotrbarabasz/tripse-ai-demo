import { spawnSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "vitest";

it("reproduces generated code and detects content/file-set drift without modifying artifacts", () => {
  const folder = mkdtempSync(join(tmpdir(), "tripse-drift-test-"));
  try {
    cpSync("src/shared/api/generated", folder, { recursive: true });
    const check = () => spawnSync(process.execPath, ["scripts/generate-api.mjs", "--check", "--output", folder], { encoding: "utf8" });
    expect(check().status).toBe(0);
    const target = join(folder, "types.gen.ts");
    const original = readFileSync(target, "utf8");
    writeFileSync(target, original + "\n// drift\n");
    expect(check().status).toBe(1);
    expect(readFileSync(target, "utf8")).toContain("// drift");
    writeFileSync(target, original);
    writeFileSync(join(folder, "unexpected.ts"), "// stale generation");
    expect(check().status).toBe(1);
  } finally { rmSync(folder, { recursive: true, force: true }); }
}, 20000);
