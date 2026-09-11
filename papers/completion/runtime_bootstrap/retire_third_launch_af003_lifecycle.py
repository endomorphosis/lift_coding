"""Retire the exact AF-003 preparing claim left by the stopped third launch."""
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


def main():
    audit_path = Path(__file__).with_name("third_launch.json")
    assert hashlib.sha256(audit_path.read_bytes()).hexdigest() == "75bf1e65adc9b2c53f39b8b1758a6a35e97c831ed6aa0c9e41dcc3750fca776c"
    audit = C.read(audit_path)
    repo = ROOT / ".worktrees/vericodegen-autoformalization-2026"
    store = WorktreeLifecycleStore(repo_root=repo)
    cid = "baguqeeraolwa4g56lfoekzpgkxgmgir2257ktucrotfa35nlesrfgvki62ta"
    record = store.load_task_attempt(canonical_task_cid=cid, task_id="AF-003", attempt=1)
    assert record.record_id == "baguqeeraig6tstwaidrb73gsifi4lp4r6kt7wosskjglaeasy4ibntcgpcpa"
    assert record.fence == 1 and record.lease_id == "06ebbebf1f957e6f56cdceab66fcc87d17f29f59"
    assert record.state.value == "preparing" and record.owner.pid == 4057439 and record.owner.start_time_ticks == 55192911
    assert record.owner.parent_pid == audit["campaign"]["lanes"]["autoformalization"]["supervisor"]["pid"]
    assert record.owner.boot_id == audit["campaign"]["controller"]["boot_id"]
    workspace = Path(record.workspace_path)
    assert not workspace.exists() and not workspace.is_symlink()
    assert "worktree " + str(workspace) + "\n" not in subprocess.check_output(["git", "worktree", "list", "--porcelain"], cwd=repo, text=True)
    state_dir = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026/autoformalization/state/paper_autoformalization_database_portal_attempts/d0b1549ed28eb90223eb395b"
    expected = dict(expected_record_id=record.record_id, expected_fence=1, expected_lease_id=record.lease_id,
                    expected_task_id="AF-003", expected_canonical_task_cid=cid, expected_attempt=1,
                    expected_branch="implementation/af-003-72ec0e1bbe59-attempt-1-1789142463",
                    expected_merge_target="agent/vericodegen-2026-autoformalization", expected_repo_root=str(repo),
                    expected_state_dir=str(state_dir))
    store.require_exact_dead_owner(workspace, **expected)
    paths = [store.workspace_path_for(workspace), store.task_index_path_for(canonical_task_cid=cid, task_id="AF-003", attempt=1)]
    report = {"schema": "paper-exact-dead-owner-lifecycle-retirement/v1", "started_at": C.now(),
              "task_id": "AF-003", "before": record.to_dict(), "workspace_absent": True,
              "record_backups": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "payload": C.read(p)} for p in paths],
              "native_api": "WorktreeLifecycleStore.finalize_exact_dead_owner", "provider_invoked": False}
    target = Path(__file__).with_name("third_launch_af003_lifecycle_retirement.json")
    C.write(target, report)
    terminal = store.finalize_exact_dead_owner(workspace, expected_owner=record.owner,
        reason="audited_third_launch_stopped_before_provider_with_absent_workspace", **expected)
    report.update(terminal=terminal.to_dict(), success=True, finished_at=C.now())
    C.write(target, report)
    print("AF-003 exact dead-owner preparing claim retired")


if __name__ == "__main__":
    main()
