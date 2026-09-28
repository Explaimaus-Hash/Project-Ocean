"""Validate process-only developer settings without provider credentials."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.config import Settings


@pytest.fixture(autouse=True)
def isolate_product_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OCEAN_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("OCEAN_REQUIRED_PRODUCT_IDS", raising=False)


def test_docs_are_enabled_by_default() -> None:
    assert Settings().docs_enabled is True


@pytest.mark.parametrize("value, expected", [("true", True), ("false", False)])
def test_process_environment_controls_docs(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("OCEAN_DOCS_ENABLED", value)
    assert Settings().docs_enabled is expected


def test_invalid_docs_setting_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCEAN_DOCS_ENABLED", "not-a-boolean")
    with pytest.raises(ValidationError):
        Settings()


def test_dotenv_is_not_loaded_implicitly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text("OCEAN_DOCS_ENABLED=false\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert Settings().docs_enabled is True


def test_explicit_settings_take_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCEAN_DOCS_ENABLED", "false")
    assert Settings(docs_enabled=True).docs_enabled is True


def test_product_settings_defaults_are_absolute_and_unconfigured() -> None:
    settings = Settings()
    assert settings.project_root.is_absolute()
    assert settings.required_product_ids == []


def test_product_settings_read_json_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OCEAN_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "OCEAN_REQUIRED_PRODUCT_IDS", '["ocean_start", "another_subset"]'
    )
    settings = Settings()
    assert settings.project_root == tmp_path
    assert settings.required_product_ids == ["ocean_start", "another_subset"]


@pytest.mark.parametrize(
    "value",
    [["duplicate", "duplicate"], ["../secret"], ["Bad"], ["x" * 97]],
)
def test_invalid_required_product_identifiers_are_rejected(value: list[str]) -> None:
    with pytest.raises(ValidationError):
        Settings(required_product_ids=value)


def test_too_many_required_products_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(required_product_ids=[f"p_{index}" for index in range(17)])


def test_relative_project_root_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(project_root=Path("relative"))
