import { request } from "../../shared/api/client/transport";

export type HealthStatus = { status: "ok"; generation_mode: "mock" | "live" };

// Both local and cloud /health responses contain these fields. Deliberately
// project only public connectivity information; discard service/version/storage.
export function parseHealth(value: unknown): HealthStatus {
  if (
    typeof value !== "object" ||
    value === null ||
    !("status" in value) ||
    value.status !== "ok" ||
    !("generation_mode" in value) ||
    (value.generation_mode !== "mock" && value.generation_mode !== "live")
  ) {
    throw new Error("invalid-health-response");
  }
  return { status: "ok", generation_mode: value.generation_mode };
}

export async function readHealth(signal: AbortSignal): Promise<HealthStatus> {
  return (await request("/health", { json: parseHealth }, { signal })).data;
}
