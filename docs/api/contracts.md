# Existing contracts and typed-client plan

Audit baseline: ARCH-001 / `0956ea2`, 2026-10-31. This is a contract inventory, not a
new versioned API. Authoritative definitions: [main.py](../../app/main.py),
[viewer.py](../../app/viewer.py), [Studio API](../../app/document_studio/api.py),
[Studio models](../../app/document_studio/models.py), [library](../../app/document_studio/library.py).

| Surface | Existing request/response semantics to preserve |
| --- | --- |
| `POST /api/trips` | TripRequest `{text}` trims whitespace, 1–10000 characters, forbids extra fields. 202 TripAccepted `{trip_id: UUID, status: queued}` and Location header. cloud_demo accepts UUID Idempotency-Key; local ignores it. |
| `GET /api/trips/{trip_id}` | TripStatus: trip_id, request_text, queued/running/completed/failed, nullable result/error, created_at/updated_at. Invalid UUID 422, absent/inaccessible job 404. `result` is currently dict/null, not a complete OpenAPI TripPlan response schema. |
| `GET /api/viewer/{token}` | `{plan, maps}` JSON; removes request_text/viewer_url, includes browser-only map config. Invalid/expired token 404. Token must match the 43-character format; cloud outer auth still applies. No response_model. |
| `GET /api/document-studio/access` | `{can_edit}`; local true after guard, cloud derived from server identity. A UI hint, not authorization. |
| Studio `trips`, `campaigns`, `drafts` | GET lists/items; POST 201; PUT item saves. Trip/Campaign and draft writes retain revision semantics; draft creation uses DraftRequest, updates DraftUpdate, responses DocumentDraft. No DELETE CRUD route. |
| Studio `templates`, `examples` | Read catalogs; examples/{identifier}/preview returns HTML, examples/{identifier}/copy POST 201 accepts operation_id UUID and returns an independent DocumentDraft. |
| Studio `library` | GET LibraryPage `{items,total,offset,limit,has_more}`. Filters: search, family, template_id, document_status, archived; sort title/created_at/updated_at, direction asc/desc; offset >=0, limit 1–100 (default 50). |
| Library mutations | POST library/{identifier}/duplicate (201), archive/restore/status (200). LibraryMutation requires revision >=1 and operation_id UUID; status additionally requires draft/in_review/ready. Archive restoration is not historical-content restoration. |
| Library history | GET library/{identifier}/revisions → DocumentSummary[]; /revisions/{revision} → historical draft, /preview → HTML. Revision >=1. No endpoint to overwrite head with historical content. |
| Trip-document projections | POST trip-documents/validate, initialize, preview accept `{draft,output_format}`. Initialize fills absent legacy sections/default offer fields without persisting; validate returns issues, preview returns HTML. |
| Marketing projections | POST marketing/validate or preview accepts `{campaign,output_format}`; GET campaigns/{identifier}/preview and drafts/{identifier}/preview render saved data. output_format a4/social, default a4; responses are HTML for preview routes. |
| Assets | GET assets lists metadata; POST assets?filename=...&rights_confirmed=true accepts raw image bytes with image Content-Type, 201. Stream limit 8 MB, 413 if exceeded; AssetStore validates image/rights. GET assets/{identifier}/content returns private image bytes. Not multipart or base64 JSON. |
| Simulator/integration | /api/demo/scenarios, POST /api/demo/messages (202), GET /api/demo/conversations/{conversation}; mock gate. WAHA webhook has separate sender/session/HMAC policy and is local composition only. /internal/jobs/{trip_id} is cloud task identity only. |

Studio rows use the `/api/document-studio/` prefix throughout. Many helpers translate
missing data → 404, conflicts → 409, domain validation → 422, storage errors → 503.
Pydantic 422 `detail` may be a list; HTTP/domain `detail` may be text. Auth/Origin/host
failures retain 401/403/400 distinctions. Readonly rejects writes with 403 before routing.
Do not globally map these to empty success results or retry all failures.

Draft schema invariants include exactly one source snapshot, campaign trip ordering,
confidentiality/template compatibility, revisions, provenance, and `sections: null`
versus `sections: []`. [planning_models.py](../../app/planning_models.py) is separate
from Studio models: do not handwrite one universal Trip type. Optional/null values and
verification warnings must survive serialization unchanged.

## API-001 generation and acceptance

**Implemented 2026-10-31:** [OpenAPI artifact](openapi.json), generated TypeScript/Zod
guards, same-origin transport, narrow adapters and TanStack Query foundation.
[Implementation guide](api-001.md) records the full response-model audit, remaining
gaps, exact commands, CI/provenance treatment and validation. The acceptance design
below is retained; it does not imply every endpoint now has a complete schema.

1. Generate OpenAPI from create_app using temporary paths, explicit local/mock mode,
   no credentials or production data. Cloud `/openapi.json` stays disabled. Produce a
   deterministic reviewed schema artifact and regeneration command from the repository.
2. Inventory endpoints without response_model, opaque `dict` payloads and helper-inferred
   returns. Generate types/client for covered contracts; supply narrowly documented
   supplemental types plus runtime guards/fixture tests for uncovered responses.
   Improving server response annotations is a separate compatible change requiring tests.
3. Pin generator/runtime dependencies and lockfile. Keep schema drift checks offline;
   never fetch a protected deployed schema in PR CI. Review schema diffs for unintended
   routes, status/content-type changes and sensitive examples.
4. Wrap same-origin fetch with bounded cancellation/timeouts, JSON/HTML/binary handling
   and structured failures. No stored IAP JWT or browser server-provider keys. Cancel
   stale reads/previews; preserve private/no-store handling and clear session caches.
5. Disable automatic mutation retries. Preserve one operation UUID per user operation,
   cloud planning idempotency key and revision conflicts. Read retries are bounded;
   stop polling on terminal state, auth failure, unmount or timeout. Never retry a
   local create as though cloud idempotency were supported.
6. Validate synthetic happy/error/auth/conflict/upload/HTML cases against FastAPI and
   generated adapters. Existing endpoint routes, schemas and security tests remain
   gates; no business-screen migration belongs in API-001.

## Future contracts, not current endpoints

Blueprint sections 7–9 propose shared job/status and tool contracts. Agree a versioning
standard for genuinely new APIs (for example /api/v1) without renaming existing routes.
Keep current queued/running/completed/failed semantics and channel-specific identity;
new approval/history/retry semantics need compatible schemas and authorization tests.
SSE is conditional on product need and auth/reconnect/proxy design; polling remains
the baseline. No Marketing, Automations or Assistant endpoint described by the vision
is represented here as implemented. See [domain workflow boundaries](architecture.md).

The FRONT-001 read-only health PoC is a small validated adapter; it must not become a
parallel handwritten business DTO set. API-001 replaces that boundary where appropriate
with deterministic generated coverage. Supplemental types for current schema gaps are
explicit temporary exceptions to the blueprint's no-duplicated-contracts goal, with
runtime/fixture validation and removal when server schemas cover them.
