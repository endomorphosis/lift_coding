from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def test_existing_main_checkout_guardrail_does_not_churn_fingerprint(tmp_path):
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        record_reconciliation_guardrail_findings,
    )

    board = tmp_path / "launch.todo.md"
    discovery_dir = tmp_path / "discovery"
    discovery_dir.mkdir()
    discovery_path = discovery_dir / "2026-06-26-vai-999-reconciliation-old.md"
    discovery_path.write_text("old dirty-checkout evidence\n", encoding="utf-8")
    board.write_text(
        "\n".join(
            (
                "# Launch board",
                "",
                "## VAI-999 Resolve dirty main checkout blocking 4 worktree merges",
                "",
                "- Status: todo",
                "- Completion: manual",
                "- Priority: P1",
                "- Track: ops",
                "- Fingerprint: old-fingerprint",
                "- Dedupe key: reconciliation_guardrail:main_checkout_dirty",
                "- Depends on:",
                "- Outputs: discovery, launch.todo.md",
                f"- Validation: test -f {shlex.quote(str(discovery_path))}",
                "- Acceptance: Existing dirty-checkout guardrail.",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    strategy_path = tmp_path / "strategy.json"
    strategy_path.write_text(json.dumps({}), encoding="utf-8")
    before_board = board.read_text(encoding="utf-8")
    before_discovery = discovery_path.read_text(encoding="utf-8")

    findings = record_reconciliation_guardrail_findings(
        todo_path=board,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        reconciliation_result={
            "attempted": True,
            "main_checkout_dirty": True,
            "candidate_count": 9,
            "main_status_short": [" M src/launch_surface.py"],
            "main_dirty_evidence": {
                "status_short": [" M src/launch_surface.py"],
                "status_paths": ["src/launch_surface.py"],
            },
            "candidates": [
                {
                    "branch": "implementation/vai-512-attempt-1-submodule-swissknife",
                    "path": str(tmp_path / "worktrees" / "vai-512"),
                    "target_ref": "main",
                }
            ],
        },
        cleanup_result={},
        task_prefix="VAI-",
        repo_root=tmp_path,
    )

    assert findings == []
    assert board.read_text(encoding="utf-8") == before_board
    assert discovery_path.read_text(encoding="utf-8") == before_discovery


def test_existing_preflight_guardrail_does_not_churn_rescue_branch_fingerprint(tmp_path):
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        record_reconciliation_guardrail_findings,
    )

    board = tmp_path / "hao.todo.md"
    discovery_dir = tmp_path / "discovery"
    discovery_dir.mkdir()
    discovery_path = discovery_dir / "2026-06-26-hao-311-reconciliation-old.md"
    discovery_path.write_text("old preflight-conflict evidence\n", encoding="utf-8")
    board.write_text(
        "\n".join(
            (
                "# HAO board",
                "",
                "## HAO-311 Resolve 8 preflight-conflicting backlogged worktree merges",
                "",
                "- Status: todo",
                "- Completion: manual",
                "- Priority: P1",
                "- Track: ops",
                "- Fingerprint: old-preflight-fingerprint",
                "- Dedupe key: reconciliation_guardrail:preflight_merge_conflict",
                "- Depends on:",
                "- Outputs: discovery, hao.todo.md",
                f"- Validation: test -f {shlex.quote(str(discovery_path))}",
                "- Acceptance: Existing preflight guardrail.",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    strategy_path = tmp_path / "strategy.json"
    strategy_path.write_text(json.dumps({}), encoding="utf-8")
    before_board = board.read_text(encoding="utf-8")
    before_discovery = discovery_path.read_text(encoding="utf-8")

    findings = record_reconciliation_guardrail_findings(
        todo_path=board,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        reconciliation_result={
            "attempted": True,
            "processed": [
                {
                    "branch": "rescue/worktree/rescue-worktree--newhash",
                    "path": str(tmp_path / "worktrees" / "hao-680"),
                    "preflight_result": {
                        "mergeable": False,
                        "conflict_paths": [
                            "hallucinate_app",
                            "implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md",
                        ],
                    },
                }
            ],
        },
        cleanup_result={},
        task_prefix="HAO-",
        repo_root=tmp_path,
    )

    assert findings == []
    assert board.read_text(encoding="utf-8") == before_board
    assert discovery_path.read_text(encoding="utf-8") == before_discovery


def test_reconciliation_guardrail_todo_conflict_repair_keeps_main_variant(tmp_path):
    from ipfs_accelerate_py.agent_supervisor.merge_conflict_repair import (
        resolve_reconciliation_guardrail_todo_conflicts,
    )

    repo = tmp_path / "repo"
    board = repo / "implementation_plan" / "docs" / "launch.todo.md"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    board.parent.mkdir(parents=True)
    board.write_text(
        "\n".join(
            (
                "# Launch board",
                "",
                "## VAI-200 Resolve dirty main checkout blocking 4 worktree merges",
                "",
                "- Status: completed",
                "- Completion: manual",
                "- Priority: P1",
                "- Track: ops",
                "- Fingerprint: base-fingerprint",
                "- Dedupe key: reconciliation_guardrail:main_checkout_dirty",
                "- Depends on:",
                "- Outputs: data/virtual_ai_os/discovery, implementation_plan/docs/launch.todo.md",
                "- Validation: test -f data/virtual_ai_os/discovery/guardrail.md",
                "- Acceptance: Reconciliation guardrail filed this because 4 branch or worktree cleanup candidates are blocked by main_checkout_dirty.",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _git(repo, "add", "implementation_plan/docs/launch.todo.md")
    _git(repo, "commit", "-m", "base board")

    _git(repo, "checkout", "-b", "branch-variant")
    board.write_text(
        board.read_text(encoding="utf-8")
        .replace("blocking 4 worktree merges", "blocking 6 worktree merges")
        .replace("base-fingerprint", "branch-fingerprint")
        .replace("because 4 branch", "because 6 branch"),
        encoding="utf-8",
    )
    _git(repo, "commit", "-am", "branch guardrail variant")

    _git(repo, "checkout", "main")
    board.write_text(
        board.read_text(encoding="utf-8")
        .replace("blocking 4 worktree merges", "blocking 8 worktree merges")
        .replace("base-fingerprint", "main-fingerprint")
        .replace("because 4 branch", "because 8 branch"),
        encoding="utf-8",
    )
    _git(repo, "commit", "-am", "main guardrail variant")
    merge = subprocess.run(
        ["git", "merge", "--no-ff", "--no-edit", "branch-variant"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert merge.returncode != 0
    assert "UU implementation_plan/docs/launch.todo.md" in _git(repo, "status", "--porcelain")

    repairs = resolve_reconciliation_guardrail_todo_conflicts(repo_root=repo)

    assert repairs[0]["resolved"] is True
    assert "UU implementation_plan/docs/launch.todo.md" not in _git(repo, "status", "--porcelain")
    source = board.read_text(encoding="utf-8")
    assert "blocking 8 worktree merges" in source
    assert "main-fingerprint" in source
    assert "branch-fingerprint" not in source
    assert "<<<<<<<" not in source


def test_launch_validation_retry_repair_preserves_playwright_gate(tmp_path):
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        record_retry_budget_findings,
    )

    board = tmp_path / "mgw.todo.md"
    events = tmp_path / "events.jsonl"
    strategy = tmp_path / "strategy.json"
    discovery = tmp_path / "discovery"
    failed_command = "PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py -q"
    board.write_text(
        "\n".join(
            (
                "# MGW",
                "",
                "## MGW-536 Close virtual AI OS launch objective gap",
                "- Status: todo",
                "- Completion: manual",
                "- Priority: P0",
                "- Track: launch",
                "- Depends on:",
                "- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
                f"- Validation: {failed_command}",
                "- Acceptance: Objective scan filed this gap for VAIOS-G729 and requires the launch Playwright validation gate.",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    events.write_text(
        "\n".join(
            json.dumps(
                {
                    "type": "implementation_finished",
                    "task_id": "MGW-536",
                    "attempt": attempt,
                    "validation_result": {
                        "attempted": True,
                        "passed": False,
                        "failed_command": failed_command,
                    },
                }
            )
            for attempt in (1, 2)
        )
        + "\n",
        encoding="utf-8",
    )
    strategy.write_text(json.dumps({}), encoding="utf-8")

    findings = record_retry_budget_findings(
        todo_path=board,
        events_path=events,
        strategy_path=strategy,
        discovery_dir=discovery,
        task_header_prefix_value="## MGW-",
        task_prefix="MGW-",
        validation_retry_budget=2,
        merge_retry_budget=0,
        implementation_retry_budget=0,
    )

    updated_board = board.read_text(encoding="utf-8")
    updated_strategy = json.loads(strategy.read_text(encoding="utf-8"))
    assert findings[0]["source_task_id"] == "MGW-536"
    assert findings[0]["launch_playwright_validation_gate"] is True
    assert findings[0]["launch_playwright_validation_command"] == (
        "(test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && "
        "(test ! -f hallucinate_app/package.json || "
        "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
    )
    assert "launch Playwright validation gate" in updated_board
    assert "npm --prefix swissknife run test:e2e:meta-glasses" in updated_board
    assert "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts" in updated_board
    assert updated_strategy["blocked_tasks"] == ["MGW-536"]
