import "../client/validation-runtime";
import type { TripRequest } from "../generated/types.gen";
import { zTripAccepted, zTripStatus, zWorkspaceCapabilities } from "../generated/zod.gen";
import { z } from "zod";
import { request } from "../client/transport";

// Mode is supplied by trusted application composition, never inferred from /health.
export type PlannerTarget = { mode: "local" } | { mode: "cloud_demo"; idempotencyKey: string };

export function createTrip(body: TripRequest, target: PlannerTarget, signal?: AbortSignal) {
  return request("/api/trips", { json: (value) => zTripAccepted.parse(value) }, {
    method: "POST", body: { json: body }, signal,
    ...(target.mode === "cloud_demo" ? { headers: { "Idempotency-Key": target.idempotencyKey } } : {}),
  });
}

export async function readJob(tripId: string, signal?: AbortSignal) {
  const response = await request(`/api/trips/${encodeURIComponent(tripId)}`, { json: (value) => zTripStatus.parse(value) }, { signal });
  // result remains opaque JSON, including completed jobs. No TripPlan/Studio cast,
  // viewer token extraction, or direct save-to-Studio conversion is supported.
  return response.data;
}

export async function readCapabilities(signal?: AbortSignal) {
  return (await request("/api/workspace/capabilities", { json: (value) => zWorkspaceCapabilities.parse(value) }, { signal })).data;
}

// /api/demo/scenarios has no response model. Project only the existing catalog;
// examples are fetched only after the authenticated capability confirms mock mode.
export const scenariosSchema = z.object({ scenarios: z.array(z.object({
  id: z.string().min(1).max(80), name: z.string().min(1).max(200), text: z.string().trim().min(1).max(10000),
})).max(10) });

export async function readScenarios(signal?: AbortSignal) {
  return (await request("/api/demo/scenarios", { json: (value) => scenariosSchema.parse(value) }, { signal })).data.scenarios;
}
