"""Typed models for CLI-backed integrations."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CLIResult:
    """Normalized result for a CLI invocation."""

    ok: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0
    command_id: str = ""
    source: str = "cli_live"
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class CLICommandSpec:
    """Allowlisted CLI command template."""

    command_id: str
    argv: list[str]
    fixture_name: str
    parser: str
    tool_family: str
    timeout_seconds: int = 10
