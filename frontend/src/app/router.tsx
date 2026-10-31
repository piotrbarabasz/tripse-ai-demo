import { HubPage } from "../features/hub/HubPage";
import { PlannerPage } from "../features/planner/PlannerPage";
import { modules } from "../shared/config/modules";
import { AppLayout } from "./layouts/AppLayout";
import { ModulePage } from "./ModulePage";
import { NotFoundPage } from "./NotFoundPage";
import { DocumentsRoute } from "../features/documents/DocumentsRoute";
import { ErrorPage } from "../shared/components/ErrorBoundary";

export const routes = [
  {
    element: <AppLayout />,
    errorElement: <ErrorPage />,
    children: [
      { index: true, element: <HubPage /> },
      { path: "documents/*", element: <DocumentsRoute /> },
      ...modules.filter((module) => module.path !== "/documents").map((module) => ({
        path: module.path.slice(1),
        element: module.path === "/planner" ? <PlannerPage /> : <ModulePage module={module} />,
      })),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
