"""Explicit local QC/normalization; never acquisition, startup, or comparison."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from backend.app.ingestion.registry import (
    PROJECT_ROOT,
    RegistryError,
    find_dataset,
    load_registry,
    resolve_local_input,
)
from backend.app.schemas.observations import ObservationRequest
from backend.app.storage.observations import ObservationStore
from backend.app.storage.product_common import ProductError, contained, read_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", required=True, help="Registered observation dataset ID"
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input", help="Relative NetCDF path below data/raw/")
    inputs.add_argument(
        "--acquisition", help="Completed acquisition ID, with verified provenance"
    )
    parser.add_argument(
        "--request", required=True, help="Relative JSON selection file in this project"
    )
    parser.add_argument(
        "--synthetic", action="store_true", help="Explicitly label fixture/demo data"
    )
    args = parser.parse_args(argv)
    try:
        registry = load_registry(PROJECT_ROOT / "config" / "data_sources.yaml")
        definition = find_dataset(registry, args.dataset)
        if definition.role != "observation" or definition.source_id not in {
            "argo",
            "ifremer_glider",
        }:
            raise ProductError(
                "unsupported_source",
                "Select a registered Argo or IFREMER observation source.",
                422,
            )
        acquisition = None
        client_processing = "local_operator_input_client_processing_unknown"
        data_mode = "synthetic" if args.synthetic else "real"
        if args.acquisition:
            from backend.app.ingestion.acquisition import read_acquisition

            acquisition = read_acquisition(PROJECT_ROOT, args.acquisition)
            if (
                acquisition.dataset_id != definition.dataset_id
                or acquisition.source_id != definition.source_id
            ):
                raise ProductError(
                    "source_mismatch", "Acquisition and selected source differ.", 422
                )
            path = contained(
                PROJECT_ROOT,
                f"data/raw/acquisitions/{acquisition.acquisition_id}/input.nc",
            )
            if acquisition.data_mode == "synthetic":
                data_mode = "synthetic"
            if acquisition.request.provider == "argo":
                if (
                    acquisition.client != "argopy"
                    or "mode=expert" not in acquisition.client_processing
                    or "no standard/research QC/data-mode filter"
                    not in acquisition.client_processing
                    or acquisition.provider_file is None
                ):
                    raise ProductError(
                        "unsupported_provenance",
                        "Argo client-processing provenance is unsupported.",
                    )
                client_processing = "argopy_expert_no_qc_filter"
        else:
            path = resolve_local_input(PROJECT_ROOT, args.input)
        if Path(args.request).is_absolute():
            raise ProductError(
                "invalid_request", "Use a project-relative selection file.", 422
            )
        request_path = contained(PROJECT_ROOT, args.request)
        request = ObservationRequest.model_validate(read_json(request_path, 16384))
        # Scientific dependencies load only after bounded request/path validation.
        from backend.app.processing.observations import normalize_observations

        collection = normalize_observations(
            path,
            request,
            source_id=definition.source_id,
            dataset_id=definition.dataset_id,
            data_mode=data_mode,
            client_processing=client_processing,
        )
        if acquisition is not None and collection.input_file != acquisition.input_file:
            raise ProductError(
                "input_changed", "Acquired input differs from recorded provenance."
            )
        metadata = ObservationStore(PROJECT_ROOT).publish(collection)
        print(
            json.dumps(
                {"status": "prepared", "metadata": metadata}, allow_nan=False, indent=2
            )
        )
        return 0
    except (ValidationError, RegistryError, ValueError, OSError):
        error = ProductError(
            "invalid_request", "Observation source, path or selection is invalid.", 422
        )
    except ProductError as caught:
        error = caught
    print(
        json.dumps(
            {
                "schema_version": 1,
                "error": {"code": error.code, "message": error.message},
            }
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
