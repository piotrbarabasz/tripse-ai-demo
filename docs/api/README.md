# API documentation

ARCH-001, 2026-10-31: existing FastAPI behavior and proposed client/assistant boundaries.
No endpoint or authentication contract changes are implemented here.

Current contracts come from source and regression tests. API-001 implements the
client foundation; assistant design remains proposed.
The [original blueprint](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md) has been reconciled;
see [scope differences and open decisions](../architecture/reconciliation.md).

- [API-001 generation, schema gaps and validation](api-001.md)
- [Generated local OpenAPI](openapi.json)
- [Backend architecture](architecture.md)
- [Current contracts and typed-client plan](contracts.md)
- [Assistant integration proposal](assistant-integration.md)
- [Architecture audit](../architecture/current-state-audit.md)
- [Existing routes](../ROUTING.md), [planning](../PLANNING.md),
  [Studio API](../DOCUMENT_STUDIO.md), [WAHA adapter](../WAHA.md)

Local FastAPI provides `/docs` and `/openapi.json`. Both cloud modes disable public
OpenAPI/docs routes; client generation uses an isolated local/offline app.
