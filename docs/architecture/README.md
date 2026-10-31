# TRIPSE architecture

ARCH-001, 2026-10-31: documentation foundation for a gradual frontend migration.
The current application remains Vanilla JavaScript + FastAPI. All React work is proposed.

- [Final-review reconciliation and missing original input](reconciliation.md)
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
original user-authored target vision belongs at `TRIPSE_ARCHITECTURE_BLUEPRINT.md`
and is pending restoration from the original input. ADR-0017 records proposed decisions;
the roadmap records future tasks. No new owner approval or deployment is recorded.
