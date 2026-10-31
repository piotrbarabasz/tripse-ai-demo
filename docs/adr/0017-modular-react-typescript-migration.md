---
id: ADR-0017
title: "Gradual modular React and TypeScript frontend migration"
status: proposed
date: 2026-10-31
author: "Codex — author of this proposal"
area: "frontend, api, architecture"
related_tasks: [ARCH-001, FRONT-001, API-001, FRONT-002, FRONT-003, AI-001]
related_prs: []
supersedes: []
---

# ADR-0017: Gradual modular React and TypeScript frontend migration

Implementation: documentation only. Character: new proposal. Owner acceptance:
not recorded. Existing frontend/backend behavior remains the current baseline.
Uses the repository [ADR template](template.md) and [standard](README.md).

## 1. Kontekst i problem

The current Vanilla JavaScript UI has separate entry points, direct DOM rendering,
window globals and coupled fetch/form/workflow state. FastAPI already exposes reusable
domain services and typed document models. Migration must preserve demonstrations,
document rendering, local/cloud/readonly security and GCP delivery. Source evidence:
[initial blueprint/audit](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md).

## 2. Rozważane alternatywy

| Alternative considered now | Trade-off |
| --- | --- |
| Keep Vanilla JS and extract ES modules | Lowest tooling/packaging change; still needs consistent routing, state, contracts and component lifecycle work. Viable if migration cost outweighs UI needs. |
| React + TypeScript + Vite, incremental `/app` | Explicit feature boundaries and compile-time interfaces; requires Node build, provenance updates and temporary dual UI maintenance. Proposed. |
| Full rewrite/cutover of existing URLs | Single end-state UI sooner, but large regression/rollback surface across documents, auth and demo. Rejected for this task. |
| SSR/full-stack React framework or separate frontend hosting | Could support future public/SEO needs; introduces server/deployment/auth/cache boundaries unnecessary for the current private app. Defer. |
| Vue/Svelte or a custom component framework | Valid alternatives; team experience and long-term ownership need confirmation. No measured superiority claim for React. |
| Plain CSS/custom primitives; SWR/custom fetch; handwritten clients | Fewer selected dependencies, but repeated component/data/contract maintenance. Retain legacy CSS for print; propose targeted libraries for app UI. |

## 3. Decyzja

Propose React + strict TypeScript + Vite; React Router scoped to `/app`; feature-based
modules. Use Tailwind CSS and selectively owned shadcn/ui primitives for application
screens, keeping print CSS/rendering isolated. Introduce TanStack Query and an offline
generated typed OpenAPI client in API-001 with explicit adapters for incomplete schemas,
HTML and binary responses.

Retain modular FastAPI, domain models/services, storage/job adapters and existing APIs.
Assistant orchestration uses explicit server tools with verified actor context and
domain services. Start mock-only; no arbitrary provider/storage access from UI/model.
Package compiled frontend in the existing FastAPI/Cloud Run image and same origin;
no new service/resource. Extend build source/provenance contracts deliberately later.
Preserve legacy routes and private boundaries; readonly_demo does not gain `/app`.
Stages and acceptance requirements: [roadmap](../architecture/migration-roadmap.md).

## 4. Uzasadnienie

**Udokumentowane:** repository code shows duplicated request/upload/state handling,
existing service seams and strict cloud/source boundaries; user request requires a
gradual migration preserving demo behavior.

**Wniosek:** a separate entry point and feature stages make parity and rollback
reviewable while reusing the backend. Same-origin packaging avoids introducing a
second browser authentication/CORS/deployment boundary initially.

**Niepotwierdzone:** owner approval, team React/library experience, ongoing ownership,
exact dependency versions, performance gain and delivery cost. No productivity or
bundle-size improvement has been measured.

## 5. Konsekwencje pozytywne i negatywne

Potential benefits: typed client boundaries, reusable UI primitives, lifecycle-managed
state and smaller feature reviews. Costs: Node dependency/security maintenance,
generation drift, React learning, dual UI regression burden and build-provenance work.
Tailwind resets can damage measured PDF layout; query defaults can retry writes or
overwrite unsaved edits. Local/browser mocks do not prove hosted IAP/chunk/preview parity.

## 6. Dług techniczny i ograniczenia

Track incomplete OpenAPI responses, planner/Studio model mismatch, shared cloud-demo
document scope, framing/header compatibility, dev-PR CI gap, script globals and repeated
upload/polling logic in the [blueprint risk register](../architecture/TRIPSE_ARCHITECTURE_BLUEPRINT.md).
Acceptance requires existing routes/security/print gates, deterministic builds/schema,
mode-specific routing tests, verified provenance and stage-specific rollback. No default
route cutover or legacy removal until separate parity acceptance. No security changes
are implicitly approved by adopting a UI framework.

## 7. Wpływ na kosztorys

Work packages: shell/toolchain/provenance; client/schema; Hub/planner; Studio/PDF parity;
assistant controls/evaluation; dependency maintenance and CI/browser coverage. Dual UI
maintenance is temporary but unquantified. Hosted build/runtime and eventual AI costs
need measured separate validation. No estimated hours or monetary amounts are asserted.
See [estimation rules](../tracking/estimates.md).

## 8. Powiązane taski, PR, commity i dokumenty

Tasks: ARCH-001, FRONT-001, API-001, FRONT-002, FRONT-003, AI-001 from user request;
no linked GitHub issues or new PR/commit yet. Audited base dev `0956ea2`.
[UI](../ui/README.md), [API](../api/README.md), [roadmap](../architecture/migration-roadmap.md),
[worklog](../tracking/worklog.csv). Preserve existing
[ADR-0001](0001-modular-fastapi.md), [ADR-0004](0004-controlled-html-browser-pdf.md),
[ADR-0011](0011-authenticated-cloud-demo.md), [ADR-0012](0012-github-actions-delivery.md),
[ADR-0013](0013-canonical-hub-navigation.md) and [ADR-0014](0014-document-library-history.md).
This proposal supersedes none of them. Owner must approve stack/library ownership,
`/app` coexistence, same-service build packaging and assistant tool/confirmation scope.
No approval evidence or decision-maker acceptance is recorded; status stays proposed.

## 9. Warunki ponownego rozważenia decyzji

Reconsider if hosted private app assets cannot use existing policies, release provenance
cannot represent deterministic frontend builds, PDF parity fails, team cannot maintain
the chosen stack, or SSR/public discoverability, independent scaling or customer tenancy
becomes a requirement. Review measured bundle/build/runtime/regression cost before any
legacy cutover; no unmeasured numeric performance threshold is asserted.

## Historia zmian

| Data | Autor | Zmiana i uzasadnienie | Powiązanie |
| --- | --- | --- | --- |
| 2026-10-31 | Codex | New documentation-only migration proposal grounded in source audit | ARCH-001 |
