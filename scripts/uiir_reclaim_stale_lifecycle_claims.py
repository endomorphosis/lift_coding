#!/usr/bin/env python3
"""Optional ops wrapper around agent-supervisor lifecycle reclaim.

Primary recovery lives in ``ipfs_accelerate_py``:

- ``WorktreeLifecycleStore.reclaim_expired_nonterminal``
- ``PortalImplementationDaemon._reclaim_expired_worktree_lifecycle_claims``
  (startup + each ``run_once`` pass + pre-acquire retry)

This script is only for manual/operator intervention or board companions that
want an explicit reclaim cycle outside a daemon process.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--task-prefix", default="UIR-")
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "external" / "ipfs_accelerate"))
    from ipfs_accelerate_py.agent_supervisor.worktree_lifecycle import (
        WorktreeLifecycleStore,
    )

    store = WorktreeLifecycleStore(repo_root=root)
    recovered = store.reclaim_expired_nonterminal(
        reason="uiir_periodic_expired_lease_reclaim",
        task_id_prefix=args.task_prefix,
    )
    print(f"reclaimed={len(recovered)}")
    for record in recovered:
        print(
            f"  {record.task_id} attempt={record.attempt} "
            f"state={record.state.value}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
