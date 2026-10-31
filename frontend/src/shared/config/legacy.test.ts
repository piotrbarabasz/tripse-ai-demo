import { describe, expect, it } from "vitest";
import { resolveLegacyHref } from "./legacy";

describe("legacy navigation", () => {
  it.each(["/hub", "/planner", "/documents/demo"] as const)(
    "keeps production %s same-origin even when a dev origin is supplied",
    (path) => {
      expect(resolveLegacyHref(path, false, "http://127.0.0.1:8000")).toBe(
        path,
      );
      expect(resolveLegacyHref(path, false, "invalid")).toBe(path);
      expect(resolveLegacyHref(path, true)).toBe(path);
      expect(resolveLegacyHref(path, true, "http://127.0.0.1:8000/")).toBe(
        `http://127.0.0.1:8000${path}`,
      );
    },
  );
  it.each([
    "javascript:alert(1)",
    "https://user:password@localhost",
    "http://localhost/path",
    "http://localhost/?key=value",
    "http://localhost/#hash",
    "invalid",
  ])("rejects a non-origin dev configuration: %s", (origin) => {
    expect(() => resolveLegacyHref("/hub", true, origin)).toThrow();
  });
});
