import { useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { sessionFailed, subscribeSession } from "./client";

export function useSessionFailure(): boolean {
  const client = useQueryClient();
  return useSyncExternalStore((listener) => subscribeSession(client, listener), () => sessionFailed(client));
}
