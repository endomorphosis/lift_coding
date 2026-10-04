#!/usr/bin/python3.12 -S
"""Read-only PGIR-211 proposal-envelope preflight."""

from __future__ import annotations

import json

from pgir211_targeted_adopt import (
    BASELINE,
    BRANCH,
    CANDIDATE,
    TASK_CID,
    TASK_ID,
    TASK_KEY,
    WORKTREE,
    build_objects,
    git,
    load_exact_task,
    require,
)


def main() -> int:
    _, _, daemon = build_objects()
    task = load_exact_task(daemon)
    require(task.task_id == TASK_ID, "task ID drifted")
    require(task.canonical_task_key == TASK_KEY, "task key changed")
    require(task.canonical_task_cid == TASK_CID, "task CID changed")
    require(git("rev-parse", "HEAD^{commit}", cwd=WORKTREE) == CANDIDATE, "candidate drifted")
    require(git("status", "--porcelain", cwd=WORKTREE) == "", "candidate is dirty")
    diagnostics: dict[str, object] = {}
    result = daemon._validate_implementation_patch(
        WORKTREE,
        task,
        baseline_ref=BASELINE,
        reconciliation_branch_name=BRANCH,
        record_event=False,
        allow_scope_adjudication=False,
        diagnostics=diagnostics,
    )
    proposal = result.proposal
    policy = result.policy
    receipt = result.receipt
    require(receipt.accepted is True, f"proposal rejected: {receipt.to_dict()}")
    require(set(proposal.changed_paths) == set(json.loads(task.metadata["proposal artifact envelope"])["paths"]), "envelope paths drifted")
    require(git("status", "--porcelain", cwd=WORKTREE) == "", "preflight dirtied candidate")
    print(
        json.dumps(
            {
                "accepted": receipt.accepted,
                "task_id": task.task_id,
                "task_key": task.canonical_task_key,
                "task_cid": task.canonical_task_cid,
                "proposal_id": proposal.proposal_id,
                "receipt_id": receipt.receipt_id,
                "changed_paths": list(proposal.changed_paths),
                "policy_version": policy.policy_version,
                "policy_limits": {
                    "max_file_bytes": policy.max_file_bytes,
                    "max_patch_bytes": policy.max_patch_bytes,
                    "max_output_bytes": policy.max_output_bytes,
                },
                "diagnostics": diagnostics,
            },
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
