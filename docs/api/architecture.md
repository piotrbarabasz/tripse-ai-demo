# API architecture

Current: [main.create_app](../../app/main.py) chooses local/cloud_demo composition or
the separate readonly_demo app. Routers adapt transport to job storage, viewer lookup,
demo messaging and document services. Retain this modular FastAPI backend; React is
another client of existing APIs, not a replacement backend.

| Boundary | Reuse / preserve |
| --- | --- |
| Planner | TripRequest → durable job → separate local worker or Cloud Tasks → PlanningPipeline/provider adapters → TripPlan and expiring viewer token. |
| Document editing | Pydantic source/draft models → DocumentService → Repository. Revision conflicts and independent source snapshots stay server-owned. |
| Library | DocumentLibrary → lightweight metadata/history plus explicit revision/operation UUID mutations. Ready remains a workflow status. |
| Images | AssetStore checks bytes, size/type and rights; local or GCS byte storage. No direct browser GCS credential/access path. |
| Messaging | WAHA and mock simulator adapt messages to shared planning; neither defines a new frontend assistant contract. |
| Security | local_only for private local modules; verified IAP principal/membership and task identity in cloud; readonly app excludes mutable routers. |

Sources: [document service](../../app/document_studio/service.py),
[repository protocol](../../app/document_studio/repository.py),
[library](../../app/document_studio/library.py), [cloud access](../../app/cloud_access.py).
JSON/GCS storage and SQLite/Firestore job adapters have different consistency and
operational properties. Migration does not replace them or promise transactions across
document head/history objects. Existing cloud document data is shared demo data, not a
new per-customer tenant store.

Proposed API-001 client layer separates generated transport types from feature mappings.
Use same-origin relative URLs and preserve status/headers. Narrow adapters handle binary
uploads, HTML previews and weakly specified JSON responses; do not pretend all endpoints
are generated, fully typed JSON. TanStack Query belongs in frontend hooks, not backend
services. See [contracts](contracts.md).

Proposed assistant orchestration invokes the same domain operations with explicit actor
context and checks. HTTP boundaries currently enforce important access rules: extracting
a service call does not automatically carry them with it. The orchestrator must enforce
the equivalent permissions, resource scope and operation constraints before invoking
services. See [assistant integration](assistant-integration.md).
