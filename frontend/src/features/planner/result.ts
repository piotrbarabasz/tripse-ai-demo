import "../../shared/api/client/validation-runtime";
import { z } from "zod";

// Narrow worker.generate_job_result/TripPlan wire projection, not a complete plan.
// Raw warning strings and private job.error are never rendered by this feature.
export const completedResultSchema = z.object({
  viewer_url: z.string().max(2048).nullish(),
  viewer_expires_at: z.number().finite().optional(),
  is_mock: z.boolean(),
  generation_mode: z.enum(["mock", "live"]),
  verification_status: z.enum(["verified", "partial", "unverified"]),
  warnings: z.array(z.string()).max(100).optional(),
}).refine((value) => value.is_mock === (value.generation_mode === "mock"));

export function safeViewerPath(value: unknown, origin: string, expiresAt: number | undefined, now = Date.now()): string | null {
  if (typeof value !== "string" || value.trim() !== value || value.startsWith("//") || value.includes("\\") ||
    [...value].some((char) => char.charCodeAt(0) < 32) || !expiresAt || !Number.isFinite(expiresAt * 1000) || expiresAt * 1000 <= now) return null;
  if (!/^\/trip\/[A-Za-z0-9_-]{43}$/.test(value) && !/^https?:\/\/[^/]+\/trip\/[A-Za-z0-9_-]{43}$/.test(value)) return null;
  try {
    const url = new URL(value, origin);
    if (url.origin !== origin || url.username || url.password || url.search || url.hash || !/^\/trip\/[A-Za-z0-9_-]{43}$/.test(url.pathname)) return null;
    return url.pathname;
  } catch { return null; }
}
