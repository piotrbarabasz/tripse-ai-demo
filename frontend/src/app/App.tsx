import type { ComponentProps } from "react";
import { RouterProvider, useRoutes } from "react-router-dom";
import { ErrorBoundary } from "../shared/components/ErrorBoundary";
import { routes } from "./router";

export function AppRoutes() {
  return useRoutes(routes);
}
export function App({ router }: { router: ComponentProps<typeof RouterProvider>["router"] }) {
  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  );
}
