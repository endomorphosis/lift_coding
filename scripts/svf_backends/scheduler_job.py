#!/usr/bin/env python3
"""Run one actual owner TaskQueue job with a narrow SHA-256 computation hook.

This is a scheduler qualification, not an inference simulation. The native
worker owns claim, execution and completion; this module never writes a task
result into the queue. It cannot execute commands or access arbitrary files.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

TASK_TYPE = "svf.sha256"


def hash_fixture(task: dict) -> dict:
    if task.get("task_type") != TASK_TYPE:
        raise ValueError("unexpected scheduler task type")
    value = json.loads(task["payload"]["prompt"])
    if set(value) != {"nonce", "bytes_base64"} or re.fullmatch(r"[0-9a-f]{32}", value["nonce"]) is None:
        raise ValueError("invalid bounded fixture payload")
    data = base64.b64decode(value["bytes_base64"], validate=True)
    if not 1 <= len(data) <= 4096:
        raise ValueError("scheduler fixture exceeds its byte bound")
    digest = hashlib.sha256(data).hexdigest()
    return {"operation": "sha256", "nonce": value["nonce"], "size_bytes": len(data),
            "sha256": digest, "output": digest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--worker-id", required=True)
    args = parser.parse_args()
    owner_root = Path(__file__).resolve().parents[2] / "external/ipfs_accelerate"
    # The readiness entrypoint ipfs_accelerate_py.py lives beside this module;
    # put the real owner package first so it cannot shadow the native worker.
    sys.path.insert(0, str(owner_root))
    import ipfs_accelerate_py
    if Path(ipfs_accelerate_py.__file__).resolve() != owner_root / "ipfs_accelerate_py/__init__.py":
        raise ValueError("native scheduler package does not match the declared owner checkout")
    from ipfs_accelerate_py.p2p_tasks.task_queue import TaskQueue
    from ipfs_accelerate_py.p2p_tasks.worker import run_worker
    queued = TaskQueue(args.queue).get(args.task_id)
    if not queued or queued.get("status") != "queued":
        raise ValueError("the isolated fixture must already be queued")
    hash_fixture(queued)  # Admission validation; no result is persisted here.
    code = run_worker(queue_path=args.queue, worker_id=args.worker_id, once=True,
        p2p_service=False, mesh=False, supported_task_types=[TASK_TYPE],
        extra_handlers={TASK_TYPE: hash_fixture}, poll_interval_s=0.05)
    row = TaskQueue(args.queue).get(args.task_id)
    if code != 0 or not row or row.get("status") != "completed":
        raise ValueError("native scheduler did not complete the fixture job")
    print(json.dumps({"task_id": args.task_id, "worker_id": args.worker_id, "completed": True,
                      "work_complete": False, "completion_authority": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
