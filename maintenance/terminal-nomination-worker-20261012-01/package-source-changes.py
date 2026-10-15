"""Package the exact eleven frozen stage files without earlier dirty overlays."""
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
worker = json.loads((STAGE / "worker-context-validation.json").read_text())
entry = json.loads((STAGE / "entrypoint-validation-02.json").read_text())
export = json.loads((STAGE / "exporter-validation.json").read_text())
assert worker["all_final_passed"] and entry["qualified"] and export["qualified"]
pins = worker["sources"] + entry["owned_sources"] + [export["producer_source"], export["test_source"]]
assert len(pins) == len({row["path"] for row in pins}) == 11
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
result = {"schema": "reviewed-source-worker-source-manifest@1", "checkout": str(checkout), "files": files,
    "patch_path": str(patch_path), "patch_bytes": len(patch), "patch_sha256": hashlib.sha256(patch).hexdigest(),
    "patch_basis": "Six existing deltas against exact captured bytes; five new files. Earlier dirty overlays excluded.",
    "patch_applies_cleanly_to_captured_baseline": True, "applied_changed_bytes_match_checkout": True,
    "all_eleven_python_syntax_checked": True, "original_dirty_checkout_or_git_index_mutated": False,
    "remote_publication_performed": False, "whole_repository_test_pass_claimed": False}
(STAGE / "source-manifest.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
print(json.dumps({"files": len(files), "patch_bytes": len(patch), "patch_sha256": result["patch_sha256"], "clean_apply": True}))
