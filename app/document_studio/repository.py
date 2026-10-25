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


class StorageError(Exception):
    pass


class ConflictError(Exception):
    pass


class Repository(Protocol):
    def list(self, kind): ...
    def get(self, kind, identifier): ...
    def save(self, kind, value, *, create=False): ...


class JsonRepository:
    def __init__(self, root=None, fixtures=None):
        self.root = Path(root) if root is not None else ROOT / "local-data" / "document-studio"
        self.fixtures = Path(fixtures) if fixtures is not None else ROOT / "demo-fixtures"
        self.lock = RLock()

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
        return value
