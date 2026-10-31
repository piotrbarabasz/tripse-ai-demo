import { BrowserRouter, useRoutes } from "react-router-dom";
import { ErrorBoundary } from "../shared/components/ErrorBoundary";
import { routes } from "./router";

export function AppRoutes() {
  return useRoutes(routes);
}
export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "")}>
        <AppRoutes />
      </BrowserRouter>
    </ErrorBoundary>
  );
}
