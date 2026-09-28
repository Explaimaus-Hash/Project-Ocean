"""Immutable prepared results. HTTP reads never load raw data or run matching."""

import hashlib
import os
import re
import time
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from tempfile import mkdtemp

from ..schemas.comparison_api import (
    ComparisonManifest,
    ComparisonMetadata,
    ComparisonSnapshot,
    comparison_id,
)
from .product_common import ProductError, contained, describe_file, read_json, stat_file

MAX_RESULT_BYTES = 2097152
MAX_REPORT_BYTES = 1048576
MAX_MANIFEST_BYTES = 131072
MAX_RESULTS = 32
MAX_DIRECTORY_ENTRIES = 64
ID_PATTERN = r"c_[a-f0-9]{24}"


def _publish_directory(stage: Path, destination: Path) -> None:
    """Bounded Windows rename retry; never change permissions or overwrite a target.

    WinError 5 was observed intermittently at this exact step locally. It does
    not identify the external cause. Persistent denial remains a clear failure.
    """
    parent = destination.parent.resolve()
    if (
        stage.resolve().parent != parent
        or destination.resolve().parent != parent
        or not stage.name.startswith(".comparison_")
        or not re.fullmatch(ID_PATTERN, destination.name)
    ):
        raise ProductError("unsafe_product_path", "Publication path is unsafe.")
    delays = (0.05, 0.1, 0.2)
    for attempt in range(len(delays) + 1):
        if destination.exists():
            raise FileExistsError("Comparison destination already exists")
        try:
            stage.rename(destination)
            return
        except OSError as error:
            if getattr(error, "winerror", None) not in (5, 32, 33) or attempt == len(
                delays
            ):
                raise
            time.sleep(delays[attempt])


def _id(value: str) -> str:
    if not re.fullmatch(ID_PATTERN, value):
        raise ProductError(
            "invalid_comparison_id", "Invalid comparison identifier.", 422
        )
    return value


def _encode(model, maximum):
    payload = (model.model_dump_json() + "\n").encode()
    if len(payload) > maximum:
        raise ProductError("comparison_limit", "Split the comparison selection.", 413)
    return payload


def _project(report, identifier, prepared_at):
    """Explicit allowlist: private contexts, hashes, reference text never published."""
    m = report.matching
    p = m.strict_assessment.policy
    residuals = {r.sample_id: r.model_minus_observation for r in report.residuals}
    return ComparisonSnapshot(
        metadata=ComparisonMetadata(
            comparison_id=identifier,
            prepared_at=prepared_at,
            model_id=p.model_id,
            collection_id=p.collection_id,
            observation_acquisition_id=p.acquisition_id,
            data_mode=report.data_mode,
            status=report.status,
            overlap_status=m.overlap_status,
            assumptions=m.assumptions,
            assumption_id=m.assumption_id,
            blockers=m.blockers,
            strict_blockers=m.strict_assessment.blockers,
            summary=report.summary,
        ),
        samples=tuple(
            {**r.model_dump(), "model_minus_observation": residuals.get(r.sample_id)}
            for r in m.results
        ),
    )


class ComparisonStore:
    def __init__(self, root: Path):
        self.root = root  # No filesystem access at construction/startup.

    def _path(self, identifier, filename):
        return contained(self.root, f"data/comparisons/{_id(identifier)}/{filename}")

    def _entries(self):
        directory = contained(self.root, "data/comparisons")
        try:
            entries = (
                list(islice(directory.iterdir(), MAX_DIRECTORY_ENTRIES + 1))
                if directory.exists()
                else []
            )
        except OSError:
            raise ProductError(
                "comparisons_unavailable", "Comparison catalogue is unavailable.", 503
            ) from None
        if len(entries) > MAX_DIRECTORY_ENTRIES:
            raise ProductError(
                "catalogue_limit", "Comparison catalogue exceeds limits.", 503
            )
        selected = sorted(e.name for e in entries if re.fullmatch(ID_PATTERN, e.name))
        if len(selected) > MAX_RESULTS:
            raise ProductError(
                "catalogue_limit", "Comparison catalogue exceeds limits.", 503
            )
        return selected

    def _manifest(self, identifier):
        path = self._path(identifier, "manifest.json")
        try:
            if not path.exists():
                raise ProductError("not_prepared", "Comparison is not prepared.", 404)
            before = stat_file(path, MAX_MANIFEST_BYTES)
            manifest = ComparisonManifest.model_validate(
                read_json(path, MAX_MANIFEST_BYTES)
            )
            if stat_file(path, MAX_MANIFEST_BYTES) != before:
                raise ProductError("comparison_changed", "Prepared comparison changed.")
            if manifest.metadata.comparison_id != identifier:
                raise ValueError("Identity differs")
            expected = manifest.result_file
            if stat_file(self._path(identifier, "result.json"), MAX_RESULT_BYTES) != (
                expected.size_bytes,
                expected.modified_ns,
            ):
                raise ProductError("comparison_changed", "Prepared comparison changed.")
            return manifest
        except (ValueError, TypeError):
            raise ProductError(
                "invalid_comparison", "Comparison metadata is invalid."
            ) from None
        except OSError:
            raise ProductError(
                "comparisons_unavailable", "Comparison is unavailable.", 503
            ) from None

    def _snapshot(self, identifier):
        manifest = self._manifest(identifier)
        path = self._path(identifier, "result.json")
        before = stat_file(path, MAX_RESULT_BYTES)
        try:
            with path.open("rb") as stream:
                payload = stream.read(MAX_RESULT_BYTES + 1)
            if (
                len(payload) > MAX_RESULT_BYTES
                or hashlib.sha256(payload).hexdigest() != manifest.result_file.sha256
                or stat_file(path, MAX_RESULT_BYTES) != before
            ):
                raise ProductError("comparison_changed", "Prepared comparison changed.")
            result = ComparisonSnapshot.model_validate_json(payload)
            if (
                result.metadata != manifest.metadata
                or self._manifest(identifier) != manifest
            ):
                raise ProductError("comparison_changed", "Prepared comparison changed.")
            return result
        except (ValueError, TypeError):
            raise ProductError(
                "invalid_comparison", "Prepared comparison is invalid."
            ) from None
        except OSError:
            raise ProductError(
                "comparisons_unavailable", "Comparison is unavailable.", 503
            ) from None

    def metadata(self, identifier):
        return self._snapshot(identifier).metadata.model_dump(mode="json")

    def catalogue(self):
        entries = []
        for identifier in self._entries():
            try:
                metadata = self._manifest(identifier).metadata.model_dump(mode="json")
                entries.append(
                    dict(
                        comparison_id=identifier,
                        availability="prepared_snapshot",
                        metadata=metadata,
                    )
                )
            except ProductError as error:
                entries.append(
                    dict(
                        comparison_id=identifier,
                        availability="unavailable",
                        reason_code=error.code,
                    )
                )
        return dict(schema_version=1, comparisons=entries)

    def samples(self, identifier, *, offset=0, limit=100, matched=None):
        if (
            type(offset) is not int
            or type(limit) is not int
            or not 0 <= offset <= 5000
            or not 1 <= limit <= 500
            or (matched is not None and type(matched) is not bool)
        ):
            raise ProductError(
                "invalid_request", "Comparison page is outside limits.", 422
            )
        snapshot = self._snapshot(identifier)
        selected = tuple(
            r for r in snapshot.samples if matched is None or r.matched == matched
        )
        page = selected[offset : offset + limit]
        return dict(
            schema_version=1,
            metadata=snapshot.metadata.model_dump(mode="json"),
            offset=offset,
            limit=limit,
            matched=matched,
            total=len(selected),
            next_offset=offset + len(page)
            if offset + len(page) < len(selected)
            else None,
            samples=[r.model_dump(mode="json") for r in page],
        )

    def publish(self, report):
        """Internal operator-only publication of freshly authenticated metrics.

        Local files are trusted operator storage, not authenticated public uploads.
        The CLI reruns matching; no HTTP endpoint can call this operation.
        """
        from ..comparison.metrics import serialize_metrics
        from ..schemas.comparison_metrics import ExploratoryMetricsReport

        report_bytes = serialize_metrics(report)
        report = ExploratoryMetricsReport.model_validate_json(report_bytes)
        identifier = comparison_id(report_bytes)
        parent = contained(self.root, "data/comparisons")
        parent.mkdir(parents=True, exist_ok=True)
        lock = contained(self.root, "data/comparisons/.publish.lock")
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise ProductError(
                "comparison_busy", "Comparison publication is busy.", 503
            ) from None
        os.close(fd)
        temporary = None
        try:
            destination = self._path(identifier, "manifest.json").parent
            if destination.exists():
                old = self._snapshot(identifier)
                manifest = self._manifest(identifier)
                if (
                    describe_file(
                        self._path(identifier, "report.json"), MAX_REPORT_BYTES
                    )
                    != manifest.report_file
                    or hashlib.sha256(report_bytes).hexdigest()
                    != manifest.report_file.sha256
                    or old != _project(report, identifier, old.metadata.prepared_at)
                ):
                    raise ProductError(
                        "comparison_conflict", "Existing comparison differs."
                    )
                return old.metadata.model_dump(mode="json")
            if len(self._entries()) >= MAX_RESULTS:
                raise ProductError(
                    "catalogue_limit", "Comparison capacity is reached.", 413
                )
            snapshot = _project(report, identifier, datetime.now(UTC))
            public_bytes = _encode(snapshot, MAX_RESULT_BYTES)
            temporary = Path(mkdtemp(prefix=".comparison_", dir=parent))
            for filename, content in (
                ("report.json", report_bytes),
                ("result.json", public_bytes),
            ):
                with (temporary / filename).open("xb") as stream:
                    stream.write(content)
            manifest = ComparisonManifest(
                metadata=snapshot.metadata,
                report_file=describe_file(temporary / "report.json", MAX_REPORT_BYTES),
                result_file=describe_file(temporary / "result.json", MAX_RESULT_BYTES),
            )
            with (temporary / "manifest.json").open("xb") as stream:
                stream.write(_encode(manifest, MAX_MANIFEST_BYTES))
            if (
                ComparisonSnapshot.model_validate(
                    read_json(temporary / "result.json", MAX_RESULT_BYTES)
                )
                != snapshot
            ):
                raise ProductError(
                    "publication_failed", "Comparison verification failed."
                )
            _publish_directory(temporary, destination)
            temporary = None
            return self.metadata(identifier)
        except OSError:
            raise ProductError(
                "publication_failed", "Comparison publication failed."
            ) from None
        finally:
            if temporary is not None:
                for name in ("report.json", "result.json", "manifest.json"):
                    (temporary / name).unlink(missing_ok=True)
                temporary.rmdir()
            lock.unlink(missing_ok=True)
