# Component and styling strategy

Status: proposed, subject to [ADR-0017](../adr/0017-modular-react-typescript-migration.md).

Use Tailwind CSS for the new application UI and selected shadcn/ui source components
for accessible primitives. Keep copied primitive code small, owned by the repository
and reviewed for keyboard/focus behavior and dependency cost. Do not install a whole
component catalog or redesign the document brand during the shell stage.

Three boundaries:

- Shared primitives: buttons, inputs, dialogs, labels, status/error messages. Accept
  ordinary props; contain no fetch, permissions or document-specific validation.
- Shared application presentation: shell navigation, page header, loading/empty/error
  layouts. Compose primitives; expose focus targets and responsive behavior.
- Feature components: planner form/progress, document source picker, section editor,
  library and preview controls. Feature hooks call typed adapters and translate server
  errors into actionable UI. Extract only demonstrated reuse.

Map application tokens to existing [brand guidance](../document-system/design/brand-guidelines.md)
and [brand-tokens.css](../../app/document_studio/frontend/brand-tokens.css) deliberately.
Scope application styles and resets to the app document. Existing print HTML has its
own typography, physical page dimensions, pagination and validation markers; Tailwind
preflight and UI-library CSS must not enter it.

Reuse server-rendered HTML in separate controlled preview documents/windows. Preserve
print-export.js readiness/diagnostics and window.print gates. Do not render server HTML
inside a React component with raw HTML insertion or reimplement pagination during the
editor migration. Header/IAP compatibility of framed previews is an explicit gate.

Parity checks cover keyboard navigation, dialog focus return, labels/errors, contrast,
mobile layout, unsaved edits, slow/out-of-order previews, revision conflicts, rights
confirmation/upload failures and print validation. Maintain the eight-template,
marketing-variant, long-content, images, A4/social PDF matrix described in
[PDF QA](../audits/DOC_PDF_003.md). Screenshots alone do not establish PDF text integrity.
