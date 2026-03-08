"""Fixture loading for CLI integrations."""

import json
from pathlib import Path
from typing import Any


def get_cli_fixtures_dir() -> Path:
    """Return the default CLI fixtures directory."""
    return Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "cli"


def load_cli_fixture(path_parts: list[str], fixture_name: str) -> dict[str, Any]:
    """Load a JSON CLI fixture."""
    fixture_path = get_cli_fixtures_dir().joinpath(*path_parts, fixture_name)
    with fixture_path.open() as handle:
        return json.load(handle)
