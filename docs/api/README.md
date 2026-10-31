# API documentation

ARCH-001, 2026-10-31: existing FastAPI behavior and proposed client/assistant boundaries.
No endpoint or authentication contract changes are implemented here.

- [Backend architecture](architecture.md)
- [Current contracts and typed-client plan](contracts.md)
- [Assistant integration proposal](assistant-integration.md)
- [Architecture audit](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md)
- [Existing routes](../ROUTING.md), [planning](../PLANNING.md),
  [Studio API](../DOCUMENT_STUDIO.md), [WAHA adapter](../WAHA.md)

Local FastAPI provides `/docs` and `/openapi.json`. Both cloud modes disable public
OpenAPI/docs routes; future client generation must use an isolated local/offline app.
