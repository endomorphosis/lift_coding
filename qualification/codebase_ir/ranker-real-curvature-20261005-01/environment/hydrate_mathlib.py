"""Root-owned, separately bounded dependency hydration; never a proof check."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
COMMIT = "5ed2965256430c3649e86755f9576b54eca72435"


def main():
    destination = ROOT / "mathlib4"
    assert not destination.exists()
    plan = {"schema": "ranker-analytic-mathlib-hydration@1", "kind": "dependency_setup_only",
            "official_repository": "https://github.com/leanprover-community/mathlib4.git",
            "tag": "v4.34.0", "expected_commit": COMMIT,
            "clone_wall_seconds": 120, "capture_bytes": 65536,
            "proof_solver_limits_unchanged": {"wall_seconds": 20, "cpu_seconds": 20,
                                             "output_bytes": 65536, "workspace_bytes": 16777216},
            "native_proof_checks": 0, "fit_calls": 0}
    (ROOT / "clone-request.json").write_text(json.dumps(plan, indent=2) + "\n")
    started = time.monotonic()
    try:
        result = subprocess.run(["git", "clone", "--depth", "1", "--branch", "v4.34.0",
                                 "--single-branch", plan["official_repository"], str(destination)],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        raw = result.stdout
        assert len(raw) <= 65536
        (ROOT / "clone.log").write_bytes(raw)
        plan.update(returncode=result.returncode, elapsed_seconds=time.monotonic() - started)
        assert result.returncode == 0
        commit = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], timeout=10).decode().strip()
        assert commit == COMMIT
        plan.update(actual_commit=commit,
                    lake_manifest_sha256=hashlib.sha256((destination / "lake-manifest.json").read_bytes()).hexdigest(),
                    lean_toolchain=(destination / "lean-toolchain").read_text().strip(), status="pinned_checkout_ready")
    except BaseException as error:
        plan.update(status="failed", error={"type": type(error).__name__, "message": str(error)},
                    elapsed_seconds=time.monotonic() - started)
        raise
    finally:
        (ROOT / "clone-closed.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
