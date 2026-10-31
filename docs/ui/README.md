# UI documentation

Existing UI: Vanilla JavaScript served by FastAPI. FRONT-001A adds a standalone React
shell under `frontend/`, with no FastAPI or deployment integration. See
[startup and scope](../../frontend/README.md) and [local validation](front-001a-validation.md).
ARCH-001 future migration proposals and ADR-0017 retain their proposed status.

Later stages remain migration proposals, not owner-approved implementation decisions. The
[original blueprint](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md) has been reconciled;
see [scope differences and open decisions](../architecture/reconciliation.md).

- [Architecture and module boundaries](architecture.md)
- [Routing and coexistence](routing.md)
- [Component and styling strategy](component-strategy.md)
- [Current-state technical audit](../architecture/current-state-audit.md)
- [Migration stages](../architecture/migration-roadmap.md)
- Existing behavior: [Hub](../HUB.md), [viewer](../VIEWER.md),
  [Studio](../DOCUMENT_STUDIO.md), [document design](../document-system/design/layout-rules.md)
