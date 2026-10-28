"""Lightweight document metadata and library operations over the existing Repository."""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid5, NAMESPACE_URL

from pydantic import Field
from app.document_studio.models import Model, Identifier, Title, BusinessStatus, Confidentiality, LibraryOperation, now
from app.document_studio.repository import ConflictError
from app.document_studio.templates import TEMPLATES


class DocumentSummary(Model):
    document_id: Identifier
    title: Title
    template_id: str
    family: Literal["offer", "pilot", "marketing"]
    layout_variant: str
    confidentiality: Confidentiality
    source_type: Literal["trip", "campaign"]
    source_id: Identifier
    source_title: Title
    document_status: BusinessStatus
    archived_at: datetime | None
    revision: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None
    duplicated_from_document_id: Identifier | None

    @classmethod
    def from_draft(cls, draft):
        source = draft.trip_snapshot or draft.campaign_snapshot
        return cls(document_id=draft.document_id, title=draft.title, template_id=draft.template_id,
            family=TEMPLATES[draft.template_id].family, layout_variant=draft.layout_variant,
            confidentiality=draft.confidentiality, source_type="trip" if draft.trip_snapshot else "campaign",
            source_id=source.trip_id if draft.trip_snapshot else source.campaign_id, source_title=source.title,
            document_status=draft.document_status, archived_at=draft.archived_at, revision=draft.revision,
            created_at=draft.created_at, updated_at=draft.updated_at, created_by=draft.created_by,
            updated_by=draft.updated_by, duplicated_from_document_id=draft.duplicated_from_document_id)


class LibraryPage(Model):
    items: list[DocumentSummary]
    total: int
    offset: int
    limit: int
    has_more: bool


class LibraryMutation(Model):
    revision: int = Field(ge=1)
    operation_id: UUID


class StatusMutation(LibraryMutation):
    document_status: Literal["draft", "in_review", "ready"]


class DocumentLibrary:
    def __init__(self, repository):
        self.repository = repository

    def list(self, *, search="", family=None, template_id=None, document_status=None,
             archived="exclude", sort="updated_at", direction="desc", offset=0, limit=50):
        if template_id and template_id not in TEMPLATES:
            raise ValueError("Nieznany szablon")
        rows = self.repository.list_documents()
        def visible(row):
            if archived == "only":
                return row.document_status == "archived"
            return archived == "include" or document_status == "archived" or row.document_status != "archived"
        def ordering(row):
            value = getattr(row, sort)
            if sort == "title":
                return value.casefold(), row.document_id
            return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).timestamp(), row.document_id
        rows = [row for row in rows if search.casefold() in row.title.casefold()
            and (not family or row.family == family) and (not template_id or row.template_id == template_id)
            and (not document_status or row.document_status == document_status)
            and visible(row)]
        rows.sort(key=ordering, reverse=direction == "desc")
        return LibraryPage(items=rows[offset:offset+limit], total=len(rows), offset=offset, limit=limit,
                           has_more=offset+limit < len(rows))

    @staticmethod
    def _matches(draft, mutation, kind):
        op = draft.last_library_operation
        return (op and op.operation_id == str(mutation.operation_id) and op.kind == kind
            and op.base_revision == mutation.revision
            and (kind != "status" or draft.document_status == mutation.document_status))

    def transition(self, identifier, mutation, kind, actor=None):
        draft = self.repository.get("drafts", identifier)
        if self._matches(draft, mutation, kind):
            return draft
        if draft.revision != mutation.revision:
            raise ConflictError("Dane zmieniły się. Otwórz ponownie przed zmianą statusu.")
        target = "archived" if kind == "archive" else "draft" if kind == "restore" else mutation.document_status
        if kind == "status" and draft.document_status == "archived":
            raise ValueError("Najpierw przywróć dokument z archiwum")
        if kind == "restore" and draft.document_status != "archived":
            return draft
        if target == draft.document_status:
            return draft
        draft.document_status = target
        draft.archived_at = now() if target == "archived" else None
        draft.updated_by = actor
        draft.last_library_operation = LibraryOperation(operation_id=str(mutation.operation_id), kind=kind, base_revision=mutation.revision)
        try:
            return self.repository.save("drafts", draft)
        except ConflictError:
            current = self.repository.get("drafts", identifier)
            if self._matches(current, mutation, kind):
                return current
            raise

    def duplicate(self, identifier, mutation, actor=None):
        copy_id = uuid5(NAMESPACE_URL, f"tripse-document-copy:{identifier}:{mutation.revision}:{mutation.operation_id}").hex
        try:
            existing = self.repository.get("drafts", copy_id)
        except KeyError:
            existing = None
        if existing:
            if existing.duplicated_from_document_id != identifier:
                raise ConflictError("Identyfikator operacji jest już użyty")
            return existing
        original = self.repository.get("drafts", identifier)
        if original.revision != mutation.revision:
            raise ConflictError("Dokument zmienił się. Odśwież przed duplikowaniem.")
        copy = original.model_copy(deep=True)
        copy.document_id, copy.revision = copy_id, 1
        copy.title = original.title[:192] + " — kopia"
        copy.created_at = copy.updated_at = now()
        copy.created_by = copy.updated_by = actor
        copy.document_status, copy.archived_at = "draft", None
        copy.last_library_operation = None
        copy.duplicated_from_document_id = original.document_id
        try:
            return self.repository.save("drafts", copy, create=True)
        except ConflictError:
            existing = self.repository.get("drafts", copy_id)
            if existing.duplicated_from_document_id != identifier:
                raise
            return existing
