"""Safe executor for allowlisted CLI command templates."""

import os
import shutil
import subprocess
import time

from handsfree.cli.fixtures import load_cli_fixture
from handsfree.cli.models import CLIResult
from handsfree.cli.policy import get_command_spec


class CLIExecutor:
    """Execute GitHub CLI commands through a narrow allowlist."""

    def __init__(self) -> None:
        self.timeout_seconds = int(os.getenv("HANDSFREE_CLI_TIMEOUT_SECONDS", "10"))
        self.max_output_bytes = int(os.getenv("HANDSFREE_CLI_MAX_OUTPUT_BYTES", "20000"))

    def is_enabled(self) -> bool:
        """Return whether CLI-backed flows are explicitly enabled."""
        return os.getenv("HANDSFREE_GH_CLI_ENABLED", "false").lower() == "true"

    def fixture_mode(self) -> bool:
        """Return whether fixture mode is enabled."""
        return os.getenv("HANDSFREE_CLI_FIXTURE_MODE", "false").lower() == "true"

    def execute(self, command_id: str, fixture_group: str, **kwargs: object) -> CLIResult:
        """Execute an allowlisted command or replay a fixture."""
        spec = get_command_spec(command_id, **kwargs)

        if self.fixture_mode():
            return self._load_fixture_result(spec, fixture_group)

        if shutil.which(spec.argv[0]) is None:
            return self._load_fixture_result(spec, fixture_group, source="fixture_missing_binary")

        started = time.monotonic()
        try:
            completed = subprocess.run(
                spec.argv,
                capture_output=True,
                text=True,
                timeout=min(spec.timeout_seconds, self.timeout_seconds),
                check=False,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError):
            return self._load_fixture_result(spec, fixture_group, source="fixture_cli_error")

        duration_ms = int((time.monotonic() - started) * 1000)
        stdout = completed.stdout[: self.max_output_bytes]
        stderr = completed.stderr[: self.max_output_bytes]
        return CLIResult(
            ok=completed.returncode == 0,
            stdout=stdout,
            stderr=stderr,
            exit_code=completed.returncode,
            duration_ms=duration_ms,
            command_id=spec.command_id,
            source="cli_live",
            trace={
                "tool_family": spec.tool_family,
                "argv": spec.argv,
                "parser": spec.parser,
            },
        )

    def _load_fixture_result(
        self,
        spec,
        fixture_group: str,
        source: str = "fixture",
    ) -> CLIResult:
        fixture = load_cli_fixture([fixture_group], spec.fixture_name)
        return CLIResult(
            ok=fixture.get("ok", True),
            stdout=fixture.get("stdout", ""),
            stderr=fixture.get("stderr", ""),
            exit_code=fixture.get("exit_code", 0),
            duration_ms=fixture.get("duration_ms", 0),
            command_id=spec.command_id,
            source=source,
            trace={
                "tool_family": spec.tool_family,
                "fixture_name": spec.fixture_name,
                "parser": spec.parser,
            },
        )
