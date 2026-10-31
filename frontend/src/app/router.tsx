import { HubPage } from "../features/hub/HubPage";
import { modules } from "../shared/config/modules";
import { AppLayout } from "./layouts/AppLayout";
import { ModulePage } from "./ModulePage";
import { NotFoundPage } from "./NotFoundPage";

export const routes = [
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <HubPage /> },
      ...modules.map((module) => ({
        path: module.path.slice(1),
        element: <ModulePage module={module} />,
      })),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
