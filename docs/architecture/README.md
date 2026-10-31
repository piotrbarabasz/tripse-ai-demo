# TRIPSE architecture

ARCH-001, 2026-10-31: documentation foundation for a gradual frontend migration.
The current application remains Vanilla JavaScript + FastAPI. All React work is proposed.

- [Architecture blueprint and source audit](TRIPSE_ARCHITECTURE_BLUEPRINT.md)
- [Incremental migration roadmap and validation record](migration-roadmap.md)
- [Proposed ADR-0017](../adr/0017-modular-react-typescript-migration.md)
- [UI documentation](../ui/README.md) and [API documentation](../api/README.md)
- [Current route inventory](../ROUTING.md), [ADR register](../adr/README.md),
  [work tracking](../tracking/README.md)
- [Document system documentation](../document-system/README.md),
  [historical repository audit](../tracking/repository-audit.md),
  [delivery documentation](../GITHUB_CICD.md)

Existing specialist and historical documents remain in place. Their dated implementation
claims must be read with their stated scope; the blueprint distinguishes observed code
from future design. No deployment or cloud-state verification is part of ARCH-001.
