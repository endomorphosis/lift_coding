"""Package only this stage's explicit source deltas against captured bytes."""
from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

STAGE = Path(__file__).resolve().parent
BASELINE = json.loads((STAGE / "beginning-source-pins.json").read_text())
CHECKOUT = Path(BASELINE["checkout"])
FILES = {
    "ipfs_accelerate_py/agent_supervisor/runtime/code_source_inspection.py": "3af0075290cf480acd423a6461d56f861418737c8b810ab22452f0290a9f7643",
    "ipfs_accelerate_py/agent_supervisor/runtime/intent_source_inspection.py": "089a5df3161b177ea0873f023d0595140357e429e9fa508a8c7c09ea4b567372",
    "ipfs_accelerate_py/agent_supervisor/runtime/intent_source_nomination.py": "38c55e9fd72e32533644e04f16098c6a70227eb848125ca9646b129b4a0d326c",
    "ipfs_accelerate_py/agent_supervisor/runtime/task_context_bundle.py": "89b73940bd8d4a2e0ae2dce17800beac48346a2e9e9a337e8ebb93801bfde2f9",
    "benchmarks/agent_supervisor/container_coding/terminal_indexed_preparation.py": "6360c20d9b86b8224b0c521d06b4dde4f35b37eecfc77551b6d7d223d79c83c7",
    "test/api/test_intent_source_nomination.py": "9aacf5cab0f8cfc1b7990beecc3275d7b1c9f79d5f590cc09f82bdd23f037c64",
    "test/api/test_intent_source_inspection.py": "416227eb3e8ad56512e16703e5ba91ff9b0d92fd481ea56b94497a096ebbf8ab",
    "benchmarks/agent_supervisor/container_coding/test_terminal_source_nomination.py": "ed416d7e1fffeb4e07a6265686d7f9d1713b35180993c38db593770c79a2b23b",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    old_pins = {entry["path"]: entry for entry in BASELINE["files"]}
    chunks = []
    manifest = []
    current = {}
    with tempfile.TemporaryDirectory(prefix="source-patch-check-", dir=STAGE) as temp:
        scratch = Path(temp)
        for name, expected in FILES.items():
            raw = (CHECKOUT / name).read_bytes()
            assert digest(raw) == expected, (name, "frozen source changed")
            compile(raw, name, "exec")
            current[name] = raw
            old = (STAGE / "baseline" / name).read_bytes() if name in old_pins else b""
            if name in old_pins:
                assert digest(old) == old_pins[name]["sha256"]
                assert len(old) == old_pins[name]["bytes"]
                destination = scratch / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(old)
            diff = "".join(difflib.unified_diff(
                old.decode("utf-8").splitlines(keepends=True),
                raw.decode("utf-8").splitlines(keepends=True),
                fromfile=f"a/{name}" if name in old_pins else "/dev/null",
                tofile=f"b/{name}",
            ))
            assert diff
            chunks.append(diff)
            manifest.append({
                "path": name, "absolute_path": str(CHECKOUT / name),
                "bytes": len(raw), "sha256": expected,
                "absent_before": name not in old_pins,
                "before_sha256": digest(old) if name in old_pins else None,
                "before_bytes": len(old) if name in old_pins else None,
            })
        patch = "".join(chunks).encode("utf-8")
        patch_path = STAGE / "changes.patch"
        patch_path.write_bytes(patch)
        subprocess.run(["git", "init", "--quiet", str(scratch)], check=True, capture_output=True)
        subprocess.run(["git", "apply", "--check", str(patch_path)], cwd=scratch, check=True, capture_output=True)
        subprocess.run(["git", "apply", str(patch_path)], cwd=scratch, check=True, capture_output=True)
        assert all((scratch / name).read_bytes() == raw for name, raw in current.items())
        assert all((CHECKOUT / name).read_bytes() == raw for name, raw in current.items())
    result = {
        "schema": "intent-source-nomination-source-manifest@1",
        "checkout": str(CHECKOUT), "files": manifest,
        "patch_path": str(patch_path), "patch_bytes": len(patch), "patch_sha256": digest(patch),
        "patch_basis": "Three deltas against exact stage-captured bytes and five new files; earlier dirty overlays excluded.",
        "patch_applies_cleanly_to_captured_baseline": True,
        "applied_changed_bytes_match_checkout": True,
        "all_eight_python_syntax_checked": True,
        "original_dirty_checkout_or_git_index_mutated": False,
        "runtime_archive_built_or_installed": False,
        "automatic_worker_consumption_qualified": False,
        "signed_planning_inputs_modified": False,
        "remote_publication_performed": False,
        "whole_repository_test_pass_claimed": False,
    }
    (STAGE / "source-manifest.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"files": len(manifest), "patch_bytes": len(patch), "patch_sha256": digest(patch), "applies_cleanly": True}))


if __name__ == "__main__":
    main()
