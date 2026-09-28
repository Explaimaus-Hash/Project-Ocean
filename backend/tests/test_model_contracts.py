"""Offline contract tests only: no model preparation or provider access."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.app.schemas.models import (
    ModelIdentity,
    ModelManifest,
    serialize_model_manifest,
)


@pytest.fixture
def identity_data():
    return {
        "request": {
            "acquisition_id": "a_" + "1" * 24,
            "variables": ["thetao"],
            "selection": {
                "region": {"west": 65, "east": 66, "south": -1, "north": 0},
                "start_time": "2019-01-29T00:00:00Z",
                "end_time": "2019-01-30T00:00:00Z",
                "vertical_min": 0.49,
                "vertical_max": 10,
                "vertical_kind": "depth_m",
            },
        },
        "provenance": {
            "acquisition_id": "a_" + "1" * 24,
            "acquisition_manifest_sha256": "2" * 64,
            "input_sha256": "3" * 64,
            "input_size_bytes": 1024,
            "dataset_id": "copernicus_fixture",
            "provider_dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1D-m",
            "source_version": "202311",
            "client": "synthetic_fixture",
            "client_version": "1",
            "client_processing": "synthetic fixture; no provider access",
            "retrieved_at": None,
            "data_mode": "synthetic",
        },
        "axes": {
            "times": ["2019-01-29T00:00:00Z", "2019-01-30T00:00:00Z"],
            "depth_m": [0.5, 1.5],
            "latitude": [-1, 0],
            "longitude": [65, 66],
            "source_time_indices": [0, 1],
            "source_depth_indices": [0, 1],
            "source_latitude_indices": [4, 5],
            "source_longitude_indices": [6, 7],
            "source_time_units": "hours since 1950-01-01",
            "calendar": "gregorian",
        },
        "variables": [
            {
                "source_name": "thetao",
                "units": "degrees_C",
                "standard_name": "sea_water_potential_temperature",
                "long_name": "Synthetic potential temperature",
                "source_dtype": "int16",
                "cell_methods": "area: mean",
                "unit_long": None,
                "temperature_scale": "unresolved",
            }
        ],
    }


def test_roundtrip_and_immutable_native_contract(identity_data):
    identity = ModelIdentity.model_validate(identity_data)
    restored = ModelIdentity.model_validate_json(identity.model_dump_json())
    assert restored == identity
    assert restored.model_id() == identity.model_id()
    assert identity.model_id().startswith("m_")
    assert len(identity.model_id()) == 26
    assert identity.axes.times[0].hour == 0
    assert identity.axes.source_latitude_indices == (4, 5)
    assert identity.policy.comparison_ready is False
    assert identity.policy.api_serving is False
    with pytest.raises(ValidationError):
        identity.axes.depth_m = (9,)
    with pytest.raises(TypeError):
        identity.axes.depth_m[0] = 9


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("request", "variables"), ["thetao", "thetao"]),
        (("request", "variables"), ["TEMP"]),
        (("request", "acquisition_id"), "../../private"),
        (("request", "selection", "vertical_kind"), "pressure_dbar"),
        (("provenance", "acquisition_id"), "a_" + "0" * 24),
        (("provenance", "source_id"), "godas"),
        (("provenance", "retrieved_at"), "2026-09-10T00:00:00"),
        (("axes", "times"), ["2019-01-29T00:00:00", "2019-01-30T00:00:00"]),
        (("axes", "times"), ["2019-01-30T00:00:00Z", "2019-01-29T00:00:00Z"]),
        (("axes", "times"), ["2019-01-28T00:00:00Z", "2019-01-30T00:00:00Z"]),
        (("axes", "calendar"), "360_day"),
        (("axes", "depth_m"), [1.5, 0.5]),
        (("axes", "depth_m"), [0.5, 0.5]),
        (("axes", "depth_m"), [-1, 1.5]),
        (("axes", "depth_m"), [0.5, 11]),
        (("axes", "depth_m"), [0.5, float("nan")]),
        (("axes", "longitude"), [65, 180]),
        (("axes", "latitude"), [-1, 91]),
        (("axes", "latitude"), [-2, -1]),
        (("axes", "source_depth_indices"), [0, 2]),
        (("axes", "source_depth_indices"), [0]),
        (("axes", "source_depth_indices"), [False, 1]),
        (("axes", "depth_positive"), "up"),
        (("limits", "max_preparation_values"), 15),
        (("limits", "max_depth_levels"), 1),
        (("limits", "max_time_steps"), 1),
        (("limits", "max_axis_values"), 1),
        (("limits", "max_depth_levels"), 65),
        (("policy", "comparison_ready"), True),
        (("policy", "api_serving"), True),
        (("policy", "temporal_support"), "instantaneous"),
        (("policy", "display_only"), True),
        (("request", "password"), "must_not_be_accepted"),
    ],
)
def test_reject_invalid_contract(identity_data, path, value):
    data = deepcopy(identity_data)
    data.setdefault("limits", {})
    data.setdefault("policy", {})
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(ValidationError):
        ModelIdentity.model_validate(data)


def test_variable_metadata_and_order_are_checked(identity_data):
    identity_data["variables"][0]["temperature_scale"] = "not_applicable"
    with pytest.raises(ValidationError):
        ModelIdentity.model_validate(identity_data)
    identity_data["variables"][0]["source_name"] = "so"
    with pytest.raises(ValidationError):
        ModelIdentity.model_validate(identity_data)


@pytest.mark.parametrize("change", ["input", "manifest", "limits", "mode", "version"])
def test_identity_changes_with_provenance_or_policy(identity_data, change):
    original = ModelIdentity.model_validate(identity_data).model_id()
    if change == "input":
        identity_data["provenance"]["input_sha256"] = "4" * 64
    elif change == "manifest":
        identity_data["provenance"]["acquisition_manifest_sha256"] = "5" * 64
    elif change == "limits":
        identity_data["limits"] = {"max_depth_levels": 8}
    elif change == "mode":
        identity_data["provenance"]["data_mode"] = "real"
    else:
        identity_data["provenance"]["source_version"] = "other_version"
    assert ModelIdentity.model_validate(identity_data).model_id() != original


def test_manifest_identity_and_file_budgets(identity_data):
    identity = ModelIdentity.model_validate(identity_data)
    record = {"size_bytes": 1024, "modified_ns": 1, "sha256": "6" * 64}
    data = {
        "model_id": identity.model_id(),
        "identity": identity.model_dump(mode="json"),
        "created_at": "2026-09-10T00:00:00Z",
        "scientific_file": record.copy(),
        "source_metadata_file": record.copy(),
    }
    manifest = ModelManifest.model_validate(data)
    assert ModelManifest.model_validate_json(manifest.model_dump_json()) == manifest
    assert serialize_model_manifest(manifest).endswith(b"\n")
    limited = deepcopy(data)
    limited["identity"]["limits"]["max_manifest_bytes"] = 1024
    limited["model_id"] = ModelIdentity.model_validate(limited["identity"]).model_id()
    with pytest.raises(ValueError, match="manifest byte budget"):
        serialize_model_manifest(ModelManifest.model_validate(limited))
    for field, value in (
        ("model_id", "m_" + "0" * 24),
        ("created_at", "2026-09-10T00:00:00"),
        ("status", "comparison_ready"),
    ):
        invalid = {**data, field: value}
        with pytest.raises(ValidationError):
            ModelManifest.model_validate(invalid)
    data["source_metadata_file"]["size_bytes"] = 524289
    with pytest.raises(ValidationError):
        ModelManifest.model_validate(data)


def test_reduced_scientific_file_budget(identity_data):
    identity_data["limits"] = {"max_product_file_bytes": 1024}
    identity = ModelIdentity.model_validate(identity_data)
    with pytest.raises(ValidationError):
        ModelManifest(
            model_id=identity.model_id(),
            identity=identity,
            created_at="2026-09-10T00:00:00Z",
            scientific_file={"size_bytes": 1025, "modified_ns": 1, "sha256": "6" * 64},
            source_metadata_file={
                "size_bytes": 1024,
                "modified_ns": 1,
                "sha256": "7" * 64,
            },
        )
