# TRIPSE architecture

ARCH-001, 2026-10-31: documentation foundation for a gradual frontend migration.
The current application remains Vanilla JavaScript + FastAPI. All React work is proposed.

- [Original architecture blueprint: proposed long-term vision](TRIPSE_ARCHITECTURE_BLUEPRINT.md)
- [Completed source reconciliation and open decisions](reconciliation.md)
- [Current implementation: technical audit](current-state-audit.md)
- [Incremental migration roadmap and validation record](migration-roadmap.md)
- [Proposed ADR-0017](../adr/0017-modular-react-typescript-migration.md)
- [UI documentation](../ui/README.md) and [API documentation](../api/README.md)
- [Current route inventory](../ROUTING.md), [ADR register](../adr/README.md),
  [work tracking](../tracking/README.md)
- [Document system documentation](../document-system/README.md),
  [historical repository audit](../tracking/repository-audit.md),
  [delivery documentation](../GITHUB_CICD.md)

Existing specialist and historical documents remain in place. Their dated implementation
claims must be read with their stated scope. The audit describes current code; the
original user-authored blueprint records the proposed target vision. Its 446 lines are
preserved unchanged and reconciled with this documentation. ADR-0017 records proposed
decisions; the roadmap records future tasks. Documentation completion does not approve
the stack, stage numbering or implementation. No new owner approval or deployment is recorded.
