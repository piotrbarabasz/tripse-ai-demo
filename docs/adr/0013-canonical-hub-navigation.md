---
id: ADR-0013
title: "Canonical Hub homepage and explicit planner navigation"
status: proposed
date: 2026-10-28
author: "Codex — implementation proposal"
area: "UI routing, navigation and proxy access boundaries"
related_tasks: []
related_prs: []
supersedes: [ADR-0008]
---

# ADR-0013: Canonical Hub homepage and explicit planner navigation

Implemented locally for review; formal owner approval and deployment are not
recorded. `proposed` is intentional. This replaces ADR-0008's choice to preserve
the root planner and carries forward its independent-module and private-Hub rules.

## 1. Context and problem

ADR-0008 retained `/` as the planner while introducing a separate local Hub.
Authenticated cloud composition inherited that split; readonly preview already
redirected to Hub. The user now explicitly requests one homepage and a stable
planner URL. Hostname-only return links hide Hub navigation on Cloud Run.

## 2. Alternatives considered

Retain inconsistent entrypoints; replace the planner UI with a duplicate; use
broad path rewriting; or move the existing form to an explicit route. The chosen
route change needs no framework, API alias or new data/authentication mechanism.

## 3. Decision

Use relative `GET /` → 302 `/hub` in all compositions. Hub renders directly.
The existing planner form moves to `/planner` in local/authenticated cloud modes;
readonly preview retains `/preview/planner`. Studio and mock simulator URLs stay.
Module links and the Make planner helper use the canonical route. APIs and token
viewers remain unchanged. Navigation visibility uses a fixed backend-rendered
hint based on trusted local access or authenticated cloud composition, with all
authorization still enforced server-side. Public token viewers have no Hub link.

Caddy explicitly allows the relocated public planner but keeps Hub, Studio,
simulator and internal jobs private. Its root redirect therefore ends at a denied
Hub; proxy users open `/planner` directly. No local/proxy trust bypass is added.

## 4. Rationale

**Documented:** the 2026-10-28 routing request explicitly replaces the earlier
root-preservation choice, which ADR-0008 listed as a reconsideration trigger.
**Inference:** a canonical homepage and explicit planner URL reduce ambiguous
links while retaining the existing FastAPI composition and CSP.
**Unconfirmed:** formal approval of this ADR and deployed acceptance of the change.

## 5. Positive and negative consequences

Consistent application entry and working cloud return links; one planner UI and
unchanged API consumers. Bookmarks to `/` now reach Hub. Public Caddy homepage
cannot launch private modules; its users must bookmark `/planner`. The existing
public local planner/API exposure is preserved, not expanded to private modules.

## 6. Technical debt and limitations

No public authenticated portal is added to Caddy. Live Caddy HTTPS validation is
unavailable in this review; configuration and backend proxy restrictions are
tested. Human Cloud Run acceptance follows a separately approved delivery.
Trailing slash normalization remains FastAPI's existing 307 behavior.

## 7. Cost impact

Maintenance of route documentation, UI links and routing/security/browser
regressions. No dependency, service, storage schema or paid provider change.
No measured hours or costs supplied; [estimation rules](../tracking/estimates.md).

## 8. Related work and acceptance

User request dated 2026-10-28; no external task ID, new commit or PR exists.
[Routing inventory and validation](../ROUTING.md), [prior ADR](0008-local-demo-hub.md),
[Hub](../HUB.md), [cloud composition](0011-authenticated-cloud-demo.md).
Existing module and storage decisions are retained. No formal owner acceptance.

## 9. Reconsideration criteria

Public authenticated Caddy Hub, tenant navigation, public sharing, new identity
providers, route-level access changes, or automatic integration across modules.

## Change history

| Date | Author | Change and reason | Reference |
|---|---|---|---|
| 2026-10-28 | Codex | Replace root-planner preservation with canonical Hub; preserve API and access boundaries | User routing request; no task/PR ID |
