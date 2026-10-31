import { expect, it } from "vitest";
import { fixture } from "../../shared/api/test-fixtures";
import { completedResultSchema, safeViewerPath } from "./result";

const token = "A".repeat(43);
const origin = "https://tripse.example";
const expiry = 4102444800;
it("validates the actual synthetic worker result and drops unneeded plan fields", () => {
  const parsed = completedResultSchema.parse(fixture.completed_result);
  expect(parsed.is_mock).toBe(true);
  expect(parsed.verification_status).toBe("unverified");
  expect(parsed).not.toHaveProperty("places");
  expect(parsed).not.toHaveProperty("request_text");
});
it.each([`/trip/${token}`, `${origin}/trip/${token}`])("accepts same-origin viewer %s", (url) => {
  expect(safeViewerPath(url, origin, expiry)).toBe(`/trip/${token}`);
});
it.each([null, undefined, "", `//tripse.example/trip/${token}`, `https://evil.example/trip/${token}`, `http://tripse.example/trip/${token}`, `${origin}/trip/${token}?x=1`, `${origin}/trip/${token}#a`, `${origin}/trip/${token}/`, `${origin}/trip/short`, `${origin}/trip/${"!".repeat(43)}`, `${origin}/api/viewer/${token}`, `https://user:password@tripse.example/trip/${token}`, `/trip/${token}\n`, ` /trip/${token}`, `/trip/%41${token.slice(1)}`, `/trip/../trip/${token}`, `https:\\tripse.example\trip\${token}`, "javascript:alert(1)"])("rejects unsafe viewer %s", (url) => {
  expect(safeViewerPath(url, origin, expiry)).toBeNull();
});
it.each([undefined, 0, -1, NaN, Infinity, Date.now() / 1000 - 1])("rejects missing/expired viewer expiry %s", (expires) => {
  expect(safeViewerPath(`/trip/${token}`, origin, expires)).toBeNull();
});
it.each([null, {}, { is_mock: "true" }, { is_mock: false, generation_mode: "mock", verification_status: "verified" }])("rejects malformed or contradictory result", (value) => {
  expect(completedResultSchema.safeParse(value).success).toBe(false);
});
