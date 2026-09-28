"""Read-only pressure-depth report; explicit reference evidence and assumptions."""

import argparse
import json
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from backend.app.ingestion.registry import PROJECT_ROOT
from backend.app.processing.depth import convert_pressures, pressure_input
from backend.app.schemas.depth import (
    DepthCollectionReference,
    DepthRequest,
    serialize_depth_report,
)
from backend.app.storage.observations import (
    MAX_COLLECTION_BYTES,
    ObservationStore,
    observation_id,
)
from backend.app.storage.product_common import ProductError, contained, describe_file


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--reference-evidence", required=True)
    parser.add_argument(
        "--assume-zero-geopotential", action="store_true", required=True
    )
    args = parser.parse_args(argv)
    try:
        collection_id = observation_id(args.collection_id)
        path = contained(
            PROJECT_ROOT, f"data/observations/{collection_id}/collection.json"
        )
        before = describe_file(path, MAX_COLLECTION_BYTES)
        collection = ObservationStore(PROJECT_ROOT).collection(collection_id)
        info = collection.variables["PRES"]
        units = (
            info.units
            if collection.selection.value_mode == "raw"
            else info.adjusted_units
        )
        if units not in {"dbar", "decibar", "decibars"}:
            raise ProductError(
                "unsupported_pressure_units", "Sea pressure in dbar is required."
            )
        report = convert_pressures(
            DepthRequest(
                pressure_units="dbar",
                pressure_reference="sea_pressure_zero_at_surface",
                reference_evidence=args.reference_evidence,
                assumptions="zero_dynamic_height_zero_surface_geopotential",
                source_collection=DepthCollectionReference(
                    collection_id=collection_id,
                    collection_sha256=before.sha256,
                    data_mode=collection.data_mode,
                ),
                samples=tuple(pressure_input(sample) for sample in collection.samples),
            )
        )
        if describe_file(path, MAX_COLLECTION_BYTES) != before:
            raise ProductError("observations_changed", "Source observations changed.")
        sys.stdout.write(serialize_depth_report(report).decode("utf-8"))
        return 0
    except ProductError as error:
        code = error.code
    except (ValidationError, ValueError, TypeError):
        code = "invalid_depth_request"
    print(
        json.dumps(
            {"error": {"code": code, "message": "Depth report was not produced."}}
        ),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
