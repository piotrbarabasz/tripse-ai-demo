"""Private raster uploads: decode, validate, strip metadata, re-encode.

No client-provided filename is used as a filesystem path. Images are immutable.
"""
import io
import os
import tempfile
import warnings
from pathlib import PurePath

from PIL import Image, ImageOps, UnidentifiedImageError

from app.document_studio.models import ImageAsset
from app.document_studio.repository import StorageError

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 24_000_000
FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class AssetStore:
    def __init__(self, repository, binary_store=None):
        self.repository = repository
        self.binary_store = binary_store

    def image_path(self, asset):
        metadata = self.repository._path(self.repository.root, "assets", asset.asset_id)
        path = metadata.with_suffix("." + EXTENSIONS[asset.media_type])
        if path.resolve().parent != metadata.parent:
            raise ValueError("Invalid asset path")
        return path

    def get(self, identifier):
        asset = self.repository.get("assets", identifier)
        if self.binary_store is not None:
            return asset, self.binary_store.read(asset)
        path = self.image_path(asset)
        if not path.is_file():
            raise StorageError("Asset file unavailable")
        return asset, path

    def upload(self, data, media_type, filename, rights_confirmed):
        if not rights_confirmed:
            raise ValueError("Potwierdź prawo do użycia zdjęcia.")
        if media_type not in EXTENSIONS:
            raise ValueError("Dozwolone są wyłącznie JPG, PNG i WebP.")
        if PurePath(filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError("Nazwa pliku musi mieć rozszerzenie JPG, PNG lub WebP.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("Zdjęcie przekracza limit 8 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as probe:
                    actual = FORMATS.get(probe.format)
                    if actual != media_type:
                        raise ValueError("Zawartość pliku nie odpowiada deklarowanemu typowi.")
                    if probe.width * probe.height > MAX_PIXELS:
                        raise ValueError("Zdjęcie przekracza limit 24 megapikseli.")
                    if getattr(probe, "n_frames", 1) != 1:
                        raise ValueError("Wybierz zdjęcie statyczne, bez animacji.")
                    probe.verify()
                with Image.open(io.BytesIO(data)) as original:
                    original.load()
                    image = ImageOps.exif_transpose(original).convert("RGB" if actual == "image/jpeg" else "RGBA")
                    # A fresh image discards EXIF, GPS, ICC, comments and other metadata.
                    clean = Image.new(image.mode, image.size)
                    clean.paste(image)
                    encoded = io.BytesIO()
                    clean.save(encoded, format={"image/jpeg":"JPEG", "image/png":"PNG", "image/webp":"WEBP"}[actual])
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise ValueError("Nie można odczytać bezpiecznego zdjęcia JPG/PNG/WebP.") from exc
        asset = ImageAsset(original_name=filename, media_type=actual, width=clean.width, height=clean.height, rights_confirmed=True)
        if self.binary_store is not None:
            self.binary_store.write(asset, encoded.getvalue())
            try:
                return self.repository.save("assets", asset, create=True)
            except StorageError:
                # A timeout may follow a committed metadata write. Keep immutable
                # bytes: deleting them could break an already published asset.
                raise
            except Exception:
                self.binary_store.delete(asset)
                raise
        path = self.image_path(asset)
        temporary = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                stream.write(encoded.getvalue())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            try:
                self.repository.save("assets", asset, create=True)
            except StorageError:
                # Preserve bytes when the metadata commit outcome is unknown.
                raise
            except Exception:
                path.unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise StorageError("Cannot save image") from exc
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return asset
