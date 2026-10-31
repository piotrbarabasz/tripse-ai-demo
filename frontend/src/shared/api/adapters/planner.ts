import "../client/validation-runtime";
import type { TripRequest } from "../generated/types.gen";
import { zTripAccepted, zTripStatus } from "../generated/zod.gen";
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
