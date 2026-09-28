"""Bounded archive planning, separate from real operator execution."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.app.schemas.product_api import CatalogueResponse
from backend.app.schemas.products import PerformanceLimits
from backend.app.storage.product_common import ProductError
from scripts.prepare_bio_roms_archive import batch_dates


def test_480_times_plan_to_120_nonoverlapping_small_products():
    times = [
        datetime(1980, 1, 24, tzinfo=UTC) + timedelta(days=30 * i) for i in range(480)
    ]
    batches = batch_dates(times)
    assert len(batches) == 120
    assert batches[0][0] == times[0].date()
    assert batches[-1][1] == times[-1].date()
    assert all((end - start).days == 90 for start, end in batches)
    assert all(a[1] < b[0] for a, b in zip(batches, batches[1:], strict=False))
    assert batch_dates(times[:5])[-1] == (times[4].date(), times[4].date())


def test_archive_rejects_empty_oversized_and_duplicate_times():
    t = datetime(1980, 1, 24, tzinfo=UTC)
    for times in ([], [t] * 481, [t, t], [t, t - timedelta(days=1)]):
        with pytest.raises(ProductError):
            batch_dates(times)


def test_only_catalogue_capacity_changes_not_per_product_work():
    limits = PerformanceLimits(max_products=128)
    assert limits.max_preparation_values == 8000000
    assert limits.max_time_steps == 12
    assert limits.max_product_file_bytes == 134217728
    with pytest.raises(ValidationError):
        PerformanceLimits(max_products=129)


def test_public_archive_catalogue_accepts_128_but_rejects_129_products():
    from backend.app.schemas.products import Capabilities

    def catalogue(count):
        identifiers = [f"p_{i}" for i in range(count)]
        return {
            "schema_version": 1,
            "datasets": [
                {
                    "source_id": "incois_bio_roms",
                    "dataset_id": "incois_bio_roms_v2",
                    "title": "Synthetic fixture",
                    "role": "model",
                    "origin_url": "https://example.org",
                    "status": "ready",
                    "reason_code": "prepared_selection_available",
                    "product_ids": identifiers,
                }
            ],
            "products": [
                {
                    "product_id": identifier,
                    "dataset_id": "incois_bio_roms_v2",
                    "status": "ready",
                    "data_mode": "synthetic",
                    "variables": ["SST"],
                    "times": ["1980-01-24T00:00:00Z"],
                    "capabilities": Capabilities().model_dump(),
                    "region": {"west": 30, "east": 120, "south": -30, "north": 30},
                }
                for identifier in identifiers
            ],
        }

    assert len(CatalogueResponse.model_validate(catalogue(128)).products) == 128
    with pytest.raises(ValidationError):
        CatalogueResponse.model_validate(catalogue(129))
