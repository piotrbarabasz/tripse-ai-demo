# TRIPSE documentation

ARCH-001 closure, 2026-10-31. Current application: Vanilla JavaScript + modular FastAPI.
React migration and the long-term product architecture are proposed; no new UI is implemented.

- [Architecture index](architecture/README.md)
- [Original architecture blueprint — proposed vision](architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md)
- [Current implementation audit](architecture/current-state-audit.md)
- [Completed source reconciliation and open owner decisions](architecture/reconciliation.md)
- [Incremental migration roadmap](architecture/migration-roadmap.md)
- [UI documentation](ui/README.md), [API documentation](api/README.md)
- [ADR register and statuses](adr/README.md), [worklog and tracking](tracking/README.md)
- [Document system](document-system/README.md), [Studio instructions](DOCUMENT_STUDIO.md)
- [Current routing](ROUTING.md), [Hub](HUB.md), [planning](PLANNING.md), [viewer](VIEWER.md)
- [CI/CD](GITHUB_CICD.md), [deployment/rollback](DEPLOY_GCP.md),
  [historical accepted release and limits](RELEASE_2026_10_28.md)

## Mapping the blueprint's proposed documentation structure

Blueprint section 5 proposes later uppercase document names. ARCH-001 uses the commissioned
filenames below; these links fulfill current responsibilities without creating duplicate
definitions or pretending optional future documents exist.

| Blueprint responsibility / proposed name | Current documentation or future scope |
| --- | --- |
| SYSTEM_CONTEXT.md | [Current-state audit](architecture/current-state-audit.md) and [reconciliation](architecture/reconciliation.md). |
| INTEGRATION_CONTRACTS.md | [API architecture](api/architecture.md), [contracts](api/contracts.md), [assistant](api/assistant-integration.md). |
| MIGRATION_PLAN.md | [migration-roadmap.md](architecture/migration-roadmap.md). |
| UI_ARCHITECTURE.md / DESIGN_SYSTEM.md | [UI architecture](ui/architecture.md), [routing](ui/routing.md), [component strategy](ui/component-strategy.md). |
| API_CLIENT.md | [Client generation/contract plan](api/contracts.md). |
| UI features/HUB, TRIP_PLANNER, DOCUMENT_STUDIO | Existing module guides above plus roadmap acceptance; feature-specific expansion remains future work. |
| UI features/MARKETING, ASSISTANT; Automations domain | [Marketing guide](MARKETING_COLLECTION.md), [assistant proposal](api/assistant-integration.md), [retained future scope](architecture/migration-roadmap.md). A separate Marketing/Automations app is not implemented. |
| API_ARCHITECTURE.md / DOMAIN_MODEL.md / STORAGE_AND_JOBS.md | [API architecture](api/architecture.md), [contract inventory](api/contracts.md), [source audit](architecture/current-state-audit.md), existing domain docs. Deeper cross-domain specifications remain future work. |
| ASSISTANT_AND_TOOLS.md / SECURITY.md | [Assistant/tool proposal](api/assistant-integration.md), [audit security boundaries](architecture/current-state-audit.md), existing [document security](document-system/architecture/security.md). Future customer identity is undecided. |
| Optional infra/DEPLOYMENT.md / OBSERVABILITY.md | Existing CI/CD, deployment, release and incident records remain in place. Optional restructuring/observability expansion is future work. |

Existing historical reports and ADRs remain authoritative for their dated evidence only.
The missing historical `DOC_TEMPLATES_006.md` report is recorded in reconciliation;
current guidance and the pre-implementation coverage audit do not replace its evidence.
