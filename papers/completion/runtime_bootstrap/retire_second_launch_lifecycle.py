"""Retire only the three audited, absent-workspace, dead-owner preparing claims."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import materialize_paper_database as M
import paper_supervisor_campaign as C
M._native(ROOT)
from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import WorktreeLifecycleStore

EXPECTED = {
    "autoformalization": ("baguqeera7wi2i3cgnckqpbly4ltm2ieqhecsy3zyql2kse3obraezvi2mb6q", 1398721, 55050334),
    "law_to_action": ("baguqeerat2egz6mpn3enryei6hietpybfm2fhrx5q25b2ggcnodwgahhrwxq", 1398279, 55050315),
    "neurosymbolic_supervision": ("baguqeerau3ioa5wrpissedl4remstetrfeu64bj3s7lgcx6me2fleu35nc3q", 1398668, 55050331),
}


def main():
    audit_path = Path(__file__).with_name("second_launch.json")
    audit_bytes = audit_path.read_bytes()
    assert hashlib.sha256(audit_bytes).hexdigest() == "f0f9f70a6f2bc6f8e968bd18be1fcf46499e2208d846ac9fb0ef5ce606d8358a"
    audit = json.loads(audit_bytes)
    report_path = Path(__file__).with_name("second_launch_lifecycle_retirement.json")
    report = {"schema": "paper-exact-dead-owner-lifecycle-retirement/v1", "started_at": C.now(),
              "native_api": "WorktreeLifecycleStore.finalize_exact_dead_owner", "lanes": {},
              "task_database_mutated": False, "provider_invoked": False}
    plans = []
    for paper, (record_id, pid, ticks) in EXPECTED.items():
        anchor = audit["exact_maintenance_anchors"][paper]
        repo = ROOT / ".worktrees" / ("vericodegen-" + paper + "-2026")
        store = WorktreeLifecycleStore(repo_root=repo)
        record = store.load_task_attempt(canonical_task_cid=anchor["portal_event_task_cid"], task_id=anchor["task_alias"], attempt=1)
        assert record and record.record_id == record_id and record.fence == 1 and record.state.value == "preparing"
        assert record.owner.pid == pid and record.owner.start_time_ticks == ticks
        assert record.owner.parent_pid == audit["processes"][paper + ":supervisor"]["pid"]
        assert record.owner.boot_id == audit["processes"][paper + ":supervisor"]["boot_id"]
        workspace = Path(record.workspace_path)
        assert not workspace.exists() and not workspace.is_symlink()
        assert workspace.is_relative_to(Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026" / paper / "worktrees")
        registered = subprocess.check_output(["git", "worktree", "list", "--porcelain"], cwd=repo, text=True)
        assert "worktree " + str(workspace) + "\n" not in registered
        expected = dict(expected_record_id=record_id, expected_fence=record.fence, expected_lease_id=record.lease_id,
                        expected_task_id=anchor["task_alias"], expected_canonical_task_cid=anchor["portal_event_task_cid"],
                        expected_attempt=1, expected_branch=record.branch,
                        expected_merge_target="agent/vericodegen-2026-" + paper,
                        expected_repo_root=str(repo), expected_state_dir=str(Path(anchor["failure_event_file"]["path"]).parent))
        store.require_exact_dead_owner(workspace, **expected)
        paths = [store.workspace_path_for(workspace), store.task_index_path_for(canonical_task_cid=record.canonical_task_cid, task_id=record.task_id, attempt=record.attempt)]
        report["lanes"][paper] = {"before": record.to_dict(), "workspace_absent": True,
                                  "record_backups": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "payload": json.loads(p.read_text())} for p in paths]}
        plans.append((paper, store, record, expected))
    C.write(report_path, report)
    for paper, store, record, expected in plans:
        terminal = store.finalize_exact_dead_owner(record.workspace_path, expected_owner=record.owner,
                    reason="audited_second_launch_stopped_before_provider_with_absent_workspace", **expected)
        report["lanes"][paper]["terminal"] = terminal.to_dict()
        report["lanes"][paper]["retired_at"] = C.now()
        C.write(report_path, report)
        print(paper, "exact dead-owner lifecycle retired", flush=True)
    report.update(success=True, finished_at=C.now())
    C.write(report_path, report)


if __name__ == "__main__":
    main()
