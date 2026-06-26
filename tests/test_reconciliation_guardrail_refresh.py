from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))


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
