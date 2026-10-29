#!/usr/bin/env python3
"""Record actual plan/native validation and watchdog test evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def main() -> int:
    import validate_plan
    validation = validate_plan.validate(native_root=Path("/home/barberb/ipfs_accelerate_py"))
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_*.py", "-v"]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        sys.stderr.write(completed.stderr)
        return completed.returncode
    hashes = {path.relative_to(HERE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(HERE.rglob("*")) if path.is_file() and path.name != "validation_results.json" and "__pycache__" not in path.parts and ".runtime" not in path.parts}
    result = {"schema": "worldwide-legal-search.validation-evidence@1", "recorded_at": datetime.now(timezone.utc).isoformat(), "plan_validation": validation,
              "watchdog_tests": {"argv": command, "exit_code": completed.returncode, "output": completed.stdout + completed.stderr},
              "package_sha256": hashes, "live_campaign_started": False, "native_adapter_implemented": False, "website_implementation_validated": False,
              "limitations": ["Native validation checks real parser/profile/policy compatibility, not live execution", "Watchdog tests exercise the host loop and protocol; native lifecycle/rescue wiring is an explicit first-milestone task", "No provider calls, full source inventory, website implementation, browser benchmark or deployment performed"]}
    (HERE / "validation_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"plan_tasks": validation["tasks"], "goal_nodes": validation["goals"], "native_checked": validation["native_checked"], "unit_tests_exit_code": completed.returncode, "evidence": str(HERE / "validation_results.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
