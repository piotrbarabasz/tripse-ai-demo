# API architecture

FRONT-002 adds only the guarded read-only workspace capability contract to the
existing composition. [The Planner integration guide](../ui/front-002-planner.md)
documents actor-derived create permission, mode trust and result projection. Existing
Planner endpoints/worker/storage/viewer behavior stays unchanged; readonly has no
capability route. React queries consume API-001 and stop on session failure while
the in-memory private cache is cleared.

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

Implemented API-001 client layer separates generated transport types from feature mappings.
The [implementation guide](api-001.md) documents offline composition, generated Zod
guards, temporary gap projections and the in-memory query provider. Existing backend
response semantics and local/cloud/readonly composition remain unchanged.
Use same-origin relative URLs and preserve status/headers. Narrow adapters handle binary
uploads, HTML previews and weakly specified JSON responses; do not pretend all endpoints
are generated, fully typed JSON. TanStack Query belongs in frontend hooks, not backend
services. See [contracts](contracts.md).

Proposed assistant orchestration invokes the same domain operations with explicit actor
context and checks. HTTP boundaries currently enforce important access rules: extracting
a service call does not automatically carry them with it. The orchestrator must enforce
the equivalent permissions, resource scope and operation constraints before invoking
services. See [assistant integration](assistant-integration.md).

## Retained target workflows

[Blueprint sections 1, 6, 8–10](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md) describe
future Trip Catalog/reuse, Marketing, Automations and Assistant capabilities. Current
campaign services do not establish a separate Marketing API; current jobs are not a
general approval/workflow engine. New modules must reuse authorized domain operations,
with scoped contracts, idempotency, result/error/status and distinct retention rules
for inputs, job results, images/files, conversations and audit metadata.

First AI workflow: existing permitted Studio trip → DocumentService → editable draft
with ID, revision and missing-field warnings. A planner job result is a different model;
conversion requires an explicit future adapter/ownership decision. UI, Assistant and
WhatsApp invoke shared use cases with their own identity checks. Manual UI remains
usable without AI. See [reconciliation](../architecture/reconciliation.md).

Do not move durable state to Cloud Run memory/localStorage or migrate the database for
the frontend alone. New endpoint versioning and optional SSE require explicit contracts;
existing endpoints/polling remain compatible. Customer identity/tenancy, LIVE providers,
external sending and hosting changes remain separate gates.
