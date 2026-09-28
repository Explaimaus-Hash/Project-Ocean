"""Immutable local observation collections; no raw/provider work in HTTP reads."""

import hashlib
import json
import re
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from tempfile import mkdtemp

from pydantic import ValidationError

from ..schemas.observations import ObservationCollection
from .product_common import ProductError, contained, describe_file, read_json, stat_file

MAX_COLLECTION_BYTES = 16 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_COLLECTIONS = 32
MAX_PAGE_SAMPLES = 500


def observation_id(value: str) -> str:
    if not re.fullmatch(r"o_[a-f0-9]{24}", value):
        raise ProductError(
            "invalid_collection_id", "Invalid observation identifier.", 422
        )
    return value


def _serialize(value: dict, maximum: int) -> bytes:
    try:
        content = json.dumps(value, allow_nan=False, separators=(",", ":")).encode()
    except (TypeError, ValueError):
        raise ProductError(
            "invalid_observations", "Observation values are invalid."
        ) from None
    if len(content) > maximum:
        raise ProductError(
            "observation_limit", "Observation output exceeds limits.", 413
        )
    return content


class ObservationStore:
    """Construct without filesystem reads or scientific imports."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, collection_id: str, filename: str) -> Path:
        return contained(
            self.root, f"data/observations/{observation_id(collection_id)}/{filename}"
        )

    def _manifest(self, collection_id: str):
        # Public contracts import only Pydantic, never processing/provider clients.
        from ..schemas.observation_api import ObservationManifest

        path = self._path(collection_id, "manifest.json")
        if not path.exists():
            raise ProductError(
                "not_prepared", "Observation collection is not prepared.", 404
            )
        stat_file(path, MAX_MANIFEST_BYTES)
        try:
            manifest = ObservationManifest.model_validate(
                read_json(path, MAX_MANIFEST_BYTES)
            )
        except (ValidationError, ValueError, TypeError):
            raise ProductError(
                "invalid_observations", "Observation metadata is invalid."
            ) from None
        if manifest.metadata.collection_id != collection_id:
            raise ProductError("invalid_observations", "Observation identity differs.")
        actual = stat_file(
            self._path(collection_id, "collection.json"), MAX_COLLECTION_BYTES
        )
        expected = manifest.collection_file
        if actual != (expected.size_bytes, expected.modified_ns):
            raise ProductError(
                "observations_changed", "Prepared observations have changed."
            )
        return manifest

    def metadata(self, collection_id: str) -> dict:
        return self._manifest(collection_id).metadata.model_dump(mode="json")

    def collection(self, collection_id: str) -> ObservationCollection:
        manifest = self._manifest(collection_id)
        path = self._path(collection_id, "collection.json")
        before = stat_file(path, MAX_COLLECTION_BYTES)
        try:
            with path.open("rb") as stream:
                content = stream.read(MAX_COLLECTION_BYTES + 1)
        except OSError:
            raise ProductError(
                "not_prepared", "Observations are unavailable.", 404
            ) from None
        if (
            len(content) > MAX_COLLECTION_BYTES
            or hashlib.sha256(content).hexdigest() != manifest.collection_file.sha256
            or stat_file(path, MAX_COLLECTION_BYTES) != before
        ):
            raise ProductError(
                "observations_changed", "Prepared observations have changed."
            )
        try:
            result = ObservationCollection.model_validate_json(content)
        except (ValidationError, ValueError, TypeError):
            raise ProductError(
                "invalid_observations", "Observation samples are invalid."
            ) from None
        if self._public(result) != manifest.metadata.model_dump(mode="json"):
            raise ProductError("invalid_observations", "Observation metadata differs.")
        return result

    @staticmethod
    def _public(collection: ObservationCollection) -> dict:
        return collection.model_dump(
            mode="json", exclude={"samples", "input_file", "source_filename"}
        ) | {"input_sha256": collection.input_file.sha256}

    def catalogue(self) -> dict:
        directory = contained(self.root, "data/observations")
        try:
            entries = (
                list(islice(directory.iterdir(), MAX_COLLECTIONS + 1))
                if directory.exists()
                else []
            )
        except OSError:
            raise ProductError(
                "observations_unavailable", "Observation catalogue is unavailable.", 503
            ) from None
        if len(entries) > MAX_COLLECTIONS:
            raise ProductError(
                "catalogue_limit", "Observation catalogue exceeds limits.", 503
            )
        collections = []
        for entry in sorted(entries):
            if entry.name.startswith("."):
                continue
            if not re.fullmatch(r"o_[a-f0-9]{24}", entry.name):
                continue
            try:
                metadata = self.metadata(entry.name)
                collections.append(
                    {
                        "collection_id": entry.name,
                        "status": "ready",
                        "metadata": metadata,
                    }
                )
            except ProductError as error:
                collections.append(
                    {
                        "collection_id": entry.name,
                        "status": "not_prepared",
                        "reason_code": error.code,
                    }
                )
        return {"schema_version": 1, "collections": collections}

    def samples(
        self,
        collection_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
        profile_id: str | None = None,
    ) -> dict:
        if not 0 <= offset <= 5000 or not 1 <= limit <= MAX_PAGE_SAMPLES:
            raise ProductError(
                "invalid_request", "Observation page is outside limits.", 422
            )
        if profile_id is not None and not re.fullmatch(r"r_[a-f0-9]{24}", profile_id):
            raise ProductError("invalid_request", "Profile identifier is invalid.", 422)
        collection = self.collection(collection_id)
        selected = collection.samples
        if profile_id is not None:
            selected = [item for item in selected if item.profile_id == profile_id]
            if not selected:
                raise ProductError(
                    "profile_not_found", "Profile is absent from this collection.", 404
                )
        page = selected[offset : offset + limit]
        return {
            "schema_version": 1,
            "collection_id": collection_id,
            "source_id": collection.source_id,
            "dataset_id": collection.dataset_id,
            "data_mode": collection.data_mode,
            "display_only": False,
            "comparison_result": False,
            "profile_id": profile_id,
            "offset": offset,
            "limit": limit,
            "total": len(selected),
            "next_offset": offset + len(page)
            if offset + len(page) < len(selected)
            else None,
            "samples": [item.model_dump(mode="json") for item in page],
        }

    def publish(self, collection: ObservationCollection) -> dict:
        """Publish a validated scientific snapshot without changing any raw file."""
        from ..schemas.observation_api import (
            ObservationManifest,
            ObservationMetadataResponse,
        )

        collection = ObservationCollection.model_validate(collection.model_dump())
        collection_id = observation_id(collection.collection_id)
        content = _serialize(collection.model_dump(mode="json"), MAX_COLLECTION_BYTES)
        destination = self._path(collection_id, "collection.json").parent
        if destination.exists():
            prior = self.collection(collection_id)
            if prior.model_dump(mode="json") != collection.model_dump(mode="json"):
                raise ProductError(
                    "observation_conflict", "Existing observation collection differs."
                )
            return self.metadata(collection_id)
        parent = contained(self.root, "data/observations")
        parent.mkdir(parents=True, exist_ok=True)
        if len(list(islice(parent.iterdir(), MAX_COLLECTIONS))) >= MAX_COLLECTIONS:
            raise ProductError(
                "catalogue_limit", "Observation capacity is reached.", 413
            )
        temporary = Path(mkdtemp(prefix=".observations_", dir=parent))
        try:
            output = temporary / "collection.json"
            with output.open("xb") as stream:
                stream.write(content)
            metadata = ObservationMetadataResponse.model_validate(
                self._public(collection)
            )
            manifest = ObservationManifest(
                schema_version=1,
                metadata=metadata,
                created_at=datetime.now(UTC),
                collection_file=describe_file(output, MAX_COLLECTION_BYTES),
            )
            with (temporary / "manifest.json").open("xb") as stream:
                stream.write(
                    _serialize(manifest.model_dump(mode="json"), MAX_MANIFEST_BYTES)
                )
            temporary.rename(destination)
        except OSError:
            raise ProductError(
                "publication_failed", "Observation publication failed."
            ) from None
        finally:
            # Remove only the two files created by this invocation, never raw inputs.
            if temporary.exists():
                for filename in ("collection.json", "manifest.json"):
                    (temporary / filename).unlink(missing_ok=True)
                temporary.rmdir()
        return self.metadata(collection_id)
