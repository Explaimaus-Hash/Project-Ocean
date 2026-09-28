"""Read a bounded, validated source registry without contacting providers."""

from pathlib import Path

from pydantic import ValidationError

from ..schemas.datasets import DatasetDefinition, SourceRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAX_REGISTRY_BYTES = 128 * 1024


class RegistryError(ValueError):
    """Safe operator error that never embeds raw configuration or file paths."""


def load_registry(path: Path | None = None) -> SourceRegistry:
    """Load registry only on an explicit operator request, never at API startup."""
    import yaml

    if path is None:
        path = PROJECT_ROOT / "config" / "data_sources.yaml"
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_REGISTRY_BYTES + 1)
        if len(raw) > MAX_REGISTRY_BYTES:
            raise RegistryError("Registry exceeds the configured size limit")
        content = yaml.safe_load(raw)
        return SourceRegistry.model_validate(content)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, RecursionError):
        raise RegistryError("Registry is unavailable or invalid") from None


def find_dataset(registry: SourceRegistry, dataset_id: str) -> DatasetDefinition:
    """Resolve an explicit identifier without guessing sources or paths."""
    for definition in registry.datasets:
        if definition.dataset_id == dataset_id:
            return definition
    raise RegistryError("Unknown dataset ID")


def resolve_local_input(project_root: Path, relative_path: str) -> Path:
    """Keep reads below the resolved project raw-data root, including symlinks."""
    root = project_root.resolve()
    raw_root = (root / "data" / "raw").resolve()
    candidate = (root / relative_path).resolve()
    if not raw_root.is_relative_to(root) or not candidate.is_relative_to(raw_root):
        raise RegistryError("Local input must stay inside the project raw-data folder")
    return candidate
