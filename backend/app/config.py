"""Validated process-environment settings with no implicit file loading."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas.products import Identifier


class Settings(BaseSettings):
    """Configure local prepared products without reading them during startup."""

    model_config = SettingsConfigDict(
        env_prefix="OCEAN_",
        env_file=None,
        extra="ignore",
        frozen=True,
    )

    docs_enabled: bool = True
    project_root: Path = Path(__file__).parents[2]
    required_product_ids: list[Identifier] = Field(default_factory=list, max_length=16)

    @field_validator("project_root")
    @classmethod
    def absolute_project_root(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("Project root must be an absolute path")
        return value

    @field_validator("required_product_ids")
    @classmethod
    def unique_required_products(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Required product identifiers must be unique")
        return value
