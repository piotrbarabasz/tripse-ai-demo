import { lazy, Suspense } from "react";
import { PageHeader } from "../../shared/components/PageHeader";

const DocumentsWorkspace = lazy(() => import("./DocumentsWorkspace"));

export function DocumentsRoute() {
  return <Suspense fallback={<PageHeader eyebrow="Dokumenty TRIPSE" title="Document Studio">Wczytywanie przestrzeni dokumentów…</PageHeader>}><DocumentsWorkspace /></Suspense>;
}
