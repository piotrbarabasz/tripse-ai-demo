# Assistant integration through domain services

Status: **proposal**, AI-001. Current OpenAIPlanner produces structured trip drafts;
the mock WhatsApp simulator and WAHA adapter are not a general assistant tool platform.
No assistant endpoints, conversations or tool registry are implemented by ARCH-001.

Proposed flow: React assistant feature → authenticated FastAPI orchestration boundary
→ explicit typed tool registry → existing domain services/job adapters → structured
tool results. Model output proposes operations; server code decides whether they are
allowed. Provider keys, tools and storage access remain server-side.

Candidate tools (names and schemas are illustrative, not existing HTTP contracts):

| Tool capability | Domain seam | Required controls |
| --- | --- | --- |
| List templates / inspect permitted sources | Template registry, Repository reads | Existing mode/member/resource scope; redact operational/private data from model context. |
| Request plan / inspect progress | Job adapter and PlanningPipeline | Editor requirement for creation, bounded input/budget/time, existing idempotency and principal scope. Model never supplies verified route facts. |
| Propose document / validate | DocumentService, section validators | Validate typed input; preview proposal first; preserve snapshot/provenance and confidentiality. |
| Persist draft / transition status | DocumentService, DocumentLibrary | Explicit user intent/confirmation for consequential writes; exact current revision and operation UUID; authorization rechecked at execution. |

AI-001 starts with mock tools and synthetic data; writes may remain disabled until the
confirmation and audit design is accepted. No automatic export, publishing, messaging,
deletion, arbitrary HTTP/SQL, shell execution or IAM tools. Browser print remains the
existing explicit user operation. Tool results are data, never executable instructions.
Treat retrieved text/documents as untrusted content that cannot extend the tool allowlist
or override permissions. Enforce arguments/results via schemas and reject unknown tools.

The orchestrator must propagate verified actor context and repeat relevant authorization;
direct service calls otherwise bypass router/middleware checks. Preserve reader/editor
and internal-task separation. readonly_demo receives no orchestration routes. Cloud mock
startup currently rejects provider secrets: live cloud assistant enablement therefore
requires a separate reviewed mode/security/budget decision, not a hidden AI-001 default.

Before any real tool writes, decide owner-approved confirmation rules, retention and
redaction for conversation/tool audit metadata, request correlation, timeout/cancellation,
bounded steps/cost and failure recovery. Record safe operation metadata without raw
customer documents, credentials or IAP assertions. Confirmations bind tool arguments and
revision; an edited proposal invalidates the earlier confirmation. Replays must not
repeat mutations, and stale revisions fail visibly.

Acceptance: mock multi-step success/failure, unauthorized reader, cross-origin write,
unknown tool, injected instructions, invalid arguments, stale revision, duplicate request,
timeout/cancel and partial-failure cases. Measure provider costs only in separately
authorized live validation. See [roadmap](../architecture/migration-roadmap.md).
