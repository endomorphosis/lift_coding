"""Reproduce campaign validation import in a fresh native worker checkout."""
from pathlib import Path
from types import SimpleNamespace
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
LANE = ROOT / ".worktrees/vericodegen-neurosymbolic_supervision-2026"
OUTPUT = Path(__file__).with_suffix(".json")
SPEC = importlib.util.spec_from_file_location("materializer_repro", ROOT / "scripts/materialize_paper_database.py")
MAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAT)
MAT._native(ROOT)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon, parse_task_file
from ipfs_accelerate_py.agent_supervisor.todo_daemon.database_portal_bridge import DatabasePortalExecutionBridge
from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import DatabaseTaskSource
from ipfs_accelerate_py.agent_supervisor.validation.project_dependency_preflight import preflight_validation_project_dependencies
from ipfs_accelerate_py.agent_supervisor.validation.validation_commands import validation_command_repository_root


def git(args, cwd):
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def run():
    source_index = hashlib.sha256((ROOT / ".git/index").read_bytes()).hexdigest()
    report = {"schema": "paper-validation-worker-preflight/v1", "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "lane": str(LANE), "parent_commit": git(["rev-parse", "HEAD"], LANE),
              "native_guard_modified": False, "provider_invoked": False, "live_task_rows_modified": False,
              "submodules": [], "cleanup": []}
    paths = ["external/ipfs_accelerate", "external/ipfs_datasets", "external/ipfs_kit"]
    with tempfile.TemporaryDirectory(prefix="vericodegen-validation-worktree-") as tmp:
        folder, child = Path(tmp), Path(tmp) / "worker"
        try:
            MAT.materialize("neurosymbolic_supervision", folder / "control.duckdb", ROOT)
            with DatabaseTaskSource(folder / "control.duckdb", install_schema=False) as source:
                record = source.get_task("NS-001")
                attempt = SimpleNamespace(task_cid=record.task_cid, task_alias=record.task_alias,
                                          attempt_id="preflight-repro", claim_id="preflight-repro")
                projection = DatabasePortalExecutionBridge._render_projection(None, attempt, record)
            projected = folder / "task.md"
            projected.write_text(projection)
            commands = parse_task_file(projected, "NS-")[0].validation
            git(["worktree", "add", "--detach", str(child), report["parent_commit"]], LANE)
            daemon = object.__new__(PortalImplementationDaemon)
            daemon.repo_root, daemon.worktree_submodule_paths = LANE, tuple(paths)
            daemon._record_event = lambda *args, **kwargs: None
            daemon._initialize_worktree_submodules(child, branch_name="", offline_local_only=True, submodule_paths=paths)
            for relative in paths:
                expected = git(["rev-parse", "HEAD:" + relative], child)
                actual = git(["rev-parse", "HEAD"], child / relative)
                assert actual == expected
                report["submodules"].append({"path": relative, "commit": actual, "exact_pin": True})
            report["worktree_common_gitdir"] = git(["rev-parse", "--git-common-dir"], child)
            report["lane_common_gitdir"] = git(["rev-parse", "--git-common-dir"], LANE)
            original = "bash -lc 'python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-001'"
            assert validation_command_repository_root(original) is None
            original_result = preflight_validation_project_dependencies(child, [original])
            assert original_result["passed"] is False
            assert original_result["invalid_commands"][0]["reason"] == "validation_repository_root_is_unsafe"
            assert len(commands) == 1 and validation_command_repository_root(commands[0]) == ""
            corrected_result = preflight_validation_project_dependencies(
                child, commands,
                task_authority={"board_namespace": "vericodegen-2026-neurosymbolic_supervision",
                                "canonical_task_cid": record.task_cid,
                                "declared_outputs": [o["path"] for o in record.outputs]},
            )
            report.update(original_command=original, corrected_commands=commands,
                          original_preflight=original_result, corrected_preflight=corrected_result)
            assert corrected_result["passed"] is True, corrected_result
            report["passed"] = True
        finally:
            for relative in reversed(paths):
                target = child / relative
                if (target / ".git").exists():
                    git(["worktree", "remove", "--force", str(target)], LANE / relative)
                    report["cleanup"].append({"path": relative, "removed": not target.exists()})
            if child.exists():
                git(["worktree", "remove", "--force", str(child)], LANE)
            report["test_worktree_removed"] = not child.exists()
            report["root_index_unchanged"] = hashlib.sha256((ROOT / ".git/index").read_bytes()).hexdigest() == source_index
            OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(OUTPUT), "passed": report["passed"], "provider_invoked": False}))


if __name__ == "__main__":
    run()
