"""Package the exact six frozen stage files without earlier dirty overlays."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

STAGE = Path(__file__).resolve().parent
baseline = json.loads((STAGE / "beginning-source-pins.json").read_text())
checkout = Path(baseline["checkout"])
before_pins = {row["path"]: row for row in baseline["files"]}
validation = json.loads((STAGE / "final-focused-validation.json").read_text())
assert validation["all_selected_cases_passed"]
pins = validation["current_source_checks"]
assert len(pins) == len({row["path"] for row in pins}) == 6
assert {row["path"] for row in pins if row["path"] in before_pins} == {
    "benchmarks/agent_supervisor/container_coding/terminal_context_audit.py",
    "benchmarks/agent_supervisor/container_coding/terminal_container_supervisor.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/reviewed_source_nomination_context.py"}
chunks, files, current = [], [], {}
with tempfile.TemporaryDirectory(prefix="patch-check-", dir=STAGE) as temp:
    scratch = Path(temp)
    for row in pins:
        name = row["path"]
        raw = (checkout / name).read_bytes()
        assert len(raw) == row["bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
        compile(raw, name, "exec")
        old = (STAGE / "baseline" / name).read_bytes() if name in before_pins else b""
        if name in before_pins:
            assert len(old) == before_pins[name]["bytes"] and hashlib.sha256(old).hexdigest() == before_pins[name]["sha256"]
            target = scratch / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(old)
        chunks.append("".join(difflib.unified_diff(old.decode().splitlines(keepends=True), raw.decode().splitlines(keepends=True),
            fromfile="a/" + name if name in before_pins else "/dev/null", tofile="b/" + name)))
        current[name] = raw
        files.append({"path": name, "absolute_path": str(checkout / name), "bytes": len(raw), "sha256": row["sha256"],
            "absent_before": name not in before_pins, "before_bytes": len(old) if name in before_pins else None,
            "before_sha256": hashlib.sha256(old).hexdigest() if name in before_pins else None})
    patch = "".join(chunks).encode()
    patch_path = STAGE / "changes.patch"
    patch_path.write_bytes(patch)
    subprocess.run(["git", "init", "--quiet", str(scratch)], check=True, capture_output=True)
    subprocess.run(["git", "apply", "--check", str(patch_path)], cwd=scratch, check=True, capture_output=True)
    subprocess.run(["git", "apply", str(patch_path)], cwd=scratch, check=True, capture_output=True)
    assert all((scratch / name).read_bytes() == raw == (checkout / name).read_bytes() for name, raw in current.items())
result = {"schema": "reviewed-source-audit-source-manifest@1", "checkout": str(checkout), "files": files,
    "patch_path": str(patch_path), "patch_bytes": len(patch), "patch_sha256": hashlib.sha256(patch).hexdigest(),
    "patch_basis": "Three existing deltas against exact captured bytes; three new files. Earlier dirty overlays excluded.",
    "patch_applies_cleanly_to_captured_baseline": True, "applied_changed_bytes_match_checkout": True,
    "all_six_python_syntax_checked": True, "original_dirty_checkout_or_git_index_mutated": False,
    "remote_publication_performed": False, "whole_repository_test_pass_claimed": False}
(STAGE / "source-manifest.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(json.dumps({"files": len(files), "patch_bytes": len(patch), "patch_sha256": result["patch_sha256"], "clean_apply": True}))
