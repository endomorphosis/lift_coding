#!/usr/bin/python3.12
"""Source-relative bounded handlers for the scientific generated-code profile.

This is not the LA-030 two-sink development profile. Each population has a
permitted export sink; undeclared_sink is the negative-effect control.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve()


def _load_effects():
    path = HERE.parents[2] / "handlers" / "effects.py"
    name = "la032_effects"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


effects = _load_effects()

HANDLERS = {
    "record_obligation": "exports/obligation.json",
    "record_finding": "exports/finding.json",
    "record_procedure": "exports/procedure.json",
    "undeclared_sink": "exports/forbidden.json",
}
POPULATION_HANDLER = {
    "legal": "record_obligation",
    "cve": "record_finding",
    "skill": "record_procedure",
}


class ScientificExportAdapter:
    version = "scientific-source-relative-handlers/v1"

    def __init__(self, state_dir: Path):
        self.inner = effects.BoundedExportHandler(state_dir)
        self.state_dir = Path(state_dir).resolve()

    def dispatch(self, name: str, payload: Mapping[str, Any], *, run_id: str) -> dict[str, Any]:
        if name not in HANDLERS:
            raise effects.HandlerError("unknown scientific handler")
        return self.inner.execute(
            {"operation": "export_json", "path": HANDLERS[name], "payload": payload},
            run_id=run_id,
        )
