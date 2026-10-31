import { queryOptions } from "@tanstack/react-query";
import { apiKeys } from "../../shared/api/query/client";
import { readLibrary, readRevisions } from "../../shared/api/adapters/studio";
import type { LibraryFilters } from "../../shared/api/adapters/studio";

export const initialFilters: LibraryFilters = { search: "", archived: "exclude", sort: "updated_at", direction: "desc", offset: 0, limit: 25 };

// Key changes cancel both the debounce and network read. No old results are used
// as placeholder data under a new filter, and transient private searches use gc=0.
function debounceSearch(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const abort = () => { clearTimeout(timer); reject(new DOMException("Cancelled", "AbortError")); };
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, 300);
    if (signal.aborted) abort();
    else signal.addEventListener("abort", abort, { once: true });
  });
}

export function documentLibraryQuery(filters: LibraryFilters) {
  return queryOptions({
    queryKey: apiKeys.library(filters), gcTime: 0,
    queryFn: async ({ signal }) => {
      if (filters.search) await debounceSearch(signal);
      return readLibrary(filters, signal);
    },
  });
}

export function revisionsQuery(identifier: string) {
  return queryOptions({ queryKey: [...apiKeys.studio, "revisions", identifier], gcTime: 0,
    queryFn: ({ signal }) => readRevisions(identifier, signal) });
}
