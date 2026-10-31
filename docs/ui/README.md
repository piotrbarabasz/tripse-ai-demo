# UI documentation

Existing UI: Vanilla JavaScript served by FastAPI. FRONT-001A adds the React shell;
FRONT-001B serves its compiled output privately under `/app`, adds the health PoC
and image/source contracts. See [startup](../../frontend/README.md),
[current integration/rollback/evidence](front-001b-integration.md) and
[historical FRONT-001A validation](front-001a-validation.md).
ARCH-001 future migration proposals and ADR-0017 retain their proposed status.

Later stages remain migration proposals, not owner-approved implementation decisions. The
[original blueprint](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md) has been reconciled;
see [scope differences and open decisions](../architecture/reconciliation.md).

- [Architecture and module boundaries](architecture.md)
- [FRONT-002 operational Hub/Planner, security and validation](front-002-planner.md)
- [FRONT-003A read-only catalog/library, access and validation](front-003a-documents.md)
- [FRONT-003B creation wizard, recovery, snapshots and validation](front-003b-creation.md)
- [API-001 client, query conventions and schema gaps](../api/api-001.md)
- [Routing and coexistence](routing.md)
- [Component and styling strategy](component-strategy.md)
- [Current-state technical audit](../architecture/current-state-audit.md)
- [Migration stages](../architecture/migration-roadmap.md)
- Existing behavior: [Hub](../HUB.md), [viewer](../VIEWER.md),
  [Studio](../DOCUMENT_STUDIO.md), [document design](../document-system/design/layout-rules.md)
