---
id: ADR-0014
title: "Document library metadata and immutable previous-revision snapshots"
status: proposed
date: 2026-10-28
author: "Codex — implementation proposal"
area: "Document Studio persistence, metadata, revision history"
related_tasks: [DOCUMENT-LIBRARY-001]
related_prs: []
supersedes: []
---

# ADR-0014: Document library metadata and revision history

Implemented and tested locally; no cloud deployment or formal owner approval.
This extends ADR-0002/0003/0011 without replacing JSON/GCS or their access model.

## 1. Context and problem

The existing editable document is a complete `DocumentDraft` with optimistic
revision checks. Listing every draft downloads large snapshots; a revision number
alone preserves no prior content. DOCUMENT-LIBRARY-001 requires metadata queries,
copies, archive/restore and readable saved versions without another database.

## 2. Alternatives considered

Full-document listings; a mutable separate GCS index; immutable copies of candidate
writes; or previous-committed snapshots plus object metadata. A separate mutable
index risks inconsistency with the authoritative object. Archiving candidates
could expose failed concurrent writes as accepted revisions. Firestore indexing
and server-generated PDF storage are explicitly deferred.

## 3. Decision

Keep current documents in `drafts/` (GCS: `documents/drafts/`). Before updating a
document, preserve its previous committed state create-only in
`revisions/{document_id}/{revision:010d}.json` (GCS: `documents/revisions/`).
Only then replace the current document using existing revision/CAS checks.
Creation writes revision 1 as the current document. History combines immutable
previous states and the current head; it does not invent earlier missing versions.

GCS writes metadata `tripse_document` with the current object in the same upload,
using `if_generation_match` for its head and `0` for immutable history. Repeated
history creation must match the preserved document exactly. Local history uses
fsynced temporary files and create-only hard-link publication; current state still
uses atomic replace. A shared lock coordinates repository instances within one
Python process, not multiple API processes.

Local `metadata/` files are disposable caches tied to each data file's inode,
size and mtime. Stale/missing caches fall back to validated full documents; cache
write failure does not turn a committed document into a failed save. GCS legacy
objects without metadata are read until their next explicit save attaches it.
Metadata queries expose stable filters/sort/offset/limit; current implementation
scans metadata, leaving an indexed implementation possible later.

Technical `status: draft` is retained for compatibility; separate
`document_status` is `draft`, `in_review`, `ready` or `archived`. Ready is not
approval and cannot bypass export checks. Restore from archive returns to draft.
Author IDs come only from the verified cloud principal; local/unknown historical
authors remain null. Source identity/title are derived from snapshots for metadata,
not copied into redundant mutable fields on `DocumentDraft`.

## 4. Rationale

**Documented:** user requires existing Repository, complete editable state and
safe GCS preconditions without multi-object transaction claims.
**Inference:** preserve-before-head ensures a failed head write leaves the last
valid state readable; atomically attached GCS metadata avoids a second index commit.
**Unconfirmed:** production load, retention policy, legal archival requirements
and formal owner acceptance of this ADR.

## 5. Positive and negative consequences

All eight types reuse the same storage, editors and permissions. Snapshot content,
assets and revision conflicts remain intact. History requires extra objects and
storage/operations. Multiple GCS writes are not a transaction: a failed/ambiguous
head upload may leave a redundant previous snapshot, and a timeout after commit
requires rereading the head rather than blindly retrying an old revision.

## 6. Technical debt and limitations

Local operation remains single-process; metadata scan is O(n). History is
application-level create-only persistence, not WORM/legal archive or independent
backup. Missing pre-feature history cannot be reconstructed. Historical preview
uses the installed renderer; no archived PDF or frozen renderer binary is stored.
Historical content restoration, retention/pruning, employee-level ACLs and an
indexed Firestore catalogue are not implemented. Live GCP/container testing was
not performed in this task; see validation evidence in the user documentation.

## 7. Cost impact

Extra JSON/GCS copies, metadata/list/read operations and future retention/backup
work. No measured hours, monetary amounts or claimed savings. No new services.

## 8. Related work and acceptance

Task DOCUMENT-LIBRARY-001. No new PR/commit or formal ADR acceptance.
[Instructions and API](../DOCUMENT_STUDIO.md),
[local repository](../../app/document_studio/repository.py),
[GCS adapter](../../app/document_studio/cloud_storage.py),
[library service](../../app/document_studio/library.py),
[tests](../../tests/test_document_library.py).
Original choices: [JSON](0002-local-json-storage.md),
[snapshots](0003-document-snapshots.md), [cloud](0011-authenticated-cloud-demo.md).

## 9. Reconsideration criteria

Large metadata scans, multiple local API processes, transactional document/index
updates, formal audit requirements, per-person access, legal retention, or
immutable exported PDFs justify a new design and acceptance review.

## Change history

| Date | Author | Change | Reference |
|---|---|---|---|
| 2026-10-28 | Codex | Add metadata/history contract and document write ordering, retries and limits; retain proposed status | DOCUMENT-LIBRARY-001 |
