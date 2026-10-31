import { MutationCache, QueryCache, QueryClient, queryOptions } from "@tanstack/react-query";
import { ApiError } from "../client/errors";
import { createTrip, readJob } from "../adapters/planner";
import type { PlannerTarget } from "../adapters/planner";
import type { TripRequest } from "../generated/types.gen";
import { readLibrary, saveDraft } from "../adapters/studio";
import type { LibraryFilters } from "../adapters/studio";
import type { DraftUpdate } from "../generated/types.gen";

export const apiKeys = {
  all: ["private-api"] as const,
  job: (id: string) => ["private-api", "planner", "job", id] as const,
  studio: ["private-api", "studio"] as const,
  library: (filters: LibraryFilters) => ["private-api", "studio", "library", filters] as const,
};

// Cache removal intentionally discards query data, including the failing query.
// Keep only an observable session-failure flag so mounted UIs do not fall back to
// a fresh pending query and hide the 401 or refetch it after cache removal.
const sessions = new WeakMap<QueryClient, { failed: boolean; listeners: Set<() => void> }>();
export function sessionFailed(client: QueryClient): boolean { return sessions.get(client)?.failed ?? false; }
export function subscribeSession(client: QueryClient, listener: () => void): () => void {
  const state = sessions.get(client);
  state?.listeners.add(listener);
  return () => { state?.listeners.delete(listener); };
}

export function createApiQueryClient(onSessionFailure?: () => void): QueryClient {
  const sessionError = (error: Error) => {
    if (error instanceof ApiError && error.kind === "unauthenticated") {
      const state = sessions.get(client);
      if (state) state.failed = true;
      client.clear(); // also aborts active reads; no private persisted cache
      state?.listeners.forEach((listener) => listener());
      onSessionFailure?.();
    }
  };
  const client = new QueryClient({
    queryCache: new QueryCache({ onError: sessionError }),
    mutationCache: new MutationCache({ onError: sessionError }),
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 5 * 60 * 1000, refetchOnWindowFocus: false, refetchOnReconnect: false },
      mutations: { retry: false, networkMode: "always" },
    },
  });
  sessions.set(client, { failed: false, listeners: new Set() });
  return client;
}

// Safe reads currently make one attempt. Callers explicitly refetch after errors.
export function jobQuery(tripId: string, pollingSignal?: AbortSignal) {
  return queryOptions({
    queryKey: apiKeys.job(tripId),
    queryFn: ({ signal }) => readJob(tripId, pollingSignal ? AbortSignal.any([signal, pollingSignal]) : signal),
    refetchInterval: (query) => pollingSignal?.aborted || query.state.error || !query.state.data || !["queued", "running"].includes(query.state.data.status) ? false : 1500,
    refetchIntervalInBackground: false,
  });
}

export function libraryQuery(filters: LibraryFilters = {}) {
  return queryOptions({ queryKey: apiKeys.library(filters), queryFn: ({ signal }) => readLibrary(filters, signal) });
}

export function createTripMutation(target: PlannerTarget, signal?: AbortSignal) {
  return { mutationFn: (body: TripRequest) => createTrip(body, target, signal), retry: false as const };
}

export function saveDraftMutation(client: QueryClient, identifier: string) {
  return {
    mutationFn: (value: DraftUpdate) => saveDraft(identifier, value),
    retry: false as const,
    onSuccess: async () => { await client.invalidateQueries({ queryKey: apiKeys.studio }); },
  };
}
