"""Deterministic local settings for offline backend tests."""

import pytest


@pytest.fixture(autouse=True)
def clear_docs_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the caller's developer-docs preference out of test defaults."""
    monkeypatch.delenv("OCEAN_DOCS_ENABLED", raising=False)
