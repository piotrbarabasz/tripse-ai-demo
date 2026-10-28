"""Validated JSON storage. Fixtures are read-only fallbacks; edits are local overlays."""
import os
import re
import tempfile
from pathlib import Path
from threading import RLock
from typing import Protocol

from pydantic import ValidationError

from app.document_studio.models import Campaign, DocumentDraft, ImageAsset, Trip

ROOT = Path(__file__).resolve().parents[2]
MODELS = {"trips": (Trip, "trip_id"), "campaigns": (Campaign, "campaign_id"), "drafts": (DocumentDraft, "document_id"), "assets": (ImageAsset, "asset_id")}
_ROOT_LOCKS = {}


class StorageError(Exception):
    pass


class ConflictError(Exception):
    pass


class Repository(Protocol):
    def list(self, kind): ...
    def get(self, kind, identifier): ...
    def save(self, kind, value, *, create=False): ...
    def list_documents(self): ...
    def list_revisions(self, identifier): ...
    def get_revision(self, identifier, revision): ...


class JsonRepository:
    def __init__(self, root=None, fixtures=None):
        self.root = Path(root) if root is not None else ROOT / "local-data" / "document-studio"
        self.fixtures = Path(fixtures) if fixtures is not None else ROOT / "demo-fixtures"
        self.lock = _ROOT_LOCKS.setdefault(str(self.root.resolve()), RLock())

    def initialize(self):
        for kind in (*MODELS, "assets"):
            (self.root / kind).mkdir(parents=True, exist_ok=True)

    def _path(self, base, kind, identifier):
        if (kind not in MODELS or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", identifier)
                or identifier.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}):
            raise ValueError("Invalid resource ID")
        folder = (base / kind).resolve()
        path = folder / f"{identifier}.json"
        if not folder.is_relative_to(base.resolve()) or path.resolve().parent != folder:
            raise ValueError("Resource path escapes its directory")
        return path

    def get(self, kind, identifier):
        path = self._path(self.root, kind, identifier)
        if not path.exists() and kind in {"trips", "campaigns"}:
            path = self._path(self.fixtures, kind, identifier)
        if not path.exists():
            raise KeyError(identifier)
        model, key = MODELS[kind]
        try:
            value = model.model_validate_json(path.read_text(encoding="utf-8"))
            if getattr(value, key) != identifier:
                raise StorageError("Resource ID does not match filename")
            return value
        except (OSError, UnicodeError, ValidationError) as exc:
            raise StorageError("Cannot read stored document data") from exc

    def list(self, kind):
        # A corrupt local edit must never silently fall back to the fixture.
        identifiers = set()
        bases = [self.fixtures, self.root] if kind in {"trips", "campaigns"} else [self.root]
        for base in bases:
            identifiers.update(p.stem for p in (base / kind).glob("*.json"))
        return [self.get(kind, identifier) for identifier in sorted(identifiers)]

    def save(self, kind, value, *, create=False):
        model, key = MODELS[kind]
        value = model.model_validate(value.model_dump(mode="json"))
        identifier = getattr(value, key)
        path = self._path(self.root, kind, identifier)
        with self.lock:
            try:
                previous = self.get(kind, identifier)
            except KeyError:
                previous = None
            if create and previous is not None:
                raise ConflictError("Resource already exists")
            if previous is not None:
                if value.revision != previous.revision:
                    raise ConflictError("Dane zmieniły się. Otwórz ponownie przed zapisem.")
                value.revision += 1
            elif value.revision != 1:
                raise ConflictError("New resources must have revision 1")
            if hasattr(value, "updated_at"):
                from app.document_studio.models import now
                value.updated_at = now()
            if kind == "drafts" and previous is not None:
                self._archive(previous)
            temporary = None
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as stream:
                    temporary = stream.name
                    stream.write(value.model_dump_json(indent=2))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            except OSError as exc:
                raise StorageError("Cannot save document data") from exc
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
            if kind == "drafts":
                self._cache_summary(path, value)
        return value

    def _revision_path(self, identifier, revision):
        self._path(self.root, "drafts", identifier)
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise ValueError("Invalid revision")
        folder = (self.root / "revisions" / identifier).resolve()
        if not folder.is_relative_to(self.root.resolve()):
            raise ValueError("Revision path escapes its directory")
        target = folder / f"{revision:010d}.json"
        if target.resolve().parent != folder:
            raise ValueError("Revision file escapes its directory")
        return target

    def _archive(self, draft):
        path = self._revision_path(draft.document_id, draft.revision)
        temporary = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                stream.write(draft.model_dump_json(indent=2))
                stream.flush()
                os.fsync(stream.fileno())
            try:
                # Publish a complete file, create-only. Never expose a partly written revision.
                os.link(temporary, path)
            except FileExistsError:
                stored = DocumentDraft.model_validate_json(path.read_bytes())
                if stored.model_dump(mode="json") != draft.model_dump(mode="json"):
                    raise StorageError("Immutable revision does not match the committed document")
            self._cache_summary(path, draft)
        except (OSError, ValueError) as exc:
            raise StorageError("Cannot preserve previous document revision") from exc
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _stamp(path):
        stat = path.stat()
        return [stat.st_ino, stat.st_size, stat.st_mtime_ns]

    def _metadata_path(self, path):
        target = (self.root / "metadata" / path.relative_to(self.root.resolve())).resolve()
        if not target.is_relative_to(self.root.resolve()):
            raise ValueError("Metadata path escapes its directory")
        return target

    def _cache_summary(self, path, draft):
        from app.document_studio.library import DocumentSummary
        temporary = None
        try:
            target = self._metadata_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            import json
            raw = json.dumps({"stamp": self._stamp(path), "document": DocumentSummary.from_draft(draft).model_dump(mode="json")})
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except (OSError, ValueError):
            # Cache is disposable: a failed cache write cannot undo a committed document.
            pass
        finally:
            if temporary and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass  # Temporary cache cleanup is not part of the document commit.

    def _summary(self, path, identifier, revision=None):
        from app.document_studio.library import DocumentSummary
        import json
        try:
            cached = json.loads(self._metadata_path(path).read_bytes())
            row = DocumentSummary.model_validate(cached["document"])
            if cached["stamp"] == self._stamp(path) and row.document_id == identifier and (revision is None or row.revision == revision):
                return row
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            draft = DocumentDraft.model_validate_json(path.read_bytes())
            if draft.document_id != identifier or revision is not None and draft.revision != revision:
                raise StorageError("Document revision identity mismatch")
            row = DocumentSummary.from_draft(draft)
            self._cache_summary(path, draft)
            return row
        except (OSError, ValueError) as exc:
            raise StorageError("Cannot read document metadata") from exc

    def list_documents(self):
        with self.lock:
            return [self._summary(self._path(self.root, "drafts", p.stem), p.stem)
                    for p in (self.root / "drafts").glob("*.json")]

    def get_revision(self, identifier, revision):
        with self.lock:
            current = self.get("drafts", identifier)
            if current.revision == revision:
                return current
            path = self._revision_path(identifier, revision)
            if not path.exists():
                raise KeyError(revision)
            try:
                draft = DocumentDraft.model_validate_json(path.read_bytes())
                if draft.document_id != identifier or draft.revision != revision:
                    raise StorageError("Document revision identity mismatch")
                return draft
            except (OSError, ValueError) as exc:
                raise StorageError("Cannot read historical document") from exc

    def list_revisions(self, identifier):
        with self.lock:
            current = self._path(self.root, "drafts", identifier)
            if not current.exists():
                raise KeyError(identifier)
            rows = [self._summary(current, identifier)]
            folder = self._revision_path(identifier, 1).parent
            for path in folder.glob("[0-9]*.json"):
                if path.stem.isdigit():
                    row = self._summary(self._revision_path(identifier, int(path.stem)), identifier, int(path.stem))
                    if row.revision < rows[0].revision:
                        rows.append(row)
            return sorted(rows, key=lambda row: row.revision, reverse=True)
