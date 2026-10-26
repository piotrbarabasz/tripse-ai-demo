"""Private GCS JSON overlays with generation CAS; no filesystem emulation."""
from pydantic import ValidationError

from app.document_studio.repository import MODELS, JsonRepository, StorageError, ConflictError


class GCSRepository:
    def __init__(self, bucket, fixtures=None):
        # Only the fixture reader uses filesystem paths; initialize is never called.
        self.fixture_reader = JsonRepository(fixtures=fixtures)
        self.bucket = bucket

    def initialize(self):
        pass

    def _name(self, kind, identifier):
        self.fixture_reader._path(self.fixture_reader.fixtures, kind, identifier)
        return f"documents/{kind}/{identifier}.json"

    def _read(self, kind, identifier):
        from google.api_core.exceptions import NotFound, GoogleAPIError
        blob = self.bucket.blob(self._name(kind, identifier))
        try:
            # download_as_bytes sets generation from the same GET response. No
            # separate reload/download race can associate bytes with a newer version.
            raw = blob.download_as_bytes(timeout=10)
            value = MODELS[kind][0].model_validate_json(raw)
            if getattr(value, MODELS[kind][1]) != identifier:
                raise StorageError("Stored resource ID mismatch")
            if blob.generation is None:
                raise StorageError("Storage returned no generation")
            return value, int(blob.generation)
        except NotFound:
            if kind in {"trips", "campaigns"}:
                try:
                    path = self.fixture_reader._path(self.fixture_reader.fixtures, kind, identifier)
                    value = MODELS[kind][0].model_validate_json(path.read_bytes())
                    if getattr(value, MODELS[kind][1]) != identifier:
                        raise StorageError("Fixture resource ID mismatch")
                    return value, 0
                except FileNotFoundError:
                    pass
                except (OSError, ValidationError) as exc:
                    raise StorageError("Cannot read fixture") from exc
            raise KeyError(identifier) from None
        except (GoogleAPIError, ValidationError, OSError) as exc:
            raise StorageError("Cannot read cloud document") from exc

    def get(self, kind, identifier):
        return self._read(kind, identifier)[0]

    def list(self, kind):
        from google.api_core.exceptions import GoogleAPIError
        self._name(kind, "validation")
        prefix = f"documents/{kind}/"
        try:
            identifiers = {b.name[len(prefix):-5] for b in self.bucket.list_blobs(prefix=prefix, timeout=10)
                           if b.name.endswith(".json")}
            if kind in {"trips", "campaigns"}:
                identifiers.update(p.stem for p in (self.fixture_reader.fixtures / kind).glob("*.json"))
            return [self.get(kind, identifier) for identifier in sorted(identifiers)]
        except GoogleAPIError as exc:
            raise StorageError("Cannot list cloud documents") from exc

    def save(self, kind, value, *, create=False):
        from google.api_core.exceptions import PreconditionFailed, GoogleAPIError
        model, key = MODELS[kind]
        value = model.model_validate(value.model_dump(mode="json"))
        identifier = getattr(value, key)
        name = self._name(kind, identifier)
        try:
            previous, generation = self._read(kind, identifier)
        except KeyError:
            previous, generation = None, 0
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
        try:
            self.bucket.blob(name).upload_from_string(value.model_dump_json(),
                content_type="application/json", if_generation_match=generation, timeout=10)
        except PreconditionFailed:
            raise ConflictError("Concurrent cloud edit; reopen before saving") from None
        except (GoogleAPIError, OSError) as exc:
            raise StorageError("Cannot save cloud document") from exc
        return value


class GCSAssetBytes:
    def __init__(self, bucket):
        self.bucket = bucket

    def _blob(self, asset):
        return self.bucket.blob(f"images/{asset.asset_id}")

    def write(self, asset, data):
        from google.api_core.exceptions import GoogleAPIError
        try:
            self._blob(asset).upload_from_string(data, content_type=asset.media_type,
                                               if_generation_match=0, timeout=10)
        except (GoogleAPIError, OSError) as exc:
            raise StorageError("Cannot save cloud image") from exc

    def read(self, asset):
        from google.api_core.exceptions import GoogleAPIError
        try:
            return self._blob(asset).download_as_bytes(timeout=10)
        except (GoogleAPIError, OSError) as exc:
            raise StorageError("Cloud image unavailable") from exc

    def delete(self, asset):
        from google.api_core.exceptions import GoogleAPIError
        try:
            blob = self._blob(asset)
            blob.reload(timeout=10)
            blob.delete(if_generation_match=blob.generation, timeout=10)
        except GoogleAPIError:
            # Unreferenced immutable blobs are safe; operator cleanup can retry.
            pass
