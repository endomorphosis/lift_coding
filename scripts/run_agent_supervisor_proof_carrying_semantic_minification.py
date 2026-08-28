#!/usr/bin/env python3
"""Bootstrap and operate the PCSM DuckDB + Quack control plane.

The authority split is deliberately narrow:

* ``DatabaseTaskSource@1`` over DuckDB is transactional task/goal authority.
* one fenced loopback Quack process exclusively owns the DuckDB file while
  supervisors are running;
* DuckLake is an optional, rebuildable history projection and is never read by
  readiness, completion, promotion, or release gates.

The Markdown plan, objectives, and task board are immutable bootstrap inputs.
This operator never mutates their status fields and never publishes the raw
Quack authentication token.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import socket
import stat as stat_module
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parents[1]
ACCEL_ROOT: Final = ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_CONFIG: Final = Path(
    "config/proof_carrying_semantic_minification_v1_supervisor.json"
)
RUNTIME_RELATIVE: Final = Path(
    "data/agent_supervisor/proof_carrying_semantic_minification_v1"
)
BOOTSTRAP_RECEIPT_NAME: Final = "bootstrap-materialization.json"
DUCKLAKE_RECEIPT_NAME: Final = "ducklake-history-projection.json"
OPERATOR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-operator@1"
)
POPULATION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-population@1"
)
BOOTSTRAP_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-bootstrap@1"
)
DATABASE_TASK_SOURCE_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/database-task-source@1"
)
DUCKLAKE_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-ducklake-projection@1"
)
GOAL_RE: Final = re.compile(r"^## (PCSM-G\d{3}) (.+)$", re.MULTILINE)
QUACK_ENDPOINT_RE: Final = re.compile(
    r"^quack:(?://)?(127(?:\.\d{1,3}){3}|localhost):(\d{1,5})$",
    re.IGNORECASE,
)
READY_STATUSES: Final = (
    "proposed",
    "admitted",
    "pending",
    "ready",
    "todo",
    "queued",
    "retrying",
)
COMPLETED_STATUSES: Final = ("completed", "skipped", "complete", "done")
ACTIVE_STATUSES: Final = ("claimed", "in_progress", "running")
TERMINAL_STATUSES: Final = (
    *COMPLETED_STATUSES,
    "cancelled",
    "failed",
    "quarantined",
    "rejected",
)
OWNER_DML_PREFIXES: Final = (
    "UPDATE ",
    "DELETE ",
    "MERGE ",
    "INSERT OR REPLACE",
    "INSERT OR IGNORE",
)
OWNER_DAEMON_COMMAND: Final = "state-owner-daemon"
EXECUTOR_OWNER_SESSION_BASE: Final = "pcsm-v1-executor"
INTERNAL_CLIENT_GRANT_TTL_SECONDS: Final = 86_400.0
EXECUTOR_BOOTSTRAP_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-executor-bootstrap@1"
)
OWNER_RESTART_ADMISSION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-owner-restart-admission@1"
)
OWNER_RESTART_RECEIPT_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-owner-restart-receipt@1"
)
OWNER_DATABASE_VERIFICATION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-owner-database-verification@1"
)
QUACK_STATE_SERVER_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/quack-state-server@1"
)
QUACK_STATE_SERVER_INTERFACE: Final = "QuackStateServer@1"
STATE_SERVER_IDENTITY_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/state-server-identity@1"
)
STATE_SERVER_IDENTITY_INTERFACE: Final = "StateServerIdentity@1"
HANDOFF_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-handoff-repair@1"
)
HANDOFF_EXECUTION_ROUTE_CONTINUATION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-execution-route-continuation@1"
)
HANDOFF_BLOCKED_RETRY_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-blocked-retry-handoff@1"
)
HANDOFF_BLOCKED_RETRY_SIDECAR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-blocked-retry-sidecar-evidence@1"
)
CURRENT_HEAD_BLOCKED_RETRY_BATCH_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-current-head-blocked-retry-batch@1"
)
CURRENT_HEAD_BLOCKED_RETRY_BATCH_ENTRY_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-current-head-blocked-retry-entry@1"
)
CURRENT_HEAD_BLOCKED_RETRY_BATCH_EVIDENCE_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-current-head-blocked-retry-evidence@1"
)
CURRENT_HEAD_BLOCKED_RETRY_BATCH_RESULT_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-current-head-blocked-retry-result@1"
)
CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-current-head-descendant-repair@1"
)
STALE_WORKTREE_CLEANUP_TRANSITION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-stale-worktree-cleanup-transition@1"
)
VALIDATION_PATH_COMPATIBILITY_TRANSITION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-validation-path-compatibility-transition@1"
)
DATABASE_WATCHDOG_ACTIVITY_TRANSITION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-database-watchdog-activity-transition@1"
)
TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "typed-database-blocked-retry-recovery@1"
)
HANDOFF_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-repair.json"
)
HANDOFF_REPLAY_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-replay-repair.json"
)
HANDOFF_REPLAY_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-restart-replay-repair@1"
)
HANDOFF_REPLAY_REPAIR_BASE_COMMIT: Final = "fe8331645cc4276e2684737e3b0999a9009a2fae"
HANDOFF_REPLAY_REPAIR_SEALED_OPERATOR_IDENTITY: Final = (
    "sha256:a4506885482cd8442cd7646f44d9106f9913c7cde4bfd521fe71cd38cb7b1164"
)
HANDOFF_REPLAY_REPAIR_SEALED_RECEIPT_ID: Final = (
    "sha256:8c2da662fbc39c2eb3fcfffe973baf7a9fe70bc05e655d02187696a721569c1e"
)
HANDOFF_GENERATION_REPLAY_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-generation-replay-repair.json"
)
HANDOFF_GENERATION_REPLAY_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-restart-generation-replay-repair@1"
)
HANDOFF_COMMAND_AUTHORITY_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-command-authority-repair.json"
)
HANDOFF_COMMAND_AUTHORITY_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-command-authority-repair@1"
)
HANDOFF_COMMAND_AUTHORITY_REPAIR_BASE_COMMIT: Final = (
    "9eb2077b661e137dd4459945886ef0979df0b56e"
)
HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_COMMIT: Final = (
    "307c97ebcdee425ecdd93813c8898712b46b3fc8"
)
HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_TREE: Final = (
    "209d81f01b3a900d1d041721bd235b86a7319950"
)
HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OPERATOR_IDENTITY: Final = (
    "sha256:691345158b9bfac25b5124b8e2b5bbe5bac2e35492fc0c292a6feec8fa585131"
)
HANDOFF_COMMAND_VERIFIER_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-command-verifier-repair.json"
)
HANDOFF_COMMAND_VERIFIER_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-command-verifier-repair@1"
)
HANDOFF_COMMAND_VERIFIER_REPAIR_BASE_COMMIT: Final = (
    "e8a75491066ba25afd2b7d08012c3dd1e401a5e3"
)
HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_COMMIT: Final = (
    "c16dd9b8c0920c5a690abe48542957af0fc44593"
)
HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_TREE: Final = (
    "369f064026ac82a049bc15bab8ccc060bfe82796"
)
HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OPERATOR_IDENTITY: Final = (
    "sha256:4c93ab0e5732c7cd8e055daec07b4d27958f3feb49794e942a11cb1d8d746f63"
)
HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-bootstrap-broker-resilience-repair.json"
)
HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-bootstrap-broker-resilience-repair@1"
)
CURRENT_HEAD_BLOCKED_RETRY_BATCH_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "current-head-blocked-retry-batch.json"
)
CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-current-head-blocked-retry-repair.json"
)
STALE_WORKTREE_CLEANUP_TRANSITION_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-stale-worktree-cleanup-transition.json"
)
VALIDATION_PATH_COMPATIBILITY_TRANSITION_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-validation-path-compatibility-transition.json"
)
DATABASE_WATCHDOG_ACTIVITY_TRANSITION_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-database-watchdog-activity-transition.json"
)
STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT: Final = (
    "8b8be83c6d9c578c4cec450092e140b929ce12e9"
)
STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD: Final = (
    "059d684952a5cdf3430edf70a43c3b9b31dc650a"
)
STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE: Final = (
    "067b308e8ff0fba4b9017f240ad774e6cdedd3cf"
)
VALIDATION_PATH_COMPATIBILITY_TRANSITION_BASE_COMMIT: Final = (
    "ab977725e0444c25cf2f55473839ee006abbe697"
)
VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD: Final = (
    "a668ee23c76a69916d3214e7db07651d22f0dda1"
)
VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE: Final = (
    "5edcbd2baae9c38785a2832eedec6c893cc3c924"
)
VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD: Final = (
    "8be57ea10aaf3d32897581f26523bb139d659a4c"
)
VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE: Final = (
    "c9b3e3d9acf2983465cf84f4f93e770a7444872d"
)
DATABASE_WATCHDOG_ACTIVITY_TRANSITION_BASE_COMMIT: Final = (
    "PENDING_DATABASE_WATCHDOG_ACTIVITY_TRANSITION_BASE_COMMIT"
)
DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD: Final = (
    "c757022cf3b2ad35031afe4912ff20cbe6144a5d"
)
DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_TREE: Final = (
    "a1e7239ea168a881be333733cb6baf570b9a4595"
)
DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD: Final = (
    "7ecaa95972cd772051930c6ecc7626b333846b0d"
)
DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_TREE: Final = (
    "751fc8d37e7bb7746082a39f2623b3d2291b5f38"
)
CURRENT_HEAD_BLOCKED_RETRY_REPAIR_BASE_COMMIT: Final = (
    "db9304284cfe857f08377ef756b4896192dd5111"
)
CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_HEAD: Final = (
    "9c0881ddbd766bb28eee82b25626e990de7a48eb"
)
CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_TREE: Final = (
    "d25161aa168b63cec55dea59cb5eb9880ff7e841"
)
CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD: Final = (
    "aa5cde27b5772a3f26f4b0bf9e00f1c52ce4c8c9"
)
CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_TREE: Final = (
    "92891293dea1aa8e8d10fb7ee731f808c881de9a"
)
CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_CONFIG_ID: Final = (
    "sha256:ecdad8bf8acde7e444c54f3f765b71d46123d52a76dcc3289f932f49011f0b82"
)
CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_ACCELERATOR_HEAD: Final = (
    "e33a439d17aaf8635f5d80520e93c9c52d56fa09"
)
CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_ACCELERATOR_TREE: Final = (
    "e74410285ade6ceb70c42660e5f1372029bb1d1a"
)
HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_BASE_COMMIT: Final = (
    "9cc27d09f18532dccdc68ef9e429150905823ae2"
)
HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_COMMIT: Final = (
    "bc4cbda714b0e7f9052d4a6efdc3ae9abefa2c0d"
)
HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_TREE: Final = (
    "8b57998dd5fce8c35c03f97ff6b9d342ff93c9dd"
)
HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OPERATOR_IDENTITY: Final = (
    "sha256:c1bcb0c761ab42a6c7e59ec85007ec647fb31574ab6040731de32c5327de0940"
)
HANDOFF_GENERATION_REPLAY_REPAIR_BASE_COMMIT: Final = (
    "3208c41917944182865889c48e57bc128ab8a463"
)
HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_COMMIT: Final = (
    "f40c309b948514e6ad74ea9b29b13abadc74b478"
)
HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_TREE: Final = (
    "7f85ea44e369bd725ac9366f170725ee8e2546b1"
)
HANDOFF_REPAIR_SEALED_OUTER_COMMIT: Final = (
    "a985e87f77a59afc78f8d73bf0d4c18566000442"
)
HANDOFF_REPAIR_SEALED_OUTER_TREE: Final = (
    "47958a8a04d8a5e7a1fbd9155823597e977ffa8c"
)
HANDOFF_REPAIR_SEALED_OPERATOR_IDENTITY: Final = (
    "sha256:c6b1bb0991c29d07bbd248358039d051956e75e10243a44d4d78b7e72d790e80"
)
HANDOFF_REPAIR_SEALED_RECEIPT_ID: Final = (
    "sha256:e0ce20f7218d7eef119f5853b034e8275870cd527d7df70b398fda8e72455861"
)
HANDOFF_REPAIR_MAX_TASK_ATTEMPTS: Final = 2
HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND: Final = "task.blocked.retry.recover"
HANDOFF_REPAIR_BLOCKED_RETRY_OPERATION: Final = (
    "database_operator_blocked_retry_recovery"
)
HANDOFF_REPAIR_BLOCKED_RETRY_REASON: Final = (
    "database_operator_blocked_retry_recovery"
)
CURRENT_HEAD_BLOCKED_RETRY_BATCH_OPERATION: Final = (
    "task.blocked.retry.recover.batch"
)
CURRENT_HEAD_BLOCKED_RETRY_TERMINAL_REASON: Final = (
    "protected-path preservation event chain is not exact"
)
CURRENT_HEAD_BLOCKED_RETRY_POST_RECOVERY_REQUIREMENT: Final = (
    "fresh_portal_claim_and_current_head_revalidation"
)
CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS: Final = {
    "PCSM-013": {
        "task_cid": (
            "baguqeera5pkum2zplgdvym6ucu5yhvwo2yfl7el5hhac5cwdhd4uacgya5bq"
        ),
        "source_revision": 8,
        "source_attempt_number": 2,
        "source_task_body_id": (
            "sha256:316a90efd6a51a0ac01cf9887cd9ce182f5cef2c7d4ec5e1"
            "2453eaeccde71046"
        ),
        "source_completion_receipt_id": (
            "sha256:4657ef0be7d634aaf937903f88d1fe5a895d40af56494791"
            "24ba26d62f0c0880"
        ),
    },
    "PCSM-016": {
        "task_cid": (
            "baguqeera5ntif64zvn6jxokaqwjj6t64mjaboxsy2yhmlifs5xwm2i7dlkia"
        ),
        "source_revision": 4,
        "source_attempt_number": 1,
        "source_task_body_id": (
            "sha256:6753faa4201e7449a7b14441d3ed22468517e03706a0caa3"
            "dae41db18372454d"
        ),
        "source_completion_receipt_id": (
            "sha256:c4d0a86fda93ef0addc308ecc33f42c5d39381183bf065a9"
            "048b413873277e3e"
        ),
    },
    "PCSM-017": {
        "task_cid": (
            "baguqeeravik6msftwaidryxvqqb2y6evm7gkeqch5dbhrgvgtjhoymtpfa4a"
        ),
        "source_revision": 4,
        "source_attempt_number": 1,
        "source_task_body_id": (
            "sha256:674b43216c1da57eef0a707404b246e6c39831ecdb6d23b2"
            "b42031eccb1f8692"
        ),
        "source_completion_receipt_id": (
            "sha256:a06ee1539e4c0b48840dbd354b6550554d0a16f48b6b8bd7"
            "09095f8f8bce0fc5"
        ),
    },
    "PCSM-018": {
        "task_cid": (
            "baguqeeraa5k5sw3vgizciinrkscjudqi67b6gqz7hwhbomdj6c47xd3u777q"
        ),
        "source_revision": 4,
        "source_attempt_number": 1,
        "source_task_body_id": (
            "sha256:714096554355bd73a2360b8950559e9ecb06ddea72c4df5c"
            "eddb54507604109d"
        ),
        "source_completion_receipt_id": (
            "sha256:02b82457187480e7ef8c4652c89bbb34124c43b6e10f55a6"
            "588b9de4e0fcf5e6"
        ),
    },
}
CURRENT_HEAD_BLOCKED_RETRY_INCIDENT_EXPECTATIONS: Final = {
    "PCSM-013": {
        "lane_index": 0,
        "portal_attempt_id": "5415d64990254cf912239edd",
        "rescue_commit": "0f2f459e330c087fd224530691a8a9c58f122ed7",
        "merge_commit": "b723da398df6fabb7602cd2c84146a80d43bb226",
    },
    "PCSM-016": {
        "lane_index": 3,
        "portal_attempt_id": "1053223fd16c95904203f13d",
        "rescue_commit": "f42bfaa6da74e8132de7ea3bcc5f0e666438fb86",
        "merge_commit": "eb52860cd2b1854462dc7ce54be0feae6f64bd49",
    },
    "PCSM-017": {
        "lane_index": 1,
        "portal_attempt_id": "f122e173dac6c6ed1a59adf8",
        "rescue_commit": "20880fddd69a69d7a8f06ce5e8626ca7b6b5b8e3",
        "merge_commit": "8836019efbe5de8e77da6738a6bb9617a271fe32",
    },
    "PCSM-018": {
        "lane_index": 2,
        "portal_attempt_id": "88fa9dcc6ee1064bcdce5670",
        "rescue_commit": "00847e788fdd44c99bf7f7afb7cfd9167a338675",
        "merge_commit": "de272f66e7046105d2ad8c5bed836f18bd4c7ef5",
    },
}
HANDOFF_REPAIR_SOURCE_TASK_BODY_ID: Final = (
    "sha256:8992ab06d2296750d97d9c40011b1e2fb517df37d222871f28adbded0bed8bb1"
)
HANDOFF_REPAIR_PORTAL_ATTEMPT_RELATIVE: Final = (
    RUNTIME_RELATIVE
    / "state"
    / "lane-0"
    / "pcsm_lane_0_database_portal_attempts"
    / "9a0e3458b52874ca9098d9f5"
)
HANDOFF_REPAIR_TASK_CID: Final = (
    "baguqeera6mvj3326qcksmlmwafo3s7ppd4s22vnbsn4tjnk4ylbjyqiesypa"
)
HANDOFF_REPAIR_COMPLETION_RECEIPT_ID: Final = (
    "sha256:e00019f28ba2031bf94076661378b1de877c843512c7a41071968a56001361a3"
)
HANDOFF_REPAIR_ROUTE_POLICY_ID: Final = (
    "baguqeerahvwjwfbexnsqdflng54qvtuqoiwf4junsjaafyuhvl2fmjkeettq"
)
HANDOFF_REPAIR_ROUTE_SOURCE_PROJECTION_CID: Final = (
    "baguqeeraortwkvzwu52ibvbutlskq5e7c65ubmop67fgsou5twrmmj3uawaq"
)
HANDOFF_REPAIR_STABLE_BINDING_ID: Final = (
    "baguqeeranwwwzvu237trolqpqxsireo7cqhhgzkrsxgyhy4px2wz6m2jc6la"
)
HANDOFF_REPAIR_SOURCE_ATTEMPT: Final = {
    "attempt_id": "attempt:53a9ee3f434e4551932f258aa9c903c6",
    "claim_id": "claim:617b52197f564c58ade577daf8430602",
    "lease_id": "lease:b562bfc2ae884a958362697b3c5c7185",
    "owner_session_id": "pcsm-v1-executor:shard:0-of-4:track:ef26cb9db64a",
    "attempt_number": 1,
    "fencing_token": 1,
    "fence_epoch": 1,
    "task_revision": 4,
}
HANDOFF_REPAIR_REQUIRED_VALIDATIONS: Final = frozenset(
    {
        (
            ".",
            (
                "python",
                "-m",
                "py_compile",
                "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
                "scripts/generate_proof_carrying_semantic_minification_board.py",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
            ),
        ),
        (
            ".",
            (
                "python",
                "scripts/generate_proof_carrying_semantic_minification_board.py",
                "--check",
            ),
        ),
        (
            ".",
            (
                "python",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
                "--check-all",
            ),
        ),
        (
            ".",
            (
                "env",
                "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:"
                "external/ipfs_kit:Mcp-Plus-Plus",
                "python",
                "-m",
                "pytest",
                "-q",
                "external/ipfs_datasets/tests/proof_context",
            ),
        ),
        (
            "external/ipfs_accelerate",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/api/test_agent_supervisor_database_portal_bridge.py",
                "test/api/test_agent_supervisor_merge_train.py",
                "test/api/test_agent_supervisor_task_attempt_limit.py",
                "test/api/test_agent_supervisor_multi_supervisor_shutdown.py",
            ),
        ),
        (
            "external/ipfs_accelerate",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/api/causal_federation/test_admitted_executor.py::"
                "test_operator_blocked_retry_recovers_once_and_replays_after_restart",
                "test/api/causal_federation/test_admitted_executor.py::"
                "test_typed_daemon_promotes_local_attempt_before_provider",
                "test/api/causal_federation/test_admitted_executor.py::"
                "test_executor_typed_operation_catalog_is_closed_and_full_fidelity",
                "test/api/"
                "test_agent_supervisor_validation_retry_seed_conflict_recovery.py",
            ),
        ),
    }
)
_RESTART_IMMUTABLE_SOURCE_NAMES: Final = frozenset(
    {"objectives", "plan", "taskboard"}
)
_RESTART_REPAIR_SOURCE_NAMES: Final = frozenset(
    {"config", "generator", "operator", "validator"}
)
_RESTART_ALLOWED_SOURCE_BINDING_FIELDS: Final = frozenset(
    {
        "ipfs_accelerate_origin_main_revision",
        "ipfs_accelerate_planning_revision",
        "ipfs_accelerate_planning_tree",
        "ipfs_datasets_planning_revision",
        "ipfs_datasets_planning_tree",
    }
)
_RESTART_SOURCE_FOREST_REPOSITORIES: Final = frozenset(
    {"ipfs_accelerate", "ipfs_datasets", "ipfs_kit", "mcp_plus_plus"}
)
_RESTART_SOURCE_FOREST_ENTRY_FIELDS: Final = frozenset(
    {"repository", "path", "head", "tree", "access"}
)


class OperatorError(RuntimeError):
    """Fail-closed PCSM operator error."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical_bytes(value)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _semantic_identity(value: Mapping[str, Any]) -> str:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )

    return content_identity(value)


def _atomic_json(path: Path, payload: Mapping[str, Any], *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorError(f"cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise OperatorError(f"JSON root must be an object: {path}")
    return value


def _safe_path(root: Path, value: Any, *, field: str) -> Path:
    text = str(value or "").strip()
    relative = Path(text)
    if not text or relative.is_absolute() or ".." in relative.parts:
        raise OperatorError(f"{field} must be a safe repository-relative path")
    resolved = (root / relative).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise OperatorError(f"{field} escapes repository") from exc
    return resolved


def _ensure_private_runtime_directory(path: Path) -> None:
    """Create or harden one same-user runtime directory for lane sidecars."""

    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OperatorError("private runtime directories require no-follow access")
    before = path.stat(follow_symlinks=False)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | nofollow
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise OperatorError(f"runtime directory cannot be opened safely: {path}") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            not stat_module.S_ISDIR(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise OperatorError(f"runtime directory is not an owned directory: {path}")
        os.fchmod(descriptor, 0o700)
        hardened = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
        if (
            stat_module.S_IMODE(hardened.st_mode) != 0o700
            or (named.st_dev, named.st_ino) != (hardened.st_dev, hardened.st_ino)
            or named.st_uid != os.geteuid()
        ):
            raise OperatorError(f"runtime directory could not be hardened: {path}")
    finally:
        os.close(descriptor)


def _git(*arguments: str, check: bool = True, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=not binary,
        check=False,
    )
    if check and completed.returncode != 0:
        error = completed.stderr or completed.stdout
        if isinstance(error, bytes):
            error = error.decode("utf-8", errors="replace")
        raise OperatorError(
            f"git {' '.join(arguments)} failed: {str(error).strip()}"
        )
    return completed.stdout


def _git_in_repository(
    repository: Path,
    *arguments: str,
    binary: bool = False,
) -> str | bytes:
    """Read one exact Git object or relationship from a bound repository."""

    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        text=not binary,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr or completed.stdout
        if isinstance(error, bytes):
            error = error.decode("utf-8", errors="replace")
        raise OperatorError(
            f"git {' '.join(arguments)} failed in {repository}: "
            f"{str(error).strip()}"
        )
    return completed.stdout


def _assert_clean_current_tree(config: Mapping[str, Any]) -> tuple[str, str]:
    status_output = str(
        _git("status", "--porcelain=v1", "--untracked-files=all")
    ).strip()
    if status_output:
        raise OperatorError(
            "refusing to materialize from a dirty worktree; commit the exact "
            "plan, board, configuration, validator, and operator first"
        )
    head = str(_git("rev-parse", "HEAD")).strip()
    tree = str(_git("rev-parse", "HEAD^{tree}")).strip()
    branch = str(_git("branch", "--show-current")).strip()
    required_branch = str(config.get("merge_target_branch") or "").strip()
    if required_branch and branch != required_branch:
        raise OperatorError(
            f"execution branch {branch!r} differs from configured branch "
            f"{required_branch!r}"
        )
    binding = config.get("source_binding")
    binding = binding if isinstance(binding, Mapping) else {}
    ancestor = str(binding.get("accelerator_required_ancestor") or "").strip()
    if ancestor:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, "HEAD"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise OperatorError("configured accelerator base is not an ancestor")
    return head, tree


def _tracked_bytes(path: Path, *, head: str) -> bytes:
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise OperatorError(f"authority input escapes repository: {path}") from exc
    if path.is_symlink() or not path.is_file():
        raise OperatorError(f"authority input is not a regular file: {relative}")
    working = path.read_bytes()
    recorded = _git("show", f"{head}:{relative}", binary=True)
    if not isinstance(recorded, bytes) or working != recorded:
        raise OperatorError(f"authority input differs from current HEAD: {relative}")
    return working


def _git_commit_tree(
    commit: Any,
    *,
    field: str,
    repository: Path = ROOT,
) -> str:
    revision = str(commit or "").strip()
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise OperatorError(f"{field} must be an exact Git commit")
    try:
        object_type = subprocess.run(
            ["git", "cat-file", "-t", revision],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
        tree_result = subprocess.run(
            ["git", "rev-parse", f"{revision}^{{tree}}"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise OperatorError(f"{field} is unavailable") from exc
    tree = tree_result.stdout.strip()
    if (
        object_type.returncode != 0
        or object_type.stdout.strip() != "commit"
        or tree_result.returncode != 0
        or re.fullmatch(r"[0-9a-f]{40}", tree) is None
    ):
        raise OperatorError(f"{field} is not an available Git commit")
    return tree


def _git_is_ancestor(
    ancestor: Any,
    descendant: Any,
    *,
    field: str,
    repository: Path = ROOT,
) -> None:
    older = str(ancestor or "").strip()
    newer = str(descendant or "").strip()
    if not older or not newer:
        raise OperatorError(f"{field} has an empty revision")
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return
    if completed.returncode == 1:
        raise OperatorError(f"{field} is not monotonic")
    raise OperatorError(f"cannot verify {field}")


def _git_blob_at(*, head: str, path: Path, field: str) -> bytes:
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise OperatorError(f"{field} escapes repository") from exc
    try:
        value = _git("show", f"{head}:{relative}", binary=True)
    except OperatorError as exc:
        raise OperatorError(f"{field} is absent from the sealed source") from exc
    if not isinstance(value, bytes):
        raise OperatorError(f"{field} could not be read as bytes")
    return value


def _json_mapping_bytes(value: bytes, *, field: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorError(f"{field} must be a JSON object") from exc
    if not isinstance(decoded, dict):
        raise OperatorError(f"{field} must be a JSON object")
    return decoded


def _exact_int(value: Any, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise OperatorError(f"{field} must be an integer >= {minimum}")
    return value


def _restart_source_paths(board: Any) -> dict[str, Path]:
    return {
        "config": board.config_path,
        "taskboard": board.path(board.taskboard_path),
        "objectives": board.path(board.objectives_path),
        "plan": board.path(board.plan_path),
        "validator": board.path(board.validator_path),
        "generator": (
            ROOT / "scripts/generate_proof_carrying_semantic_minification_board.py"
        ),
        "operator": Path(__file__).resolve(),
    }


def _restart_static_config(config: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    try:
        normalized = json.loads(_canonical_bytes(config))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise OperatorError(f"{label} config is not canonical JSON") from exc
    if not isinstance(normalized, dict):
        raise OperatorError(f"{label} config must be an object")
    source_binding = normalized.get("source_binding")
    if not isinstance(source_binding, dict):
        raise OperatorError(f"{label} config has no source_binding object")
    for field in _RESTART_ALLOWED_SOURCE_BINDING_FIELDS:
        source_binding.pop(field, None)
    normalized.pop("max_task_attempts", None)
    return normalized


def _verified_restart_forest_transition(
    bootstrap_forest: Any,
    current_forest: Mapping[str, Any],
    *,
    bootstrap_head: str,
    current_head: str,
) -> dict[str, Any]:
    if not isinstance(bootstrap_forest, Mapping):
        raise OperatorError("bootstrap source forest is absent")
    bootstrap_body = dict(bootstrap_forest)
    bootstrap_root = str(bootstrap_body.pop("source_forest_root", "") or "")
    if (
        set(bootstrap_body)
        != {"source_head", "nested_repositories", "cross_repository_writes"}
        or bootstrap_body.get("cross_repository_writes") is not True
        or re.fullmatch(r"sha256:[0-9a-f]{64}", bootstrap_root) is None
        or _identity(bootstrap_body) != bootstrap_root
        or bootstrap_body.get("source_head") != bootstrap_head
    ):
        raise OperatorError("bootstrap source forest identity is invalid")
    current_body = dict(current_forest)
    current_root = str(current_body.pop("source_forest_root", "") or "")
    if (
        set(current_body)
        != {"source_head", "nested_repositories", "cross_repository_writes"}
        or current_body.get("cross_repository_writes") is not True
        or re.fullmatch(r"sha256:[0-9a-f]{64}", current_root) is None
        or _identity(current_body) != current_root
        or current_body.get("source_head") != current_head
    ):
        raise OperatorError("current source forest identity is invalid")
    prior_items = bootstrap_forest.get("nested_repositories")
    current_items = current_forest.get("nested_repositories")
    if not isinstance(prior_items, list) or not isinstance(current_items, list):
        raise OperatorError("restart source forests have no nested repositories")
    if any(
        not isinstance(item, Mapping)
        or set(item) != _RESTART_SOURCE_FOREST_ENTRY_FIELDS
        for item in (*prior_items, *current_items)
    ):
        raise OperatorError("restart source forest entry is malformed")
    prior = {str(item.get("repository") or ""): item for item in prior_items}
    current = {str(item.get("repository") or ""): item for item in current_items}
    if (
        len(prior) != len(prior_items)
        or len(current) != len(current_items)
        or set(prior) != _RESTART_SOURCE_FOREST_REPOSITORIES
        or set(current) != _RESTART_SOURCE_FOREST_REPOSITORIES
    ):
        raise OperatorError("restart source forest repository set changed")
    transitions: list[dict[str, Any]] = []
    for repository_name in sorted(prior):
        older = prior[repository_name]
        newer = current[repository_name]
        if not isinstance(older, Mapping) or not isinstance(newer, Mapping):
            raise OperatorError("restart source forest entry is malformed")
        path = str(older.get("path") or "")
        if (
            path != str(newer.get("path") or "")
            or older.get("access") != newer.get("access")
        ):
            raise OperatorError(
                f"{repository_name} restart source authority changed"
            )
        nested = _safe_path(ROOT, path, field=f"{repository_name}.path")
        old_head = str(older.get("head") or "")
        new_head = str(newer.get("head") or "")
        old_tree = _git_commit_tree(
            old_head,
            field=f"{repository_name}.bootstrap_head",
            repository=nested,
        )
        new_tree = _git_commit_tree(
            new_head,
            field=f"{repository_name}.current_head",
            repository=nested,
        )
        if (
            old_tree != str(older.get("tree") or "")
            or new_tree != str(newer.get("tree") or "")
        ):
            raise OperatorError(f"{repository_name} restart tree binding changed")
        _git_is_ancestor(
            old_head,
            new_head,
            field=f"{repository_name} bootstrap-to-current lineage",
            repository=nested,
        )
        transitions.append(
            {
                "repository": repository_name,
                "path": path,
                "bootstrap_head": old_head,
                "bootstrap_tree": old_tree,
                "current_head": new_head,
                "current_tree": new_tree,
                "changed": old_head != new_head,
            }
        )
    return {
        "bootstrap_source_forest_root": bootstrap_root,
        "current_source_forest_root": current_root,
        "repositories": transitions,
    }


def _verified_blocked_retry_handoff(
    value: Any,
    *,
    source_attempt: Mapping[str, Any],
    source_completion_receipt_id: str,
    bootstrap_attempt_limit: int,
    current_attempt_limit: int,
) -> dict[str, Any]:
    """Validate the one exact, attempt-preserving PCSM-010 retry handoff."""

    if not isinstance(value, Mapping):
        raise OperatorError("PCSM blocked-retry handoff is absent")
    handoff = dict(value)
    expected_fields = {
        "schema",
        "command_operation",
        "control_operation",
        "queue_reason",
        "source_status",
        "source_revision",
        "source_task_body",
        "source_task_body_id",
        "source_completion_receipt_id",
        "source_cooldown_absent",
        "target_status",
        "target_revision",
        "max_task_attempts_before",
        "max_task_attempts_after",
        "attempt_refunded",
        "fresh_attempt_number",
        "delay_ms",
        "started_at_ms",
        "retry_not_before_ms",
        "sidecar_evidence",
    }
    source_body = handoff.get("source_task_body")
    terminal_receipt = (
        source_body.get("completion_receipt")
        if isinstance(source_body, Mapping)
        else None
    )
    evidence = handoff.get("sidecar_evidence")
    evidence_body = dict(evidence) if isinstance(evidence, Mapping) else {}
    evidence_id = str(evidence_body.pop("evidence_id", "") or "")
    files = evidence.get("files") if isinstance(evidence, Mapping) else None
    facts = evidence.get("facts") if isinstance(evidence, Mapping) else None
    expected_file_paths = {
        "coordination": (
            RUNTIME_RELATIVE
            / "state/lane-0/pcsm_lane_0_database_coordination.duckdb"
        ).as_posix(),
        "execution": (
            RUNTIME_RELATIVE
            / "state/lane-0/pcsm_lane_0_database_execution.duckdb"
        ).as_posix(),
        "portal_attempt_binding": (
            HANDOFF_REPAIR_PORTAL_ATTEMPT_RELATIVE
            / "database-attempt-binding.json"
        ).as_posix(),
        "portal_events": (
            HANDOFF_REPAIR_PORTAL_ATTEMPT_RELATIVE / "portal-events.jsonl"
        ).as_posix(),
        "diagnostic_receipt": (
            HANDOFF_REPAIR_PORTAL_ATTEMPT_RELATIVE
            / "implementation-logs/pcsm-010-diagnostic-receipt.json"
        ).as_posix(),
    }
    file_map: dict[str, Mapping[str, Any]] = {}
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, Mapping):
                raise OperatorError("PCSM blocked-retry file evidence is malformed")
            role = str(item.get("role") or "")
            if role in file_map:
                raise OperatorError("PCSM blocked-retry file evidence is duplicated")
            file_map[role] = item
    expected_fact_fields = {
        "source_attempt",
        "coordination_task",
        "coordination_attempt",
        "coordination_claim",
        "coordination_lease",
        "coordination_task_completion_count",
        "coordination_newer_attempt_count",
        "coordination_newer_fence_count",
        "execution_attempt",
        "execution_phase_sequence",
        "execution_provider_invocation",
        "execution_effect_claim_count",
        "portal_attempt_binding",
        "portal_implementation_finished",
        "diagnostic_receipt",
    }
    coordination_task = facts.get("coordination_task") if isinstance(facts, Mapping) else None
    coordination_attempt = (
        facts.get("coordination_attempt") if isinstance(facts, Mapping) else None
    )
    coordination_claim = (
        facts.get("coordination_claim") if isinstance(facts, Mapping) else None
    )
    coordination_lease = (
        facts.get("coordination_lease") if isinstance(facts, Mapping) else None
    )
    execution_attempt = (
        facts.get("execution_attempt") if isinstance(facts, Mapping) else None
    )
    provider = (
        facts.get("execution_provider_invocation")
        if isinstance(facts, Mapping)
        else None
    )
    portal_binding = (
        facts.get("portal_attempt_binding") if isinstance(facts, Mapping) else None
    )
    portal_finished = (
        facts.get("portal_implementation_finished")
        if isinstance(facts, Mapping)
        else None
    )
    diagnostic = (
        facts.get("diagnostic_receipt") if isinstance(facts, Mapping) else None
    )
    started_at_ms = handoff.get("started_at_ms")
    if (
        set(handoff) != expected_fields
        or handoff.get("schema") != HANDOFF_BLOCKED_RETRY_SCHEMA
        or handoff.get("command_operation")
        != HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND
        or handoff.get("control_operation")
        != HANDOFF_REPAIR_BLOCKED_RETRY_OPERATION
        or handoff.get("queue_reason") != HANDOFF_REPAIR_BLOCKED_RETRY_REASON
        or handoff.get("source_status") != "blocked"
        or handoff.get("source_revision") != source_attempt.get("task_revision")
        or not isinstance(source_body, Mapping)
        or handoff.get("source_task_body_id")
        != HANDOFF_REPAIR_SOURCE_TASK_BODY_ID
        or _identity(source_body) != HANDOFF_REPAIR_SOURCE_TASK_BODY_ID
        or not isinstance(terminal_receipt, Mapping)
        or _identity(terminal_receipt) != source_completion_receipt_id
        or terminal_receipt.get("operation")
        != "database_portal_terminal_failure"
        or terminal_receipt.get("reason") != "portal_provider_failed"
        or terminal_receipt.get("retryable") is not False
        or handoff.get("source_completion_receipt_id")
        != source_completion_receipt_id
        or handoff.get("source_cooldown_absent") is not True
        or handoff.get("target_status") != "retrying"
        or handoff.get("target_revision") != int(source_attempt["task_revision"]) + 1
        or handoff.get("max_task_attempts_before") != bootstrap_attempt_limit
        or handoff.get("max_task_attempts_after") != current_attempt_limit
        or bootstrap_attempt_limit != int(source_attempt["attempt_number"])
        or current_attempt_limit != int(source_attempt["attempt_number"]) + 1
        or handoff.get("attempt_refunded") is not False
        or handoff.get("fresh_attempt_number") != current_attempt_limit
        or handoff.get("delay_ms") != 0
        or type(started_at_ms) is not int
        or started_at_ms <= 1787743027778
        or handoff.get("retry_not_before_ms") != started_at_ms
        or not isinstance(evidence, Mapping)
        or set(evidence) != {
            "schema",
            "evidence_id",
            "lane_index",
            "stable_binding_id",
            "files",
            "facts",
        }
        or evidence.get("schema") != HANDOFF_BLOCKED_RETRY_SIDECAR_SCHEMA
        or evidence.get("lane_index") != 0
        or evidence.get("stable_binding_id")
        != HANDOFF_REPAIR_STABLE_BINDING_ID
        or re.fullmatch(r"sha256:[0-9a-f]{64}", evidence_id) is None
        or _identity(evidence_body) != evidence_id
        or set(file_map) != set(expected_file_paths)
        or not isinstance(facts, Mapping)
        or set(facts) != expected_fact_fields
        or facts.get("source_attempt") != dict(source_attempt)
        or not isinstance(coordination_task, Mapping)
        or coordination_task.get("status") != "blocked"
        or coordination_task.get("revision") != source_attempt.get("task_revision")
        or not isinstance(coordination_attempt, Mapping)
        or coordination_attempt.get("status") != "expired"
        or coordination_attempt.get("revision") != 2
        or coordination_attempt.get("finished_at_ms") != 1787743027778
        or not isinstance(coordination_claim, Mapping)
        or coordination_claim.get("state") != "expired"
        or coordination_claim.get("revision") != 34
        or coordination_claim.get("expires_at_ms") != 1787743011400
        or not isinstance(coordination_lease, Mapping)
        or coordination_lease.get("state") != "expired"
        or coordination_lease.get("revision") != 34
        or coordination_lease.get("expires_at_ms") != 1787743011400
        or facts.get("coordination_task_completion_count") != 0
        or facts.get("coordination_newer_attempt_count") != 0
        or facts.get("coordination_newer_fence_count") != 0
        or not isinstance(execution_attempt, Mapping)
        or execution_attempt.get("status") != "failed"
        or execution_attempt.get("revision") != 3
        or execution_attempt.get("committed_phase") != "failed"
        or execution_attempt.get("started_at_ms") != 1787742329266
        or execution_attempt.get("finished_at_ms") != 1787742964256
        or facts.get("execution_phase_sequence")
        != [
            {"phase": "claimed", "revision": 1},
            {"phase": "context", "revision": 2},
            {"phase": "failed", "revision": 3},
        ]
        or not isinstance(provider, Mapping)
        or provider.get("callback_state") != "started_outcome_unknown"
        or provider.get("provider_effect_state") != "unknown_may_have_started"
        or provider.get("failure_fingerprint")
        != "sha256:e8a21d888af199e829abba3128a06e576bed90c02ccb60969b241b8f11ed3246"
        or facts.get("execution_effect_claim_count") != 0
        or not isinstance(portal_binding, Mapping)
        or portal_binding.get("binding_id")
        != "sha256:76a22ab25ce1a82aa6faa8d14e5730ddc4eeadd1a10f4a4ff7ef41856356e450"
        or portal_binding.get("task_revision") != 3
        or portal_binding.get("repository_tree_id")
        != "cd81f5731ee64c29161830c9933d6739e0dd3eb3"
        or not isinstance(portal_finished, Mapping)
        or portal_finished.get("event_id")
        != "sha256:7ac8f6ca2076822f6b6711e99fcf16e5b90189109d0dadba502c02252beb8e91"
        or portal_finished.get("projected_task_cid")
        != "baguqeerafge4blotsftqdygafum7kp2kaipqk5n6f5gcbgg54ileqkdh2u4a"
        or portal_finished.get("attempt") != 1
        or portal_finished.get("provider_dispatched") is not True
        or portal_finished.get("attempt_consumed") is not True
        or portal_finished.get("returncode") != 78
        or not isinstance(diagnostic, Mapping)
        or diagnostic.get("receipt_id")
        != "baguqeerajm2bu5i3iejl4lmxf3nrew3ljnkxwl3odujmxfp26dxnqx6wygja"
        or diagnostic.get("failure_id")
        != "baguqeeraseeqvjzceffsvxnadwjymhzmje6kzraydbjnr35q63wmccmx42bq"
        or diagnostic.get("reason_code") != "stale_proposal_replay"
    ):
        raise OperatorError("PCSM blocked-retry handoff is not admitted")
    for role, expected_path in expected_file_paths.items():
        item = file_map[role]
        if (
            set(item) != {"role", "path", "sha256", "size_bytes"}
            or item.get("role") != role
            or item.get("path") != expected_path
            or re.fullmatch(r"sha256:[0-9a-f]{64}", str(item.get("sha256") or ""))
            is None
            or type(item.get("size_bytes")) is not int
            or int(item["size_bytes"]) < 1
        ):
            raise OperatorError("PCSM blocked-retry file evidence is not exact")
        _safe_path(ROOT, expected_path, field=f"blocked_retry_handoff.{role}")
    return handoff


def _verified_generation_replay_repair(
    *,
    sealed_operator_identity: str,
    current_operator_identity: str,
    current_head: str,
) -> dict[str, Any]:
    """Admit only the generation-7 idempotent-replay revision correction."""

    payload = _json_mapping_bytes(
        _tracked_bytes(HANDOFF_GENERATION_REPLAY_REPAIR_PATH, head=current_head),
        field="PCSM restart generation replay repair receipt",
    )
    expected_fields = {
        "schema",
        "reason",
        "source_replay_repair_receipt_id",
        "sealed_outer_commit",
        "sealed_outer_tree",
        "sealed_operator_identity",
        "repair_base_commit",
        "repair_base_tree",
        "repair_base_operator_identity",
        "current_operator_identity",
        "exact_change",
        "failed_restart",
        "durable_generation_evidence",
        "recovery_already_committed",
        "attempt_refunded",
        "manual_database_mutation",
        "receipt_id",
    }
    exact_change = payload.get("exact_change")
    failed_restart = payload.get("failed_restart")
    generation_evidence = payload.get("durable_generation_evidence")
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    operator_path = Path(__file__).resolve()
    relative_operator = operator_path.relative_to(ROOT).as_posix()
    base_commit = HANDOFF_GENERATION_REPLAY_REPAIR_BASE_COMMIT
    if (
        set(payload) != expected_fields
        or payload.get("schema")
        != HANDOFF_GENERATION_REPLAY_REPAIR_SCHEMA
        or payload.get("reason")
        != "generation_7_zero_revision_idempotent_replay"
        or payload.get("source_replay_repair_receipt_id")
        != HANDOFF_REPLAY_REPAIR_SEALED_RECEIPT_ID
        or payload.get("sealed_outer_commit")
        != HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_COMMIT
        or payload.get("sealed_outer_tree")
        != HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_TREE
        or payload.get("sealed_operator_identity")
        != HANDOFF_REPLAY_REPAIR_SEALED_OPERATOR_IDENTITY
        or sealed_operator_identity
        != HANDOFF_REPLAY_REPAIR_SEALED_OPERATOR_IDENTITY
        or payload.get("repair_base_commit") != base_commit
        or not isinstance(exact_change, Mapping)
        or dict(exact_change)
        != {
            "field": "idempotent_replay_store_revision",
            "previous_invariant": (
                "result_revision_at_least_original_store_revision_plus_one"
            ),
            "admitted_invariant": (
                "result_matches_unchanged_current_generation_revision"
            ),
            "accepted_generation": 7,
            "accepted_fence_epoch": 7,
            "accepted_revision_before": 0,
            "accepted_revision_after": 0,
        }
        or not isinstance(failed_restart, Mapping)
        or dict(failed_restart)
        != {
            "owner_generation": 7,
            "owner_fence_epoch": 7,
            "task_status": "retrying",
            "task_revision": 5,
            "command_id": (
                "cmd:blocked-retry-recovery:"
                "ee9b5a7a09bbc060ac83799b4c31474499a69580534f160f5605b30d0a147cd7"
            ),
            "idempotency_key": (
                "executor-blocked-retry-recovery:"
                "ee9b5a7a09bbc060ac83799b4c31474499a69580534f160f5605b30d0a147cd7"
            ),
            "result_digest": (
                "sha256:ba3a88d6bd6f2c848b273fb5362919909fa6c9d0813258df089a0cc08bc04f1e"
            ),
            "error": "blocked-retry owner command was not exactly admitted",
        }
        or not isinstance(generation_evidence, Mapping)
        or dict(generation_evidence)
        != {
            "accepted_command_generation": {
                "generation": 6,
                "fence_epoch": 6,
                "revision_after": 1,
                "store_revision_before": 0,
                "birth_id": "birth:e787b5521732b8e883cd5b37f7792218",
            },
            "failed_replay_generation": {
                "generation": 7,
                "fence_epoch": 7,
                "revision_before": 0,
                "revision_after": 0,
                "birth_id": "birth:588998262d8d7feac01bc2982b080d52",
            },
        }
        or payload.get("recovery_already_committed") is not True
        or payload.get("attempt_refunded") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError(
            "PCSM restart generation replay repair receipt is not admitted"
        )

    if (
        _git_commit_tree(
            HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_COMMIT,
            field="sealed generation replay repair commit",
        )
        != HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_TREE
        or _git_commit_tree(base_commit, field="generation replay repair base")
        != payload.get("repair_base_tree")
    ):
        raise OperatorError("PCSM generation replay repair tree binding changed")
    _git_is_ancestor(
        HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_COMMIT,
        base_commit,
        field="generation replay repair base lineage",
    )
    _git_is_ancestor(
        base_commit,
        current_head,
        field="generation replay repair current lineage",
    )
    parents = str(_git("show", "-s", "--format=%P", base_commit)).strip().split()
    changed_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_COMMIT}"
                f"..{base_commit}",
            )
        ).splitlines()
        if line
    )
    sealed_bytes = _git_blob_at(
        head=HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_COMMIT,
        path=operator_path,
        field="sealed zero-revision replay operator",
    )
    base_bytes = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="generation replay repair base operator",
    )
    current_bytes = _tracked_bytes(operator_path, head=current_head)
    pending_base = (
        "PENDING_" + "GENERATION_REPLAY_REPAIR_BASE_COMMIT"
    ).encode("ascii")
    call_start = b"        result = client." + b"recover_blocked_task_retry(\n"
    call_start_with_generation = (
        b"        generation_before = client.load_generation()\n" + call_start
    )
    call_end = b"".join(
        (
            b"            now_ms=int(blocked_retry_handoff.get(\"started_at_ms\") ",
            b"or -1),\n",
            b"        )\n",
            b"    finally:\n",
        )
    )
    call_end_with_generation = b"".join(
        (
            b"            now_ms=int(blocked_retry_handoff.get(\"started_at_ms\") ",
            b"or -1),\n",
            b"        )\n",
            b"        generation_after = client.load_generation()\n",
            b"    finally:\n",
        )
    )
    old_revision_checks = b"".join(
        (
            b"        or result.result_digest != _identity(result_body)\n",
            b"        or result.revision < store_revision_before + 1\n",
            b"        or (\n",
            b"            blocked_retry_state == \"pending_apply\"\n",
            b"            and result.revision != store_revision_before + 1\n",
            b"        )\n",
            b"        or result.generation != int(identity.generation)\n",
            b"        or result.fence_epoch != int(identity.fence_epoch)\n",
        )
    )
    new_revision_checks = b"".join(
        (
            b"        or result.result_digest != _identity(result_body)\n",
            b"        or generation_before.generation != int(identity.generation)\n",
            b"        or generation_before.fence_epoch != int(identity.fence_epoch)\n",
            b"        or generation_after.generation != int(identity.generation)\n",
            b"        or generation_after.fence_epoch != int(identity.fence_epoch)\n",
            b"        or result.generation != generation_after.generation\n",
            b"        or result.fence_epoch != generation_after.fence_epoch\n",
            b"        or result.revision != generation_after.revision\n",
            b"        or (\n",
            b"            blocked_retry_state == \"pending_apply\"\n",
            b"            and (\n",
            b"                generation_before.revision != store_revision_before\n",
            b"                or generation_after.revision\n",
            b"                != store_revision_before + 1\n",
            b"            )\n",
            b"        )\n",
            b"        or (\n",
            b"            blocked_retry_state == \"command_replay_required\"\n",
            b"            and generation_after.to_dict()\n",
            b"            != generation_before.to_dict()\n",
            b"        )\n",
        )
    )
    expected_current = (
        base_bytes.replace(pending_base, base_commit.encode("ascii"), 1)
        .replace(call_start, call_start_with_generation, 1)
        .replace(call_end, call_end_with_generation, 1)
        .replace(old_revision_checks, new_revision_checks, 1)
    )
    if (
        parents != [HANDOFF_GENERATION_REPLAY_REPAIR_SEALED_OUTER_COMMIT]
        or changed_paths != (relative_operator,)
        or _identity(sealed_bytes)
        != HANDOFF_REPLAY_REPAIR_SEALED_OPERATOR_IDENTITY
        or _identity(base_bytes)
        != payload.get("repair_base_operator_identity")
        or base_bytes.count(pending_base) != 1
        or base_bytes.count(call_start) != 1
        or base_bytes.count(call_end) != 1
        or base_bytes.count(old_revision_checks) != 1
    ):
        raise OperatorError("PCSM generation replay repair source delta changed")
    if current_bytes != expected_current:
        _verified_handoff_command_authority_repair(
            sealed_operator_identity=_identity(expected_current),
            current_operator_identity=current_operator_identity,
            current_head=current_head,
        )
    elif _identity(current_bytes) != current_operator_identity:
        raise OperatorError("PCSM generation replay repair identity changed")
    return payload


def _verified_handoff_command_authority_repair(
    *,
    sealed_operator_identity: str,
    current_operator_identity: str,
    current_head: str,
) -> dict[str, Any]:
    """Admit only separation of current-head and durable retry identities."""

    payload = _json_mapping_bytes(
        _tracked_bytes(HANDOFF_COMMAND_AUTHORITY_REPAIR_PATH, head=current_head),
        field="PCSM restart command-authority repair receipt",
    )
    expected_fields = {
        "schema",
        "reason",
        "source_generation_replay_repair_receipt_id",
        "sealed_outer_commit",
        "sealed_outer_tree",
        "sealed_operator_identity",
        "repair_base_commit",
        "repair_base_tree",
        "repair_base_operator_identity",
        "current_operator_identity",
        "current_source_handoff",
        "historical_command_authority",
        "exact_change",
        "durable_replay",
        "nested_accelerator_repair",
        "validation",
        "historical_replay_receipts_preserved",
        "attempt_refunded",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    current_handoff = payload.get("current_source_handoff")
    historical = payload.get("historical_command_authority")
    exact_change = payload.get("exact_change")
    durable_replay = payload.get("durable_replay")
    accelerator_repair = payload.get("nested_accelerator_repair")
    validation = payload.get("validation")
    operator_path = Path(__file__).resolve()
    relative_operator = operator_path.relative_to(ROOT).as_posix()
    base_commit = HANDOFF_COMMAND_AUTHORITY_REPAIR_BASE_COMMIT
    expected_accelerator_paths = [
        "ipfs_accelerate_py/agent_supervisor/task_sources/"
        "control_plane_contracts.py",
        "ipfs_accelerate_py/agent_supervisor/task_sources/"
        "quack_state_client.py",
        "ipfs_accelerate_py/agent_supervisor/task_sources/"
        "typed_database_task_source.py",
        "ipfs_accelerate_py/agent_supervisor/task_sources/"
        "typed_state_owner.py",
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_daemon.py",
        "scripts/run_agent_supervisor_causal_event_federation.py",
        "test/api/causal_federation/test_admitted_executor.py",
        "test/api/test_agent_supervisor_database_implementation_daemon.py",
    ]
    expected_exact_change = {
        "field": "operator_handoff_receipt_id",
        "previous_authority": "current_source_handoff_receipt_id",
        "admitted_authority": "historical_sealed_handoff_receipt_id",
        "expected_recovery_receipt_changed": True,
        "recovery_command_changed": True,
        "owner_restart_admission_reporting_changed": False,
        "current_source_handoff_remains_content_addressed": True,
    }
    expected_durable_replay = {
        "task_cid": HANDOFF_REPAIR_TASK_CID,
        "task_status_after_recovery": "retrying",
        "task_revision_after_recovery": 5,
        "operator_handoff_receipt_id": HANDOFF_REPAIR_SEALED_RECEIPT_ID,
        "command_id": (
            "cmd:blocked-retry-recovery:"
            "ee9b5a7a09bbc060ac83799b4c31474499a69580534f160f5605b30d0a147cd7"
        ),
        "idempotency_key": (
            "executor-blocked-retry-recovery:"
            "ee9b5a7a09bbc060ac83799b4c31474499a69580534f160f5605b30d0a147cd7"
        ),
        "result_digest": (
            "sha256:ba3a88d6bd6f2c848b273fb5362919909fa6c9d0813258df089a0cc08bc04f1e"
        ),
        "replay_outcome": "idempotent_replay",
        "replay_changed": False,
    }
    expected_accelerator_repair = {
        "repository": "external/ipfs_accelerate",
        "prior_commit": "4d4f361c424c2543dc3b25597af12cdd5d961e0c",
        "prior_tree": "c2a1f18bb0d383d90ebae74037a489fb3034d428",
        "repair_commit": "45f8abca891ce304d56aac0ea5113b4cde9a7b60",
        "repair_tree": "f1048b00fb4df02824bcbf2bcc85951df0546eab",
        "merge_commit": "82f31f60cadb4b243d9d4d38e6040d3118fb90a8",
        "merge_tree": "f1048b00fb4df02824bcbf2bcc85951df0546eab",
        "merge_parents": [
            "4d4f361c424c2543dc3b25597af12cdd5d961e0c",
            "45f8abca891ce304d56aac0ea5113b4cde9a7b60",
        ],
        "changed_paths": expected_accelerator_paths,
    }
    if (
        set(payload) != expected_fields
        or payload.get("schema") != HANDOFF_COMMAND_AUTHORITY_REPAIR_SCHEMA
        or payload.get("reason")
        != "typed_attempt_terminal_transition_command_authority_separation"
        or payload.get("source_generation_replay_repair_receipt_id")
        != "sha256:4af075a3eecf56687c90ebd416132f83630c646a0c44210ca680aefca2bb0b67"
        or payload.get("sealed_outer_commit")
        != HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_COMMIT
        or payload.get("sealed_outer_tree")
        != HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_TREE
        or payload.get("sealed_operator_identity")
        != HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OPERATOR_IDENTITY
        or sealed_operator_identity
        != HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OPERATOR_IDENTITY
        or payload.get("repair_base_commit") != base_commit
        or payload.get("current_operator_identity")
        != current_operator_identity
        or not isinstance(current_handoff, Mapping)
        or set(current_handoff) != {"path", "receipt_id"}
        or current_handoff.get("path")
        != HANDOFF_REPAIR_PATH.relative_to(ROOT).as_posix()
        or not isinstance(historical, Mapping)
        or dict(historical)
        != {
            "path": HANDOFF_REPAIR_PATH.relative_to(ROOT).as_posix(),
            "sealed_outer_commit": HANDOFF_REPAIR_SEALED_OUTER_COMMIT,
            "receipt_id": HANDOFF_REPAIR_SEALED_RECEIPT_ID,
        }
        or not isinstance(exact_change, Mapping)
        or dict(exact_change) != expected_exact_change
        or not isinstance(durable_replay, Mapping)
        or dict(durable_replay) != expected_durable_replay
        or not isinstance(accelerator_repair, Mapping)
        or dict(accelerator_repair) != expected_accelerator_repair
        or not isinstance(validation, Mapping)
        or dict(validation)
        != {
            "typed_admission_lifecycle_tests": 15,
            "typed_admission_lifecycle_outcome": "passed",
            "current_handoff_required_validations": 6,
            "current_handoff_required_outcome": "passed",
            "measurement_status": "measured",
        }
        or payload.get("historical_replay_receipts_preserved") is not True
        or payload.get("attempt_refunded") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError("PCSM command-authority repair receipt is not admitted")

    current_handoff_bytes = _tracked_bytes(HANDOFF_REPAIR_PATH, head=current_head)
    current_handoff_body = _json_mapping_bytes(
        current_handoff_bytes,
        field="PCSM current-source handoff receipt",
    )
    historical_handoff_bytes = _git_blob_at(
        head=HANDOFF_REPAIR_SEALED_OUTER_COMMIT,
        path=HANDOFF_REPAIR_PATH,
        field="historical PCSM handoff receipt",
    )
    historical_handoff_body = _json_mapping_bytes(
        historical_handoff_bytes,
        field="historical PCSM handoff receipt",
    )
    if (
        current_handoff.get("receipt_id")
        != current_handoff_body.get("receipt_id")
        or current_handoff.get("receipt_id") == HANDOFF_REPAIR_SEALED_RECEIPT_ID
        or _identity(
            {
                key: value
                for key, value in current_handoff_body.items()
                if key != "receipt_id"
            }
        )
        != current_handoff.get("receipt_id")
        or historical_handoff_body.get("receipt_id")
        != HANDOFF_REPAIR_SEALED_RECEIPT_ID
        or _identity(
            {
                key: value
                for key, value in historical_handoff_body.items()
                if key != "receipt_id"
            }
        )
        != HANDOFF_REPAIR_SEALED_RECEIPT_ID
    ):
        raise OperatorError("PCSM current and historical handoff identities diverged")

    accelerator_repository = ROOT / "external" / "ipfs_accelerate"
    for field, commit, tree in (
        (
            "prior accelerator",
            expected_accelerator_repair["prior_commit"],
            expected_accelerator_repair["prior_tree"],
        ),
        (
            "typed-admission repair",
            expected_accelerator_repair["repair_commit"],
            expected_accelerator_repair["repair_tree"],
        ),
        (
            "typed-admission merge",
            expected_accelerator_repair["merge_commit"],
            expected_accelerator_repair["merge_tree"],
        ),
    ):
        if _git_commit_tree(commit, field=field, repository=accelerator_repository) != tree:
            raise OperatorError(f"{field} tree changed")
    merge_parents = subprocess.run(
        ["git", "show", "-s", "--format=%P", expected_accelerator_repair["merge_commit"]],
        cwd=accelerator_repository,
        text=True,
        capture_output=True,
        check=False,
    )
    changed_paths = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{expected_accelerator_repair['prior_commit']}.."
            f"{expected_accelerator_repair['repair_commit']}",
        ],
        cwd=accelerator_repository,
        text=True,
        capture_output=True,
        check=False,
    )
    if (
        merge_parents.returncode != 0
        or merge_parents.stdout.strip().split()
        != expected_accelerator_repair["merge_parents"]
        or changed_paths.returncode != 0
        or sorted(changed_paths.stdout.splitlines()) != expected_accelerator_paths
    ):
        raise OperatorError("PCSM typed-admission accelerator repair lineage changed")

    if (
        _git_commit_tree(
            HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_COMMIT,
            field="sealed command-authority repair commit",
        )
        != HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_TREE
        or _git_commit_tree(base_commit, field="command-authority repair base")
        != payload.get("repair_base_tree")
    ):
        raise OperatorError("PCSM command-authority repair tree binding changed")
    _git_is_ancestor(
        base_commit,
        current_head,
        field="command-authority repair current lineage",
    )
    parents = str(_git("show", "-s", "--format=%P", base_commit)).strip().split()
    changed_outer_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_COMMIT}.."
                f"{base_commit}",
            )
        ).splitlines()
        if line
    )
    sealed_bytes = _git_blob_at(
        head=HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_COMMIT,
        path=operator_path,
        field="sealed command-authority operator",
    )
    base_bytes = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="command-authority repair base operator",
    )
    current_bytes = _tracked_bytes(operator_path, head=current_head)
    pending_base = (
        "PENDING_" + "HANDOFF_COMMAND_AUTHORITY_REPAIR_BASE_COMMIT"
    ).encode("ascii")
    expected_current = base_bytes.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    )
    stable_expected_receipt = (
        b'"operator_handoff_receipt_id": HANDOFF_REPAIR_SEALED_RECEIPT_ID'
    )
    stable_command_argument = (
        b"handoff_receipt_id = HANDOFF_REPAIR_SEALED_RECEIPT_ID"
    )
    if (
        parents != [HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OUTER_COMMIT]
        or changed_outer_paths != (relative_operator,)
        or _identity(sealed_bytes)
        != HANDOFF_COMMAND_AUTHORITY_REPAIR_SEALED_OPERATOR_IDENTITY
        or _identity(base_bytes) != payload.get("repair_base_operator_identity")
        or base_bytes.count(pending_base) != 1
        or base_bytes.count(stable_expected_receipt) != 3
        or base_bytes.count(stable_command_argument) != 2
    ):
        raise OperatorError("PCSM command-authority repair source delta changed")
    if current_bytes != expected_current:
        _verified_handoff_command_authority_verifier_repair(
            sealed_operator_identity=_identity(expected_current),
            current_operator_identity=current_operator_identity,
            current_head=current_head,
        )
    elif _identity(current_bytes) != current_operator_identity:
        raise OperatorError("PCSM command-authority repair identity changed")
    return payload


def _verified_handoff_command_authority_verifier_repair(
    *,
    sealed_operator_identity: str,
    current_operator_identity: str,
    current_head: str,
) -> dict[str, Any]:
    """Admit only corrected self-witness counts and descendant delegation."""

    payload = _json_mapping_bytes(
        _tracked_bytes(HANDOFF_COMMAND_VERIFIER_REPAIR_PATH, head=current_head),
        field="PCSM restart command-verifier repair receipt",
    )
    expected_fields = {
        "schema",
        "reason",
        "source_command_authority_repair_receipt_id",
        "sealed_outer_commit",
        "sealed_outer_tree",
        "sealed_operator_identity",
        "repair_base_commit",
        "repair_base_tree",
        "repair_base_operator_identity",
        "current_operator_identity",
        "exact_change",
        "validation",
        "attempt_refunded",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    exact_change = payload.get("exact_change")
    validation = payload.get("validation")
    operator_path = Path(__file__).resolve()
    relative_operator = operator_path.relative_to(ROOT).as_posix()
    base_commit = HANDOFF_COMMAND_VERIFIER_REPAIR_BASE_COMMIT
    if (
        set(payload) != expected_fields
        or payload.get("schema") != HANDOFF_COMMAND_VERIFIER_REPAIR_SCHEMA
        or payload.get("reason")
        != "command_authority_source_witness_count_correction"
        or payload.get("source_command_authority_repair_receipt_id")
        != "sha256:a21810696ed9824fcd872ae7a0b6efe90204a03b96b73d24970afbeb74c3d3b3"
        or payload.get("sealed_outer_commit")
        != HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_COMMIT
        or payload.get("sealed_outer_tree")
        != HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_TREE
        or payload.get("sealed_operator_identity")
        != HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OPERATOR_IDENTITY
        or sealed_operator_identity
        != HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OPERATOR_IDENTITY
        or payload.get("repair_base_commit") != base_commit
        or payload.get("current_operator_identity")
        != current_operator_identity
        or not isinstance(exact_change, Mapping)
        or dict(exact_change)
        != {
            "stable_expected_receipt_pattern_previous_count": 1,
            "stable_expected_receipt_pattern_observed_count": 3,
            "stable_command_argument_pattern_previous_count": 1,
            "stable_command_argument_pattern_observed_count": 2,
            "current_operator_mismatch_action_before": "reject",
            "current_operator_mismatch_action_after": (
                "verify_exact_descendant_repair"
            ),
            "durable_command_identity_changed": False,
            "database_state_changed": False,
        }
        or not isinstance(validation, Mapping)
        or dict(validation)
        != {
            "base_source_counts_measured": True,
            "base_expected_receipt_pattern_count": 3,
            "base_command_argument_pattern_count": 2,
            "measurement_status": "measured",
        }
        or payload.get("attempt_refunded") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError("PCSM command-verifier repair receipt is not admitted")
    if (
        _git_commit_tree(
            HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_COMMIT,
            field="sealed command-verifier repair commit",
        )
        != HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_TREE
        or _git_commit_tree(base_commit, field="command-verifier repair base")
        != payload.get("repair_base_tree")
    ):
        raise OperatorError("PCSM command-verifier repair tree binding changed")
    _git_is_ancestor(
        base_commit,
        current_head,
        field="command-verifier repair current lineage",
    )
    parents = str(_git("show", "-s", "--format=%P", base_commit)).strip().split()
    changed_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_COMMIT}.."
                f"{base_commit}",
            )
        ).splitlines()
        if line
    )
    sealed_bytes = _git_blob_at(
        head=HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_COMMIT,
        path=operator_path,
        field="sealed command-verifier operator",
    )
    base_bytes = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="command-verifier repair base operator",
    )
    current_bytes = _tracked_bytes(operator_path, head=current_head)
    pending_base = (
        "PENDING_" + "HANDOFF_COMMAND_VERIFIER_REPAIR_BASE_COMMIT"
    ).encode("ascii")
    expected_current = base_bytes.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    )
    if (
        parents != [HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OUTER_COMMIT]
        or changed_paths != (relative_operator,)
        or _identity(sealed_bytes)
        != HANDOFF_COMMAND_VERIFIER_REPAIR_SEALED_OPERATOR_IDENTITY
        or _identity(base_bytes) != payload.get("repair_base_operator_identity")
        or base_bytes.count(pending_base) != 1
    ):
        raise OperatorError("PCSM command-verifier repair source delta changed")
    if current_bytes != expected_current:
        _verified_bootstrap_broker_resilience_repair(
            sealed_operator_identity=_identity(expected_current),
            current_operator_identity=current_operator_identity,
            current_head=current_head,
        )
    elif _identity(current_bytes) != current_operator_identity:
        raise OperatorError("PCSM command-verifier repair identity changed")
    return payload


def _validation_path_compatibility_transition_payload(
    *,
    current_head: str,
) -> tuple[bytes, dict[str, Any]]:
    """Load the exact add-only validation-path compatibility receipt."""

    receipt_bytes = _tracked_bytes(
        VALIDATION_PATH_COMPATIBILITY_TRANSITION_PATH,
        head=current_head,
    )
    payload = _json_mapping_bytes(
        receipt_bytes,
        field="validation-path compatibility transition receipt",
    )
    required_fields = {
        "schema",
        "reason",
        "prior_checkpoint",
        "repair_base",
        "sealed_source",
        "validation_surface",
        "validations",
        "historical_receipts_preserved",
        "database_authority_preserved",
        "task_state_mutation",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    if (
        set(payload) != required_fields
        or payload.get("schema")
        != VALIDATION_PATH_COMPATIBILITY_TRANSITION_SCHEMA
        or payload.get("reason")
        != "restore_declared_agent_supervisor_validation_path"
        or not isinstance(payload.get("prior_checkpoint"), Mapping)
        or not isinstance(payload.get("repair_base"), Mapping)
        or not isinstance(payload.get("sealed_source"), Mapping)
        or not isinstance(payload.get("validation_surface"), Mapping)
        or not isinstance(payload.get("validations"), list)
        or payload.get("historical_receipts_preserved") is not True
        or payload.get("database_authority_preserved") is not True
        or payload.get("task_state_mutation") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError(
            "validation-path compatibility transition seal is invalid"
        )
    return receipt_bytes, payload


def _verified_validation_path_compatibility_operator_descendant(
    *,
    current_operator: bytes,
    current_head: str,
    operator_path: Path,
) -> dict[str, Any]:
    """Admit only the placeholder-sealed operator and add-only receipt chain."""

    base_commit = VALIDATION_PATH_COMPATIBILITY_TRANSITION_BASE_COMMIT
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        raise OperatorError(
            "validation-path compatibility transition base is unsealed"
        )
    receipt_bytes, payload = _validation_path_compatibility_transition_payload(
        current_head=current_head
    )
    checkpoint = payload["prior_checkpoint"]
    repair_base = payload["repair_base"]
    sealed_source = payload["sealed_source"]
    if (
        checkpoint.get("source_head")
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD
        or checkpoint.get("repository_tree_id")
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE
        or checkpoint.get("prior_artifact_commit")
        != "9b056251a42aac444478745b3ccb73e3507215e8"
        or checkpoint.get("stale_worktree_cleanup_transition_receipt_id")
        != "sha256:4d86e1fa4452a720859175d2e228dd09f50f92159577154f96ade16cb6e5e0b7"
        or repair_base.get("source_head") != base_commit
        or repair_base.get("parent")
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD
        or sealed_source.get("parent") != base_commit
    ):
        raise OperatorError(
            "validation-path compatibility operator checkpoint changed"
        )
    if (
        _git_commit_tree(
            VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
            field="validation-path compatibility checkpoint",
        )
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE
        or _git_commit_tree(
            base_commit,
            field="validation-path compatibility repair base",
        )
        != repair_base.get("repository_tree_id")
    ):
        raise OperatorError(
            "validation-path compatibility operator tree binding changed"
        )

    relative_operator = operator_path.relative_to(ROOT).as_posix()
    expected_base_paths = (
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        relative_operator,
        "test/test_pcsm_validation_path_compatibility_transition.py",
    )
    base_parents = str(
        _git("show", "-s", "--format=%P", base_commit)
    ).strip().split()
    base_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD}..{base_commit}",
            )
        ).splitlines()
        if line
    )
    base_operator = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="validation-path compatibility base operator",
    )
    pending_base = (
        "PENDING_" + "VALIDATION_PATH_COMPATIBILITY_TRANSITION_BASE_COMMIT"
    ).encode("ascii")
    expected_operator = base_operator.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    )
    sealed_head = str(sealed_source.get("source_head") or "")
    sealed_tree = _git_commit_tree(
        sealed_head,
        field="validation-path compatibility sealed source",
    )
    sealed_parents = str(
        _git("show", "-s", "--format=%P", sealed_head)
    ).strip().split()
    sealed_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{base_commit}..{sealed_head}")
        ).splitlines()
        if line
    )
    sealed_operator = _git_blob_at(
        head=sealed_head,
        path=operator_path,
        field="validation-path compatibility sealed operator",
    )
    if (
        base_parents
        != [VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD]
        or base_paths != expected_base_paths
        or tuple(repair_base.get("changed_paths") or ())
        != expected_base_paths
        or repair_base.get("operator_identity") != _identity(base_operator)
        or base_operator.count(pending_base) != 1
        or sealed_source.get("repository_tree_id") != sealed_tree
        or sealed_parents != [base_commit]
        or sealed_paths != (relative_operator,)
        or tuple(sealed_source.get("changed_paths") or ())
        != (relative_operator,)
        or sealed_source.get("operator_identity")
        != _identity(expected_operator)
        or sealed_operator != expected_operator
    ):
        raise OperatorError(
            "validation-path compatibility operator delta changed"
        )

    receipt_relative = VALIDATION_PATH_COMPATIBILITY_TRANSITION_PATH.relative_to(
        ROOT
    ).as_posix()
    additions = tuple(
        line
        for line in str(
            _git(
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                receipt_relative,
            )
        ).splitlines()
        if line
    )
    if len(additions) != 1:
        raise OperatorError(
            "validation-path compatibility receipt introduction is not exact"
        )
    artifact_commit = additions[0]
    artifact_parents = str(
        _git("show", "-s", "--format=%P", artifact_commit)
    ).strip().split()
    artifact_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{sealed_head}..{artifact_commit}")
        ).splitlines()
        if line
    )
    if (
        artifact_parents != [sealed_head]
        or artifact_paths != (receipt_relative,)
        or _git_blob_at(
            head=artifact_commit,
            path=VALIDATION_PATH_COMPATIBILITY_TRANSITION_PATH,
            field="introduced validation-path compatibility receipt",
        )
        != receipt_bytes
    ):
        raise OperatorError(
            "validation-path compatibility artifact commit changed"
        )
    _git_is_ancestor(
        artifact_commit,
        current_head,
        field="validation-path compatibility artifact-to-current lineage",
    )
    database_watchdog_activity_transition: dict[str, Any] = {}
    if current_operator != expected_operator:
        database_watchdog_activity_transition = (
            _verified_database_watchdog_activity_operator_descendant(
                current_operator=current_operator,
                current_head=current_head,
                operator_path=operator_path,
            )
        )
    return {
        "receipt": payload,
        "receipt_bytes": receipt_bytes,
        "artifact_commit": artifact_commit,
        "base_commit": base_commit,
        "base_operator": base_operator,
        "sealed_source_head": sealed_head,
        "sealed_source_tree": sealed_tree,
        "expected_operator": expected_operator,
        "database_watchdog_activity_transition": (
            database_watchdog_activity_transition
        ),
    }


def _database_watchdog_activity_transition_payload(
    *,
    current_head: str,
) -> tuple[bytes, dict[str, Any]]:
    """Load the exact add-only database-watchdog activity receipt."""

    receipt_bytes = _tracked_bytes(
        DATABASE_WATCHDOG_ACTIVITY_TRANSITION_PATH,
        head=current_head,
    )
    payload = _json_mapping_bytes(
        receipt_bytes,
        field="database-watchdog activity transition receipt",
    )
    required_fields = {
        "schema",
        "reason",
        "prior_checkpoint",
        "repair_base",
        "sealed_source",
        "watchdog_activity_contract",
        "validations",
        "historical_receipts_preserved",
        "database_authority_preserved",
        "task_state_mutation",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    if (
        set(payload) != required_fields
        or payload.get("schema")
        != DATABASE_WATCHDOG_ACTIVITY_TRANSITION_SCHEMA
        or payload.get("reason")
        != "defer_stale_projection_watchdog_for_exact_successor_database_activity"
        or not isinstance(payload.get("prior_checkpoint"), Mapping)
        or not isinstance(payload.get("repair_base"), Mapping)
        or not isinstance(payload.get("sealed_source"), Mapping)
        or not isinstance(payload.get("watchdog_activity_contract"), Mapping)
        or not isinstance(payload.get("validations"), list)
        or payload.get("historical_receipts_preserved") is not True
        or payload.get("database_authority_preserved") is not True
        or payload.get("task_state_mutation") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError(
            "database-watchdog activity transition seal is invalid"
        )
    return receipt_bytes, payload


def _verified_database_watchdog_activity_operator_descendant(
    *,
    current_operator: bytes,
    current_head: str,
    operator_path: Path,
) -> dict[str, Any]:
    """Admit only the exact watchdog B/S/A source transition."""

    base_commit = DATABASE_WATCHDOG_ACTIVITY_TRANSITION_BASE_COMMIT
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        raise OperatorError(
            "database-watchdog activity transition base is unsealed"
        )
    receipt_bytes, payload = _database_watchdog_activity_transition_payload(
        current_head=current_head
    )
    checkpoint = payload["prior_checkpoint"]
    repair_base = payload["repair_base"]
    sealed_source = payload["sealed_source"]
    if (
        checkpoint.get("source_head")
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD
        or checkpoint.get("repository_tree_id")
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_TREE
        or checkpoint.get("prior_artifact_commit")
        != "c6e4a75f03662d9fe2ed26246735638d9be3ae88"
        or checkpoint.get(
            "validation_path_compatibility_transition_receipt_id"
        )
        != "sha256:e9aa30a3d9e1a1e5603b463bbcc38ba52cee745c66712d5a9d33c83bb4781485"
        or repair_base.get("source_head") != base_commit
        or repair_base.get("parent")
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD
        or sealed_source.get("parent") != base_commit
    ):
        raise OperatorError(
            "database-watchdog activity operator checkpoint changed"
        )
    if (
        _git_commit_tree(
            DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
            field="database-watchdog activity checkpoint",
        )
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_TREE
        or _git_commit_tree(
            base_commit,
            field="database-watchdog activity repair base",
        )
        != repair_base.get("repository_tree_id")
    ):
        raise OperatorError(
            "database-watchdog activity operator tree binding changed"
        )

    relative_operator = operator_path.relative_to(ROOT).as_posix()
    expected_base_paths = (
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        relative_operator,
        "test/test_pcsm_database_watchdog_activity_transition.py",
    )
    base_parents = str(
        _git("show", "-s", "--format=%P", base_commit)
    ).strip().split()
    base_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD}..{base_commit}",
            )
        ).splitlines()
        if line
    )
    base_operator = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="database-watchdog activity base operator",
    )
    pending_base = (
        "PENDING_" + "DATABASE_WATCHDOG_ACTIVITY_TRANSITION_BASE_COMMIT"
    ).encode("ascii")
    expected_operator = base_operator.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    )
    sealed_head = str(sealed_source.get("source_head") or "")
    sealed_tree = _git_commit_tree(
        sealed_head,
        field="database-watchdog activity sealed source",
    )
    sealed_parents = str(
        _git("show", "-s", "--format=%P", sealed_head)
    ).strip().split()
    sealed_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{base_commit}..{sealed_head}")
        ).splitlines()
        if line
    )
    sealed_operator = _git_blob_at(
        head=sealed_head,
        path=operator_path,
        field="database-watchdog activity sealed operator",
    )
    if (
        base_parents
        != [DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD]
        or base_paths != expected_base_paths
        or tuple(repair_base.get("changed_paths") or ())
        != expected_base_paths
        or repair_base.get("operator_identity") != _identity(base_operator)
        or base_operator.count(pending_base) != 1
        or sealed_source.get("repository_tree_id") != sealed_tree
        or sealed_parents != [base_commit]
        or sealed_paths != (relative_operator,)
        or tuple(sealed_source.get("changed_paths") or ())
        != (relative_operator,)
        or sealed_source.get("operator_identity")
        != _identity(expected_operator)
        or sealed_operator != expected_operator
        or current_operator != expected_operator
    ):
        raise OperatorError(
            "database-watchdog activity operator delta changed"
        )

    receipt_relative = DATABASE_WATCHDOG_ACTIVITY_TRANSITION_PATH.relative_to(
        ROOT
    ).as_posix()
    additions = tuple(
        line
        for line in str(
            _git(
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                receipt_relative,
            )
        ).splitlines()
        if line
    )
    if len(additions) != 1:
        raise OperatorError(
            "database-watchdog activity receipt introduction is not exact"
        )
    artifact_commit = additions[0]
    artifact_parents = str(
        _git("show", "-s", "--format=%P", artifact_commit)
    ).strip().split()
    artifact_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{sealed_head}..{artifact_commit}")
        ).splitlines()
        if line
    )
    if (
        artifact_parents != [sealed_head]
        or artifact_paths != (receipt_relative,)
        or _git_blob_at(
            head=artifact_commit,
            path=DATABASE_WATCHDOG_ACTIVITY_TRANSITION_PATH,
            field="introduced database-watchdog activity receipt",
        )
        != receipt_bytes
    ):
        raise OperatorError(
            "database-watchdog activity artifact commit changed"
        )
    _git_is_ancestor(
        artifact_commit,
        current_head,
        field="database-watchdog activity artifact-to-current lineage",
    )
    return {
        "receipt": payload,
        "receipt_bytes": receipt_bytes,
        "artifact_commit": artifact_commit,
        "base_commit": base_commit,
        "base_operator": base_operator,
        "sealed_source_head": sealed_head,
        "sealed_source_tree": sealed_tree,
        "expected_operator": expected_operator,
    }


def _verified_bootstrap_broker_operator_descendant(
    *,
    expected_historical_operator: bytes,
    historical_operator_identity: str,
    current_operator: bytes,
    current_head: str,
    operator_path: Path,
) -> None:
    """Bind the blocked-retry seal and its admitted operator successors."""

    descendant = _json_mapping_bytes(
        _tracked_bytes(
            CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_PATH,
            head=current_head,
        ),
        field="current-head blocked-retry descendant repair",
    )
    descendant_body = dict(descendant)
    descendant_receipt_id = str(descendant_body.pop("receipt_id", "") or "")
    repair_base = descendant.get("repair_base")
    sealed_source = descendant.get("sealed_source")
    if (
        descendant.get("schema")
        != CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_SCHEMA
        or not isinstance(repair_base, Mapping)
        or repair_base.get("source_head")
        != CURRENT_HEAD_BLOCKED_RETRY_REPAIR_BASE_COMMIT
        or not isinstance(sealed_source, Mapping)
        or re.fullmatch(
            r"[0-9a-f]{40}", str(sealed_source.get("source_head") or "")
        )
        is None
        or re.fullmatch(r"sha256:[0-9a-f]{64}", descendant_receipt_id) is None
        or _identity(descendant_body) != descendant_receipt_id
    ):
        raise OperatorError("PCSM current-head blocked-retry operator delta changed")

    blocked_retry_head = str(sealed_source["source_head"])
    historical_operator = _git_blob_at(
        head=CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_HEAD,
        path=operator_path,
        field="historical blocked-retry operator",
    )
    blocked_retry_operator = _git_blob_at(
        head=blocked_retry_head,
        path=operator_path,
        field="sealed blocked-retry operator",
    )
    if (
        historical_operator != expected_historical_operator
        or _identity(expected_historical_operator) != historical_operator_identity
        or sealed_source.get("operator_identity")
        != _identity(blocked_retry_operator)
    ):
        raise OperatorError("PCSM current-head blocked-retry operator delta changed")
    _git_is_ancestor(
        CURRENT_HEAD_BLOCKED_RETRY_REPAIR_BASE_COMMIT,
        current_head,
        field="blocked-retry operator descendant lineage",
    )
    if current_operator == blocked_retry_operator:
        return

    transition = _json_mapping_bytes(
        _tracked_bytes(STALE_WORKTREE_CLEANUP_TRANSITION_PATH, head=current_head),
        field="stale-worktree cleanup transition receipt",
    )
    transition_body = dict(transition)
    transition_receipt_id = str(transition_body.pop("receipt_id", "") or "")
    checkpoint = transition.get("prior_checkpoint")
    transition_base = transition.get("repair_base")
    transition_seal = transition.get("sealed_source")
    if (
        transition.get("schema") != STALE_WORKTREE_CLEANUP_TRANSITION_SCHEMA
        or transition.get("reason")
        != "delegate_daemon_stale_worktree_cleanup_to_supervisor"
        or not isinstance(checkpoint, Mapping)
        or checkpoint.get("descendant_repair_receipt_id")
        != descendant_receipt_id
        or not isinstance(transition_base, Mapping)
        or transition_base.get("source_head")
        != STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT
        or not isinstance(transition_seal, Mapping)
        or transition_seal.get("parent")
        != STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT
        or re.fullmatch(
            r"[0-9a-f]{40}", str(transition_seal.get("source_head") or "")
        )
        is None
        or re.fullmatch(r"sha256:[0-9a-f]{64}", transition_receipt_id) is None
        or _identity(transition_body) != transition_receipt_id
    ):
        raise OperatorError("PCSM stale-worktree cleanup operator delta changed")

    transition_base_operator = _git_blob_at(
        head=STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT,
        path=operator_path,
        field="stale-worktree cleanup base operator",
    )
    pending_base = (
        "PENDING_" + "STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT"
    ).encode("ascii")
    expected_transition_operator = transition_base_operator.replace(
        pending_base,
        STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT.encode("ascii"),
        1,
    )
    transition_head = str(transition_seal["source_head"])
    transition_operator = _git_blob_at(
        head=transition_head,
        path=operator_path,
        field="stale-worktree cleanup sealed operator",
    )
    relative_operator = operator_path.relative_to(ROOT).as_posix()
    transition_parents = str(
        _git("show", "-s", "--format=%P", transition_head)
    ).strip().split()
    transition_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT}.."
                f"{transition_head}",
            )
        ).splitlines()
        if line
    )
    if (
        transition_base_operator.count(pending_base) != 1
        or transition_base.get("operator_identity")
        != _identity(transition_base_operator)
        or transition_parents != [STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT]
        or transition_paths != (relative_operator,)
        or tuple(transition_seal.get("changed_paths") or ())
        != (relative_operator,)
        or _git_commit_tree(
            transition_head,
            field="stale-worktree cleanup sealed operator",
        )
        != transition_seal.get("repository_tree_id")
        or transition_seal.get("operator_identity")
        != _identity(expected_transition_operator)
        or transition_operator != expected_transition_operator
    ):
        raise OperatorError("PCSM stale-worktree cleanup operator delta changed")
    _git_is_ancestor(
        transition_head,
        current_head,
        field="stale-worktree cleanup operator descendant lineage",
    )
    if current_operator != expected_transition_operator:
        try:
            _verified_validation_path_compatibility_operator_descendant(
                current_operator=current_operator,
                current_head=current_head,
                operator_path=operator_path,
            )
        except OperatorError as exc:
            raise OperatorError(
                "PCSM stale-worktree cleanup operator delta changed"
            ) from exc


def _verified_bootstrap_broker_resilience_repair(
    *,
    sealed_operator_identity: str,
    current_operator_identity: str,
    current_head: str,
) -> dict[str, Any]:
    """Admit only the per-client bootstrap continue-instead-of-SIGTERM delta."""

    payload = _json_mapping_bytes(
        _tracked_bytes(
            HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_PATH,
            head=current_head,
        ),
        field="PCSM bootstrap broker resilience repair receipt",
    )
    expected_fields = {
        "schema",
        "reason",
        "source_command_verifier_repair_receipt_id",
        "sealed_outer_commit",
        "sealed_outer_tree",
        "sealed_operator_identity",
        "repair_base_commit",
        "repair_base_tree",
        "repair_base_operator_identity",
        "current_operator_identity",
        "exact_change",
        "validation",
        "attempt_refunded",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    exact_change = payload.get("exact_change")
    validation = payload.get("validation")
    operator_path = Path(__file__).resolve()
    relative_operator = operator_path.relative_to(ROOT).as_posix()
    base_commit = HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_BASE_COMMIT
    if (
        set(payload) != expected_fields
        or payload.get("schema") != HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SCHEMA
        or payload.get("reason")
        != "executor_bootstrap_per_client_admit_must_not_sigterm"
        or payload.get("source_command_verifier_repair_receipt_id")
        != "sha256:bf05d1a412d17becf0042570dd27be6eb3c5ca04f19488ecb9b8633b5042a134"
        or payload.get("sealed_outer_commit")
        != HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_COMMIT
        or payload.get("sealed_outer_tree")
        != HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_TREE
        or payload.get("sealed_operator_identity")
        != HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OPERATOR_IDENTITY
        or sealed_operator_identity
        != HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OPERATOR_IDENTITY
        or payload.get("repair_base_commit") != base_commit
        or payload.get("current_operator_identity")
        != current_operator_identity
        or not isinstance(exact_change, Mapping)
        or dict(exact_change)
        != {
            "timeout_after_accept_action_before": "sigterm_supervisor",
            "timeout_after_accept_action_after": "continue",
            "peer_oserror_action_before": "sigterm_supervisor",
            "peer_oserror_action_after": "continue",
            "per_client_admit_error_action_before": "sigterm_supervisor",
            "per_client_admit_error_action_after": "continue",
            "listener_oserror_action": "fail_closed",
            "durable_command_identity_changed": False,
            "database_state_changed": False,
        }
        or not isinstance(validation, Mapping)
        or dict(validation)
        != {
            "casf_timeout_continue_matched": True,
            "measurement_status": "measured",
        }
        or payload.get("attempt_refunded") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError(
            "PCSM bootstrap broker resilience repair receipt is not admitted"
        )
    if (
        _git_commit_tree(
            HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_COMMIT,
            field="sealed bootstrap broker resilience commit",
        )
        != HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_TREE
        or _git_commit_tree(
            base_commit,
            field="bootstrap broker resilience repair base",
        )
        != payload.get("repair_base_tree")
    ):
        raise OperatorError(
            "PCSM bootstrap broker resilience repair tree binding changed"
        )
    _git_is_ancestor(
        HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_COMMIT,
        base_commit,
        field="bootstrap broker resilience repair base lineage",
    )
    _git_is_ancestor(
        base_commit,
        current_head,
        field="bootstrap broker resilience repair current lineage",
    )
    parents = str(_git("show", "-s", "--format=%P", base_commit)).strip().split()
    changed_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_COMMIT}.."
                f"{base_commit}",
            )
        ).splitlines()
        if line
    )
    sealed_bytes = _git_blob_at(
        head=HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_COMMIT,
        path=operator_path,
        field="sealed bootstrap broker operator",
    )
    base_bytes = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="bootstrap broker resilience repair base operator",
    )
    current_bytes = _tracked_bytes(operator_path, head=current_head)
    pending_base = (
        "PENDING_" + "HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_BASE_COMMIT"
    ).encode("ascii")
    expected_current = base_bytes.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    )
    if (
        parents
        != [HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OUTER_COMMIT]
        or changed_paths != (relative_operator,)
        or _identity(sealed_bytes)
        != HANDOFF_BOOTSTRAP_BROKER_RESILIENCE_REPAIR_SEALED_OPERATOR_IDENTITY
        or _identity(base_bytes) != payload.get("repair_base_operator_identity")
        or base_bytes.count(pending_base) != 1
        or _identity(expected_current)
        != payload.get("current_operator_identity")
    ):
        raise OperatorError(
            "PCSM bootstrap broker resilience repair source delta changed"
        )
    if current_bytes != expected_current:
        _verified_bootstrap_broker_operator_descendant(
            expected_historical_operator=expected_current,
            historical_operator_identity=current_operator_identity,
            current_operator=current_bytes,
            current_head=current_head,
            operator_path=operator_path,
        )
    elif _identity(current_bytes) != current_operator_identity:
        raise OperatorError(
            "PCSM bootstrap broker resilience repair identity changed"
        )
    return payload


def _verified_operator_replay_repair(
    *,
    sealed_operator_identity: str,
    current_operator_identity: str,
    current_head: str,
) -> dict[str, Any]:
    """Admit only the post-generation-6 zero-revision replay correction."""

    payload = _json_mapping_bytes(
        _tracked_bytes(HANDOFF_REPLAY_REPAIR_PATH, head=current_head),
        field="PCSM restart replay repair receipt",
    )
    expected_fields = {
        "schema",
        "reason",
        "source_handoff_repair_receipt_id",
        "sealed_outer_commit",
        "sealed_outer_tree",
        "sealed_operator_identity",
        "repair_base_commit",
        "repair_base_tree",
        "repair_base_operator_identity",
        "current_operator_identity",
        "exact_change",
        "failed_restart",
        "recovery_already_committed",
        "attempt_refunded",
        "manual_database_mutation",
        "receipt_id",
    }
    exact_change = payload.get("exact_change")
    failed_restart = payload.get("failed_restart")
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    operator_path = Path(__file__).resolve()
    relative_operator = operator_path.relative_to(ROOT).as_posix()
    base_commit = HANDOFF_REPLAY_REPAIR_BASE_COMMIT
    if (
        set(payload) != expected_fields
        or payload.get("schema") != HANDOFF_REPLAY_REPAIR_SCHEMA
        or payload.get("reason")
        != "generation_6_valid_zero_store_revision_replay_validation"
        or payload.get("source_handoff_repair_receipt_id")
        != HANDOFF_REPAIR_SEALED_RECEIPT_ID
        or payload.get("sealed_outer_commit")
        != HANDOFF_REPAIR_SEALED_OUTER_COMMIT
        or payload.get("sealed_outer_tree")
        != HANDOFF_REPAIR_SEALED_OUTER_TREE
        or payload.get("sealed_operator_identity")
        != HANDOFF_REPAIR_SEALED_OPERATOR_IDENTITY
        or sealed_operator_identity
        != HANDOFF_REPAIR_SEALED_OPERATOR_IDENTITY
        or payload.get("repair_base_commit") != base_commit
        or payload.get("current_operator_identity")
        != HANDOFF_REPLAY_REPAIR_SEALED_OPERATOR_IDENTITY
        or not isinstance(exact_change, Mapping)
        or dict(exact_change)
        != {
            "field": "store_revision_before",
            "previous_lower_bound": 1,
            "admitted_lower_bound": 0,
            "accepted_store_revision_before": 0,
            "accepted_store_revision_after": 1,
        }
        or not isinstance(failed_restart, Mapping)
        or dict(failed_restart)
        != {
            "owner_generation": 6,
            "owner_fence_epoch": 6,
            "task_status": "retrying",
            "task_revision": 5,
            "command_id": (
                "cmd:blocked-retry-recovery:"
                "ee9b5a7a09bbc060ac83799b4c31474499a69580534f160f5605b30d0a147cd7"
            ),
            "idempotency_key": (
                "executor-blocked-retry-recovery:"
                "ee9b5a7a09bbc060ac83799b4c31474499a69580534f160f5605b30d0a147cd7"
            ),
            "result_digest": (
                "sha256:ba3a88d6bd6f2c848b273fb5362919909fa6c9d0813258df089a0cc08bc04f1e"
            ),
            "error": "blocked-retry owner command was not exactly admitted",
        }
        or payload.get("recovery_already_committed") is not True
        or payload.get("attempt_refunded") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError("PCSM restart replay repair receipt is not admitted")

    if (
        _git_commit_tree(
            HANDOFF_REPAIR_SEALED_OUTER_COMMIT,
            field="sealed restart repair commit",
        )
        != HANDOFF_REPAIR_SEALED_OUTER_TREE
        or _git_commit_tree(base_commit, field="restart replay repair base")
        != payload.get("repair_base_tree")
    ):
        raise OperatorError("PCSM restart replay repair tree binding changed")
    _git_is_ancestor(
        HANDOFF_REPAIR_SEALED_OUTER_COMMIT,
        base_commit,
        field="restart replay repair base lineage",
    )
    _git_is_ancestor(
        base_commit,
        current_head,
        field="restart replay repair current lineage",
    )
    parents = str(_git("show", "-s", "--format=%P", base_commit)).strip().split()
    changed_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{HANDOFF_REPAIR_SEALED_OUTER_COMMIT}..{base_commit}",
            )
        ).splitlines()
        if line
    )
    sealed_bytes = _git_blob_at(
        head=HANDOFF_REPAIR_SEALED_OUTER_COMMIT,
        path=operator_path,
        field="sealed blocked-retry operator",
    )
    base_bytes = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="restart replay repair base operator",
    )
    current_bytes = _tracked_bytes(operator_path, head=current_head)
    pending_base = ("PENDING_" + "REPAIR_BASE_COMMIT").encode("ascii")
    old_bound = b"        or store_revision_before < " + b"1\n"
    new_bound = b"        or store_revision_before < " + b"0\n"
    expected_repaired = base_bytes.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    ).replace(old_bound, new_bound, 1)
    if (
        parents != [HANDOFF_REPAIR_SEALED_OUTER_COMMIT]
        or changed_paths != (relative_operator,)
        or _identity(sealed_bytes) != HANDOFF_REPAIR_SEALED_OPERATOR_IDENTITY
        or _identity(base_bytes)
        != payload.get("repair_base_operator_identity")
        or base_bytes.count(pending_base) != 1
        or base_bytes.count(old_bound) != 1
        or _identity(expected_repaired)
        != HANDOFF_REPLAY_REPAIR_SEALED_OPERATOR_IDENTITY
    ):
        raise OperatorError("PCSM restart replay repair source delta changed")
    if current_bytes != expected_repaired:
        _verified_generation_replay_repair(
            sealed_operator_identity=_identity(expected_repaired),
            current_operator_identity=current_operator_identity,
            current_head=current_head,
        )
    elif _identity(current_bytes) != current_operator_identity:
        raise OperatorError("PCSM restart replay repair identity changed")
    return payload


def _verified_handoff_repair(
    *,
    bootstrap_receipt_id: str,
    plan_root_cid: str,
    bootstrap_tree: str,
    database_task_count: int,
    bootstrap_attempt_limit: int,
    current_attempt_limit: int,
    current_source_identities: Mapping[str, str],
    forest_transition: Mapping[str, Any],
    current_source_binding: Mapping[str, Any],
    current_head: str,
) -> dict[str, Any]:
    payload = _json_mapping_bytes(
        _tracked_bytes(HANDOFF_REPAIR_PATH, head=current_head),
        field="PCSM handoff repair receipt",
    )
    expected_fields = {
        "schema",
        "reason",
        "bootstrap_receipt_id",
        "plan_root_cid",
        "task_alias",
        "task_cid",
        "source_attempt",
        "source_completion_receipt_id",
        "blocked_retry_handoff",
        "max_task_attempts_before",
        "max_task_attempts_after",
        "execution_route_continuation",
        "current_authority_source_identities",
        "accelerate_origin_main_merge",
        "datasets_current_head_receipt",
        "validations",
        "historical_receipt_preserved",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    source_attempt = payload.get("source_attempt")
    blocked_retry_handoff = payload.get("blocked_retry_handoff")
    datasets_receipt = payload.get("datasets_current_head_receipt")
    accelerate_merge = payload.get("accelerate_origin_main_merge")
    continuation = payload.get("execution_route_continuation")
    validations = payload.get("validations")
    listed_identities = payload.get("current_authority_source_identities")
    continuation_fields = {
        "schema",
        "policy_id",
        "plan_root_cid",
        "repository_tree_id",
        "source_revision",
        "source_projection_cid",
        "origin_task_revision",
        "execution_mode",
        "task_count",
        "lane_count",
        "stable_binding_id",
        "stable_authority",
    }
    stable_authority_fields = {
        "interface",
        "store_id",
        "database_uuid",
        "schema_fingerprint",
        "repository_id",
        "schema_revision",
        "route_policy_id",
        "plan_root_cid",
        "repository_tree_id",
        "source_projection_cid",
    }
    stable_authority = (
        continuation.get("stable_authority")
        if isinstance(continuation, Mapping)
        else None
    )
    if (
        set(payload) != expected_fields
        or payload.get("schema") != HANDOFF_REPAIR_SCHEMA
        or payload.get("reason")
        != "pcsm_010_current_head_validation_handoff_repair"
        or payload.get("bootstrap_receipt_id") != bootstrap_receipt_id
        or payload.get("plan_root_cid") != plan_root_cid
        or payload.get("task_alias") != "PCSM-010"
        or payload.get("task_cid") != HANDOFF_REPAIR_TASK_CID
        or not isinstance(source_attempt, Mapping)
        or dict(source_attempt) != HANDOFF_REPAIR_SOURCE_ATTEMPT
        or any(
            type(source_attempt.get(field)) is not int
            for field in (
                "attempt_number",
                "fencing_token",
                "fence_epoch",
                "task_revision",
            )
        )
        or payload.get("source_completion_receipt_id")
        != HANDOFF_REPAIR_COMPLETION_RECEIPT_ID
        or not isinstance(blocked_retry_handoff, Mapping)
        or type(payload.get("max_task_attempts_before")) is not int
        or type(payload.get("max_task_attempts_after")) is not int
        or payload.get("max_task_attempts_before") != bootstrap_attempt_limit
        or payload.get("max_task_attempts_after") != current_attempt_limit
        or bootstrap_attempt_limit != 1
        or current_attempt_limit != HANDOFF_REPAIR_MAX_TASK_ATTEMPTS
        or not isinstance(continuation, Mapping)
        or set(continuation) != continuation_fields
        or continuation.get("schema")
        != HANDOFF_EXECUTION_ROUTE_CONTINUATION_SCHEMA
        or continuation.get("policy_id") != HANDOFF_REPAIR_ROUTE_POLICY_ID
        or continuation.get("plan_root_cid") != plan_root_cid
        or continuation.get("repository_tree_id") != bootstrap_tree
        or type(continuation.get("source_revision")) is not int
        or continuation.get("source_revision") != 1
        or continuation.get("source_projection_cid")
        != HANDOFF_REPAIR_ROUTE_SOURCE_PROJECTION_CID
        or type(continuation.get("origin_task_revision")) is not int
        or continuation.get("origin_task_revision") != 1
        or continuation.get("execution_mode") != "grok-codex"
        or type(continuation.get("task_count")) is not int
        or continuation.get("task_count") != database_task_count
        or type(continuation.get("lane_count")) is not int
        or continuation.get("lane_count") != 4
        or continuation.get("stable_binding_id")
        != HANDOFF_REPAIR_STABLE_BINDING_ID
        or not isinstance(stable_authority, Mapping)
        or set(stable_authority) != stable_authority_fields
        or stable_authority.get("interface")
        != "TypedDatabaseTaskSourceStableQuackAuthority@1"
        or stable_authority.get("route_policy_id")
        != continuation.get("policy_id")
        or stable_authority.get("plan_root_cid") != plan_root_cid
        or stable_authority.get("repository_tree_id") != bootstrap_tree
        or stable_authority.get("source_projection_cid")
        != continuation.get("source_projection_cid")
        or type(stable_authority.get("schema_revision")) is not int
        or stable_authority.get("schema_revision", 0) < 1
        or any(
            not isinstance(stable_authority.get(field), str)
            or not stable_authority.get(field)
            for field in (
                "store_id",
                "database_uuid",
                "schema_fingerprint",
                "repository_id",
            )
        )
        or _semantic_identity(stable_authority)
        != continuation.get("stable_binding_id")
        or not isinstance(listed_identities, Mapping)
        or set(listed_identities) != _RESTART_REPAIR_SOURCE_NAMES
        or any(
            listed_identities[name] != current_source_identities[name]
            for name in sorted(_RESTART_REPAIR_SOURCE_NAMES - {"operator"})
        )
        or listed_identities["operator"]
        != HANDOFF_REPAIR_SEALED_OPERATOR_IDENTITY
        or not isinstance(datasets_receipt, Mapping)
        or not isinstance(accelerate_merge, Mapping)
        or not isinstance(validations, list)
        or not validations
        or payload.get("historical_receipt_preserved") is not True
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError("PCSM handoff repair receipt is not admitted")
    _verified_blocked_retry_handoff(
        blocked_retry_handoff,
        source_attempt=source_attempt,
        source_completion_receipt_id=HANDOFF_REPAIR_COMPLETION_RECEIPT_ID,
        bootstrap_attempt_limit=bootstrap_attempt_limit,
        current_attempt_limit=current_attempt_limit,
    )
    if listed_identities["operator"] != current_source_identities["operator"]:
        _verified_operator_replay_repair(
            sealed_operator_identity=str(listed_identities["operator"]),
            current_operator_identity=current_source_identities["operator"],
            current_head=current_head,
        )
    observed_validations: set[tuple[str, tuple[str, ...]]] = set()
    for index, validation in enumerate(validations):
        if not isinstance(validation, Mapping) or set(validation) != {
            "cwd",
            "command",
            "outcome",
            "summary",
            "measurement_status",
        }:
            raise OperatorError(f"PCSM handoff validation {index} is malformed")
        command = validation.get("command")
        cwd = validation.get("cwd")
        if (
            not isinstance(cwd, str)
            or not cwd
            or not isinstance(command, list)
            or not command
            or any(not isinstance(item, str) or not item for item in command)
            or validation.get("outcome") != "passed"
            or validation.get("measurement_status") != "measured"
            or not isinstance(validation.get("summary"), str)
            or not validation.get("summary")
        ):
            raise OperatorError(f"PCSM handoff validation {index} is not passed")
        observed_validations.add((cwd, tuple(command)))
    if (
        len(observed_validations) != len(validations)
        or observed_validations != HANDOFF_REPAIR_REQUIRED_VALIDATIONS
    ):
        raise OperatorError("PCSM handoff validations are not the exact required set")

    transition_items = forest_transition.get("repositories")
    transition_fields = {
        "repository",
        "path",
        "bootstrap_head",
        "bootstrap_tree",
        "current_head",
        "current_tree",
        "changed",
    }
    if (
        not isinstance(transition_items, list)
        or any(
            not isinstance(item, Mapping) or set(item) != transition_fields
            for item in transition_items
        )
    ):
        raise OperatorError("PCSM handoff forest transition is malformed")
    dataset_transition = next(
        (
            item
            for item in transition_items
            if item.get("repository") == "ipfs_datasets"
        ),
        None,
    )
    accelerator_transition = next(
        (
            item
            for item in transition_items
            if item.get("repository") == "ipfs_accelerate"
        ),
        None,
    )
    changed_repositories = {
        str(item.get("repository") or "")
        for item in transition_items
        if item.get("changed") is True
    }
    if set(datasets_receipt) != {"path", "identity", "source_commit", "source_tree"}:
        raise OperatorError("PCSM datasets handoff receipt binding is not exact")
    receipt_path = str(datasets_receipt.get("path") or "")
    receipt_identity = str(datasets_receipt.get("identity") or "")
    if (
        not isinstance(dataset_transition, Mapping)
        or dataset_transition.get("changed") is not True
        or changed_repositories != {"ipfs_accelerate", "ipfs_datasets"}
        or receipt_path
        != "artifacts/proof_carrying_semantic_minification/handoff/"
        "datasets-proof-context-current-head.json"
    ):
        raise OperatorError("PCSM datasets handoff transition is not exact")
    if (
        not isinstance(accelerator_transition, Mapping)
        or accelerator_transition.get("changed") is not True
        or set(accelerate_merge)
        != {
            "bootstrap_commit",
            "origin_main_commit",
            "merged_commit",
            "merged_tree",
            "current_commit",
            "current_tree",
        }
        or accelerate_merge.get("bootstrap_commit")
        != accelerator_transition.get("bootstrap_head")
        or accelerate_merge.get("current_commit")
        != accelerator_transition.get("current_head")
        or accelerate_merge.get("current_tree")
        != accelerator_transition.get("current_tree")
        or accelerate_merge.get("origin_main_commit")
        != current_source_binding.get("ipfs_accelerate_origin_main_revision")
        or _git_commit_tree(
            accelerate_merge.get("merged_commit"),
            field="accelerator admitted origin/main merge",
            repository=_safe_path(
                ROOT,
                str(accelerator_transition.get("path") or ""),
                field="accelerate_origin_main_merge.path",
            ),
        )
        != accelerate_merge.get("merged_tree")
    ):
        raise OperatorError("PCSM accelerator origin/main transition is not exact")
    accelerator_repository = _safe_path(
        ROOT,
        str(accelerator_transition.get("path") or ""),
        field="accelerate_origin_main_merge.path",
    )
    _git_is_ancestor(
        accelerate_merge.get("origin_main_commit"),
        accelerate_merge.get("current_commit"),
        field="accelerator origin/main merge lineage",
        repository=accelerator_repository,
    )
    _git_is_ancestor(
        accelerate_merge.get("merged_commit"),
        accelerate_merge.get("current_commit"),
        field="accelerator handoff repair lineage",
        repository=accelerator_repository,
    )
    merge_parents = subprocess.run(
        [
            "git",
            "show",
            "-s",
            "--format=%P",
            str(accelerate_merge.get("merged_commit") or ""),
        ],
        cwd=accelerator_repository,
        text=True,
        capture_output=True,
        check=False,
    )
    if (
        merge_parents.returncode != 0
        or set(merge_parents.stdout.strip().split())
        != {
            str(accelerate_merge.get("bootstrap_commit") or ""),
            str(accelerate_merge.get("origin_main_commit") or ""),
        }
    ):
        raise OperatorError("PCSM accelerator transition is not the exact merge")
    current_dataset_receipt = _safe_path(
        ROOT,
        receipt_path,
        field="datasets_current_head_receipt.path",
    )
    receipt_bytes = _tracked_bytes(current_dataset_receipt, head=current_head)
    receipt_body = _json_mapping_bytes(
        receipt_bytes,
        field="datasets current-head receipt",
    )
    receipt_source = receipt_body.get("source_binding")
    historical_receipt = receipt_body.get("historical_receipt")
    if (
        _identity(receipt_bytes) != receipt_identity
        or receipt_body.get("schema")
        != "lift_coding.proof-carrying-semantic-minification."
        "datasets-package-current-head@1"
        or receipt_body.get("status") != "qualified_current_head"
        or receipt_body.get("authority") != "composed_workspace_validation_only"
        or datasets_receipt.get("source_commit")
        != dataset_transition.get("current_head")
        or datasets_receipt.get("source_tree")
        != dataset_transition.get("current_tree")
        or not isinstance(receipt_source, Mapping)
        or receipt_source.get("repository") != "ipfs_datasets_py"
        or receipt_source.get("commit")
        != dataset_transition.get("current_head")
        or receipt_source.get("tree")
        != dataset_transition.get("current_tree")
        or receipt_source.get("origin_main_is_ancestor") is not True
        or receipt_source.get("origin_main_commit")
        != current_source_binding.get("ipfs_datasets_origin_main_revision")
        or not isinstance(historical_receipt, Mapping)
        or historical_receipt.get("preserved_unchanged") is not True
    ):
        raise OperatorError("PCSM datasets current-head receipt changed identity")
    return payload


def _source_forest_at_commit(
    config: Mapping[str, Any],
    *,
    head: str,
) -> dict[str, Any]:
    """Reproduce a historical forest without changing live nested checkouts."""

    binding = config.get("source_binding")
    if not isinstance(binding, Mapping):
        raise OperatorError("historical source_binding is absent")
    specifications = (
        (
            "ipfs_accelerate",
            "ipfs_accelerate_submodule_path",
            "ipfs_accelerate_planning_revision",
            "ipfs_accelerate_planning_tree",
            "ipfs_accelerate_origin_main_revision",
        ),
        (
            "ipfs_datasets",
            "ipfs_datasets_submodule_path",
            "ipfs_datasets_planning_revision",
            "ipfs_datasets_planning_tree",
            "ipfs_datasets_origin_main_revision",
        ),
        (
            "ipfs_kit",
            "ipfs_kit_submodule_path",
            "ipfs_kit_planning_revision",
            "ipfs_kit_planning_tree",
            "ipfs_kit_origin_main_revision",
        ),
        (
            "mcp_plus_plus",
            "mcp_plus_plus_submodule_path",
            "mcp_plus_plus_planning_revision",
            "mcp_plus_plus_planning_tree",
            "mcp_plus_plus_origin_main_revision",
        ),
    )
    nested: list[dict[str, str]] = []
    for repository_name, path_field, revision_field, tree_field, origin_field in (
        specifications
    ):
        relative = str(binding.get(path_field) or "")
        revision = str(binding.get(revision_field) or "")
        tree = str(binding.get(tree_field) or "")
        origin = str(binding.get(origin_field) or "")
        repository = _safe_path(
            ROOT,
            relative,
            field=f"historical {repository_name} path",
        )
        if (
            not repository.is_dir()
            or _git_commit_tree(
                revision,
                field=f"historical {repository_name} revision",
                repository=repository,
            )
            != tree
        ):
            raise OperatorError(
                f"historical {repository_name} revision differs from its tree"
            )
        _git_is_ancestor(
            origin,
            revision,
            field=f"historical {repository_name} origin lineage",
            repository=repository,
        )
        tree_row = str(_git("ls-tree", head, "--", relative)).strip().split()
        if (
            len(tree_row) < 3
            or tree_row[0] != "160000"
            or tree_row[1] != "commit"
            or tree_row[2] != revision
        ):
            raise OperatorError(
                f"historical {repository_name} gitlink differs from its seal"
            )
        nested.append(
            {
                "repository": repository_name,
                "path": relative,
                "head": revision,
                "tree": tree,
                "access": "supervisor_scoped_cross_repository_worktree",
            }
        )
    result: dict[str, Any] = {
        "source_head": head,
        "nested_repositories": nested,
        "cross_repository_writes": True,
    }
    result["source_forest_root"] = _identity(result)
    return result


def _verified_stale_worktree_cleanup_transition(
    *,
    board: Any,
    current_head: str,
    current_config: Mapping[str, Any],
    current_source_identities: Mapping[str, str],
    prior_artifact_commit: str,
    prior_descendant_repair_receipt_id: str,
    prior_batch_receipt_id: str,
    prior_config_bytes: bytes,
    prior_operator_bytes: bytes,
    prior_validator_bytes: bytes,
) -> dict[str, Any]:
    """Admit one exact daemon-to-supervisor stale-cleanup transition."""

    base_commit = STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        raise OperatorError("stale-worktree cleanup transition base is unsealed")
    receipt_bytes = _tracked_bytes(
        STALE_WORKTREE_CLEANUP_TRANSITION_PATH,
        head=current_head,
    )
    payload = _json_mapping_bytes(
        receipt_bytes,
        field="stale-worktree cleanup transition receipt",
    )
    required_fields = {
        "schema",
        "reason",
        "prior_checkpoint",
        "repair_base",
        "sealed_source",
        "safety_policy",
        "validations",
        "historical_receipts_preserved",
        "database_authority_preserved",
        "task_state_mutation",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    checkpoint = payload.get("prior_checkpoint")
    repair_base = payload.get("repair_base")
    sealed_source = payload.get("sealed_source")
    safety_policy = payload.get("safety_policy")
    validations = payload.get("validations")
    if (
        set(payload) != required_fields
        or payload.get("schema") != STALE_WORKTREE_CLEANUP_TRANSITION_SCHEMA
        or payload.get("reason")
        != "delegate_daemon_stale_worktree_cleanup_to_supervisor"
        or not isinstance(checkpoint, Mapping)
        or not isinstance(repair_base, Mapping)
        or not isinstance(sealed_source, Mapping)
        or not isinstance(safety_policy, Mapping)
        or not isinstance(validations, list)
        or not validations
        or payload.get("historical_receipts_preserved") is not True
        or payload.get("database_authority_preserved") is not True
        or payload.get("task_state_mutation") is not False
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError("stale-worktree cleanup transition seal is invalid")

    expected_safety_policy = {
        "daemon_stale_cleanup_action": "detect_and_delegate",
        "destructive_cleanup_authority": "supervisor_worktree_reconciliation",
        "daemon_stale_cleanup_may_remove_worktree": False,
        "daemon_stale_cleanup_may_delete_branch": False,
        "dirty_bytes_require_rescue_before_retirement": True,
        "peer_active_state_requires_preservation": True,
    }
    if dict(safety_policy) != expected_safety_policy:
        raise OperatorError("stale-worktree cleanup safety policy changed")

    checkpoint_fields = {
        "source_head",
        "repository_tree_id",
        "prior_artifact_commit",
        "descendant_repair_receipt_id",
        "blocked_retry_batch_receipt_id",
        "changed_receipts",
    }
    checkpoint_head = str(checkpoint.get("source_head") or "")
    checkpoint_receipts = checkpoint.get("changed_receipts")
    if (
        set(checkpoint) != checkpoint_fields
        or _git_commit_tree(
            checkpoint_head,
            field="stale-worktree cleanup prior checkpoint",
        )
        != checkpoint.get("repository_tree_id")
        or checkpoint.get("prior_artifact_commit") != prior_artifact_commit
        or checkpoint.get("descendant_repair_receipt_id")
        != prior_descendant_repair_receipt_id
        or checkpoint.get("blocked_retry_batch_receipt_id")
        != prior_batch_receipt_id
        or not isinstance(checkpoint_receipts, list)
        or not checkpoint_receipts
    ):
        raise OperatorError("stale-worktree cleanup prior checkpoint changed")
    _git_is_ancestor(
        prior_artifact_commit,
        checkpoint_head,
        field="blocked-retry artifact-to-cleanup checkpoint lineage",
    )
    receipt_path_pattern = re.compile(
        r"artifacts/proof_carrying_semantic_minification/receipts/"
        r"PCSM-[0-9]{3}\.json"
    )
    checkpoint_paths = tuple(
        sorted(
            line
            for line in str(
                _git(
                    "diff",
                    "--name-only",
                    f"{prior_artifact_commit}..{checkpoint_head}",
                )
            ).splitlines()
            if line
        )
    )
    listed_checkpoint_paths: list[str] = []
    for item in checkpoint_receipts:
        if not isinstance(item, Mapping) or set(item) != {"path", "bytes_id"}:
            raise OperatorError("cleanup checkpoint receipt binding is malformed")
        path = str(item.get("path") or "")
        if (
            receipt_path_pattern.fullmatch(path) is None
            or _identity(
                _git_blob_at(
                    head=checkpoint_head,
                    path=ROOT / path,
                    field=f"cleanup checkpoint receipt {path}",
                )
            )
            != item.get("bytes_id")
        ):
            raise OperatorError("cleanup checkpoint receipt binding changed")
        listed_checkpoint_paths.append(path)
    if (
        len(set(listed_checkpoint_paths)) != len(listed_checkpoint_paths)
        or tuple(sorted(listed_checkpoint_paths)) != checkpoint_paths
    ):
        raise OperatorError(
            "cleanup checkpoint contains non-receipt or unbound descendants"
        )

    operator_path = Path(__file__).resolve()
    validator_path = board.path(board.validator_path)
    if (
        _git_blob_at(
            head=checkpoint_head,
            path=board.config_path,
            field="cleanup checkpoint config",
        )
        != prior_config_bytes
        or _git_blob_at(
            head=checkpoint_head,
            path=operator_path,
            field="cleanup checkpoint operator",
        )
        != prior_operator_bytes
        or _git_blob_at(
            head=checkpoint_head,
            path=validator_path,
            field="cleanup checkpoint validator",
        )
        != prior_validator_bytes
    ):
        raise OperatorError("cleanup checkpoint changed prior source authority")
    checkpoint_gitlink = str(
        _git("ls-tree", checkpoint_head, "--", "external/ipfs_accelerate")
    ).strip().split()
    if (
        len(checkpoint_gitlink) < 3
        or checkpoint_gitlink[:2] != ["160000", "commit"]
        or checkpoint_gitlink[2]
        != str(
            _json_mapping_bytes(
                prior_config_bytes,
                field="prior blocked-retry config",
            )["source_binding"]["ipfs_accelerate_planning_revision"]
        )
    ):
        raise OperatorError("cleanup checkpoint accelerator gitlink changed")

    repair_base_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "config_identity",
        "validator_identity",
        "accelerator_head",
        "accelerator_tree",
        "changed_paths",
        "nested_changed_paths",
    }
    expected_base_paths = (
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
        "test/test_pcsm_stale_worktree_cleanup_transition.py",
    )
    expected_nested_paths = (
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_daemon.py",
        "test/api/test_agent_supervisor_implementation_daemon_runner.py",
    )
    base_tree = _git_commit_tree(
        base_commit,
        field="stale-worktree cleanup repair base",
    )
    base_parents = str(
        _git("show", "-s", "--format=%P", base_commit)
    ).strip().split()
    base_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{checkpoint_head}..{base_commit}")
        ).splitlines()
        if line
    )
    base_operator = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="stale-worktree cleanup base operator",
    )
    base_config_bytes = _git_blob_at(
        head=base_commit,
        path=board.config_path,
        field="stale-worktree cleanup base config",
    )
    base_config = _json_mapping_bytes(
        base_config_bytes,
        field="stale-worktree cleanup base config",
    )
    base_validator = _git_blob_at(
        head=base_commit,
        path=validator_path,
        field="stale-worktree cleanup base validator",
    )
    expected_config = _json_mapping_bytes(
        prior_config_bytes,
        field="prior blocked-retry config",
    )
    expected_binding = expected_config.get("source_binding")
    if not isinstance(expected_binding, dict):
        raise OperatorError("prior blocked-retry source binding is absent")
    expected_binding["ipfs_accelerate_planning_revision"] = (
        STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD
    )
    expected_binding["ipfs_accelerate_planning_tree"] = (
        STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE
    )
    base_gitlink = str(
        _git("ls-tree", base_commit, "--", "external/ipfs_accelerate")
    ).strip().split()
    if (
        set(repair_base) != repair_base_fields
        or repair_base.get("source_head") != base_commit
        or repair_base.get("repository_tree_id") != base_tree
        or repair_base.get("parent") != checkpoint_head
        or base_parents != [checkpoint_head]
        or repair_base.get("operator_identity") != _identity(base_operator)
        or repair_base.get("config_identity") != _identity(base_config_bytes)
        or repair_base.get("validator_identity") != _identity(base_validator)
        or base_validator != prior_validator_bytes
        or repair_base.get("accelerator_head")
        != STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD
        or repair_base.get("accelerator_tree")
        != STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE
        or tuple(repair_base.get("changed_paths") or ()) != expected_base_paths
        or base_paths != expected_base_paths
        or tuple(repair_base.get("nested_changed_paths") or ())
        != expected_nested_paths
        or base_config != expected_config
        or len(base_gitlink) < 3
        or base_gitlink[:2] != ["160000", "commit"]
        or base_gitlink[2] != STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD
    ):
        raise OperatorError("stale-worktree cleanup repair base changed")

    accelerator_repository = ROOT / "external/ipfs_accelerate"
    if (
        _git_commit_tree(
            STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD,
            field="stale-worktree cleanup accelerator",
            repository=accelerator_repository,
        )
        != STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE
    ):
        raise OperatorError("stale-worktree cleanup accelerator tree changed")
    nested_parents = subprocess.run(
        [
            "git",
            "show",
            "-s",
            "--format=%P",
            STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD,
        ],
        cwd=accelerator_repository,
        text=True,
        capture_output=True,
        check=False,
    )
    nested_paths = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{checkpoint_gitlink[2]}..{STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD}",
        ],
        cwd=accelerator_repository,
        text=True,
        capture_output=True,
        check=False,
    )
    if (
        nested_parents.returncode != 0
        or nested_parents.stdout.strip().split() != [checkpoint_gitlink[2]]
        or nested_paths.returncode != 0
        or tuple(nested_paths.stdout.splitlines()) != expected_nested_paths
    ):
        raise OperatorError("stale-worktree cleanup nested delta changed")

    sealed_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "changed_paths",
    }
    sealed_head = str(sealed_source.get("source_head") or "")
    sealed_tree = _git_commit_tree(
        sealed_head,
        field="stale-worktree cleanup sealed source",
    )
    sealed_parents = str(
        _git("show", "-s", "--format=%P", sealed_head)
    ).strip().split()
    sealed_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{base_commit}..{sealed_head}")
        ).splitlines()
        if line
    )
    pending_base = (
        "PENDING_" + "STALE_WORKTREE_CLEANUP_TRANSITION_BASE_COMMIT"
    ).encode("ascii")
    expected_operator = base_operator.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    )
    sealed_operator = _git_blob_at(
        head=sealed_head,
        path=operator_path,
        field="stale-worktree cleanup sealed operator",
    )
    if (
        set(sealed_source) != sealed_fields
        or sealed_source.get("repository_tree_id") != sealed_tree
        or sealed_source.get("parent") != base_commit
        or sealed_parents != [base_commit]
        or sealed_source.get("operator_identity") != _identity(expected_operator)
        or sealed_operator != expected_operator
        or tuple(sealed_source.get("changed_paths") or ())
        != ("scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",)
        or sealed_paths
        != ("scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",)
        or base_operator.count(pending_base) != 1
    ):
        raise OperatorError("stale-worktree cleanup sealed source changed")

    required_validations = {
        (
            "external/ipfs_accelerate",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/api/test_agent_supervisor_implementation_daemon_runner.py::"
                "test_stale_worktree_cleanup_delegates_protected_dirty_checkout",
                "test/api/test_agent_supervisor_incremental_runtime.py::"
                "test_completed_rescued_dead_pool_workspace_retires_in_three_passes",
            ),
        ),
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/test_pcsm_stale_worktree_cleanup_transition.py",
            ),
        ),
        (
            ".",
            (
                "python",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
                "--check-all",
            ),
        ),
    }
    observed_validations: set[tuple[str, tuple[str, ...]]] = set()
    for validation in validations:
        if not isinstance(validation, Mapping) or set(validation) != {
            "cwd",
            "command",
            "outcome",
            "summary",
        }:
            raise OperatorError("stale-worktree cleanup validation is malformed")
        command = validation.get("command")
        if (
            not isinstance(command, list)
            or any(not isinstance(item, str) or not item for item in command)
            or validation.get("outcome") != "passed"
            or not isinstance(validation.get("summary"), str)
            or not validation.get("summary")
        ):
            raise OperatorError("stale-worktree cleanup validation did not pass")
        observed_validations.add(
            (str(validation.get("cwd") or ""), tuple(command))
        )
    if observed_validations != required_validations:
        raise OperatorError("stale-worktree cleanup validations are incomplete")

    receipt_relative = STALE_WORKTREE_CLEANUP_TRANSITION_PATH.relative_to(
        ROOT
    ).as_posix()
    receipt_additions = tuple(
        line
        for line in str(
            _git(
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                receipt_relative,
            )
        ).splitlines()
        if line
    )
    if len(receipt_additions) != 1:
        raise OperatorError("stale-worktree cleanup receipt introduction is not exact")
    artifact_commit = receipt_additions[0]
    artifact_parents = str(
        _git("show", "-s", "--format=%P", artifact_commit)
    ).strip().split()
    artifact_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{sealed_head}..{artifact_commit}")
        ).splitlines()
        if line
    )
    if (
        artifact_parents != [sealed_head]
        or artifact_paths != (receipt_relative,)
        or _git_blob_at(
            head=artifact_commit,
            path=STALE_WORKTREE_CLEANUP_TRANSITION_PATH,
            field="introduced stale-worktree cleanup receipt",
        )
        != receipt_bytes
    ):
        raise OperatorError("stale-worktree cleanup artifact commit changed")
    _git_is_ancestor(
        artifact_commit,
        current_head,
        field="stale-worktree cleanup artifact-to-current lineage",
    )

    current_config_bytes = _tracked_bytes(board.config_path, head=current_head)
    current_operator = _tracked_bytes(operator_path, head=current_head)
    current_validator = _tracked_bytes(validator_path, head=current_head)
    exact_cleanup_source = bool(
        _canonical_bytes(current_config) == _canonical_bytes(base_config)
        and current_config_bytes == base_config_bytes
        and current_operator == expected_operator
        and current_validator == base_validator
        and current_source_identities.get("config")
        == _identity(base_config_bytes)
        and current_source_identities.get("operator")
        == _identity(expected_operator)
        and current_source_identities.get("validator")
        == _identity(base_validator)
    )
    validation_path_transition: dict[str, Any] = {}
    if not exact_cleanup_source:
        validation_path_transition = (
            _verified_validation_path_compatibility_transition(
                board=board,
                current_head=current_head,
                current_config=current_config,
                current_source_identities=current_source_identities,
                prior_artifact_commit=artifact_commit,
                prior_transition_receipt_id=receipt_id,
                prior_config_bytes=base_config_bytes,
                prior_operator_bytes=expected_operator,
                prior_validator_bytes=base_validator,
            )
        )
    return {
        "receipt": payload,
        "artifact_commit": artifact_commit,
        "sealed_source_head": sealed_head,
        "sealed_source_tree": sealed_tree,
        "accelerator_head": STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD,
        "accelerator_tree": STALE_WORKTREE_CLEANUP_ACCELERATOR_TREE,
        "validation_path_compatibility_transition": validation_path_transition,
    }


def _verified_validation_path_compatibility_transition(
    *,
    board: Any,
    current_head: str,
    current_config: Mapping[str, Any],
    current_source_identities: Mapping[str, str],
    prior_artifact_commit: str,
    prior_transition_receipt_id: str,
    prior_config_bytes: bytes,
    prior_operator_bytes: bytes,
    prior_validator_bytes: bytes,
) -> dict[str, Any]:
    """Admit one exact restoration of the declared supervisor test path."""

    operator_path = Path(__file__).resolve()
    operator_gate = _verified_validation_path_compatibility_operator_descendant(
        current_operator=_tracked_bytes(operator_path, head=current_head),
        current_head=current_head,
        operator_path=operator_path,
    )
    payload = operator_gate["receipt"]
    checkpoint = payload["prior_checkpoint"]
    repair_base = payload["repair_base"]
    sealed_source = payload["sealed_source"]
    validation_surface = payload["validation_surface"]
    validations = payload["validations"]

    checkpoint_fields = {
        "source_head",
        "repository_tree_id",
        "prior_artifact_commit",
        "stale_worktree_cleanup_transition_receipt_id",
        "changed_receipts",
    }
    expected_checkpoint_receipts = [
        {
            "path": (
                "artifacts/proof_carrying_semantic_minification/receipts/"
                "PCSM-020.json"
            ),
            "bytes_id": (
                "sha256:88c0bfe17eed6e9f01cc9d14832f8d23de31e436ab31a8e0"
                "a3d732f59a10b695"
            ),
        },
        {
            "path": (
                "artifacts/proof_carrying_semantic_minification/receipts/"
                "PCSM-021.json"
            ),
            "bytes_id": (
                "sha256:6a4a3a64ddc6ed552a3c3fcecf5931ec3a396e02c91a813a"
                "8e793341ae071127"
            ),
        },
        {
            "path": (
                "artifacts/proof_carrying_semantic_minification/receipts/"
                "PCSM-022.json"
            ),
            "bytes_id": (
                "sha256:b7fe0f17fcc708f1e09f65de233c00b4019f037b08937502a"
                "2fcc88dd67b14d2"
            ),
        },
    ]
    if (
        set(checkpoint) != checkpoint_fields
        or checkpoint.get("source_head")
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD
        or checkpoint.get("repository_tree_id")
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE
        or checkpoint.get("prior_artifact_commit") != prior_artifact_commit
        or prior_artifact_commit
        != "9b056251a42aac444478745b3ccb73e3507215e8"
        or checkpoint.get("stale_worktree_cleanup_transition_receipt_id")
        != prior_transition_receipt_id
        or prior_transition_receipt_id
        != "sha256:4d86e1fa4452a720859175d2e228dd09f50f92159577154f96ade16cb6e5e0b7"
        or checkpoint.get("changed_receipts")
        != expected_checkpoint_receipts
    ):
        raise OperatorError(
            "validation-path compatibility prior checkpoint changed"
        )
    if (
        _git_commit_tree(
            VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
            field="validation-path compatibility checkpoint",
        )
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_TREE
    ):
        raise OperatorError(
            "validation-path compatibility checkpoint tree changed"
        )
    _git_is_ancestor(
        prior_artifact_commit,
        VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
        field="cleanup artifact-to-validation checkpoint lineage",
    )
    expected_checkpoint_paths = tuple(
        item["path"] for item in expected_checkpoint_receipts
    )
    checkpoint_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{prior_artifact_commit}.."
                f"{VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD}",
            )
        ).splitlines()
        if line
    )
    if checkpoint_paths != expected_checkpoint_paths:
        raise OperatorError(
            "validation-path compatibility checkpoint source delta changed"
        )
    for item in expected_checkpoint_receipts:
        path = ROOT / item["path"]
        if (
            _identity(
                _git_blob_at(
                    head=VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
                    path=path,
                    field=f"validation checkpoint receipt {item['path']}",
                )
            )
            != item["bytes_id"]
        ):
            raise OperatorError(
                "validation-path compatibility checkpoint receipt changed"
            )

    validator_path = board.path(board.validator_path)
    checkpoint_config = _git_blob_at(
        head=VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
        path=board.config_path,
        field="validation-path compatibility checkpoint config",
    )
    checkpoint_operator = _git_blob_at(
        head=VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
        path=operator_path,
        field="validation-path compatibility checkpoint operator",
    )
    checkpoint_validator = _git_blob_at(
        head=VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
        path=validator_path,
        field="validation-path compatibility checkpoint validator",
    )
    if (
        checkpoint_config != prior_config_bytes
        or checkpoint_operator != prior_operator_bytes
        or checkpoint_validator != prior_validator_bytes
        or _identity(checkpoint_config)
        != "sha256:5f4222672c5da4a409fdd8428d8de588126848a986dbd4a8ec0ff9435bb0000a"
        or _identity(checkpoint_operator)
        != "sha256:c6fcfa916619bd6692f0299d9988671ae67c1e83c4bb45640d3c84218534bf72"
        or _identity(checkpoint_validator)
        != "sha256:57e3b957019ef0ee20cee5d2f50a7bfb5b1172ea8ee04db89a3426d28a290e89"
    ):
        raise OperatorError(
            "validation-path compatibility checkpoint authority changed"
        )

    base_commit = str(operator_gate["base_commit"])
    expected_base_paths = (
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
        "test/test_pcsm_validation_path_compatibility_transition.py",
    )
    expected_nested_paths = (
        "ipfs_accelerate_py/agent_supervisor/tests/"
        "proof_carrying_semantic_minification/test_structured_decoding.py",
        "test/agent_supervisor/pcsm",
    )
    repair_base_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "config_identity",
        "validator_identity",
        "accelerator_head",
        "accelerator_tree",
        "changed_paths",
        "nested_changed_paths",
    }
    base_config_bytes = _git_blob_at(
        head=base_commit,
        path=board.config_path,
        field="validation-path compatibility base config",
    )
    base_config = _json_mapping_bytes(
        base_config_bytes,
        field="validation-path compatibility base config",
    )
    base_validator = _git_blob_at(
        head=base_commit,
        path=validator_path,
        field="validation-path compatibility base validator",
    )
    if (
        set(repair_base) != repair_base_fields
        or repair_base.get("source_head") != base_commit
        or repair_base.get("parent")
        != VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD
        or repair_base.get("operator_identity")
        != _identity(operator_gate["base_operator"])
        or repair_base.get("config_identity") != _identity(base_config_bytes)
        or repair_base.get("validator_identity") != _identity(base_validator)
        or repair_base.get("accelerator_head")
        != VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD
        or repair_base.get("accelerator_tree")
        != VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE
        or tuple(repair_base.get("changed_paths") or ())
        != expected_base_paths
        or tuple(repair_base.get("nested_changed_paths") or ())
        != expected_nested_paths
        or base_validator != prior_validator_bytes
    ):
        raise OperatorError(
            "validation-path compatibility repair base changed"
        )

    prior_config = _json_mapping_bytes(
        prior_config_bytes,
        field="validation-path compatibility prior config",
    )
    expected_config = json.loads(_canonical_bytes(prior_config))
    expected_binding = expected_config.get("source_binding")
    if not isinstance(expected_binding, dict):
        raise OperatorError(
            "validation-path compatibility source binding is absent"
        )
    expected_binding["ipfs_accelerate_planning_revision"] = (
        VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD
    )
    expected_binding["ipfs_accelerate_planning_tree"] = (
        VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE
    )
    if base_config != expected_config:
        raise OperatorError(
            "validation-path compatibility config delta changed"
        )

    base_gitlink = str(
        _git("ls-tree", base_commit, "--", "external/ipfs_accelerate")
    ).strip().split()
    if (
        len(base_gitlink) < 3
        or base_gitlink[:2] != ["160000", "commit"]
        or base_gitlink[2]
        != VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD
    ):
        raise OperatorError(
            "validation-path compatibility accelerator gitlink changed"
        )

    accelerator_repository = ROOT / "external/ipfs_accelerate"
    if (
        _git_commit_tree(
            VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
            field="validation-path compatibility accelerator",
            repository=accelerator_repository,
        )
        != VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE
    ):
        raise OperatorError(
            "validation-path compatibility accelerator tree changed"
        )
    nested_parents = str(
        _git_in_repository(
            accelerator_repository,
            "show",
            "-s",
            "--format=%P",
            VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
        )
    ).strip().split()
    nested_paths = tuple(
        line
        for line in str(
            _git_in_repository(
                accelerator_repository,
                "diff",
                "--name-only",
                f"{STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD}.."
                f"{VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}",
            )
        ).splitlines()
        if line
    )
    bridge_path = "test/agent_supervisor/pcsm"
    product_root = (
        "ipfs_accelerate_py/agent_supervisor/tests/"
        "proof_carrying_semantic_minification"
    )
    product_module = f"{product_root}/test_structured_decoding.py"
    bridge_entry = str(
        _git_in_repository(
            accelerator_repository,
            "ls-tree",
            VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
            "--",
            bridge_path,
        )
    ).strip().split(maxsplit=3)
    bridge_parent_entry = str(
        _git_in_repository(
            accelerator_repository,
            "ls-tree",
            VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
            "--",
            "test/agent_supervisor",
        )
    ).strip().split(maxsplit=3)
    product_root_entry = str(
        _git_in_repository(
            accelerator_repository,
            "ls-tree",
            VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
            "--",
            product_root,
        )
    ).strip().split(maxsplit=3)
    product_module_entry = str(
        _git_in_repository(
            accelerator_repository,
            "ls-tree",
            VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
            "--",
            product_module,
        )
    ).strip().split(maxsplit=3)
    bridge_bytes = _git_in_repository(
        accelerator_repository,
        "show",
        f"{VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}:{bridge_path}",
        binary=True,
    )
    product_module_bytes = _git_in_repository(
        accelerator_repository,
        "show",
        f"{VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}:{product_module}",
        binary=True,
    )
    expected_bridge_target = (
        b"../../ipfs_accelerate_py/agent_supervisor/tests/"
        b"proof_carrying_semantic_minification"
    )
    if (
        nested_parents != [STALE_WORKTREE_CLEANUP_ACCELERATOR_HEAD]
        or nested_paths != expected_nested_paths
        or bridge_parent_entry[:2] != ["040000", "tree"]
        or bridge_parent_entry[3:] != ["test/agent_supervisor"]
        or bridge_entry
        != [
            "120000",
            "blob",
            "302b67f7129dcafc103c6414e027f8b67f541b0d",
            bridge_path,
        ]
        or bridge_bytes != expected_bridge_target
        or product_root_entry[:2] != ["040000", "tree"]
        or product_root_entry[3:] != [product_root]
        or product_module_entry
        != [
            "100644",
            "blob",
            "c25192cb06f20469093e9fc53e4e35d0c1ae171e",
            product_module,
        ]
        or not isinstance(product_module_bytes, bytes)
        or not product_module_bytes
    ):
        raise OperatorError(
            "validation-path compatibility nested path contract changed"
        )

    sealed_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "changed_paths",
    }
    if (
        set(sealed_source) != sealed_fields
        or sealed_source.get("source_head")
        != operator_gate["sealed_source_head"]
        or sealed_source.get("repository_tree_id")
        != operator_gate["sealed_source_tree"]
        or sealed_source.get("parent") != base_commit
        or sealed_source.get("operator_identity")
        != _identity(operator_gate["expected_operator"])
        or tuple(sealed_source.get("changed_paths") or ())
        != ("scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",)
    ):
        raise OperatorError(
            "validation-path compatibility sealed source changed"
        )

    expected_validation_surface = {
        "declared_command": [
            "python",
            "-m",
            "pytest",
            "-q",
            "external/ipfs_accelerate/test/agent_supervisor",
        ],
        "declared_path": "external/ipfs_accelerate/test/agent_supervisor",
        "nested_bridge_path": "test/agent_supervisor/pcsm",
        "nested_bridge_kind": "relative_directory_symlink",
        "nested_bridge_target": (
            "../../ipfs_accelerate_py/agent_supervisor/tests/"
            "proof_carrying_semantic_minification"
        ),
        "product_test_root": product_root,
        "minimum_collected_tests": 11,
        "taskboard_validation_changed": False,
        "generator_validation_changed": False,
    }
    if dict(validation_surface) != expected_validation_surface:
        raise OperatorError(
            "validation-path compatibility validation surface changed"
        )
    required_validations = {
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "external/ipfs_accelerate/test/agent_supervisor",
            ),
        ),
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/test_pcsm_validation_path_compatibility_transition.py",
            ),
        ),
        (
            ".",
            (
                "python",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
                "--check-all",
            ),
        ),
    }
    observed_validations: set[tuple[str, tuple[str, ...]]] = set()
    declared_validation_summary = ""
    for validation in validations:
        if not isinstance(validation, Mapping) or set(validation) != {
            "cwd",
            "command",
            "outcome",
            "summary",
        }:
            raise OperatorError(
                "validation-path compatibility validation is malformed"
            )
        command = validation.get("command")
        summary = validation.get("summary")
        if (
            not isinstance(command, list)
            or any(not isinstance(item, str) or not item for item in command)
            or validation.get("outcome") != "passed"
            or not isinstance(summary, str)
            or not summary
        ):
            raise OperatorError(
                "validation-path compatibility validation did not pass"
            )
        observed = (str(validation.get("cwd") or ""), tuple(command))
        observed_validations.add(observed)
        if command == expected_validation_surface["declared_command"]:
            declared_validation_summary = summary
    if (
        len(validations) != len(required_validations)
        or observed_validations != required_validations
        or re.search(r"\b11 passed\b", declared_validation_summary) is None
    ):
        raise OperatorError(
            "validation-path compatibility validations are incomplete"
        )

    current_config_bytes = _tracked_bytes(board.config_path, head=current_head)
    current_operator = _tracked_bytes(operator_path, head=current_head)
    current_validator = _tracked_bytes(validator_path, head=current_head)
    transition_test_path = (
        ROOT / "test/test_pcsm_validation_path_compatibility_transition.py"
    )
    current_gitlink = str(
        _git("ls-tree", current_head, "--", "external/ipfs_accelerate")
    ).strip().split()
    exact_validation_path_source = bool(
        current_config_bytes != base_config_bytes
        or _canonical_bytes(current_config) != _canonical_bytes(base_config)
        or current_operator != operator_gate["expected_operator"]
        or current_validator != base_validator
        or _tracked_bytes(transition_test_path, head=current_head)
        != _git_blob_at(
            head=base_commit,
            path=transition_test_path,
            field="validation-path compatibility focused test",
        )
        or current_source_identities.get("config")
        != _identity(base_config_bytes)
        or current_source_identities.get("operator")
        != _identity(operator_gate["expected_operator"])
        or current_source_identities.get("validator")
        != _identity(base_validator)
        or len(current_gitlink) < 3
        or current_gitlink[:2] != ["160000", "commit"]
        or current_gitlink[2]
        != VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD
    ) is False
    database_watchdog_activity_transition: dict[str, Any] = {}
    if not exact_validation_path_source:
        database_watchdog_activity_transition = (
            _verified_database_watchdog_activity_transition(
                board=board,
                current_head=current_head,
                current_config=current_config,
                current_source_identities=current_source_identities,
                prior_artifact_commit=operator_gate["artifact_commit"],
                prior_transition_receipt_id=str(
                    payload.get("receipt_id") or ""
                ),
                prior_config_bytes=base_config_bytes,
                prior_operator_bytes=operator_gate["expected_operator"],
                prior_validator_bytes=base_validator,
            )
        )
    source_paths = _restart_source_paths(board)
    for name in ("taskboard", "objectives", "plan", "generator"):
        checkpoint_bytes = _git_blob_at(
            head=VALIDATION_PATH_COMPATIBILITY_CHECKPOINT_HEAD,
            path=source_paths[name],
            field=f"validation-path checkpoint {name}",
        )
        current_bytes = _tracked_bytes(source_paths[name], head=current_head)
        if (
            current_bytes != checkpoint_bytes
            or current_source_identities.get(name) != _identity(current_bytes)
        ):
            raise OperatorError(
                "validation-path compatibility changed immutable authority"
            )
    return {
        "receipt": payload,
        "artifact_commit": operator_gate["artifact_commit"],
        "sealed_source_head": operator_gate["sealed_source_head"],
        "sealed_source_tree": operator_gate["sealed_source_tree"],
        "accelerator_head": VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD,
        "accelerator_tree": VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_TREE,
        "database_watchdog_activity_transition": (
            database_watchdog_activity_transition
        ),
    }


def _verified_database_watchdog_activity_transition(
    *,
    board: Any,
    current_head: str,
    current_config: Mapping[str, Any],
    current_source_identities: Mapping[str, str],
    prior_artifact_commit: str,
    prior_transition_receipt_id: str,
    prior_config_bytes: bytes,
    prior_operator_bytes: bytes,
    prior_validator_bytes: bytes,
) -> dict[str, Any]:
    """Admit one exact guard for live successor database callback work."""

    operator_path = Path(__file__).resolve()
    operator_gate = _verified_database_watchdog_activity_operator_descendant(
        current_operator=_tracked_bytes(operator_path, head=current_head),
        current_head=current_head,
        operator_path=operator_path,
    )
    payload = operator_gate["receipt"]
    checkpoint = payload["prior_checkpoint"]
    repair_base = payload["repair_base"]
    sealed_source = payload["sealed_source"]
    watchdog_contract = payload["watchdog_activity_contract"]
    validations = payload["validations"]

    checkpoint_fields = {
        "source_head",
        "repository_tree_id",
        "prior_artifact_commit",
        "validation_path_compatibility_transition_receipt_id",
        "changed_files",
    }
    expected_checkpoint_files = [
        {
            "path": (
                "artifacts/proof_carrying_semantic_minification/receipts/"
                "PCSM-023.json"
            ),
            "bytes_id": (
                "sha256:b83deef53412fb65ef1890291c97931d4ad3ffcd72ea398750"
                "7cad1059703adc"
            ),
        },
        {
            "path": (
                "artifacts/proof_carrying_semantic_minification/receipts/"
                "PCSM-026.json"
            ),
            "bytes_id": (
                "sha256:4c6d93e833a15ee956b4d9561e5772285cb2d3053c6bb25ee8"
                "3ed73b098495ba"
            ),
        },
        {
            "path": (
                "artifacts/proof_carrying_semantic_minification/receipts/"
                "PCSM-040.json"
            ),
            "bytes_id": (
                "sha256:91a620fd993138a4356bcec8b0572bfa696e3353b2dd95110d"
                "5efd71f4b58924"
            ),
        },
        {
            "path": "test/test_pcsm_stale_worktree_cleanup_transition.py",
            "bytes_id": (
                "sha256:f170db9ffe7eedc8404a30f22dbb769e711c166bb15903636c"
                "15fde2d692d67a"
            ),
        },
    ]
    if (
        set(checkpoint) != checkpoint_fields
        or checkpoint.get("source_head")
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD
        or checkpoint.get("repository_tree_id")
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_TREE
        or checkpoint.get("prior_artifact_commit") != prior_artifact_commit
        or prior_artifact_commit
        != "c6e4a75f03662d9fe2ed26246735638d9be3ae88"
        or checkpoint.get(
            "validation_path_compatibility_transition_receipt_id"
        )
        != prior_transition_receipt_id
        or prior_transition_receipt_id
        != "sha256:e9aa30a3d9e1a1e5603b463bbcc38ba52cee745c66712d5a9d33c83bb4781485"
        or checkpoint.get("changed_files") != expected_checkpoint_files
    ):
        raise OperatorError(
            "database-watchdog activity prior checkpoint changed"
        )
    if (
        _git_commit_tree(
            DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
            field="database-watchdog activity checkpoint",
        )
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_TREE
    ):
        raise OperatorError(
            "database-watchdog activity checkpoint tree changed"
        )
    _git_is_ancestor(
        prior_artifact_commit,
        DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
        field="validation artifact-to-watchdog checkpoint lineage",
    )
    expected_checkpoint_paths = tuple(
        item["path"] for item in expected_checkpoint_files
    )
    checkpoint_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{prior_artifact_commit}.."
                f"{DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD}",
            )
        ).splitlines()
        if line
    )
    if checkpoint_paths != expected_checkpoint_paths:
        raise OperatorError(
            "database-watchdog activity checkpoint delta changed"
        )
    for item in expected_checkpoint_files:
        path = ROOT / item["path"]
        checkpoint_bytes = _git_blob_at(
            head=DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
            path=path,
            field=f"database-watchdog checkpoint file {item['path']}",
        )
        if _identity(checkpoint_bytes) != item["bytes_id"]:
            raise OperatorError(
                "database-watchdog activity checkpoint file changed"
            )

    validator_path = board.path(board.validator_path)
    checkpoint_config = _git_blob_at(
        head=DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
        path=board.config_path,
        field="database-watchdog checkpoint config",
    )
    checkpoint_operator = _git_blob_at(
        head=DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
        path=operator_path,
        field="database-watchdog checkpoint operator",
    )
    checkpoint_validator = _git_blob_at(
        head=DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
        path=validator_path,
        field="database-watchdog checkpoint validator",
    )
    if (
        checkpoint_config != prior_config_bytes
        or checkpoint_operator != prior_operator_bytes
        or checkpoint_validator != prior_validator_bytes
    ):
        raise OperatorError(
            "database-watchdog activity checkpoint authority changed"
        )

    base_commit = str(operator_gate["base_commit"])
    expected_base_paths = (
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
        "test/test_pcsm_database_watchdog_activity_transition.py",
    )
    expected_nested_paths = (
        "ipfs_accelerate_py/agent_supervisor/todo_daemon/"
        "implementation_supervisor.py",
        "test/api/"
        "test_implementation_supervisor_control_plane_pool_lease.py",
    )
    repair_base_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "config_identity",
        "validator_identity",
        "accelerator_head",
        "accelerator_tree",
        "changed_paths",
        "nested_changed_paths",
    }
    base_config_bytes = _git_blob_at(
        head=base_commit,
        path=board.config_path,
        field="database-watchdog activity base config",
    )
    base_config = _json_mapping_bytes(
        base_config_bytes,
        field="database-watchdog activity base config",
    )
    base_validator = _git_blob_at(
        head=base_commit,
        path=validator_path,
        field="database-watchdog activity base validator",
    )
    if (
        set(repair_base) != repair_base_fields
        or repair_base.get("source_head") != base_commit
        or repair_base.get("parent")
        != DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD
        or repair_base.get("operator_identity")
        != _identity(operator_gate["base_operator"])
        or repair_base.get("config_identity") != _identity(base_config_bytes)
        or repair_base.get("validator_identity") != _identity(base_validator)
        or repair_base.get("accelerator_head")
        != DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD
        or repair_base.get("accelerator_tree")
        != DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_TREE
        or tuple(repair_base.get("changed_paths") or ())
        != expected_base_paths
        or tuple(repair_base.get("nested_changed_paths") or ())
        != expected_nested_paths
        or base_validator != prior_validator_bytes
    ):
        raise OperatorError(
            "database-watchdog activity repair base changed"
        )

    prior_config = _json_mapping_bytes(
        prior_config_bytes,
        field="database-watchdog activity prior config",
    )
    expected_config = json.loads(_canonical_bytes(prior_config))
    expected_binding = expected_config.get("source_binding")
    if not isinstance(expected_binding, dict):
        raise OperatorError(
            "database-watchdog activity source binding is absent"
        )
    expected_binding["ipfs_accelerate_planning_revision"] = (
        DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD
    )
    expected_binding["ipfs_accelerate_planning_tree"] = (
        DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_TREE
    )
    if base_config != expected_config:
        raise OperatorError(
            "database-watchdog activity config delta changed"
        )

    base_gitlink = str(
        _git("ls-tree", base_commit, "--", "external/ipfs_accelerate")
    ).strip().split()
    if (
        len(base_gitlink) < 3
        or base_gitlink[:2] != ["160000", "commit"]
        or base_gitlink[2] != DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD
    ):
        raise OperatorError(
            "database-watchdog activity accelerator gitlink changed"
        )
    accelerator_repository = ROOT / "external/ipfs_accelerate"
    if (
        _git_commit_tree(
            DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD,
            field="database-watchdog activity accelerator",
            repository=accelerator_repository,
        )
        != DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_TREE
    ):
        raise OperatorError(
            "database-watchdog activity accelerator tree changed"
        )
    nested_parents = str(
        _git_in_repository(
            accelerator_repository,
            "show",
            "-s",
            "--format=%P",
            DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD,
        )
    ).strip().split()
    nested_paths = tuple(
        line
        for line in str(
            _git_in_repository(
                accelerator_repository,
                "diff",
                "--name-only",
                f"{VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD}.."
                f"{DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD}",
            )
        ).splitlines()
        if line
    )
    if (
        nested_parents != [VALIDATION_PATH_COMPATIBILITY_ACCELERATOR_HEAD]
        or nested_paths != expected_nested_paths
    ):
        raise OperatorError(
            "database-watchdog activity nested source delta changed"
        )

    sealed_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "changed_paths",
    }
    if (
        set(sealed_source) != sealed_fields
        or sealed_source.get("source_head")
        != operator_gate["sealed_source_head"]
        or sealed_source.get("repository_tree_id")
        != operator_gate["sealed_source_tree"]
        or sealed_source.get("parent") != base_commit
        or sealed_source.get("operator_identity")
        != _identity(operator_gate["expected_operator"])
        or tuple(sealed_source.get("changed_paths") or ())
        != (
            "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
        )
    ):
        raise OperatorError(
            "database-watchdog activity sealed source changed"
        )

    expected_contract = {
        "trigger": "stuck_outer_task_projection",
        "corroboration_sources": [
            "active_managed_database_worktree_pool_lease",
            "active_managed_database_nonterminal_lifecycle_claim",
        ],
        "corroboration_scope": "current_managed_child_exact_identity",
        "decision": "keep_running_before_supervisor_maintenance",
        "maintenance_invoked": False,
        "daemon_recycled": False,
        "attempt_budget_consumed": False,
        "provider_invocation_consumed": False,
    }
    if dict(watchdog_contract) != expected_contract:
        raise OperatorError(
            "database-watchdog activity contract changed"
        )

    required_validations = {
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "external/ipfs_accelerate/test/api/"
                "test_implementation_supervisor_control_plane_pool_lease.py",
            ),
        ),
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "external/ipfs_accelerate/test/agent_supervisor",
            ),
        ),
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/test_pcsm_database_watchdog_activity_transition.py",
            ),
        ),
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/test_pcsm_blocked_retry_batch_recovery.py",
                "test/test_pcsm_executor_bootstrap_broker_resilience.py",
                "test/test_pcsm_stale_worktree_cleanup_transition.py",
                "test/test_pcsm_validation_path_compatibility_transition.py",
                "test/test_pcsm_database_watchdog_activity_transition.py",
            ),
        ),
        (
            ".",
            (
                "python",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
                "--check-all",
            ),
        ),
    }
    observed_validations: set[tuple[str, tuple[str, ...]]] = set()
    summaries: dict[tuple[str, ...], str] = {}
    for validation in validations:
        if not isinstance(validation, Mapping) or set(validation) != {
            "cwd",
            "command",
            "outcome",
            "summary",
        }:
            raise OperatorError(
                "database-watchdog activity validation is malformed"
            )
        command = validation.get("command")
        summary = validation.get("summary")
        if (
            not isinstance(command, list)
            or any(not isinstance(item, str) or not item for item in command)
            or validation.get("outcome") != "passed"
            or not isinstance(summary, str)
            or not summary
        ):
            raise OperatorError(
                "database-watchdog activity validation did not pass"
            )
        observed = (str(validation.get("cwd") or ""), tuple(command))
        observed_validations.add(observed)
        summaries[tuple(command)] = summary
    focused_nested = (
        "python",
        "-m",
        "pytest",
        "-q",
        "external/ipfs_accelerate/test/api/"
        "test_implementation_supervisor_control_plane_pool_lease.py",
    )
    declared_nested = (
        "python",
        "-m",
        "pytest",
        "-q",
        "external/ipfs_accelerate/test/agent_supervisor",
    )
    if (
        len(validations) != len(required_validations)
        or observed_validations != required_validations
        or re.search(r"\b38 passed\b", summaries.get(focused_nested, ""))
        is None
        or re.search(r"\b11 passed\b", summaries.get(declared_nested, ""))
        is None
    ):
        raise OperatorError(
            "database-watchdog activity validations are incomplete"
        )

    current_config_bytes = _tracked_bytes(board.config_path, head=current_head)
    current_operator = _tracked_bytes(operator_path, head=current_head)
    current_validator = _tracked_bytes(validator_path, head=current_head)
    transition_test_path = (
        ROOT / "test/test_pcsm_database_watchdog_activity_transition.py"
    )
    prior_transition_test_path = (
        ROOT / "test/test_pcsm_validation_path_compatibility_transition.py"
    )
    current_gitlink = str(
        _git("ls-tree", current_head, "--", "external/ipfs_accelerate")
    ).strip().split()
    if (
        current_config_bytes != base_config_bytes
        or _canonical_bytes(current_config) != _canonical_bytes(base_config)
        or current_operator != operator_gate["expected_operator"]
        or current_validator != base_validator
        or _tracked_bytes(transition_test_path, head=current_head)
        != _git_blob_at(
            head=base_commit,
            path=transition_test_path,
            field="database-watchdog activity focused test",
        )
        or _tracked_bytes(prior_transition_test_path, head=current_head)
        != _git_blob_at(
            head=DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
            path=prior_transition_test_path,
            field="prior validation-path focused test",
        )
        or current_source_identities.get("config")
        != _identity(base_config_bytes)
        or current_source_identities.get("operator")
        != _identity(operator_gate["expected_operator"])
        or current_source_identities.get("validator")
        != _identity(base_validator)
        or len(current_gitlink) < 3
        or current_gitlink[:2] != ["160000", "commit"]
        or current_gitlink[2] != DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD
    ):
        raise OperatorError(
            "database-watchdog activity live source changed"
        )
    for item in expected_checkpoint_files:
        path = ROOT / item["path"]
        current_bytes = _tracked_bytes(path, head=current_head)
        if _identity(current_bytes) != item["bytes_id"]:
            raise OperatorError(
                "database-watchdog activity checkpoint evidence changed"
            )
    source_paths = _restart_source_paths(board)
    for name in ("taskboard", "objectives", "plan", "generator"):
        checkpoint_bytes = _git_blob_at(
            head=DATABASE_WATCHDOG_ACTIVITY_CHECKPOINT_HEAD,
            path=source_paths[name],
            field=f"database-watchdog checkpoint {name}",
        )
        current_bytes = _tracked_bytes(source_paths[name], head=current_head)
        if (
            current_bytes != checkpoint_bytes
            or current_source_identities.get(name) != _identity(current_bytes)
        ):
            raise OperatorError(
                "database-watchdog activity changed immutable authority"
            )
    return {
        "receipt": payload,
        "artifact_commit": operator_gate["artifact_commit"],
        "sealed_source_head": operator_gate["sealed_source_head"],
        "sealed_source_tree": operator_gate["sealed_source_tree"],
        "accelerator_head": DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_HEAD,
        "accelerator_tree": DATABASE_WATCHDOG_ACTIVITY_ACCELERATOR_TREE,
    }


def _verified_current_head_blocked_retry_descendant_repair(
    *,
    board: Any,
    current_head: str,
    current_tree: str,
    current_config: Mapping[str, Any],
    current_source_identities: Mapping[str, str],
    current_attempt_limit: int,
    historical_repair: Mapping[str, Any],
) -> dict[str, Any]:
    """Admit the exact 9c→aa5→sealed-base repair and four-task batch."""

    base_commit = CURRENT_HEAD_BLOCKED_RETRY_REPAIR_BASE_COMMIT
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        raise OperatorError("current-head blocked-retry repair base is unsealed")
    payload = _json_mapping_bytes(
        _tracked_bytes(
            CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_PATH,
            head=current_head,
        ),
        field="current-head blocked-retry descendant repair",
    )
    required_fields = {
        "schema",
        "reason",
        "historical_authority",
        "intermediate_seal",
        "repair_base",
        "sealed_source",
        "blocked_retry_batch",
        "validations",
        "historical_receipts_preserved",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    historical = payload.get("historical_authority")
    intermediate = payload.get("intermediate_seal")
    repair_base = payload.get("repair_base")
    sealed_source = payload.get("sealed_source")
    batch_binding = payload.get("blocked_retry_batch")
    validations = payload.get("validations")
    if (
        set(payload) != required_fields
        or payload.get("schema")
        != CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_SCHEMA
        or payload.get("reason")
        != "reseal_false_protected_path_blocks_for_fresh_portal_revalidation"
        or not isinstance(historical, Mapping)
        or not isinstance(intermediate, Mapping)
        or not isinstance(repair_base, Mapping)
        or not isinstance(sealed_source, Mapping)
        or not isinstance(batch_binding, Mapping)
        or not isinstance(validations, list)
        or not validations
        or payload.get("historical_receipts_preserved") is not True
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError("current-head blocked-retry descendant seal is invalid")

    historical_fields = {
        "source_head",
        "repository_tree_id",
        "config_identity",
        "operator_identity",
        "handoff_repair_receipt_id",
        "max_task_attempts",
    }
    if (
        set(historical) != historical_fields
        or historical.get("source_head")
        != CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_HEAD
        or historical.get("repository_tree_id")
        != CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_TREE
        or historical.get("config_identity")
        != "sha256:4f404caf87fe4a927875a16bf7a2117128079ae18bebd3399305f9d8963b108c"
        or historical.get("operator_identity")
        != "sha256:125612467dbf9b0c40da9bee9b9e1bfa59dce4e79df3a0bcccef3e9e5b8be433"
        or historical.get("handoff_repair_receipt_id")
        != historical_repair.get("receipt_id")
        or historical.get("max_task_attempts") != 2
    ):
        raise OperatorError("historical blocked-retry authority changed")

    intermediate_fields = {
        "source_head",
        "repository_tree_id",
        "config_identity",
        "accelerator_head",
        "accelerator_tree",
        "first_parent_chain",
        "added_receipts",
    }
    chain = intermediate.get("first_parent_chain")
    added_receipts = intermediate.get("added_receipts")
    if (
        set(intermediate) != intermediate_fields
        or intermediate.get("source_head")
        != CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD
        or intermediate.get("repository_tree_id")
        != CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_TREE
        or intermediate.get("config_identity")
        != CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_CONFIG_ID
        or intermediate.get("accelerator_head")
        != CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_ACCELERATOR_HEAD
        or intermediate.get("accelerator_tree")
        != CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_ACCELERATOR_TREE
        or not isinstance(chain, list)
        or not chain
        or not isinstance(added_receipts, list)
    ):
        raise OperatorError("intermediate blocked-retry seal changed")
    observed_chain = tuple(
        line
        for line in str(
            _git(
                "rev-list",
                "--first-parent",
                "--reverse",
                f"{CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_HEAD}.."
                f"{CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD}",
            )
        ).splitlines()
        if line
    )
    sealed_chain: list[str] = []
    for item in chain:
        if not isinstance(item, Mapping) or set(item) != {
            "commit",
            "tree",
            "parents",
        }:
            raise OperatorError("intermediate first-parent chain is malformed")
        commit = str(item.get("commit") or "")
        parents = str(_git("show", "-s", "--format=%P", commit)).strip().split()
        if (
            _git_commit_tree(commit, field="intermediate chain commit")
            != item.get("tree")
            or parents != item.get("parents")
        ):
            raise OperatorError("intermediate first-parent chain changed")
        sealed_chain.append(commit)
    if tuple(sealed_chain) != observed_chain:
        raise OperatorError("intermediate first-parent chain is incomplete")

    expected_receipt_paths = {
        f"artifacts/proof_carrying_semantic_minification/receipts/PCSM-{number}.json"
        for number in ("011", "013", "014", "015", "016", "017", "018")
    }
    observed_receipt_paths: set[str] = set()
    for item in added_receipts:
        if not isinstance(item, Mapping) or set(item) != {"path", "bytes_id"}:
            raise OperatorError("intermediate added receipt binding is malformed")
        path = str(item.get("path") or "")
        observed_receipt_paths.add(path)
        if _identity(
            _git_blob_at(
                head=CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD,
                path=ROOT / path,
                field=f"intermediate receipt {path}",
            )
        ) != item.get("bytes_id"):
            raise OperatorError("intermediate receipt bytes changed")
    intermediate_paths = {
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_HEAD}.."
                f"{CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD}",
            )
        ).splitlines()
        if line
    }
    if (
        observed_receipt_paths != expected_receipt_paths
        or intermediate_paths
        != expected_receipt_paths
        | {
            "config/proof_carrying_semantic_minification_v1_supervisor.json",
            "external/ipfs_accelerate",
        }
    ):
        raise OperatorError("intermediate blocked-retry source delta changed")

    base_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "config_identity",
        "validator_identity",
        "accelerator_head",
        "accelerator_tree",
        "changed_paths",
        "nested_commits",
        "max_task_attempts_before",
        "max_task_attempts_after",
    }
    if set(repair_base) != base_fields:
        raise OperatorError("blocked-retry repair base fields are not exact")
    base_tree = _git_commit_tree(base_commit, field="blocked-retry repair base")
    base_parents = str(
        _git("show", "-s", "--format=%P", base_commit)
    ).strip().split()
    base_paths = tuple(
        line
        for line in str(
            _git(
                "diff",
                "--name-only",
                f"{CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD}..{base_commit}",
            )
        ).splitlines()
        if line
    )
    expected_base_paths = (
        "config/proof_carrying_semantic_minification_v1_supervisor.json",
        "external/ipfs_accelerate",
        "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
        "scripts/validate_proof_carrying_semantic_minification_board.py",
        "test/test_pcsm_blocked_retry_batch_recovery.py",
    )
    operator_path = Path(__file__).resolve()
    base_operator = _git_blob_at(
        head=base_commit,
        path=operator_path,
        field="blocked-retry base operator",
    )
    base_config = _git_blob_at(
        head=base_commit,
        path=board.config_path,
        field="blocked-retry base config",
    )
    base_validator = _git_blob_at(
        head=base_commit,
        path=board.path(board.validator_path),
        field="blocked-retry base validator",
    )
    accelerator_head = str(repair_base.get("accelerator_head") or "")
    accelerator_tree = str(repair_base.get("accelerator_tree") or "")
    if (
        repair_base.get("source_head") != base_commit
        or repair_base.get("repository_tree_id") != base_tree
        or repair_base.get("parent")
        != CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD
        or base_parents != [CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD]
        or repair_base.get("operator_identity") != _identity(base_operator)
        or repair_base.get("config_identity") != _identity(base_config)
        or repair_base.get("validator_identity") != _identity(base_validator)
        or tuple(repair_base.get("changed_paths") or ()) != expected_base_paths
        or base_paths != expected_base_paths
        or repair_base.get("max_task_attempts_before") != 2
        or repair_base.get("max_task_attempts_after") != 3
        or current_attempt_limit != 3
        or current_tree != str(_git("rev-parse", "HEAD^{tree}")).strip()
    ):
        raise OperatorError("blocked-retry repair base changed")
    base_config_payload = _json_mapping_bytes(
        base_config,
        field="blocked-retry base config",
    )
    base_binding = base_config_payload.get("source_binding")
    if (
        not isinstance(base_binding, Mapping)
        or base_config_payload.get("max_task_attempts") != 3
        or base_binding.get("ipfs_accelerate_planning_revision")
        != accelerator_head
        or base_binding.get("ipfs_accelerate_planning_tree")
        != accelerator_tree
        or _git_commit_tree(
            accelerator_head,
            field="blocked-retry accelerator repair",
            repository=ROOT / "external/ipfs_accelerate",
        )
        != accelerator_tree
    ):
        raise OperatorError("blocked-retry base config changed")

    nested_commits = repair_base.get("nested_commits")
    if not isinstance(nested_commits, list) or len(nested_commits) != 2:
        raise OperatorError("blocked-retry nested repair chain is absent")
    previous = CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_ACCELERATOR_HEAD
    accelerator_repository = ROOT / "external/ipfs_accelerate"
    for item in nested_commits:
        if not isinstance(item, Mapping) or set(item) != {
            "commit",
            "tree",
            "parent",
            "changed_paths",
        }:
            raise OperatorError("blocked-retry nested repair is malformed")
        commit = str(item.get("commit") or "")
        parents = subprocess.run(
            ["git", "show", "-s", "--format=%P", commit],
            cwd=accelerator_repository,
            text=True,
            capture_output=True,
            check=False,
        )
        changed = subprocess.run(
            ["git", "diff", "--name-only", f"{previous}..{commit}"],
            cwd=accelerator_repository,
            text=True,
            capture_output=True,
            check=False,
        )
        if (
            parents.returncode != 0
            or parents.stdout.strip().split() != [previous]
            or item.get("parent") != previous
            or _git_commit_tree(
                commit,
                field="blocked-retry nested commit",
                repository=accelerator_repository,
            )
            != item.get("tree")
            or changed.returncode != 0
            or changed.stdout.splitlines() != item.get("changed_paths")
        ):
            raise OperatorError("blocked-retry nested repair chain changed")
        previous = commit
    if previous != accelerator_head:
        raise OperatorError("blocked-retry nested repair endpoint changed")

    sealed_fields = {
        "source_head",
        "repository_tree_id",
        "parent",
        "operator_identity",
        "changed_paths",
    }
    sealed_head = str(sealed_source.get("source_head") or "")
    sealed_tree = _git_commit_tree(
        sealed_head,
        field="blocked-retry sealed source",
    )
    sealed_parents = str(
        _git("show", "-s", "--format=%P", sealed_head)
    ).strip().split()
    sealed_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{base_commit}..{sealed_head}")
        ).splitlines()
        if line
    )
    pending_base = (
        "PENDING_" + "CURRENT_HEAD_BLOCKED_RETRY_REPAIR_BASE_COMMIT"
    ).encode("ascii")
    expected_operator = base_operator.replace(
        pending_base,
        base_commit.encode("ascii"),
        1,
    )
    sealed_operator = _git_blob_at(
        head=sealed_head,
        path=operator_path,
        field="blocked-retry sealed operator",
    )
    if (
        set(sealed_source) != sealed_fields
        or sealed_source.get("repository_tree_id") != sealed_tree
        or sealed_source.get("parent") != base_commit
        or sealed_parents != [base_commit]
        or sealed_source.get("operator_identity") != _identity(expected_operator)
        or sealed_operator != expected_operator
        or tuple(sealed_source.get("changed_paths") or ())
        != ("scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",)
        or sealed_paths
        != ("scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",)
        or base_operator.count(pending_base) != 1
    ):
        raise OperatorError("blocked-retry sealed source changed")

    batch_fields = {
        "path",
        "batch_receipt_id",
        "sealed_source_head",
        "sealed_source_tree",
    }
    if (
        set(batch_binding) != batch_fields
        or batch_binding.get("path")
        != CURRENT_HEAD_BLOCKED_RETRY_BATCH_PATH.relative_to(ROOT).as_posix()
        or re.fullmatch(
            r"sha256:[0-9a-f]{64}",
            str(batch_binding.get("batch_receipt_id") or ""),
        )
        is None
        or batch_binding.get("sealed_source_head") != sealed_head
        or batch_binding.get("sealed_source_tree") != sealed_tree
    ):
        raise OperatorError("blocked-retry batch binding changed")
    batch_bytes = _tracked_bytes(
        CURRENT_HEAD_BLOCKED_RETRY_BATCH_PATH,
        head=current_head,
    )
    batch = _json_mapping_bytes(
        batch_bytes,
        field="current-head blocked-retry batch",
    )
    verified_batch = _verified_current_head_blocked_retry_batch(
        batch,
        sealed_source_head=sealed_head,
        sealed_source_tree=sealed_tree,
        current_attempt_limit=current_attempt_limit,
    )
    if verified_batch.get("batch_receipt_id") != batch_binding.get(
        "batch_receipt_id"
    ):
        raise OperatorError("blocked-retry batch identity changed")

    receipt_relative = (
        CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_PATH.relative_to(ROOT).as_posix()
    )
    batch_relative = CURRENT_HEAD_BLOCKED_RETRY_BATCH_PATH.relative_to(ROOT).as_posix()
    receipt_additions = tuple(
        line
        for line in str(
            _git(
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                receipt_relative,
            )
        ).splitlines()
        if line
    )
    batch_additions = tuple(
        line
        for line in str(
            _git(
                "log",
                "--diff-filter=A",
                "--format=%H",
                "--",
                batch_relative,
            )
        ).splitlines()
        if line
    )
    if (
        len(receipt_additions) != 1
        or receipt_additions != batch_additions
    ):
        raise OperatorError("blocked-retry artifact introduction is not exact")
    artifact_commit = receipt_additions[0]
    artifact_parents = str(
        _git("show", "-s", "--format=%P", artifact_commit)
    ).strip().split()
    artifact_paths = tuple(
        line
        for line in str(
            _git("diff", "--name-only", f"{sealed_head}..{artifact_commit}")
        ).splitlines()
        if line
    )
    if (
        artifact_parents != [sealed_head]
        or artifact_paths != tuple(sorted((batch_relative, receipt_relative)))
        or _git_blob_at(
            head=artifact_commit,
            path=CURRENT_HEAD_BLOCKED_RETRY_BATCH_PATH,
            field="introduced blocked-retry batch",
        )
        != batch_bytes
        or _git_blob_at(
            head=artifact_commit,
            path=CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_PATH,
            field="introduced blocked-retry descendant receipt",
        )
        != _tracked_bytes(
            CURRENT_HEAD_BLOCKED_RETRY_DESCENDANT_REPAIR_PATH,
            head=current_head,
        )
    ):
        raise OperatorError("blocked-retry artifacts changed after introduction")

    required_validations = {
        (
            "external/ipfs_accelerate",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/api/causal_federation/test_admitted_executor.py",
                "-k",
                "operator_blocked_retry_recovers_once_and_replays_after_restart",
            ),
        ),
        (
            ".",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/test_pcsm_blocked_retry_batch_recovery.py",
            ),
        ),
    }
    observed_validations: set[tuple[str, tuple[str, ...]]] = set()
    for validation in validations:
        if not isinstance(validation, Mapping) or set(validation) != {
            "cwd",
            "command",
            "outcome",
            "summary",
        }:
            raise OperatorError("blocked-retry validation is malformed")
        command = validation.get("command")
        if (
            not isinstance(command, list)
            or any(not isinstance(item, str) or not item for item in command)
            or validation.get("outcome") != "passed"
            or not isinstance(validation.get("summary"), str)
            or not validation.get("summary")
        ):
            raise OperatorError("blocked-retry validation did not pass")
        observed_validations.add(
            (str(validation.get("cwd") or ""), tuple(command))
        )
    if observed_validations != required_validations:
        raise OperatorError("blocked-retry validations are incomplete")

    current_config_bytes = _tracked_bytes(board.config_path, head=current_head)
    current_operator = _tracked_bytes(operator_path, head=current_head)
    current_validator = _tracked_bytes(
        board.path(board.validator_path),
        head=current_head,
    )
    _git_is_ancestor(
        artifact_commit,
        current_head,
        field="blocked-retry artifact-to-current lineage",
    )
    exact_blocked_retry_source = bool(
        current_config_bytes == base_config
        and _canonical_bytes(current_config)
        == _canonical_bytes(base_config_payload)
        and current_operator == expected_operator
        and current_validator == base_validator
        and current_source_identities.get("config") == _identity(base_config)
        and current_source_identities.get("operator")
        == _identity(expected_operator)
        and current_source_identities.get("validator")
        == _identity(base_validator)
    )
    cleanup_transition: dict[str, Any] = {}
    if not exact_blocked_retry_source:
        cleanup_transition = _verified_stale_worktree_cleanup_transition(
            board=board,
            current_head=current_head,
            current_config=current_config,
            current_source_identities=current_source_identities,
            prior_artifact_commit=artifact_commit,
            prior_descendant_repair_receipt_id=receipt_id,
            prior_batch_receipt_id=str(
                verified_batch.get("batch_receipt_id") or ""
            ),
            prior_config_bytes=base_config,
            prior_operator_bytes=expected_operator,
            prior_validator_bytes=base_validator,
        )
    return {
        "receipt": payload,
        "blocked_retry_batch": verified_batch,
        "sealed_source_head": sealed_head,
        "sealed_source_tree": sealed_tree,
        "artifact_commit": artifact_commit,
        "stale_worktree_cleanup_transition": cleanup_transition,
    }


def _owner_restart_admission(
    board: Any,
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    """Admit the exact bootstrap or one receipt-bound descendant repair."""

    current_head, current_tree = _assert_clean_current_tree(config)
    bootstrap = _json_object(paths["bootstrap_receipt"])
    if bootstrap.get("schema") != BOOTSTRAP_SCHEMA:
        raise OperatorError("owner restart bootstrap schema is not admitted")
    bootstrap_receipt_id = str(bootstrap.get("bootstrap_receipt_id") or "")
    bootstrap_body = dict(bootstrap)
    bootstrap_body.pop("bootstrap_receipt_id", None)
    if (
        re.fullmatch(r"sha256:[0-9a-f]{64}", bootstrap_receipt_id) is None
        or _identity(bootstrap_body) != bootstrap_receipt_id
    ):
        raise OperatorError("owner restart bootstrap receipt identity is invalid")
    bootstrap_head = str(bootstrap.get("source_head") or "")
    bootstrap_tree = str(bootstrap.get("repository_tree_id") or "")
    if _git_commit_tree(bootstrap_head, field="bootstrap source_head") != bootstrap_tree:
        raise OperatorError("bootstrap source tree does not match its commit")
    _git_is_ancestor(
        bootstrap_head,
        current_head,
        field="bootstrap-to-current source ancestry",
    )

    plan_root_cid = str(bootstrap.get("plan_root_cid") or "")
    database_receipt = bootstrap.get("database_task_source_receipt")
    if (
        not isinstance(database_receipt, Mapping)
        or database_receipt.get("schema") != DATABASE_TASK_SOURCE_SCHEMA
        or database_receipt.get("repository_tree_id") != bootstrap_tree
        or database_receipt.get("plan_root_cid") != plan_root_cid
    ):
        raise OperatorError("bootstrap database authority roots are inconsistent")
    task_cids_raw = database_receipt.get("task_cids")
    if not isinstance(task_cids_raw, list):
        raise OperatorError("bootstrap database task identities are absent")
    if any(not isinstance(item, str) or not item for item in task_cids_raw):
        raise OperatorError("bootstrap database task identities are invalid")
    task_cids = tuple(task_cids_raw)
    database_task_count = _exact_int(
        database_receipt.get("task_count"),
        field="bootstrap database task_count",
        minimum=1,
    )
    database_goal_count = _exact_int(
        database_receipt.get("goal_count"),
        field="bootstrap database goal_count",
        minimum=1,
    )
    database_plan_count = _exact_int(
        database_receipt.get("plan_count"),
        field="bootstrap database plan_count",
        minimum=1,
    )
    if (
        len(set(task_cids)) != len(task_cids)
        or database_task_count != len(task_cids)
    ):
        raise OperatorError("bootstrap database task identities are invalid")

    source_identities = bootstrap.get("source_identities")
    source_paths = _restart_source_paths(board)
    if (
        not isinstance(source_identities, Mapping)
        or set(source_identities) != set(source_paths)
    ):
        raise OperatorError("bootstrap source identity key set is not exact")
    bootstrap_sources: dict[str, bytes] = {}
    current_sources: dict[str, bytes] = {}
    current_source_identities: dict[str, str] = {}
    for name, path in source_paths.items():
        expected = str(source_identities.get(name) or "")
        bootstrap_bytes = _git_blob_at(
            head=bootstrap_head,
            path=path,
            field=f"bootstrap {name}",
        )
        if (
            re.fullmatch(r"sha256:[0-9a-f]{64}", expected) is None
            or _identity(bootstrap_bytes) != expected
        ):
            raise OperatorError(f"bootstrap {name} bytes differ from their seal")
        current_bytes = _tracked_bytes(path, head=current_head)
        if name in _RESTART_IMMUTABLE_SOURCE_NAMES and _identity(current_bytes) != expected:
            raise OperatorError(f"current {name} bytes differ from bootstrap")
        bootstrap_sources[name] = bootstrap_bytes
        current_sources[name] = current_bytes
        current_source_identities[name] = _identity(current_bytes)

    bootstrap_config = _json_mapping_bytes(
        bootstrap_sources["config"],
        field="bootstrap config",
    )
    current_config = _json_mapping_bytes(
        current_sources["config"],
        field="current config",
    )
    if _canonical_bytes(current_config) != _canonical_bytes(config):
        raise OperatorError("loaded config differs from tracked current config")
    if _canonical_bytes(
        _restart_static_config(bootstrap_config, label="bootstrap")
    ) != _canonical_bytes(_restart_static_config(current_config, label="current")):
        raise OperatorError(
            "current config changes fields outside the admitted accelerator/datasets "
            "bindings and retry policy"
        )
    bootstrap_attempt_limit = _exact_int(
        bootstrap_config.get("max_task_attempts"),
        field="bootstrap max_task_attempts",
        minimum=1,
    )
    current_attempt_limit = _exact_int(
        current_config.get("max_task_attempts"),
        field="current max_task_attempts",
        minimum=1,
    )
    current_forest = _source_forest(current_config, head=current_head)
    forest_transition = _verified_restart_forest_transition(
        bootstrap.get("source_forest"),
        current_forest,
        bootstrap_head=bootstrap_head,
        current_head=current_head,
    )
    exact_bootstrap = (
        current_head == bootstrap_head
        and current_tree == bootstrap_tree
        and current_attempt_limit == bootstrap_attempt_limit
        and all(
            current_source_identities[name] == str(source_identities[name])
            for name in source_paths
        )
    )
    repair: dict[str, Any] = {}
    descendant_repair: dict[str, Any] = {}
    admission_mode = "exact_bootstrap" if exact_bootstrap else "verified_handoff_repair"
    if not exact_bootstrap:
        if current_attempt_limit == HANDOFF_REPAIR_MAX_TASK_ATTEMPTS:
            current_source_binding = current_config.get("source_binding")
            if not isinstance(current_source_binding, Mapping):
                raise OperatorError("current source_binding is absent")
            repair = _verified_handoff_repair(
                bootstrap_receipt_id=bootstrap_receipt_id,
                plan_root_cid=plan_root_cid,
                bootstrap_tree=bootstrap_tree,
                database_task_count=database_task_count,
                bootstrap_attempt_limit=bootstrap_attempt_limit,
                current_attempt_limit=current_attempt_limit,
                current_source_identities=current_source_identities,
                forest_transition=forest_transition,
                current_source_binding=current_source_binding,
                current_head=current_head,
            )
        elif current_attempt_limit == 3:
            historical_head = CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_HEAD
            if (
                _git_commit_tree(
                    historical_head,
                    field="blocked-retry historical source",
                )
                != CURRENT_HEAD_BLOCKED_RETRY_HISTORICAL_TREE
            ):
                raise OperatorError("blocked-retry historical tree changed")
            historical_sources = {
                name: _git_blob_at(
                    head=historical_head,
                    path=path,
                    field=f"blocked-retry historical {name}",
                )
                for name, path in source_paths.items()
            }
            historical_config = _json_mapping_bytes(
                historical_sources["config"],
                field="blocked-retry historical config",
            )
            historical_binding = historical_config.get("source_binding")
            if (
                historical_config.get("max_task_attempts")
                != HANDOFF_REPAIR_MAX_TASK_ATTEMPTS
                or not isinstance(historical_binding, Mapping)
            ):
                raise OperatorError("blocked-retry historical config changed")
            historical_forest = _source_forest_at_commit(
                historical_config,
                head=historical_head,
            )
            historical_transition = _verified_restart_forest_transition(
                bootstrap.get("source_forest"),
                historical_forest,
                bootstrap_head=bootstrap_head,
                current_head=historical_head,
            )
            historical_identities = {
                name: _identity(value)
                for name, value in historical_sources.items()
            }
            repair = _verified_handoff_repair(
                bootstrap_receipt_id=bootstrap_receipt_id,
                plan_root_cid=plan_root_cid,
                bootstrap_tree=bootstrap_tree,
                database_task_count=database_task_count,
                bootstrap_attempt_limit=bootstrap_attempt_limit,
                current_attempt_limit=HANDOFF_REPAIR_MAX_TASK_ATTEMPTS,
                current_source_identities=historical_identities,
                forest_transition=historical_transition,
                current_source_binding=historical_binding,
                current_head=current_head,
            )
            descendant_repair = (
                _verified_current_head_blocked_retry_descendant_repair(
                    board=board,
                    current_head=current_head,
                    current_tree=current_tree,
                    current_config=current_config,
                    current_source_identities=current_source_identities,
                    current_attempt_limit=current_attempt_limit,
                    historical_repair=repair,
                )
            )
            admission_mode = "verified_current_head_blocked_retry_batch"
        else:
            raise OperatorError("owner restart retry policy is not admitted")
    cleanup_transition = descendant_repair.get(
        "stale_worktree_cleanup_transition"
    )
    cleanup_transition = (
        cleanup_transition
        if isinstance(cleanup_transition, Mapping)
        else {}
    )
    cleanup_transition_receipt = cleanup_transition.get("receipt")
    cleanup_transition_receipt = (
        cleanup_transition_receipt
        if isinstance(cleanup_transition_receipt, Mapping)
        else {}
    )
    validation_path_transition = cleanup_transition.get(
        "validation_path_compatibility_transition"
    )
    validation_path_transition = (
        validation_path_transition
        if isinstance(validation_path_transition, Mapping)
        else {}
    )
    validation_path_transition_receipt = validation_path_transition.get(
        "receipt"
    )
    validation_path_transition_receipt = (
        validation_path_transition_receipt
        if isinstance(validation_path_transition_receipt, Mapping)
        else {}
    )
    database_watchdog_activity_transition = validation_path_transition.get(
        "database_watchdog_activity_transition"
    )
    database_watchdog_activity_transition = (
        database_watchdog_activity_transition
        if isinstance(database_watchdog_activity_transition, Mapping)
        else {}
    )
    database_watchdog_activity_transition_receipt = (
        database_watchdog_activity_transition.get("receipt")
    )
    database_watchdog_activity_transition_receipt = (
        database_watchdog_activity_transition_receipt
        if isinstance(database_watchdog_activity_transition_receipt, Mapping)
        else {}
    )
    admission: dict[str, Any] = {
        "schema": OWNER_RESTART_ADMISSION_SCHEMA,
        "mode": admission_mode,
        "bootstrap_receipt_id": bootstrap_receipt_id,
        "bootstrap_source_head": bootstrap_head,
        "bootstrap_source_tree": bootstrap_tree,
        "current_source_head": current_head,
        "current_source_tree": current_tree,
        "plan_root_cid": plan_root_cid,
        "max_task_attempts_before": bootstrap_attempt_limit,
        "max_task_attempts_after": current_attempt_limit,
        "source_identities": current_source_identities,
        "forest_transition": forest_transition,
        "handoff_repair_receipt_id": str(repair.get("receipt_id") or ""),
        "handoff_repair": repair,
        "current_head_descendant_repair_receipt_id": str(
            descendant_repair.get("receipt", {}).get("receipt_id")
            if isinstance(descendant_repair.get("receipt"), Mapping)
            else ""
        ),
        "current_head_blocked_retry_batch_receipt_id": str(
            descendant_repair.get("blocked_retry_batch", {}).get(
                "batch_receipt_id"
            )
            if isinstance(
                descendant_repair.get("blocked_retry_batch"), Mapping
            )
            else ""
        ),
        "stale_worktree_cleanup_transition_receipt_id": str(
            cleanup_transition_receipt.get("receipt_id") or ""
        ),
        "validation_path_compatibility_transition_receipt_id": str(
            validation_path_transition_receipt.get("receipt_id") or ""
        ),
        "database_watchdog_activity_transition_receipt_id": str(
            database_watchdog_activity_transition_receipt.get("receipt_id")
            or ""
        ),
        "current_head_descendant_repair": descendant_repair,
        "database_authority": {
            "receipt_identity": _identity(database_receipt),
            "schema": DATABASE_TASK_SOURCE_SCHEMA,
            "repository_tree_id": bootstrap_tree,
            "source_head": bootstrap_head,
            "plan_root_cid": plan_root_cid,
            "projection_cid": str(database_receipt.get("projection_cid") or ""),
            "task_cids": sorted(task_cids),
            "task_count": len(task_cids),
            "goal_count": database_goal_count,
            "plan_count": database_plan_count,
        },
    }
    admission["admission_id"] = _identity(admission)
    return admission


def _source_forest(config: Mapping[str, Any], *, head: str) -> dict[str, Any]:
    """Verify the exact clean four-repository PCSM source forest."""

    binding = config.get("source_binding")
    if not isinstance(binding, Mapping):
        raise OperatorError("source_binding must be an object")
    if binding.get("require_origin_main_as_ancestor") is not True:
        raise OperatorError("source forest requires origin/main ancestry")
    nested: list[dict[str, str]] = []
    configured_repositories = (
        (
            "ipfs_accelerate",
            ("ipfs_accelerate_submodule_path",),
            ("ipfs_accelerate_planning_revision",),
            ("ipfs_accelerate_planning_tree",),
            ("ipfs_accelerate_origin_main_revision",),
        ),
        (
            "ipfs_datasets",
            ("ipfs_datasets_submodule_path", "datasets_submodule_path"),
            ("ipfs_datasets_planning_revision", "datasets_planning_revision"),
            ("ipfs_datasets_planning_tree", "datasets_planning_tree"),
            ("ipfs_datasets_origin_main_revision",),
        ),
        (
            "ipfs_kit",
            ("ipfs_kit_submodule_path", "kit_submodule_path"),
            ("ipfs_kit_planning_revision", "kit_planning_revision"),
            ("ipfs_kit_planning_tree", "kit_planning_tree"),
            ("ipfs_kit_origin_main_revision",),
        ),
        (
            "mcp_plus_plus",
            ("mcp_plus_plus_submodule_path",),
            ("mcp_plus_plus_planning_revision",),
            ("mcp_plus_plus_planning_tree",),
            ("mcp_plus_plus_origin_main_revision",),
        ),
    )

    def binding_value(fields: Sequence[str], *, field: str) -> Any:
        present = [binding.get(name) for name in fields if binding.get(name) not in (None, "")]
        if not present:
            return None
        if any(value != present[0] for value in present[1:]):
            raise OperatorError(f"{field} has conflicting canonical and legacy values")
        return present[0]

    for (
        prefix,
        path_fields,
        revision_fields,
        tree_fields,
        origin_fields,
    ) in configured_repositories:
        raw_path = binding_value(
            path_fields,
            field=f"source_binding.{prefix}_submodule_path",
        )
        raw_revision = binding_value(
            revision_fields,
            field=f"source_binding.{prefix}_planning_revision",
        )
        raw_tree = binding_value(
            tree_fields,
            field=f"source_binding.{prefix}_planning_tree",
        )
        raw_origin = binding_value(
            origin_fields,
            field=f"source_binding.{prefix}_origin_main_revision",
        )
        if any(value in (None, "") for value in (raw_path, raw_revision, raw_tree, raw_origin)):
            raise OperatorError(f"{prefix} source binding is incomplete")
        nested_path = _safe_path(
            ROOT,
            raw_path,
            field=f"source_binding.{prefix}_submodule_path",
        )
        if not nested_path.is_dir():
            raise OperatorError(f"{prefix} submodule is not initialized")
        nested_status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        if nested_status.returncode != 0 or nested_status.stdout.strip():
            raise OperatorError(f"{prefix} nested worktree is not clean")
        nested_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        nested_tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        revision = nested_head.stdout.strip()
        tree = nested_tree.stdout.strip()
        if (
            nested_head.returncode != 0
            or nested_tree.returncode != 0
            or revision != str(raw_revision)
            or tree != str(raw_tree)
        ):
            raise OperatorError(f"{prefix} nested revision differs from its seal")
        origin_main = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        if (
            origin_main.returncode != 0
            or origin_main.stdout.strip() != str(raw_origin)
        ):
            raise OperatorError(
                f"{prefix} configured origin/main differs from its fetched ref"
            )
        _git_is_ancestor(
            raw_origin,
            revision,
            field=f"{prefix} origin/main-to-planning lineage",
            repository=nested_path,
        )
        relative = nested_path.relative_to(ROOT).as_posix()
        tree_row = str(_git("ls-tree", head, "--", relative)).strip().split()
        if (
            len(tree_row) < 3
            or tree_row[0] != "160000"
            or tree_row[1] != "commit"
            or tree_row[2] != revision
        ):
            raise OperatorError(f"{prefix} gitlink differs from its nested HEAD")
        nested.append(
            {
                "repository": prefix,
                "path": relative,
                "head": revision,
                "tree": tree,
                "access": "supervisor_scoped_cross_repository_worktree",
            }
        )
    if {item["repository"] for item in nested} != _RESTART_SOURCE_FOREST_REPOSITORIES:
        raise OperatorError("source forest does not contain the exact four repositories")
    result: dict[str, Any] = {
        "source_head": head,
        "nested_repositories": nested,
        "cross_repository_writes": True,
    }
    result["source_forest_root"] = _identity(result)
    return result


def _load_config(config_path: Path) -> tuple[Any, dict[str, Any]]:
    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        load_configured_board,
    )

    board = load_configured_board(config_path, repo_root=ROOT)
    payload = dict(board.payload)
    if board.task_prefix.removeprefix("## ") != "PCSM-":
        raise OperatorError("PCSM operator requires task_prefix='PCSM-'")
    if board.board_namespace != "proof-carrying-semantic-minification-v1":
        raise OperatorError("scheduler board_namespace is not the PCSM v1 namespace")
    program = board.resolved_database_program()
    if program.authority_mode != "quack" or program.task_source_kind != "duckdb":
        raise OperatorError("PCSM requires DuckDB task authority served through Quack")
    if program.failover_policy != "fail_closed":
        raise OperatorError("PCSM Quack authority must fail closed")
    if QUACK_ENDPOINT_RE.fullmatch(program.quack_endpoint) is None:
        raise OperatorError("PCSM Quack endpoint must be a bounded loopback URI")
    return board, payload


def _control_plane_store_id(program: Any) -> str:
    """Return the compact transactional identity, not the database pathname."""

    value = str(program.store_generation or "").strip()
    if not value or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}", value) is None:
        raise OperatorError("database program has no compact control-plane store identity")
    return value


def _run_board_validator(board: Any) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(board.path(board.validator_path)), "--check-all"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                item
                for item in (
                    str(ACCEL_ROOT),
                    str(ROOT),
                    os.environ.get("PYTHONPATH", ""),
                )
                if item
            ),
        },
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise OperatorError("PCSM board validator did not return JSON") from exc
    if (
        completed.returncode != 0
        or not isinstance(payload, dict)
        or payload.get("valid") is not True
    ):
        raise OperatorError("PCSM board validator rejected the committed handoff")
    return payload


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _goal_blocks(text: str) -> list[tuple[str, str, dict[str, str]]]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.todo_vector_index import (
        normalize_metadata_key,
    )

    matches = list(GOAL_RE.finditer(text))
    result: list[tuple[str, str, dict[str, str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        fields: dict[str, str] = {}
        for line in text[match.end() : end].splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ":" not in stripped:
                continue
            key, value = stripped[2:].split(":", 1)
            normalized = normalize_metadata_key(key)
            if normalized in fields:
                raise OperatorError(
                    f"{match.group(1)} contains duplicate metadata field {normalized}"
                )
            fields[normalized] = value.strip()
        result.append((match.group(1), match.group(2).strip(), fields))
    return result


def _population(board: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.todo_vector_index import (
        parse_todo_blocks,
    )
    from ipfs_accelerate_py.agent_supervisor.validation.validation_commands import (
        split_validation_commands,
    )

    head, tree = _assert_clean_current_tree(config)
    source_forest = _source_forest(config, head=head)
    sources = {
        "config": _tracked_bytes(board.config_path, head=head),
        "taskboard": _tracked_bytes(board.path(board.taskboard_path), head=head),
        "objectives": _tracked_bytes(board.path(board.objectives_path), head=head),
        "plan": _tracked_bytes(board.path(board.plan_path), head=head),
        "validator": _tracked_bytes(board.path(board.validator_path), head=head),
        "generator": _tracked_bytes(
            ROOT / "scripts/generate_proof_carrying_semantic_minification_board.py",
            head=head,
        ),
        "operator": _tracked_bytes(Path(__file__).resolve(), head=head),
    }
    plan_root = content_identity(
        {
            "schema": "pcsm-plan-root@1",
            "source_head": head,
            "repository_tree_id": tree,
            "sources": {
                name: _identity(value) for name, value in sorted(sources.items())
            },
        }
    )

    objective_text = sources["objectives"].decode("utf-8")
    parsed_goals = _goal_blocks(objective_text)
    if not parsed_goals or parsed_goals[0][0] != "PCSM-G000":
        raise OperatorError("objectives must begin with root PCSM-G000")
    if len({item[0] for item in parsed_goals}) != len(parsed_goals):
        raise OperatorError("objectives contain duplicate goal IDs")
    goal_cids = {
        goal_id: content_identity(
            {
                "goal_id": goal_id,
                "title": title,
                "metadata": fields,
                "plan_root_cid": plan_root,
            }
        )
        for goal_id, title, fields in parsed_goals
    }
    goals: list[dict[str, Any]] = []
    goal_edges: list[dict[str, Any]] = []
    observed_goals: set[str] = set()
    for ordinal, (goal_id, title, fields) in enumerate(parsed_goals, start=1):
        parent = str(fields.get("parent") or "").strip()
        if parent and parent not in observed_goals:
            raise OperatorError(f"{goal_id} parent must precede it: {parent}")
        dependencies = _split_csv(fields.get("depends_on"))
        unknown = [item for item in dependencies if item not in goal_cids]
        if unknown:
            raise OperatorError(f"{goal_id} has unknown goal dependencies: {unknown}")
        goal = {
            "goal_cid": goal_cids[goal_id],
            "goal_id": goal_id,
            "goal_alias": goal_id,
            "title": title,
            "ordinal": ordinal,
            "status": str(fields.get("status") or "open").lower(),
            "objective_id": "objective:pcsm-root" if goal_id == "PCSM-G000" else "",
            "objective_alias": "PCSM-G000",
            "priority": str(fields.get("priority") or "P0"),
            "body": dict(fields),
        }
        if parent:
            goal["parent_goal_cid"] = goal_cids[parent]
            goal_edges.append(
                {
                    "parent_goal_cid": goal_cids[parent],
                    "child_goal_cid": goal_cids[goal_id],
                    "edge_kind": "goal_parent",
                }
            )
        for dependency in dependencies:
            goal_edges.append(
                {
                    "parent_goal_cid": goal_cids[dependency],
                    "child_goal_cid": goal_cids[goal_id],
                    "edge_kind": "goal_dependency",
                }
            )
        goals.append(goal)
        observed_goals.add(goal_id)

    task_text = sources["taskboard"].decode("utf-8")
    parsed_tasks = parse_todo_blocks(task_text, task_header_prefix="## PCSM-")
    if not parsed_tasks:
        raise OperatorError("task board contains no PCSM tasks")
    task_ids = [item[0] for item in parsed_tasks]
    if len(task_ids) != len(set(task_ids)):
        raise OperatorError("task board contains duplicate PCSM task IDs")
    task_cids = {
        task_id: content_identity(
            {
                "task_id": task_id,
                "title": title,
                "source_line": source_line,
                "metadata": fields,
                "plan_root_cid": plan_root,
                "repository_tree_id": tree,
            }
        )
        for task_id, title, source_line, fields in parsed_tasks
    }
    tasks: list[dict[str, Any]] = []
    observed_tasks: set[str] = set()
    for ordinal, (task_id, title, source_line, fields) in enumerate(
        parsed_tasks, start=1
    ):
        dependencies = _split_csv(fields.get("depends_on"))
        unknown = [item for item in dependencies if item not in task_cids]
        if unknown:
            raise OperatorError(f"{task_id} has unknown dependencies: {unknown}")
        future = [item for item in dependencies if item not in observed_tasks]
        if future:
            raise OperatorError(
                f"{task_id} dependencies must precede it for atomic ingestion: {future}"
            )
        goal_id = str(
            fields.get("subgoal_id")
            or fields.get("goal_id")
            or fields.get("goal")
            or "PCSM-G000"
        ).strip()
        if goal_id not in goal_cids:
            raise OperatorError(f"{task_id} refers to unknown goal {goal_id}")
        output_paths = _split_csv(fields.get("outputs") or fields.get("predicted_files"))
        task = dict(fields)
        if fields.get("owning_repository") != "ipfs_accelerate_py":
            raise OperatorError(
                f"{task_id} does not use the sealed Portal root execution authority"
            )
        task.update(
            {
                "task_cid": task_cids[task_id],
                "task_id": task_id,
                "task_alias": task_id,
                "title": title,
                "source_line": source_line,
                "goal_cid": goal_cids[goal_id],
                "goal_id": goal_id,
                "plan_cid": plan_root,
                "objective_id": "objective:pcsm-root",
                "ordinal": ordinal,
                "status": str(fields.get("status") or "todo").lower(),
                "priority": str(fields.get("priority") or "P1"),
                "dependencies": [task_cids[item] for item in dependencies],
                "depends_on": [task_cids[item] for item in dependencies],
                "outputs": [
                    {
                        "path": path,
                        "effect_id": content_identity(
                            {"task_cid": task_cids[task_id], "path": path}
                        ),
                    }
                    for path in output_paths
                ],
                "acceptance": [
                    str(fields.get("acceptance") or fields.get("acceptance_subset") or "")
                ],
                "validations": list(
                    split_validation_commands(str(fields.get("validation") or ""))
                ),
                "accepted_plan_root_cid": plan_root,
                "base_revision": head,
                "base_repository_tree_id": tree,
                # PCSM task paths and receipts are outer-root-relative and may
                # span several configured submodules. DatabasePortalBridge's
                # owner is the execution worktree scope; semantic authority is
                # governed independently by the sealed campaign plan.
                "owning_repository": "ipfs_accelerate_py",
            }
        )
        tasks.append(task)
        observed_tasks.add(task_id)

    projection = config.get("initial_projection")
    projection = projection if isinstance(projection, Mapping) else {}
    expected_tasks = projection.get("task_count")
    expected_goals = projection.get("goal_count")
    expected_dependencies = projection.get("task_dependency_count")
    if expected_tasks is not None and int(expected_tasks) != len(tasks):
        raise OperatorError("task count differs from configured initial projection")
    if expected_goals is not None and int(expected_goals) != len(goals):
        raise OperatorError("goal count differs from configured initial projection")
    dependency_count = sum(
        len(_split_csv(item[3].get("depends_on"))) for item in parsed_tasks
    )
    if expected_dependencies is not None and int(expected_dependencies) != dependency_count:
        raise OperatorError(
            "task dependency count differs from configured initial projection"
        )
    return {
        "schema": POPULATION_SCHEMA,
        "repository_tree_id": tree,
        "source_head": head,
        "plan_root_cid": plan_root,
        "source_identities": {
            name: _identity(value) for name, value in sorted(sources.items())
        },
        "source_forest": source_forest,
        "objectives": goals,
        "goal_edges": goal_edges,
        "plans": [
            {
                "plan_cid": plan_root,
                "plan_alias": "PCSM-PLAN-V1",
                "goal_cid": goal_cids["PCSM-G000"],
                "status": "active",
                "source_head": head,
                "repository_tree_id": tree,
            }
        ],
        "tasks": tasks,
        "task_cids_by_alias": task_cids,
        "goal_cids_by_alias": goal_cids,
    }


def _runtime_paths(board: Any) -> dict[str, Path]:
    program = board.resolved_database_program()
    database = _safe_path(ROOT, program.store_id, field="database_program.store_id")
    runtime = board.path(board.runtime_paths["root"])
    try:
        database.relative_to(runtime)
    except ValueError as exc:
        raise OperatorError("DuckDB authority store must be below runtime_paths.root") from exc
    raw_runtime = board.payload.get("runtime_paths")
    raw_runtime = raw_runtime if isinstance(raw_runtime, Mapping) else {}
    evidence = _safe_path(
        ROOT,
        raw_runtime.get("evidence") or runtime.relative_to(ROOT) / "evidence",
        field="runtime_paths.evidence",
    )
    owner = _safe_path(
        ROOT,
        raw_runtime.get("quack_owner") or runtime.relative_to(ROOT) / "quack-owner",
        field="runtime_paths.quack_owner",
    )
    raw_ducklake = board.payload.get("ducklake_projection_program")
    raw_ducklake = raw_ducklake if isinstance(raw_ducklake, Mapping) else {}
    ducklake_catalog = _safe_path(
        ROOT,
        raw_ducklake.get("catalog_path")
        or runtime.relative_to(ROOT) / "ducklake" / "catalog.duckdb",
        field="ducklake_projection_program.catalog_path",
    )
    ducklake_data = _safe_path(
        ROOT,
        raw_ducklake.get("data_path")
        or runtime.relative_to(ROOT) / "ducklake" / "data",
        field="ducklake_projection_program.data_path",
    )
    for label, path in (
        ("evidence", evidence),
        ("quack_owner", owner),
        ("ducklake_catalog", ducklake_catalog),
        ("ducklake_data", ducklake_data),
    ):
        try:
            path.relative_to(runtime)
        except ValueError as exc:
            raise OperatorError(f"{label} must be below runtime_paths.root") from exc
    return {
        "runtime": runtime,
        "database": database,
        "owner": owner,
        "bootstrap_receipt": evidence / "bootstrap" / BOOTSTRAP_RECEIPT_NAME,
        "ducklake_receipt": evidence / "bootstrap" / DUCKLAKE_RECEIPT_NAME,
        "ducklake_catalog": ducklake_catalog,
        "ducklake_data": ducklake_data,
    }


def _ducklake_projection(
    *,
    paths: Mapping[str, Path],
    population: Mapping[str, Any],
    control_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Append one non-authoritative bootstrap observation to DuckLake."""

    projection: dict[str, Any] = {
        "schema": DUCKLAKE_SCHEMA,
        "authoritative": False,
        "scheduler_gate": False,
        "completion_gate": False,
        "status": "unavailable",
        "reason_code": "ducklake_projection_unavailable",
        "source_head": str(population["source_head"]),
        "repository_tree_id": str(population["repository_tree_id"]),
        "plan_root_cid": str(population["plan_root_cid"]),
    }
    try:
        import duckdb

        catalog = paths["ducklake_catalog"]
        data_path = paths["ducklake_data"]
        catalog.parent.mkdir(parents=True, exist_ok=True)
        data_path.mkdir(parents=True, exist_ok=True)
        memory = duckdb.connect(":memory:")
        try:
            memory.execute("LOAD ducklake")
            catalog_sql = str(catalog).replace("'", "''")
            data_sql = str(data_path).replace("'", "''")
            memory.execute(
                f"ATTACH 'ducklake:{catalog_sql}' AS pcsm_history "
                f"(DATA_PATH '{data_sql}')"
            )
            memory.execute(
                """
                CREATE TABLE IF NOT EXISTS pcsm_history.bootstrap_history (
                    event_id VARCHAR,
                    observed_at_epoch DOUBLE,
                    source_head VARCHAR,
                    repository_tree_id VARCHAR,
                    plan_root_cid VARCHAR,
                    projection_cid VARCHAR,
                    task_count BIGINT,
                    goal_count BIGINT,
                    body_json VARCHAR
                )
                """
            )
            event_id = _identity(
                {
                    "source_head": population["source_head"],
                    "plan_root_cid": population["plan_root_cid"],
                    "projection_cid": control_receipt.get("projection_cid"),
                }
            )
            existing = memory.execute(
                "SELECT COUNT(*) FROM pcsm_history.bootstrap_history WHERE event_id = ?",
                [event_id],
            ).fetchone()
            if existing is None or int(existing[0]) == 0:
                memory.execute(
                    """
                    INSERT INTO pcsm_history.bootstrap_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        event_id,
                        time.time(),
                        population["source_head"],
                        population["repository_tree_id"],
                        population["plan_root_cid"],
                        str(control_receipt.get("projection_cid") or ""),
                        int(control_receipt.get("task_count") or 0),
                        int(control_receipt.get("goal_count") or 0),
                        json.dumps(
                            {
                                "authority": "DuckDB/DatabaseTaskSource@1",
                                "transport": "QuackStateServer@1",
                                "projection": "DuckLake/non-authoritative",
                            },
                            sort_keys=True,
                        ),
                    ],
                )
            row_count = int(
                memory.execute(
                    "SELECT COUNT(*) FROM pcsm_history.bootstrap_history"
                ).fetchone()[0]
            )
            memory.execute("DETACH pcsm_history")
        finally:
            memory.close()
        projection.update(
            {
                "status": "available",
                "reason_code": "",
                "event_id": event_id,
                "row_count": row_count,
                "catalog_path": str(catalog.relative_to(ROOT)),
                "data_path": str(data_path.relative_to(ROOT)),
            }
        )
    except Exception as exc:
        # This projection is optional by contract. Preserve a typed absence and
        # never use it to reject a valid DuckDB materialization.
        projection["error_class"] = type(exc).__name__
    projection["projection_receipt_id"] = _identity(projection)
    _atomic_json(paths["ducklake_receipt"], projection)
    return projection


def materialize(config_path: Path) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    board, config = _load_config(config_path)
    board_validation = _run_board_validator(board)
    paths = _runtime_paths(board)
    population = _population(board, config)
    receipt_path = paths["bootstrap_receipt"]
    if paths["database"].exists() or receipt_path.exists():
        if not paths["database"].is_file() or not receipt_path.is_file():
            raise OperatorError("partial bootstrap state exists; operator review required")
        prior = _json_object(receipt_path)
        exact = all(
            prior.get(key) == population.get(key)
            for key in ("source_head", "repository_tree_id", "plan_root_cid")
        )
        if not exact:
            raise OperatorError(
                "existing DuckDB authority is bound to a different source tree or plan"
            )
        with DatabaseTaskSource(
            paths["database"],
            owner_id="pcsm-bootstrap:verify-existing",
            install_schema=False,
            repository_tree_id=str(population["repository_tree_id"]),
            plan_root_cid=str(population["plan_root_cid"]),
        ) as source:
            snapshot = source.snapshot().to_dict()
        if int(snapshot["task_count"]) != len(population["tasks"]):
            raise OperatorError("existing DuckDB task population differs from sealed board")
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "materialize",
            "idempotent_replay": True,
            "materialized": True,
            "bootstrap_receipt": prior,
            "snapshot": snapshot,
            "board_validation": board_validation,
        }

    _ensure_private_runtime_directory(paths["runtime"])
    with DatabaseTaskSource(
        paths["database"],
        owner_id="pcsm-bootstrap:single-writer",
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        control_receipt = dict(source.materialize(population))
        snapshot = source.snapshot().to_dict()
        ready_ids = [item.task_alias for item in source.ready_tasks(limit=100).tasks]
    if int(snapshot["task_count"]) != len(population["tasks"]):
        raise OperatorError("DuckDB materialization task count is not exact")
    if int(snapshot["goal_count"]) != len(population["objectives"]):
        raise OperatorError("DuckDB materialization goal count is not exact")
    projection = config.get("initial_projection")
    projection = projection if isinstance(projection, Mapping) else {}
    expected_ready = [str(item) for item in projection.get("ready_task_ids", ())]
    if ready_ids != expected_ready:
        raise OperatorError(
            "initial DuckDB readiness frontier differs from the sealed projection"
        )
    ducklake = _ducklake_projection(
        paths=paths,
        population=population,
        control_receipt=control_receipt,
    )
    receipt = {
        "schema": BOOTSTRAP_SCHEMA,
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "plan_root_cid": population["plan_root_cid"],
        "source_identities": population["source_identities"],
        "source_forest": population["source_forest"],
        "database_task_source_receipt": control_receipt,
        "projection_cid": snapshot["projection_cid"],
        "task_count": snapshot["task_count"],
        "goal_count": snapshot["goal_count"],
        "dependency_count": snapshot["dependency_count"],
        "initial_ready_task_ids": ready_ids,
        "board_validation": board_validation,
        "authority": {
            "semantic_state": "DuckDB/DatabaseTaskSource@1",
            "state_owner_transport": "QuackStateServer@1",
            "ducklake": "optional_non_authoritative_history_projection",
        },
        "ducklake_projection": ducklake,
    }
    receipt["bootstrap_receipt_id"] = _identity(receipt)
    _atomic_json(receipt_path, receipt)
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "materialize",
        "idempotent_replay": False,
        "materialized": True,
        "bootstrap_receipt": receipt,
        "snapshot": snapshot,
    }


def _verify_control_plane(path: Path) -> Any:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_migrations import (
        MigrationRunReport,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_schema import (
        CONTROL_PLANE_MIGRATION_VERSION,
        load_control_plane_catalog,
        verify_installed_schema,
    )

    # PCSM uses the canonical full control-plane schema revision ``1``.  The
    # smaller datasets-authoritative operational profile is deliberately not
    # selected: the generic multi-supervisor rejects that profile for live
    # Quack operation, and the PCSM board needs the full proof/evidence tables.
    verification = verify_installed_schema(path)
    fingerprint = str(verification.get("schema_fingerprint") or "")
    if not fingerprint:
        raise OperatorError("existing full control plane has no schema fingerprint")
    return MigrationRunReport(
        from_version=CONTROL_PLANE_MIGRATION_VERSION,
        to_version=CONTROL_PLANE_MIGRATION_VERSION,
        receipts=(),
        schema_fingerprint=fingerprint,
        catalog_fingerprint=load_control_plane_catalog().fingerprint(),
        changed=False,
    )


def _normalized_owner_dml(sql: str) -> str:
    normalized = " ".join(str(sql or "").strip().upper().split())
    if not normalized.startswith(OWNER_DML_PREFIXES):
        raise OperatorError("mutation inbox accepts only the closed owner-DML vocabulary")
    if ";" in normalized.rstrip(";"):
        raise OperatorError("mutation inbox accepts exactly one SQL statement")
    return normalized


def _process_mutations(server: Any, mutation_dir: Path) -> None:
    mutation_dir.mkdir(parents=True, exist_ok=True)
    for request in sorted(mutation_dir.glob("*.request.json")):
        done = request.with_name(request.name.replace(".request.json", ".done.json"))
        try:
            try:
                payload = json.loads(request.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # The client creates a tiny same-filesystem request. A partial
                # read is retried rather than converted into a false failure.
                continue
            if not isinstance(payload, Mapping):
                raise OperatorError("mutation request must be an object")
            sql = str(payload.get("sql") or "")
            _normalized_owner_dml(sql)
            parameters = payload.get("parameters")
            if parameters is not None and (
                isinstance(parameters, (str, bytes, bytearray))
                or not isinstance(parameters, (Mapping, Sequence))
            ):
                raise OperatorError("mutation parameters must be a mapping or sequence")
            owner_connection = getattr(server, "_connection", None)
            if owner_connection is None:
                raise OperatorError("state-owner connection is unavailable")
            result = (
                owner_connection.execute(sql)
                if parameters is None
                else owner_connection.execute(sql, parameters)
            )
            rowcount = -1
            try:
                if getattr(result, "description", None):
                    result.fetchall()
                elif hasattr(result, "rowcount"):
                    rowcount = int(result.rowcount)
            except Exception:
                pass
            _atomic_json(done, {"ok": True, "rowcount": rowcount})
        except Exception as exc:
            _atomic_json(
                done,
                {
                    "ok": False,
                    "error": f"{type(exc).__name__}: mutation rejected",
                },
            )
        try:
            request.unlink()
        except FileNotFoundError:
            pass


def _build_state_owner(board: Any, paths: Mapping[str, Path]) -> Any:
    """Build the canonical writer-owner/read-replica Quack boundary."""

    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        build_server,
    )

    program = board.resolved_database_program()
    endpoint = QUACK_ENDPOINT_RE.fullmatch(program.quack_endpoint)
    if endpoint is None:
        raise OperatorError("configured Quack endpoint is not loopback")
    host = endpoint.group(1)
    port = int(endpoint.group(2))
    if not 1 <= port <= 65535:
        raise OperatorError("configured Quack port is out of range")
    return build_server(
        database_path=paths["database"],
        state_dir=paths["owner"],
        repository_root=ROOT,
        host=host,
        port=port,
        repository_id=(
            "repository:lift_coding/proof-carrying-semantic-minification-v1"
        ),
        store_id=_control_plane_store_id(program),
        secret_handle=program.endpoint_secret_handle,
        allow_experimental=False,
        migrate=_verify_control_plane,
        allow_legacy_board_unstall=False,
    )


def state_owner(config_path: Path) -> int:
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        ServerLifecycle,
    )

    board, config = _load_config(config_path)
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise OperatorError("materialize the sealed PCSM board before starting Quack")
    restart_admission = _owner_restart_admission(board, config, paths)
    prior_owner = _owner_restart_prior_status(
        paths["owner"] / "quack-state-server.status.json"
    )
    _require_prior_owner_continuity(restart_admission, prior_owner)
    server = _build_state_owner(board, paths)
    try:
        identity = server.start()
        ready = server.ready()
        route_policy_provider = _ExecutionRoutePolicyProvider(
            server=server,
            board=board,
            restart_admission=restart_admission,
        )
        route_policy_provider.seal()
        after_head, after_tree = _assert_clean_current_tree(config)
        if (
            after_head != restart_admission["current_source_head"]
            or after_tree != restart_admission["current_source_tree"]
        ):
            raise OperatorError("owner restart source changed during admission")
        restart_receipt = _owner_restart_receipt(
            restart_admission,
            identity,
            expected_store_id=_control_plane_store_id(
                board.resolved_database_program()
            ),
            prior_owner=prior_owner,
            database_verification=route_policy_provider.database_verification,
        )
        restart_receipt_path = (
            paths["runtime"]
            / "evidence"
            / "runtime"
            / "owner-restarts"
            / (
                f"{int(identity.generation):020d}-"
                f"{restart_receipt['receipt_id'].removeprefix('sha256:')}.json"
            )
        )
        _atomic_json(restart_receipt_path, restart_receipt)
    except Exception:
        try:
            server.stop()
        except Exception:
            pass
        raise
    print(
        json.dumps(
            {
                "schema": OPERATOR_SCHEMA,
                "command": "state-owner",
                "ready": True,
                "identity": identity.to_dict(),
                "live": ready,
                "mutation_dir": str((paths["owner"] / "mutations").relative_to(ROOT)),
                "restart_receipt": str(restart_receipt_path.relative_to(ROOT)),
                "restart_receipt_id": restart_receipt["receipt_id"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    stopped = {"value": False}

    def request_stop(_signum: int, _frame: Any) -> None:
        stopped["value"] = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    mutation_dir = paths["owner"] / "mutations"
    control_path = server.stop_control_path()
    while server.lifecycle is ServerLifecycle.READY and not stopped["value"]:
        if control_path.is_file():
            break
        _process_mutations(server, mutation_dir)
        time.sleep(0.05)
    result = server.stop()
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


def _executor_client_bindings(board: Any) -> dict[str, int]:
    lanes = max(1, int(board.max_lanes))
    if lanes == 1:
        owners = ((EXECUTOR_OWNER_SESSION_BASE, 0),)
    else:
        owners = tuple(
            (
                f"{EXECUTOR_OWNER_SESSION_BASE}:shard:{index}-of-{lanes}:"
                "track:"
                + hashlib.sha256(
                    f"{board.board_namespace}-{index}".encode()
                ).hexdigest()[:12],
                index,
            )
            for index in range(lanes)
        )
    return {
        f"database-implementation-daemon:{owner}": index
        for owner, index in owners
    }


def _executor_client_ids(board: Any) -> frozenset[str]:
    return frozenset(_executor_client_bindings(board))


def _supervisor_client_bindings(board: Any) -> dict[str, int]:
    return {
        client_id.replace(
            "database-implementation-daemon:",
            "database-implementation-supervisor:",
            1,
        ): lane_index
        for client_id, lane_index in _executor_client_bindings(board).items()
    }


def _owner_restart_prior_status(path: Path) -> dict[str, Any]:
    """Admit only a stopped or provably dead prior combined owner."""

    from ipfs_accelerate_py.agent_supervisor.merge.database_worktree_registry import (
        process_birth_id,
    )
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        ProcessBirthIdentity,
    )

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {
            "state": "absent",
            "status_identity": "",
            "server_id": "",
            "database_uuid": "",
            "store_id": "",
            "schema_revision": 0,
            "schema_fingerprint": "",
            "generation": 0,
            "fence_epoch": 0,
            "process_birth_id": "",
        }
    except OSError as exc:
        raise OperatorError("prior state-owner status cannot be inspected") from exc
    if (
        not stat_module.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat_module.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise OperatorError("prior state-owner status is not a private regular file")
    payload = _json_object(path)
    if (
        payload.get("schema") != QUACK_STATE_SERVER_SCHEMA
        or payload.get("interface") != QUACK_STATE_SERVER_INTERFACE
    ):
        raise OperatorError("prior state-owner status schema is not admitted")
    lifecycle = str(payload.get("lifecycle") or "")
    liveness = _owner_liveness(payload)
    if lifecycle == "ready" and liveness in {"alive", "unknown"}:
        raise OperatorError(
            f"prior ready state owner has {liveness} process-birth liveness"
        )
    if lifecycle != "stopped" and liveness != "dead":
        raise OperatorError("prior state owner is neither stopped nor dead")
    identity = payload.get("identity")
    if (
        not isinstance(identity, Mapping)
        or identity.get("schema") != STATE_SERVER_IDENTITY_SCHEMA
        or identity.get("interface") != STATE_SERVER_IDENTITY_INTERFACE
    ):
        raise OperatorError("prior state-owner identity schema is not admitted")
    birth_payload = identity.get("process_birth")
    try:
        birth = (
            ProcessBirthIdentity.from_dict(dict(birth_payload))
            if isinstance(birth_payload, Mapping)
            else None
        )
    except Exception as exc:
        raise OperatorError("prior state-owner process birth is malformed") from exc
    claimed_birth_id = str(identity.get("process_birth_id") or "")
    if birth is None or process_birth_id(birth) != claimed_birth_id:
        raise OperatorError("prior state-owner process birth identity differs")
    schema_revision = _exact_int(
        identity.get("schema_revision"),
        field="prior state-owner schema_revision",
        minimum=1,
    )
    generation = _exact_int(
        identity.get("generation"),
        field="prior state-owner generation",
        minimum=1,
    )
    fence_epoch = _exact_int(
        identity.get("fence_epoch"),
        field="prior state-owner fence_epoch",
        minimum=1,
    )
    result = {
        "state": "stopped" if lifecycle == "stopped" else "dead",
        "lifecycle": lifecycle,
        "liveness": liveness,
        "status_identity": _identity(payload),
        "server_id": str(identity.get("server_id") or ""),
        "database_uuid": str(identity.get("database_uuid") or ""),
        "store_id": str(identity.get("store_id") or ""),
        "schema_revision": schema_revision,
        "schema_fingerprint": str(identity.get("schema_fingerprint") or ""),
        "generation": generation,
        "fence_epoch": fence_epoch,
        "process_birth_id": claimed_birth_id,
    }
    if (
        not result["server_id"]
        or not result["database_uuid"]
        or not result["store_id"]
        or re.fullmatch(r"sha256:[0-9a-f]{64}", result["schema_fingerprint"])
        is None
        or not result["process_birth_id"]
        or str(payload.get("store_id") or "") != result["store_id"]
    ):
        raise OperatorError("prior state-owner identity is incomplete")
    return result


def _require_prior_owner_continuity(
    admission: Mapping[str, Any],
    prior_owner: Mapping[str, Any],
) -> None:
    """Require durable owner continuity for every descendant-source restart."""

    mode = admission.get("mode")
    if mode == "exact_bootstrap":
        return
    if mode not in {
        "verified_handoff_repair",
        "verified_current_head_blocked_retry_batch",
    }:
        raise OperatorError("owner restart admission mode is not recognized")
    if prior_owner.get("state") not in {"stopped", "dead"}:
        raise OperatorError(
            "descendant owner restart requires a stopped or dead prior identity"
        )
    if any(
        not prior_owner.get(field)
        for field in (
            "server_id",
            "database_uuid",
            "store_id",
            "schema_fingerprint",
            "process_birth_id",
        )
    ):
        raise OperatorError("descendant owner restart has incomplete prior continuity")
    for field in ("schema_revision", "generation", "fence_epoch"):
        _exact_int(
            prior_owner.get(field),
            field=f"prior state-owner {field}",
            minimum=1,
        )


def _current_head_blocked_retry_database_states(
    source: Any,
    batch: Mapping[str, Any],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Classify every batch member before any owner command is issued."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TYPED_DATABASE_BLOCKED_RETRY_REVALIDATION_FIELD,
    )

    entries = batch.get("entries")
    if not isinstance(entries, list):
        raise OperatorError("blocked-retry database batch is absent")
    states: dict[str, str] = {}
    projections: list[dict[str, Any]] = []
    post_statuses = {
        "retrying",
        "in_progress",
        "completed",
        "complete",
        "done",
        "skipped",
        "blocked",
        "failed",
        "quarantined",
        "cancelled",
        "canceled",
    }
    batch_receipt_id = str(batch.get("batch_receipt_id") or "")
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise OperatorError("blocked-retry database entry is malformed")
        alias = str(entry.get("task_alias") or "")
        task_cid = str(entry.get("task_cid") or "")
        task = source.get_task(alias)
        source_body = entry.get("source_task_body")
        terminal_receipt = (
            source_body.get("completion_receipt")
            if isinstance(source_body, Mapping)
            else None
        )
        if (
            task is None
            or task.task_cid != task_cid
            or not isinstance(source_body, Mapping)
            or not isinstance(terminal_receipt, Mapping)
        ):
            raise OperatorError(f"{alias} blocked-retry database task is absent")
        source_revision = int(entry["source_revision"])
        target_revision = int(entry["target_revision"])
        exact_source = bool(
            task.status == "blocked"
            and int(task.revision) == source_revision
            and task.body == source_body
        )
        if exact_source:
            if source.get_queue_entry(task_cid) is not None:
                raise OperatorError(
                    f"{alias} blocked-retry predecessor already has a cooldown"
                )
            state = "pending_apply"
        else:
            expected_body = _current_head_blocked_retry_expected_task_body(
                entry=entry,
                batch_receipt_id=batch_receipt_id,
            )
            expected_requirement = expected_body[
                TYPED_DATABASE_BLOCKED_RETRY_REVALIDATION_FIELD
            ]
            body = task.body if isinstance(task.body, Mapping) else {}
            receipt = body.get("completion_receipt")
            route = (
                receipt.get("execution_route_binding")
                if isinstance(receipt, Mapping)
                else None
            )
            if (
                int(task.revision) < target_revision
                or task.status not in post_statuses
                or body.get(TYPED_DATABASE_BLOCKED_RETRY_REVALIDATION_FIELD)
                != expected_requirement
                or not isinstance(receipt, Mapping)
                or not isinstance(route, Mapping)
                or route.get("task_alias") != alias
                or route.get("task_cid") != task_cid
                or receipt.get("execution_route_policy_id")
                != route.get("policy_id")
                or receipt.get("execution_route_origin_revision")
                != route.get("task_revision")
            ):
                raise OperatorError(
                    f"{alias} blocked-retry post-command task changed authority"
                )
            if int(task.revision) == target_revision:
                if task.status != "retrying" or body != expected_body:
                    raise OperatorError(
                        f"{alias} blocked-retry target projection changed"
                    )
                queue = source.validate_retrying_task_cooldown(
                    task_cid,
                    expected_attempt_identity={
                        field: terminal_receipt[field]
                        for field in (
                            "attempt_id",
                            "claim_id",
                            "lease_id",
                            "owner_session_id",
                            "attempt_number",
                            "fencing_token",
                            "fence_epoch",
                        )
                    },
                    expected_reason=HANDOFF_REPAIR_BLOCKED_RETRY_REASON,
                    expected_delay_ms=0,
                )
                if (
                    queue.attempt != terminal_receipt["attempt_number"]
                    or queue.retry_not_before_ms
                    != entry["retry_not_before_ms"]
                    or queue.selection_penalty != 0
                    or queue.consecutive_failures
                    != terminal_receipt["attempt_number"]
                    or queue.state != "released"
                    or queue.reason != HANDOFF_REPAIR_BLOCKED_RETRY_REASON
                ):
                    raise OperatorError(
                        f"{alias} blocked-retry cooldown changed authority"
                    )
            state = "command_replay_required"
        states[alias] = state
        current_receipt = (
            task.body.get("completion_receipt")
            if isinstance(task.body, Mapping)
            else None
        )
        projections.append(
            {
                "task_alias": alias,
                "task_cid": task_cid,
                "status": task.status,
                "revision": int(task.revision),
                "receipt_operation": (
                    str(current_receipt.get("operation") or "")
                    if isinstance(current_receipt, Mapping)
                    else ""
                ),
                "receipt_identity": (
                    _identity(current_receipt)
                    if isinstance(current_receipt, Mapping)
                    else ""
                ),
                "blocked_retry_state": state,
            }
        )
    if set(states) != set(CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS):
        raise OperatorError("blocked-retry database population is incomplete")
    return states, projections


def _restart_database_verification(source: Any, admission: Mapping[str, Any]) -> dict[str, Any]:
    """Reproduce the immutable population and exact repair source task."""

    authority = admission.get("database_authority")
    if not isinstance(authority, Mapping):
        raise OperatorError("restart admission has no database authority")
    snapshot = source.snapshot()
    page = source.list_tasks(limit=500)
    if page.next_cursor:
        raise OperatorError("restart database task population exceeds its bound")
    task_cids = sorted(str(task.task_cid) for task in page.tasks)
    expected_task_cids = sorted(str(item) for item in authority.get("task_cids", ()))
    if (
        task_cids != expected_task_cids
        or int(snapshot.task_count) != int(authority.get("task_count") or 0)
        or int(snapshot.goal_count) != int(authority.get("goal_count") or 0)
        or int(snapshot.plan_count) != int(authority.get("plan_count") or 0)
        or snapshot.plan_root_cid != authority.get("plan_root_cid")
        or snapshot.repository_tree_id != authority.get("repository_tree_id")
    ):
        raise OperatorError("restart database population differs from bootstrap")

    repair = admission.get("handoff_repair")
    task_projection: dict[str, Any] = {}
    if isinstance(repair, Mapping) and repair:
        task = source.get_task(str(repair.get("task_alias") or ""))
        attempt = repair.get("source_attempt")
        blocked_retry = repair.get("blocked_retry_handoff")
        sealed_source_body = (
            blocked_retry.get("source_task_body")
            if isinstance(blocked_retry, Mapping)
            else None
        )
        sidecar_evidence = (
            blocked_retry.get("sidecar_evidence")
            if isinstance(blocked_retry, Mapping)
            else None
        )
        receipt = (
            task.body.get("completion_receipt")
            if task is not None and isinstance(task.body, Mapping)
            else None
        )
        if (
            task is None
            or task.task_cid != repair.get("task_cid")
            or not isinstance(attempt, Mapping)
            or not isinstance(receipt, Mapping)
            or not isinstance(sealed_source_body, Mapping)
            or _identity(sealed_source_body) != HANDOFF_REPAIR_SOURCE_TASK_BODY_ID
            or not isinstance(sidecar_evidence, Mapping)
        ):
            raise OperatorError("restart repair source task changed authority")
        source_revision = int(attempt.get("task_revision") or 0)
        target_revision = int(blocked_retry.get("target_revision") or 0)
        source_receipt = sealed_source_body.get("completion_receipt")
        sealed_evidence_id = str(
            sidecar_evidence.get("evidence_id")
            if isinstance(sidecar_evidence, Mapping)
            else ""
        )
        source_route = (
            source_receipt.get("execution_route_binding")
            if isinstance(source_receipt, Mapping)
            else None
        )
        expected_recovery_receipt = {
            "schema": TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_SCHEMA,
            "operation": HANDOFF_REPAIR_BLOCKED_RETRY_OPERATION,
            **{
                field: attempt[field]
                for field in (
                    "attempt_id",
                    "claim_id",
                    "lease_id",
                    "owner_session_id",
                    "attempt_number",
                    "fencing_token",
                    "fence_epoch",
                )
            },
            "terminal_operation": "database_portal_terminal_failure",
            "terminal_reason": "portal_provider_failed",
            "source_completion_receipt_id": (
                HANDOFF_REPAIR_COMPLETION_RECEIPT_ID
            ),
            "operator_handoff_receipt_id": HANDOFF_REPAIR_SEALED_RECEIPT_ID,
            "sidecar_evidence_id": sealed_evidence_id,
            "recovered_from_revision": source_revision,
            "max_task_attempts_before": blocked_retry.get(
                "max_task_attempts_before"
            ),
            "max_task_attempts_after": blocked_retry.get(
                "max_task_attempts_after"
            ),
            "attempt_refunded": False,
            "fresh_attempt_number": blocked_retry.get(
                "fresh_attempt_number"
            ),
            "queue_reason": HANDOFF_REPAIR_BLOCKED_RETRY_REASON,
            "backoff_ms": 0,
            "retry_not_before_ms": blocked_retry.get(
                "retry_not_before_ms"
            ),
            "control_expected_status": "blocked",
            "control_expected_revision": source_revision,
            "execution_route_binding": (
                dict(source_route) if isinstance(source_route, Mapping) else {}
            ),
            "execution_route_binding_cid": (
                _semantic_identity(
                    {"task_execution_route_binding": dict(source_route)}
                )
                if isinstance(source_route, Mapping)
                else ""
            ),
            "execution_route_policy_id": HANDOFF_REPAIR_ROUTE_POLICY_ID,
            "execution_route_origin_revision": 1,
        }
        expected_recovery_body = dict(sealed_source_body)
        expected_recovery_body["completion_receipt"] = expected_recovery_receipt
        exact_source = bool(
            task.status == "blocked"
            and int(task.revision) == source_revision
            and task.body == sealed_source_body
            and receipt == source_receipt
            and _identity(receipt) == HANDOFF_REPAIR_COMPLETION_RECEIPT_ID
            and receipt.get("operation") == "database_portal_terminal_failure"
            and receipt.get("reason") == "portal_provider_failed"
            and receipt.get("retryable") is False
            and receipt.get("control_expected_status") == "in_progress"
            and receipt.get("control_expected_revision") == source_revision - 1
            and all(
                receipt.get(field) == attempt.get(field)
                for field in (
                    "attempt_id",
                    "claim_id",
                    "lease_id",
                    "owner_session_id",
                    "attempt_number",
                    "fencing_token",
                    "fence_epoch",
                )
            )
        )
        if exact_source:
            if source.get_queue_entry(task.task_cid) is not None:
                raise OperatorError(
                    "restart repair source task already has a retry cooldown"
                )
            handoff_state = "pending_apply"
        else:
            route = receipt.get("execution_route_binding")
            allowed_post_statuses = {
                "retrying",
                "in_progress",
                "completed",
                "complete",
                "done",
                "skipped",
                "blocked",
                "failed",
                "quarantined",
                "cancelled",
                "canceled",
            }
            if (
                int(task.revision) < target_revision
                or task.status not in allowed_post_statuses
                or not isinstance(route, Mapping)
                or route.get("task_cid") != task.task_cid
                or route.get("task_alias") != task.task_alias
                or route.get("policy_id") != HANDOFF_REPAIR_ROUTE_POLICY_ID
                or route.get("task_revision") != 1
                or receipt.get("execution_route_policy_id")
                != HANDOFF_REPAIR_ROUTE_POLICY_ID
                or receipt.get("execution_route_origin_revision") != 1
            ):
                raise OperatorError(
                    "restart repair post-command task changed authority"
                )
            if int(task.revision) == target_revision:
                if (
                    task.status != "retrying"
                    or receipt != expected_recovery_receipt
                    or task.body != expected_recovery_body
                ):
                    raise OperatorError(
                        "restart repair revision-5 recovery receipt changed authority"
                    )
                queue = source.validate_retrying_task_cooldown(
                    task.task_cid,
                    expected_attempt_identity={
                        field: attempt[field]
                        for field in (
                            "attempt_id",
                            "claim_id",
                            "lease_id",
                            "owner_session_id",
                            "attempt_number",
                            "fencing_token",
                            "fence_epoch",
                        )
                    },
                    expected_reason=HANDOFF_REPAIR_BLOCKED_RETRY_REASON,
                    expected_delay_ms=0,
                )
                if (
                    queue.attempt != int(attempt["attempt_number"])
                    or queue.retry_not_before_ms
                    != blocked_retry.get("retry_not_before_ms")
                    or queue.selection_penalty != 0
                    or queue.consecutive_failures
                    != int(attempt["attempt_number"])
                    or queue.state != "released"
                    or queue.reason != HANDOFF_REPAIR_BLOCKED_RETRY_REASON
                ):
                    raise OperatorError(
                        "restart repair revision-5 cooldown changed authority"
                    )
            handoff_state = "command_replay_required"
        task_projection = {
            "task_alias": task.task_alias,
            "task_cid": task.task_cid,
            "status": task.status,
            "revision": int(task.revision),
            "receipt_operation": str(receipt.get("operation") or ""),
            "receipt_identity": _identity(receipt),
            "attempt_identity": dict(attempt),
            "blocked_retry_handoff_state": handoff_state,
        }

    batch_states: dict[str, str] = {}
    batch_projections: list[dict[str, Any]] = []
    if admission.get("mode") == "verified_current_head_blocked_retry_batch":
        descendant = admission.get("current_head_descendant_repair")
        batch = (
            descendant.get("blocked_retry_batch")
            if isinstance(descendant, Mapping)
            else None
        )
        if not isinstance(batch, Mapping):
            raise OperatorError("restart admission has no blocked-retry batch")
        batch_states, batch_projections = (
            _current_head_blocked_retry_database_states(source, batch)
        )

    verification: dict[str, Any] = {
        "schema": OWNER_DATABASE_VERIFICATION_SCHEMA,
        "bootstrap_database_receipt_identity": str(
            authority.get("receipt_identity") or ""
        ),
        "repository_tree_id": snapshot.repository_tree_id,
        "plan_root_cid": snapshot.plan_root_cid,
        "task_cids": task_cids,
        "task_count": int(snapshot.task_count),
        "goal_count": int(snapshot.goal_count),
        "plan_count": int(snapshot.plan_count),
        "store_revision": int(snapshot.revision),
        "repair_source_task": task_projection,
        "current_head_blocked_retry_states": batch_states,
        "current_head_blocked_retry_tasks": batch_projections,
    }
    verification["verification_id"] = _identity(verification)
    return verification


def _owner_restart_receipt(
    admission: Mapping[str, Any],
    identity: Any,
    *,
    expected_store_id: str,
    prior_owner: Mapping[str, Any],
    database_verification: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one admitted descendant restart to its newly fenced owner."""

    _require_prior_owner_continuity(admission, prior_owner)
    admission_id = str(admission.get("admission_id") or "")
    admission_body = dict(admission)
    admission_body.pop("admission_id", None)
    authority = admission.get("database_authority")
    if (
        admission.get("schema") != OWNER_RESTART_ADMISSION_SCHEMA
        or re.fullmatch(r"sha256:[0-9a-f]{64}", admission_id) is None
        or _identity(admission_body) != admission_id
        or not isinstance(authority, Mapping)
    ):
        raise OperatorError("owner restart admission identity is invalid")
    verification_id = str(database_verification.get("verification_id") or "")
    verification_body = dict(database_verification)
    verification_body.pop("verification_id", None)
    verified_task_cids = database_verification.get("task_cids")
    authority_task_cids = authority.get("task_cids")
    if (
        database_verification.get("schema") != OWNER_DATABASE_VERIFICATION_SCHEMA
        or re.fullmatch(r"sha256:[0-9a-f]{64}", verification_id) is None
        or _identity(verification_body) != verification_id
        or str(
            database_verification.get("bootstrap_database_receipt_identity") or ""
        )
        != str(authority.get("receipt_identity") or "")
        or str(database_verification.get("plan_root_cid") or "")
        != str(admission.get("plan_root_cid") or "")
        or str(database_verification.get("repository_tree_id") or "")
        != str(admission.get("bootstrap_source_tree") or "")
        or not isinstance(verified_task_cids, list)
        or not isinstance(authority_task_cids, list)
        or verified_task_cids != sorted(str(item) for item in authority_task_cids)
        or type(database_verification.get("task_count")) is not int
        or database_verification.get("task_count") != authority.get("task_count")
        or type(database_verification.get("goal_count")) is not int
        or database_verification.get("goal_count") != authority.get("goal_count")
        or type(database_verification.get("plan_count")) is not int
        or database_verification.get("plan_count") != authority.get("plan_count")
    ):
        raise OperatorError("bound restart database verification is invalid")
    store_id = str(getattr(identity, "store_id", "") or "")
    database_uuid = str(getattr(identity, "database_uuid", "") or "")
    generation = _exact_int(
        getattr(identity, "generation", None),
        field="new state-owner generation",
        minimum=1,
    )
    fence_epoch = _exact_int(
        getattr(identity, "fence_epoch", None),
        field="new state-owner fence_epoch",
        minimum=1,
    )
    schema_revision = _exact_int(
        getattr(identity, "schema_revision", None),
        field="new state-owner schema_revision",
        minimum=1,
    )
    if (
        store_id != expected_store_id
        or not database_uuid
        or not str(getattr(identity, "server_id", "") or "")
        or generation < 1
        or fence_epoch < 1
        or schema_revision < 1
        or not str(getattr(identity, "schema_fingerprint", "") or "")
        or not str(getattr(identity, "process_birth_id", "") or "")
    ):
        raise OperatorError("new state-owner identity is invalid")
    prior_generation = int(prior_owner.get("generation") or 0)
    prior_fence_epoch = int(prior_owner.get("fence_epoch") or 0)
    if prior_generation and (
        generation <= prior_generation
        or fence_epoch <= prior_fence_epoch
        or str(prior_owner.get("server_id") or "")
        == str(getattr(identity, "server_id", "") or "")
        or str(prior_owner.get("database_uuid") or "") != database_uuid
        or str(prior_owner.get("store_id") or "") != store_id
        or int(prior_owner.get("schema_revision") or 0) != schema_revision
        or str(prior_owner.get("schema_fingerprint") or "")
        != str(getattr(identity, "schema_fingerprint", "") or "")
        or str(prior_owner.get("process_birth_id") or "")
        == str(getattr(identity, "process_birth_id", "") or "")
    ):
        raise OperatorError("new state-owner fence does not advance prior owner")
    receipt: dict[str, Any] = {
        "schema": OWNER_RESTART_RECEIPT_SCHEMA,
        "admission_id": str(admission.get("admission_id") or ""),
        "mode": str(admission.get("mode") or ""),
        "bootstrap_receipt_id": str(admission.get("bootstrap_receipt_id") or ""),
        "bootstrap_source_head": str(admission.get("bootstrap_source_head") or ""),
        "bootstrap_source_tree": str(admission.get("bootstrap_source_tree") or ""),
        "current_source_head": str(admission.get("current_source_head") or ""),
        "current_source_tree": str(admission.get("current_source_tree") or ""),
        "plan_root_cid": str(admission.get("plan_root_cid") or ""),
        "handoff_repair_receipt_id": str(
            admission.get("handoff_repair_receipt_id") or ""
        ),
        "current_head_descendant_repair_receipt_id": str(
            admission.get("current_head_descendant_repair_receipt_id") or ""
        ),
        "current_head_blocked_retry_batch_receipt_id": str(
            admission.get("current_head_blocked_retry_batch_receipt_id") or ""
        ),
        "stale_worktree_cleanup_transition_receipt_id": str(
            admission.get("stale_worktree_cleanup_transition_receipt_id") or ""
        ),
        "validation_path_compatibility_transition_receipt_id": str(
            admission.get(
                "validation_path_compatibility_transition_receipt_id"
            )
            or ""
        ),
        "database_watchdog_activity_transition_receipt_id": str(
            admission.get(
                "database_watchdog_activity_transition_receipt_id"
            )
            or ""
        ),
        "max_task_attempts_before": int(
            admission.get("max_task_attempts_before") or 0
        ),
        "max_task_attempts_after": int(
            admission.get("max_task_attempts_after") or 0
        ),
        "prior_state_owner": dict(prior_owner),
        "database_verification": dict(database_verification),
        "state_owner": {
            "server_id": str(getattr(identity, "server_id", "") or ""),
            "store_id": store_id,
            "database_uuid": database_uuid,
            "schema_revision": schema_revision,
            "schema_fingerprint": str(
                getattr(identity, "schema_fingerprint", "") or ""
            ),
            "generation": generation,
            "fence_epoch": fence_epoch,
            "process_birth_id": str(
                getattr(identity, "process_birth_id", "") or ""
            ),
        },
    }
    receipt["receipt_id"] = _identity(receipt)
    return receipt


def _process_argv(pid: int) -> tuple[str, ...]:
    try:
        payload = Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except OSError as exc:
        raise OperatorError("executor parent command line is unavailable") from exc
    if not payload or len(payload) > 131_072:
        raise OperatorError("executor parent command line is invalid")
    try:
        return tuple(
            item.decode("utf-8")
            for item in payload.rstrip(b"\x00").split(b"\x00")
            if item
        )
    except UnicodeDecodeError as exc:
        raise OperatorError("executor parent command line is not UTF-8") from exc


def _argv_values(argv: Sequence[str], option: str) -> tuple[str, ...]:
    values: list[str] = []
    index = 0
    while index < len(argv):
        token = str(argv[index])
        if token == option:
            if index + 1 >= len(argv):
                raise OperatorError(f"executor parent {option} has no value")
            values.append(str(argv[index + 1]))
            index += 2
            continue
        if token.startswith(option + "="):
            values.append(token.split("=", 1)[1])
        index += 1
    return tuple(values)


def _continued_execution_route_policy(
    tasks: Sequence[Any],
    continuation: Mapping[str, Any],
) -> tuple[Any, list[dict[str, Any]]]:
    """Reconstitute the one carried PCSM epoch policy without resealing heads."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.task_execution_route_policy import (
        TaskExecutionRouteBinding,
        TaskExecutionRouteEntry,
        TaskExecutionRoutePolicy,
        task_execution_contract_cid,
    )

    expected_policy_id = str(continuation.get("policy_id") or "")
    expected_plan_root = str(continuation.get("plan_root_cid") or "")
    expected_tree = str(continuation.get("repository_tree_id") or "")
    expected_projection = str(continuation.get("source_projection_cid") or "")
    expected_mode = str(continuation.get("execution_mode") or "")
    source_revision = _exact_int(
        continuation.get("source_revision"),
        field="continued route source_revision",
        minimum=1,
    )
    origin_revision = _exact_int(
        continuation.get("origin_task_revision"),
        field="continued route origin_task_revision",
        minimum=1,
    )
    expected_task_count = _exact_int(
        continuation.get("task_count"),
        field="continued route task_count",
        minimum=1,
    )
    if (
        expected_policy_id != HANDOFF_REPAIR_ROUTE_POLICY_ID
        or expected_projection != HANDOFF_REPAIR_ROUTE_SOURCE_PROJECTION_CID
        or source_revision != 1
        or origin_revision != 1
        or expected_mode != "grok-codex"
        or len(tasks) != expected_task_count
    ):
        raise OperatorError("continued execution route header changed authority")

    entries: list[Any] = []
    advanced: list[dict[str, Any]] = []
    for task in tasks:
        current_revision = int(getattr(task, "revision", 0) or 0)
        if current_revision < origin_revision:
            raise OperatorError("continued execution route task revision regressed")
        current_contract = task_execution_contract_cid(task)
        if current_revision == origin_revision:
            entry = TaskExecutionRouteEntry(
                task_cid=task.task_cid,
                task_alias=task.task_alias,
                task_revision=origin_revision,
                task_contract_cid=current_contract,
                execution_mode=expected_mode,
            )
        else:
            body = task.body if isinstance(task.body, Mapping) else {}
            receipt = body.get("completion_receipt")
            route = (
                receipt.get("execution_route_binding")
                if isinstance(receipt, Mapping)
                else None
            )
            try:
                binding = (
                    TaskExecutionRouteBinding.from_dict(route)
                    if isinstance(route, Mapping)
                    else None
                )
            except Exception as exc:
                raise OperatorError(
                    "advanced task has malformed carried execution-route lineage"
                ) from exc
            if (
                binding is None
                or binding.policy_id != expected_policy_id
                or binding.plan_root_cid != expected_plan_root
                or binding.repository_tree_id != expected_tree
                or binding.source_revision != source_revision
                or binding.task_cid != task.task_cid
                or binding.task_alias != task.task_alias
                or binding.task_revision != origin_revision
                or binding.task_contract_cid != current_contract
                or binding.execution_mode != expected_mode
                or receipt.get("execution_route_policy_id") != expected_policy_id
                or receipt.get("execution_route_origin_revision") != origin_revision
            ):
                raise OperatorError(
                    "advanced task differs from its carried execution-route lineage"
                )
            entry = TaskExecutionRouteEntry(
                task_cid=binding.task_cid,
                task_alias=binding.task_alias,
                task_revision=binding.task_revision,
                task_contract_cid=binding.task_contract_cid,
                execution_mode=binding.execution_mode,
            )
            advanced.append(
                {
                    "task_alias": task.task_alias,
                    "task_cid": task.task_cid,
                    "origin_revision": origin_revision,
                    "current_revision": current_revision,
                }
            )
        entries.append(entry)

    try:
        policy = TaskExecutionRoutePolicy(
            plan_root_cid=expected_plan_root,
            repository_tree_id=expected_tree,
            source_revision=source_revision,
            source_projection_cid=expected_projection,
            entries=tuple(sorted(entries, key=lambda item: item.task_cid)),
            policy_id=expected_policy_id,
        )
    except Exception as exc:
        raise OperatorError(
            "continued execution route does not reproduce its immutable policy"
        ) from exc
    if (
        len(policy.entries) != expected_task_count
        or not advanced
        or HANDOFF_REPAIR_TASK_CID
        not in {str(item["task_cid"]) for item in advanced}
    ):
        raise OperatorError("continued execution route has no exact repair lineage")
    return policy, sorted(advanced, key=lambda item: str(item["task_cid"]))


def _acquire_exact_sidecar_lock(path: Path, expected: bytes) -> int:
    """Hold one private no-follow lane lock while its sidecar is inspected."""

    descriptor = -1
    try:
        before = path.lstat()
        flags = (
            os.O_RDWR
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        if not getattr(os, "O_NOFOLLOW", 0):
            raise OperatorError("continued route sidecar lock requires no-follow access")
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (
            not stat_module.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or opened.st_nlink != 1
            or stat_module.S_IMODE(opened.st_mode) != 0o600
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise OperatorError("continued route sidecar lock is not an exact private file")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.lseek(descriptor, 0, os.SEEK_SET)
        observed = os.read(descriptor, len(expected) + 1)
        named = path.lstat()
        if (
            observed != expected
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise OperatorError("continued route sidecar lock changed authority")
        return descriptor
    except OperatorError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise OperatorError("continued route sidecar lock is unavailable") from exc


def _runtime_file_evidence(role: str, path: Path) -> dict[str, Any]:
    """Hash one owned, non-linked runtime file without following a symlink."""

    descriptor = -1
    try:
        before = path.lstat()
        no_follow = getattr(os, "O_NOFOLLOW", 0)
        if not no_follow:
            raise OperatorError("blocked-retry evidence requires no-follow access")
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow,
        )
        opened = os.fstat(descriptor)
        if (
            not stat_module.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or opened.st_nlink != 1
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
            or opened.st_size < 1
            or opened.st_size > 64 * 1024 * 1024
        ):
            raise OperatorError(
                f"blocked-retry {role} is not an exact owned file"
            )
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
        named = path.lstat()
        if (
            size != opened.st_size
            or (opened.st_dev, opened.st_ino, opened.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
            or (named.st_dev, named.st_ino, named.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
        ):
            raise OperatorError(f"blocked-retry {role} changed while hashing")
        return {
            "role": role,
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": "sha256:" + digest.hexdigest(),
            "size_bytes": size,
        }
    except OSError as exc:
        raise OperatorError(f"blocked-retry {role} cannot be hashed safely") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _verify_blocked_retry_sidecar_evidence(
    *,
    coordination_path: Path,
    execution_path: Path,
    blocked_retry_handoff: Mapping[str, Any],
) -> dict[str, Any]:
    """Reproduce the exact expired attempt-1 and Portal failure evidence."""

    try:
        import duckdb
    except Exception as exc:
        raise OperatorError("blocked-retry sidecar verifier requires DuckDB") from exc

    source_attempt = HANDOFF_REPAIR_SOURCE_ATTEMPT
    task_cid = HANDOFF_REPAIR_TASK_CID
    coordination = None
    execution = None
    try:
        coordination = duckdb.connect(str(coordination_path), read_only=True)
        coordination_task_rows = coordination.execute(
            "SELECT ready, body_json FROM coordination_tasks "
            "WHERE task_cid = ? LIMIT 2",
            [task_cid],
        ).fetchall()
        coordination_attempt_rows = coordination.execute(
            "SELECT attempt_id, task_cid, attempt_number, owner_session_id, "
            "fencing_token, fence_epoch, started_at_ms, finished_at_ms, "
            "status, revision FROM task_attempts WHERE task_cid = ? "
            "ORDER BY attempt_number",
            [task_cid],
        ).fetchall()
        coordination_claim_rows = coordination.execute(
            "SELECT claim_id, task_cid, owner_session_id, fencing_token, "
            "fence_epoch, expires_at_ms, state, revision, attempt_id, "
            "attempt_number, lease_id FROM task_claims WHERE task_cid = ? "
            "ORDER BY attempt_number",
            [task_cid],
        ).fetchall()
        coordination_lease_rows = coordination.execute(
            "SELECT lease_id, owner_session_id, fencing_token, fence_epoch, "
            "expires_at_ms, state, revision, task_cid, claim_id, attempt_id, "
            "attempt_number FROM fenced_leases WHERE task_cid = ? "
            "ORDER BY attempt_number",
            [task_cid],
        ).fetchall()
        completion_count = int(
            coordination.execute(
                "SELECT count(*) FROM task_completions WHERE task_cid = ?",
                [task_cid],
            ).fetchone()[0]
        )
        newer_attempt_count = int(
            coordination.execute(
                "SELECT count(*) FROM task_attempts WHERE task_cid = ? "
                "AND attempt_number > 1",
                [task_cid],
            ).fetchone()[0]
        )
        newer_fence_count = int(
            coordination.execute(
                "SELECT count(*) FROM fenced_leases WHERE task_cid = ? "
                "AND (fencing_token > 1 OR fence_epoch > 1)",
                [task_cid],
            ).fetchone()[0]
        )

        execution = duckdb.connect(str(execution_path), read_only=True)
        execution_attempt_rows = execution.execute(
            "SELECT attempt_id, claim_id, task_cid, task_alias, attempt_number, "
            "owner_session_id, fencing_token, fence_epoch, lease_id, "
            "committed_phase, status, started_at_ms, finished_at_ms, revision, "
            "body_json FROM database_task_attempts WHERE task_cid = ? "
            "ORDER BY attempt_number",
            [task_cid],
        ).fetchall()
        phase_rows = execution.execute(
            "SELECT phase, revision, body_json FROM attempt_phases "
            "WHERE attempt_id = ? ORDER BY revision",
            [source_attempt["attempt_id"]],
        ).fetchall()
        provider_rows = execution.execute(
            "SELECT invocation_id, result_json FROM provider_invocations "
            "WHERE attempt_id = ? LIMIT 2",
            [source_attempt["attempt_id"]],
        ).fetchall()
        effect_count = int(
            execution.execute(
                "SELECT count(*) FROM effect_claims WHERE attempt_id = ?",
                [source_attempt["attempt_id"]],
            ).fetchone()[0]
        )
    except Exception as exc:
        raise OperatorError("blocked-retry sidecar rows cannot be verified") from exc
    finally:
        if coordination is not None:
            coordination.close()
        if execution is not None:
            execution.close()

    if (
        len(coordination_task_rows) != 1
        or len(coordination_attempt_rows) != 1
        or len(coordination_claim_rows) != 1
        or len(coordination_lease_rows) != 1
        or len(execution_attempt_rows) != 1
        or len(provider_rows) != 1
    ):
        raise OperatorError("blocked-retry sidecar identity is absent or ambiguous")
    try:
        coordination_task_body = json.loads(str(coordination_task_rows[0][1]))
        execution_attempt_body = json.loads(str(execution_attempt_rows[0][14]))
        phase_bodies = [json.loads(str(row[2])) for row in phase_rows]
        provider_body = json.loads(str(provider_rows[0][1]))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise OperatorError("blocked-retry sidecar JSON is malformed") from exc

    expected_attempt = (
        source_attempt["attempt_id"],
        task_cid,
        1,
        source_attempt["owner_session_id"],
        1,
        1,
        1787742329266,
        1787743027778,
        "expired",
        2,
    )
    expected_claim = (
        source_attempt["claim_id"],
        task_cid,
        source_attempt["owner_session_id"],
        1,
        1,
        1787743011400,
        "expired",
        34,
        source_attempt["attempt_id"],
        1,
        source_attempt["lease_id"],
    )
    expected_lease = (
        source_attempt["lease_id"],
        source_attempt["owner_session_id"],
        1,
        1,
        1787743011400,
        "expired",
        34,
        task_cid,
        source_attempt["claim_id"],
        source_attempt["attempt_id"],
        1,
    )
    execution_row = execution_attempt_rows[0]
    route = (
        execution_attempt_body.get("execution_route_binding")
        if isinstance(execution_attempt_body, Mapping)
        else None
    )
    expected_execution_prefix = (
        source_attempt["attempt_id"],
        source_attempt["claim_id"],
        task_cid,
        "PCSM-010",
        1,
        source_attempt["owner_session_id"],
        1,
        1,
        source_attempt["lease_id"],
        "failed",
        "failed",
        1787742329266,
        1787742964256,
        3,
    )
    if (
        coordination_task_rows[0][0] is not False
        or coordination_task_body
        != {
            "authoritative_attempt_floor": 0,
            "authoritative_attempt_floor_source": "",
            "authoritative_revision": 4,
            "authoritative_status": "blocked",
            "authority": "task_source",
            "restart_recovery_binding": {},
            "restart_recovery_owner_session_id": "",
            "restart_recovery_ready": False,
        }
        or tuple(coordination_attempt_rows[0]) != expected_attempt
        or tuple(coordination_claim_rows[0]) != expected_claim
        or tuple(coordination_lease_rows[0]) != expected_lease
        or completion_count != 0
        or newer_attempt_count != 0
        or newer_fence_count != 0
        or tuple(execution_row[:14]) != expected_execution_prefix
        or not isinstance(route, Mapping)
        or route.get("policy_id") != HANDOFF_REPAIR_ROUTE_POLICY_ID
        or route.get("task_cid") != task_cid
        or route.get("task_revision") != 1
        or [(str(row[0]), int(row[1])) for row in phase_rows]
        != [("claimed", 1), ("context", 2), ("failed", 3)]
        or phase_bodies[-1]
        != {
            "attempt_consumed": "unknown",
            "backoff_seconds": 0,
            "deferred": False,
            "portal_retryable_failure": False,
            "portal_terminal_failure": True,
            "provider_dispatched": "unknown",
            "reason": "portal_provider_failed",
            "typed_deferral_slot_consumed": "unknown",
        }
        or not isinstance(provider_body, Mapping)
        or provider_body.get("callback_state") != "started_outcome_unknown"
        or provider_body.get("provider_effect_state") != "unknown_may_have_started"
        or provider_body.get("failure_fingerprint")
        != "sha256:e8a21d888af199e829abba3128a06e576bed90c02ccb60969b241b8f11ed3246"
        or effect_count != 0
    ):
        raise OperatorError("blocked-retry sidecar state changed authority")

    portal_root = ROOT / HANDOFF_REPAIR_PORTAL_ATTEMPT_RELATIVE
    binding_path = portal_root / "database-attempt-binding.json"
    events_path = portal_root / "portal-events.jsonl"
    diagnostic_path = (
        portal_root / "implementation-logs/pcsm-010-diagnostic-receipt.json"
    )
    binding = _json_object(binding_path)
    diagnostic = _json_object(diagnostic_path)
    try:
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorError("blocked-retry Portal events are malformed") from exc
    finished = [
        event
        for event in events
        if isinstance(event, Mapping)
        and event.get("type") == "implementation_finished"
        and event.get("task_id") == "PCSM-010"
        and event.get("attempt") == 1
    ]
    reason_codes = (
        diagnostic.get("failure", {})
        .get("proposal_gate", {})
        .get("reason_codes", [])
    )
    if (
        binding.get("binding_id")
        != "sha256:76a22ab25ce1a82aa6faa8d14e5730ddc4eeadd1a10f4a4ff7ef41856356e450"
        or binding.get("task_cid") != task_cid
        or binding.get("attempt_id") != source_attempt["attempt_id"]
        or binding.get("claim_id") != source_attempt["claim_id"]
        or binding.get("lease_id") != source_attempt["lease_id"]
        or binding.get("owner_session_id") != source_attempt["owner_session_id"]
        or binding.get("attempt_number") != 1
        or binding.get("fencing_token") != 1
        or binding.get("fence_epoch") != 1
        or binding.get("task_revision") != 3
        or binding.get("repository_tree_id") != "cd81f5731ee64c29161830c9933d6739e0dd3eb3"
        or len(finished) != 1
        or finished[0].get("event_id")
        != "sha256:7ac8f6ca2076822f6b6711e99fcf16e5b90189109d0dadba502c02252beb8e91"
        or finished[0].get("provider_dispatched") is not True
        or finished[0].get("attempt_consumed") is not True
        or finished[0].get("returncode") != 78
        or diagnostic.get("receipt_id")
        != "baguqeerajm2bu5i3iejl4lmxf3nrew3ljnkxwl3odujmxfp26dxnqx6wygja"
        or diagnostic.get("failure_id")
        != "baguqeeraseeqvjzceffsvxnadwjymhzmje6kzraydbjnr35q63wmccmx42bq"
        or reason_codes != ["stale_proposal_replay"]
    ):
        raise OperatorError("blocked-retry Portal evidence changed authority")

    observed: dict[str, Any] = {
        "schema": HANDOFF_BLOCKED_RETRY_SIDECAR_SCHEMA,
        "lane_index": 0,
        "stable_binding_id": HANDOFF_REPAIR_STABLE_BINDING_ID,
        "files": [
            _runtime_file_evidence("coordination", coordination_path),
            _runtime_file_evidence("execution", execution_path),
            _runtime_file_evidence("portal_attempt_binding", binding_path),
            _runtime_file_evidence("portal_events", events_path),
            _runtime_file_evidence("diagnostic_receipt", diagnostic_path),
        ],
        "facts": {
            "source_attempt": dict(source_attempt),
            "coordination_task": {"status": "blocked", "revision": 4},
            "coordination_attempt": {
                "status": "expired",
                "revision": 2,
                "finished_at_ms": 1787743027778,
            },
            "coordination_claim": {
                "state": "expired",
                "revision": 34,
                "expires_at_ms": 1787743011400,
            },
            "coordination_lease": {
                "state": "expired",
                "revision": 34,
                "expires_at_ms": 1787743011400,
            },
            "coordination_task_completion_count": completion_count,
            "coordination_newer_attempt_count": newer_attempt_count,
            "coordination_newer_fence_count": newer_fence_count,
            "execution_attempt": {
                "status": "failed",
                "revision": 3,
                "committed_phase": "failed",
                "started_at_ms": 1787742329266,
                "finished_at_ms": 1787742964256,
            },
            "execution_phase_sequence": [
                {"phase": str(row[0]), "revision": int(row[1])}
                for row in phase_rows
            ],
            "execution_provider_invocation": {
                "callback_state": provider_body["callback_state"],
                "provider_effect_state": provider_body["provider_effect_state"],
                "failure_fingerprint": provider_body["failure_fingerprint"],
            },
            "execution_effect_claim_count": effect_count,
            "portal_attempt_binding": {
                "binding_id": binding["binding_id"],
                "task_revision": int(binding["task_revision"]),
                "repository_tree_id": binding["repository_tree_id"],
            },
            "portal_implementation_finished": {
                "event_id": finished[0]["event_id"],
                "projected_task_cid": finished[0]["canonical_task_cid"],
                "attempt": int(finished[0]["attempt"]),
                "provider_dispatched": bool(finished[0]["provider_dispatched"]),
                "attempt_consumed": bool(finished[0]["attempt_consumed"]),
                "returncode": int(finished[0]["returncode"]),
            },
            "diagnostic_receipt": {
                "receipt_id": diagnostic["receipt_id"],
                "failure_id": diagnostic["failure_id"],
                "reason_code": reason_codes[0],
            },
        },
    }
    observed["evidence_id"] = _identity(observed)
    expected = blocked_retry_handoff.get("sidecar_evidence")
    if not isinstance(expected, Mapping) or observed != dict(expected):
        raise OperatorError("blocked-retry sidecar evidence differs from its seal")
    return observed


def _apply_blocked_retry_recovery(
    *,
    server: Any,
    board: Any,
    repair: Mapping[str, Any],
    blocked_retry_handoff: Mapping[str, Any],
    blocked_retry_state: str,
    sidecar_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Submit or replay the one process-bound, task-scoped recovery command."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client import (
        QuackStateClient,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TypedStateOwnerConnection,
    )

    identity = server.identity
    if identity is None:
        raise OperatorError("state owner has no blocked-retry identity")
    task_body = blocked_retry_handoff.get("source_task_body")
    terminal_receipt = (
        task_body.get("completion_receipt")
        if isinstance(task_body, Mapping)
        else None
    )
    evidence_id = str(sidecar_evidence.get("evidence_id") or "")
    handoff_receipt_id = HANDOFF_REPAIR_SEALED_RECEIPT_ID
    source_attempt = repair.get("source_attempt")
    if (
        blocked_retry_state
        not in {"pending_apply", "command_replay_required"}
        or not isinstance(task_body, Mapping)
        or not isinstance(terminal_receipt, Mapping)
        or not isinstance(source_attempt, Mapping)
        or evidence_id
        != str(
            (blocked_retry_handoff.get("sidecar_evidence") or {}).get(
                "evidence_id"
            )
        )
        or re.fullmatch(r"sha256:[0-9a-f]{64}", handoff_receipt_id) is None
    ):
        raise OperatorError("blocked-retry recovery inputs are not sealed")

    client_id = "pcsm-state-owner:blocked-retry-handoff"
    allowed_operations = (
        "whoami_metadata",
        "load_store_generation",
        "executor_retry_cooldown_by_task",
        "txn_load_generation",
        "txn_lookup_idempotency",
        "txn_advance_store_revision",
        "txn_record_idempotency",
        "executor_insert_retry_cooldown",
        "executor_cas_task_status_receipt",
        "executor_insert_task_revision",
    )
    store_id = _control_plane_store_id(board.resolved_database_program())
    token, grant = server.issue_typed_client_grant_record(
        client_id=client_id,
        process_birth_id=identity.process_birth_id,
        allowed_operations=allowed_operations,
        allowed_command_operations=(HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND,),
        entity_scopes={"task_cid": HANDOFF_REPAIR_TASK_CID},
        peer_pid=os.getpid(),
        ttl_seconds=60.0,
    )
    client: Any | None = None
    try:
        client = QuackStateClient(
            owner_id=client_id,
            store_id=store_id,
            process_birth_id=identity.process_birth_id,
            connection_factory=lambda _endpoint: TypedStateOwnerConnection(
                socket_path=server.typed_command_socket_path(),
                token=token,
                client_id=client_id,
                process_birth_id=identity.process_birth_id,
                store_id=store_id,
            ),
        )
        client.attach(
            board.resolved_database_program().quack_endpoint,
            server_id=identity.server_id,
        )
        generation_before = client.load_generation()
        result = client.recover_blocked_task_retry(
            task_cid=HANDOFF_REPAIR_TASK_CID,
            expected_task_revision=int(
                blocked_retry_handoff.get("source_revision") or 0
            ),
            task_body=dict(task_body),
            terminal_receipt=dict(terminal_receipt),
            max_task_attempts_before=int(
                blocked_retry_handoff.get("max_task_attempts_before") or 0
            ),
            max_task_attempts_after=int(
                blocked_retry_handoff.get("max_task_attempts_after") or 0
            ),
            operator_handoff_receipt_id=handoff_receipt_id,
            sidecar_evidence_id=evidence_id,
            now_ms=int(blocked_retry_handoff.get("started_at_ms") or -1),
        )
        generation_after = client.load_generation()
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            server.revoke_typed_client_grant(grant.grant_id)

    outcome = result.outcome.value
    expected_outcome = (
        "accepted"
        if blocked_retry_state == "pending_apply"
        else "idempotent_replay"
    )
    route = terminal_receipt.get("execution_route_binding")
    result_body = dict(result.result)
    store_revision_before = result_body.get("store_revision_before")
    expected_result = {
        "schema": TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_SCHEMA,
        "operation": HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND,
        "task_cid": HANDOFF_REPAIR_TASK_CID,
        "attempt_id": source_attempt["attempt_id"],
        "attempt_number": source_attempt["attempt_number"],
        "fresh_attempt_number": blocked_retry_handoff[
            "fresh_attempt_number"
        ],
        "task_revision": blocked_retry_handoff["target_revision"],
        "queue_revision": 1,
        "retry_not_before_ms": blocked_retry_handoff[
            "retry_not_before_ms"
        ],
        "source_completion_receipt_id": HANDOFF_REPAIR_COMPLETION_RECEIPT_ID,
        "operator_handoff_receipt_id": handoff_receipt_id,
        "sidecar_evidence_id": evidence_id,
        "max_task_attempts_before": blocked_retry_handoff[
            "max_task_attempts_before"
        ],
        "max_task_attempts_after": blocked_retry_handoff[
            "max_task_attempts_after"
        ],
        "attempt_refunded": False,
        "execution_route_binding_cid": (
            _semantic_identity({"task_execution_route_binding": dict(route)})
            if isinstance(route, Mapping)
            else ""
        ),
        "execution_route_policy_id": HANDOFF_REPAIR_ROUTE_POLICY_ID,
        "execution_route_origin_revision": 1,
        "store_revision_before": store_revision_before,
    }
    command_prefix = "cmd:blocked-retry-recovery:"
    idempotency_prefix = "executor-blocked-retry-recovery:"
    command_digest = result.command_id.removeprefix(command_prefix)
    if (
        outcome != expected_outcome
        or result.changed is not (blocked_retry_state == "pending_apply")
        or result.conflict_kind is not None
        or result_body != expected_result
        or type(store_revision_before) is not int
        or store_revision_before < 0
        or not result.command_id.startswith(command_prefix)
        or re.fullmatch(r"[0-9a-f]{64}", command_digest) is None
        or result.idempotency_key
        != f"{idempotency_prefix}{command_digest}"
        or result.result_digest != _identity(result_body)
        or generation_before.generation != int(identity.generation)
        or generation_before.fence_epoch != int(identity.fence_epoch)
        or generation_after.generation != int(identity.generation)
        or generation_after.fence_epoch != int(identity.fence_epoch)
        or result.generation != generation_after.generation
        or result.fence_epoch != generation_after.fence_epoch
        or result.revision != generation_after.revision
        or (
            blocked_retry_state == "pending_apply"
            and (
                generation_before.revision != store_revision_before
                or generation_after.revision
                != store_revision_before + 1
            )
        )
        or (
            blocked_retry_state == "command_replay_required"
            and generation_after.to_dict()
            != generation_before.to_dict()
        )
    ):
        raise OperatorError("blocked-retry owner command was not exactly admitted")
    return {
        "authorization": {
            "client_id": client_id,
            "process_birth_id": identity.process_birth_id,
            "peer_pid": os.getpid(),
            "allowed_operations": list(allowed_operations),
            "allowed_command_operations": [
                HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND
            ],
            "entity_scopes": {"task_cid": HANDOFF_REPAIR_TASK_CID},
            "revoked": True,
        },
        "command": result.to_dict(),
    }


def _verified_current_head_blocked_retry_evidence(
    value: Any,
    *,
    alias: str,
    task_cid: str,
    terminal_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one closed incident/Portal/rescue evidence binding."""

    expected = CURRENT_HEAD_BLOCKED_RETRY_INCIDENT_EXPECTATIONS.get(alias)
    required = {
        "schema",
        "task_alias",
        "task_cid",
        "lane_index",
        "portal_attempt_id",
        "portal_attempt_relative_path",
        "database_attempt_binding_path",
        "database_attempt_binding_bytes_id",
        "database_attempt_binding_id",
        "protected_path_incident_path",
        "protected_path_incident_bytes_id",
        "protected_path_incident_identity",
        "projected_portal_task_cid",
        "projected_portal_task_key",
        "portal_implementation_attempt",
        "attempt_identity",
        "rescue_commit",
        "merge_commit",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise OperatorError(f"{alias} blocked-retry sidecar evidence is not closed")
    evidence = dict(value)
    if not isinstance(expected, Mapping):
        raise OperatorError(f"{alias} blocked-retry incident is not admitted")
    lane_index = int(expected["lane_index"])
    portal_attempt_id = str(expected["portal_attempt_id"])
    attempt_root = (
        RUNTIME_RELATIVE
        / "state"
        / f"lane-{lane_index}"
        / f"pcsm_lane_{lane_index}_database_portal_attempts"
        / portal_attempt_id
    )
    binding_path = (attempt_root / "database-attempt-binding.json").as_posix()
    incident_path = (
        attempt_root / "implementation-protected-path-incident.json"
    ).as_posix()
    attempt_fields = (
        "attempt_id",
        "attempt_number",
        "claim_id",
        "lease_id",
        "owner_session_id",
        "fencing_token",
        "fence_epoch",
    )
    attempt_identity = evidence.get("attempt_identity")
    expected_attempt = {
        field: terminal_receipt.get(field) for field in attempt_fields
    }
    sha_fields = (
        "database_attempt_binding_bytes_id",
        "database_attempt_binding_id",
        "protected_path_incident_bytes_id",
        "protected_path_incident_identity",
    )
    rescue_commit = str(expected["rescue_commit"])
    merge_commit = str(expected["merge_commit"])
    rescue_parents = str(
        _git("show", "-s", "--format=%P", rescue_commit)
    ).strip().split()
    merge_parents = str(
        _git("show", "-s", "--format=%P", merge_commit)
    ).strip().split()
    rescue_paths = tuple(
        line
        for line in str(
            _git(
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                rescue_commit,
            )
        ).splitlines()
        if line
    )
    if (
        evidence.get("schema")
        != CURRENT_HEAD_BLOCKED_RETRY_BATCH_EVIDENCE_SCHEMA
        or evidence.get("task_alias") != alias
        or evidence.get("task_cid") != task_cid
        or evidence.get("lane_index") != lane_index
        or evidence.get("portal_attempt_id") != portal_attempt_id
        or evidence.get("portal_attempt_relative_path") != attempt_root.as_posix()
        or evidence.get("database_attempt_binding_path") != binding_path
        or evidence.get("protected_path_incident_path") != incident_path
        or not isinstance(attempt_identity, Mapping)
        or dict(attempt_identity) != expected_attempt
        or any(
            re.fullmatch(r"sha256:[0-9a-f]{64}", str(evidence.get(field) or ""))
            is None
            for field in sha_fields
        )
        or type(evidence.get("projected_portal_task_cid")) is not str
        or not evidence.get("projected_portal_task_cid")
        or type(evidence.get("projected_portal_task_key")) is not str
        or not evidence.get("projected_portal_task_key")
        or type(evidence.get("portal_implementation_attempt")) is not int
        or evidence.get("portal_implementation_attempt") < 1
        or evidence.get("rescue_commit") != rescue_commit
        or evidence.get("merge_commit") != merge_commit
        or len(rescue_parents) != 1
        or len(merge_parents) != 2
        or merge_parents[1] != rescue_commit
        or rescue_paths
        != (
            f"artifacts/proof_carrying_semantic_minification/receipts/{alias}.json",
        )
    ):
        raise OperatorError(f"{alias} blocked-retry sidecar evidence changed")
    _git_is_ancestor(
        merge_commit,
        CURRENT_HEAD_BLOCKED_RETRY_INTERMEDIATE_HEAD,
        field=f"{alias} rescue merge lineage",
    )
    return evidence


def _verified_current_head_blocked_retry_batch(
    value: Any,
    *,
    sealed_source_head: str,
    sealed_source_tree: str,
    current_attempt_limit: int,
) -> dict[str, Any]:
    """Verify the complete, current-head-bound PCSM-013/016/017/018 batch.

    Verification deliberately completes before any owner grant is issued.  The
    predecessor task bodies and terminal receipts are the authoritative
    database values, not the receipt files which happened to land in Git.  The
    caller must first use the restart descendant-repair chain to bind the live
    outer head to this sealed source head; keeping that ancestry proof outside
    the batch avoids a commit hashing its own identity.
    """

    if not isinstance(value, Mapping):
        raise OperatorError("current-head blocked-retry batch is absent")
    payload = dict(value)
    required_top = {
        "schema",
        "operation",
        "source_head",
        "repository_tree_id",
        "entries",
        "batch_receipt_id",
    }
    if set(payload) != required_top:
        raise OperatorError("current-head blocked-retry batch fields are not exact")
    receipt_id = str(payload.get("batch_receipt_id") or "")
    receipt_body = dict(payload)
    receipt_body.pop("batch_receipt_id", None)
    if (
        payload.get("schema") != CURRENT_HEAD_BLOCKED_RETRY_BATCH_SCHEMA
        or payload.get("operation") != CURRENT_HEAD_BLOCKED_RETRY_BATCH_OPERATION
        or payload.get("source_head") != sealed_source_head
        or payload.get("repository_tree_id") != sealed_source_tree
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(receipt_body) != receipt_id
        or re.fullmatch(r"[0-9a-f]{40}", sealed_source_head) is None
        or re.fullmatch(r"[0-9a-f]{40}", sealed_source_tree) is None
        or type(current_attempt_limit) is not int
        or current_attempt_limit < 1
    ):
        raise OperatorError("current-head blocked-retry batch seal is invalid")

    entries = payload.get("entries")
    aliases = tuple(sorted(CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS))
    if not isinstance(entries, list) or len(entries) != len(aliases):
        raise OperatorError("current-head blocked-retry batch population is not exact")
    normalized: list[dict[str, Any]] = []
    required_entry = {
        "schema",
        "task_alias",
        "task_cid",
        "source_status",
        "source_revision",
        "target_status",
        "target_revision",
        "source_task_body",
        "source_task_body_id",
        "source_completion_receipt_id",
        "max_task_attempts_before",
        "max_task_attempts_after",
        "started_at_ms",
        "retry_not_before_ms",
        "sidecar_evidence",
        "sidecar_evidence_id",
    }
    for position, raw in enumerate(entries):
        if not isinstance(raw, Mapping) or set(raw) != required_entry:
            raise OperatorError("current-head blocked-retry entry fields are not exact")
        entry = dict(raw)
        alias = str(entry.get("task_alias") or "")
        if alias != aliases[position]:
            raise OperatorError(
                "current-head blocked-retry entries are not complete and ordered"
            )
        expected = CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS[alias]
        source_revision = _exact_int(
            entry.get("source_revision"),
            field=f"{alias} blocked-retry source_revision",
            minimum=1,
        )
        target_revision = _exact_int(
            entry.get("target_revision"),
            field=f"{alias} blocked-retry target_revision",
            minimum=2,
        )
        before = _exact_int(
            entry.get("max_task_attempts_before"),
            field=f"{alias} blocked-retry max_task_attempts_before",
            minimum=1,
        )
        after = _exact_int(
            entry.get("max_task_attempts_after"),
            field=f"{alias} blocked-retry max_task_attempts_after",
            minimum=2,
        )
        started_at_ms = _exact_int(
            entry.get("started_at_ms"),
            field=f"{alias} blocked-retry started_at_ms",
        )
        retry_not_before_ms = _exact_int(
            entry.get("retry_not_before_ms"),
            field=f"{alias} blocked-retry retry_not_before_ms",
        )
        task_body = entry.get("source_task_body")
        terminal_receipt = (
            task_body.get("completion_receipt")
            if isinstance(task_body, Mapping)
            else None
        )
        route = (
            terminal_receipt.get("execution_route_binding")
            if isinstance(terminal_receipt, Mapping)
            else None
        )
        sidecar_evidence = entry.get("sidecar_evidence")
        attempt_number = (
            terminal_receipt.get("attempt_number")
            if isinstance(terminal_receipt, Mapping)
            else None
        )
        text_attempt_fields = (
            "attempt_id",
            "claim_id",
            "lease_id",
            "owner_session_id",
        )
        integer_attempt_fields = ("fencing_token", "fence_epoch")
        if (
            entry.get("schema")
            != CURRENT_HEAD_BLOCKED_RETRY_BATCH_ENTRY_SCHEMA
            or entry.get("task_cid") != expected["task_cid"]
            or entry.get("source_status") != "blocked"
            or source_revision != expected["source_revision"]
            or entry.get("target_status") != "retrying"
            or target_revision != source_revision + 1
            or not isinstance(task_body, Mapping)
            or _identity(task_body) != expected["source_task_body_id"]
            or entry.get("source_task_body_id")
            != expected["source_task_body_id"]
            or not isinstance(terminal_receipt, Mapping)
            or _identity(terminal_receipt)
            != expected["source_completion_receipt_id"]
            or entry.get("source_completion_receipt_id")
            != expected["source_completion_receipt_id"]
            or terminal_receipt.get("operation")
            != "database_portal_terminal_failure"
            or terminal_receipt.get("reason")
            != CURRENT_HEAD_BLOCKED_RETRY_TERMINAL_REASON
            or terminal_receipt.get("retryable") is not False
            or terminal_receipt.get("control_expected_status") != "in_progress"
            or terminal_receipt.get("control_expected_revision")
            != source_revision - 1
            or type(attempt_number) is not int
            or attempt_number != expected["source_attempt_number"]
            or before != attempt_number
            or after != attempt_number + 1
            or current_attempt_limit < after
            or started_at_ms != retry_not_before_ms
            or not isinstance(sidecar_evidence, Mapping)
            or re.fullmatch(
                r"sha256:[0-9a-f]{64}",
                str(entry.get("sidecar_evidence_id") or ""),
            )
            is None
            or any(
                type(terminal_receipt.get(field)) is not str
                or not terminal_receipt.get(field)
                for field in text_attempt_fields
            )
            or any(
                type(terminal_receipt.get(field)) is not int
                or terminal_receipt.get(field) < 1
                for field in integer_attempt_fields
            )
            or not isinstance(route, Mapping)
            or route.get("task_alias") != alias
            or route.get("task_cid") != expected["task_cid"]
            or type(route.get("policy_id")) is not str
            or not route.get("policy_id")
            or type(route.get("task_revision")) is not int
            or route.get("task_revision") < 1
            or terminal_receipt.get("execution_route_policy_id")
            != route.get("policy_id")
            or terminal_receipt.get("execution_route_origin_revision")
            != route.get("task_revision")
        ):
            raise OperatorError(
                f"{alias} current-head blocked-retry predecessor is not exact"
            )
        verified_evidence = _verified_current_head_blocked_retry_evidence(
            sidecar_evidence,
            alias=alias,
            task_cid=str(expected["task_cid"]),
            terminal_receipt=terminal_receipt,
        )
        if _identity(verified_evidence) != entry.get("sidecar_evidence_id"):
            raise OperatorError(
                f"{alias} current-head blocked-retry evidence identity changed"
            )
        entry["sidecar_evidence"] = verified_evidence
        normalized.append(entry)

    verified = dict(payload)
    verified["entries"] = normalized
    return verified


def _verify_current_head_blocked_retry_live_sidecars(
    batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Reproduce the sealed Portal bindings and protected-path incidents."""

    entries = batch.get("entries")
    if not isinstance(entries, list):
        raise OperatorError("current-head blocked-retry entries are absent")
    observations: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise OperatorError("current-head blocked-retry entry is malformed")
        alias = str(entry.get("task_alias") or "")
        task_cid = str(entry.get("task_cid") or "")
        evidence = entry.get("sidecar_evidence")
        if not isinstance(evidence, Mapping):
            raise OperatorError(f"{alias} blocked-retry sidecar evidence is absent")
        binding_path = _safe_path(
            ROOT,
            evidence.get("database_attempt_binding_path"),
            field=f"{alias} database attempt binding path",
        )
        incident_path = _safe_path(
            ROOT,
            evidence.get("protected_path_incident_path"),
            field=f"{alias} protected-path incident path",
        )
        try:
            binding_bytes = binding_path.read_bytes()
            incident_bytes = incident_path.read_bytes()
        except OSError as exc:
            raise OperatorError(
                f"{alias} blocked-retry live sidecar evidence is absent"
            ) from exc
        binding = _json_mapping_bytes(
            binding_bytes,
            field=f"{alias} database attempt binding",
        )
        incident = _json_mapping_bytes(
            incident_bytes,
            field=f"{alias} protected-path incident",
        )
        attempt = evidence.get("attempt_identity")
        if not isinstance(attempt, Mapping):
            raise OperatorError(f"{alias} attempt identity is absent")
        if (
            _identity(binding_bytes)
            != evidence.get("database_attempt_binding_bytes_id")
            or binding.get("binding_id")
            != evidence.get("database_attempt_binding_id")
            or binding.get("schema")
            != "ipfs_accelerate_py/agent-supervisor/database-portal-attempt-binding@1"
            or binding.get("task_alias") != alias
            or binding.get("task_cid") != task_cid
            or binding.get("canonical_task_key") != task_cid
            or binding.get("projection_authority") is not False
            or any(
                binding.get(field) != attempt.get(field)
                for field in (
                    "attempt_id",
                    "attempt_number",
                    "claim_id",
                    "lease_id",
                    "owner_session_id",
                    "fencing_token",
                    "fence_epoch",
                )
            )
            or _identity(incident_bytes)
            != evidence.get("protected_path_incident_bytes_id")
            or _identity(incident)
            != evidence.get("protected_path_incident_identity")
            or incident.get("schema")
            != "implementation-protected-path-incident-v1"
            or incident.get("task_id") != alias
            or incident.get("reason") != "implementation_protected_path_mutated"
            or incident.get("requires_operator_clearance") is not True
            or incident.get("shared_checkout_restored") is not False
            or incident.get("protected_paths")
            != ["config/proof_carrying_semantic_minification_v1_supervisor.json"]
            or incident.get("canonical_task_cid")
            != evidence.get("projected_portal_task_cid")
            or incident.get("canonical_task_key")
            != evidence.get("projected_portal_task_key")
            or incident.get("attempt")
            != evidence.get("portal_implementation_attempt")
        ):
            raise OperatorError(
                f"{alias} blocked-retry live sidecar evidence changed"
            )
        observations.append(
            {
                "task_alias": alias,
                "task_cid": task_cid,
                "lane_index": evidence["lane_index"],
                "database_attempt_binding_bytes_id": _identity(binding_bytes),
                "protected_path_incident_bytes_id": _identity(incident_bytes),
                "rescue_commit": evidence["rescue_commit"],
                "merge_commit": evidence["merge_commit"],
            }
        )
    return {
        "verified_count": len(observations),
        "observations": observations,
    }


def _current_head_blocked_retry_expected_task_body(
    *,
    entry: Mapping[str, Any],
    batch_receipt_id: str,
) -> dict[str, Any]:
    """Derive the exact retrying body, including its durable Portal guard."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TYPED_DATABASE_BLOCKED_RETRY_REVALIDATION_FIELD,
        typed_database_blocked_retry_revalidation_requirement,
    )

    task_body = entry.get("source_task_body")
    terminal_receipt = (
        task_body.get("completion_receipt")
        if isinstance(task_body, Mapping)
        else None
    )
    route = (
        terminal_receipt.get("execution_route_binding")
        if isinstance(terminal_receipt, Mapping)
        else None
    )
    if (
        not isinstance(task_body, Mapping)
        or not isinstance(terminal_receipt, Mapping)
        or not isinstance(route, Mapping)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", batch_receipt_id) is None
    ):
        raise OperatorError("current-head blocked-retry expected body is invalid")
    source_revision = int(entry["source_revision"])
    fresh_attempt_number = int(entry["max_task_attempts_after"])
    source_receipt_id = str(entry["source_completion_receipt_id"])
    sidecar_evidence_id = str(entry["sidecar_evidence_id"])
    retry_not_before_ms = int(entry["retry_not_before_ms"])
    recovery_receipt = {
        "schema": TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_SCHEMA,
        "operation": HANDOFF_REPAIR_BLOCKED_RETRY_OPERATION,
        **{
            field: terminal_receipt[field]
            for field in (
                "attempt_id",
                "claim_id",
                "lease_id",
                "owner_session_id",
                "attempt_number",
                "fencing_token",
                "fence_epoch",
            )
        },
        "terminal_operation": terminal_receipt["operation"],
        "terminal_reason": terminal_receipt["reason"],
        "source_completion_receipt_id": source_receipt_id,
        "operator_handoff_receipt_id": batch_receipt_id,
        "sidecar_evidence_id": sidecar_evidence_id,
        "recovered_from_revision": source_revision,
        "max_task_attempts_before": entry["max_task_attempts_before"],
        "max_task_attempts_after": fresh_attempt_number,
        "attempt_refunded": False,
        "fresh_attempt_number": fresh_attempt_number,
        "queue_reason": HANDOFF_REPAIR_BLOCKED_RETRY_REASON,
        "backoff_ms": 0,
        "retry_not_before_ms": retry_not_before_ms,
        "control_expected_status": "blocked",
        "control_expected_revision": source_revision,
        "execution_route_binding": dict(route),
        "execution_route_binding_cid": _semantic_identity(
            {"task_execution_route_binding": dict(route)}
        ),
        "execution_route_policy_id": route["policy_id"],
        "execution_route_origin_revision": route["task_revision"],
    }
    requirement = typed_database_blocked_retry_revalidation_requirement(
        task_cid=str(entry["task_cid"]),
        source_completion_receipt_id=source_receipt_id,
        operator_handoff_receipt_id=batch_receipt_id,
        sidecar_evidence_id=sidecar_evidence_id,
        recovered_from_revision=source_revision,
        fresh_attempt_number=fresh_attempt_number,
    )
    expected = dict(task_body)
    expected["completion_receipt"] = recovery_receipt
    expected[TYPED_DATABASE_BLOCKED_RETRY_REVALIDATION_FIELD] = requirement
    return expected


def _apply_current_head_blocked_retry_entry(
    *,
    server: Any,
    board: Any,
    batch_receipt_id: str,
    entry: Mapping[str, Any],
    blocked_retry_state: str,
) -> dict[str, Any]:
    """Submit/replay one independently granted member of the verified batch."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client import (
        QuackStateClient,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TypedStateOwnerConnection,
    )

    identity = server.identity
    if identity is None:
        raise OperatorError("state owner has no current-head blocked-retry identity")
    alias = str(entry.get("task_alias") or "")
    task_cid = str(entry.get("task_cid") or "")
    task_body = entry.get("source_task_body")
    terminal_receipt = (
        task_body.get("completion_receipt")
        if isinstance(task_body, Mapping)
        else None
    )
    if (
        alias not in CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS
        or task_cid
        != CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS[alias]["task_cid"]
        or blocked_retry_state
        not in {"pending_apply", "command_replay_required"}
        or not isinstance(task_body, Mapping)
        or not isinstance(terminal_receipt, Mapping)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", batch_receipt_id) is None
    ):
        raise OperatorError("current-head blocked-retry command inputs are not exact")
    expected_task_body = _current_head_blocked_retry_expected_task_body(
        entry=entry,
        batch_receipt_id=batch_receipt_id,
    )
    revalidation_requirement = expected_task_body.get(
        "fresh_portal_revalidation_requirement"
    )
    if not isinstance(revalidation_requirement, Mapping):
        raise OperatorError(
            "current-head blocked-retry command has no fresh Portal guard"
        )

    client_id = f"pcsm-state-owner:blocked-retry-batch:{alias.lower()}"
    allowed_operations = (
        "whoami_metadata",
        "load_store_generation",
        "executor_retry_cooldown_by_task",
        "txn_load_generation",
        "txn_lookup_idempotency",
        "txn_advance_store_revision",
        "txn_record_idempotency",
        "executor_insert_retry_cooldown",
        "executor_cas_task_status_receipt",
        "executor_insert_task_revision",
    )
    store_id = _control_plane_store_id(board.resolved_database_program())
    token, grant = server.issue_typed_client_grant_record(
        client_id=client_id,
        process_birth_id=identity.process_birth_id,
        allowed_operations=allowed_operations,
        allowed_command_operations=(HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND,),
        entity_scopes={"task_cid": task_cid},
        peer_pid=os.getpid(),
        ttl_seconds=60.0,
    )
    client: Any | None = None
    try:
        client = QuackStateClient(
            owner_id=client_id,
            store_id=store_id,
            process_birth_id=identity.process_birth_id,
            connection_factory=lambda _endpoint: TypedStateOwnerConnection(
                socket_path=server.typed_command_socket_path(),
                token=token,
                client_id=client_id,
                process_birth_id=identity.process_birth_id,
                store_id=store_id,
            ),
        )
        client.attach(
            board.resolved_database_program().quack_endpoint,
            server_id=identity.server_id,
        )
        generation_before = client.load_generation()
        result = client.recover_blocked_task_retry(
            task_cid=task_cid,
            expected_task_revision=int(entry["source_revision"]),
            task_body=dict(task_body),
            terminal_receipt=dict(terminal_receipt),
            max_task_attempts_before=int(entry["max_task_attempts_before"]),
            max_task_attempts_after=int(entry["max_task_attempts_after"]),
            operator_handoff_receipt_id=batch_receipt_id,
            sidecar_evidence_id=str(entry["sidecar_evidence_id"]),
            now_ms=int(entry["started_at_ms"]),
            require_fresh_portal_revalidation=True,
        )
        generation_after = client.load_generation()
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            server.revoke_typed_client_grant(grant.grant_id)

    outcome = result.outcome.value
    expected_outcome = (
        "accepted"
        if blocked_retry_state == "pending_apply"
        else "idempotent_replay"
    )
    route = terminal_receipt["execution_route_binding"]
    result_body = dict(result.result)
    store_revision_before = result_body.get("store_revision_before")
    expected_result = {
        "schema": TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_SCHEMA,
        "operation": HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND,
        "task_cid": task_cid,
        "attempt_id": terminal_receipt["attempt_id"],
        "attempt_number": terminal_receipt["attempt_number"],
        "fresh_attempt_number": entry["max_task_attempts_after"],
        "task_revision": entry["target_revision"],
        "queue_revision": 1,
        "retry_not_before_ms": entry["retry_not_before_ms"],
        "source_completion_receipt_id": entry[
            "source_completion_receipt_id"
        ],
        "operator_handoff_receipt_id": batch_receipt_id,
        "sidecar_evidence_id": entry["sidecar_evidence_id"],
        "max_task_attempts_before": entry["max_task_attempts_before"],
        "max_task_attempts_after": entry["max_task_attempts_after"],
        "attempt_refunded": False,
        "execution_route_binding_cid": _semantic_identity(
            {"task_execution_route_binding": dict(route)}
        ),
        "execution_route_policy_id": route["policy_id"],
        "execution_route_origin_revision": route["task_revision"],
        "store_revision_before": store_revision_before,
        "fresh_portal_revalidation_requirement_id": (
            revalidation_requirement["requirement_id"]
        ),
    }
    command_prefix = "cmd:blocked-retry-recovery:"
    command_digest = result.command_id.removeprefix(command_prefix)
    if (
        outcome != expected_outcome
        or result.changed is not (blocked_retry_state == "pending_apply")
        or result.conflict_kind is not None
        or result_body != expected_result
        or type(store_revision_before) is not int
        or store_revision_before < 0
        or not result.command_id.startswith(command_prefix)
        or re.fullmatch(r"[0-9a-f]{64}", command_digest) is None
        or result.idempotency_key
        != f"executor-blocked-retry-recovery:{command_digest}"
        or result.result_digest != _identity(result_body)
        or generation_before.generation != int(identity.generation)
        or generation_before.fence_epoch != int(identity.fence_epoch)
        or generation_after.generation != int(identity.generation)
        or generation_after.fence_epoch != int(identity.fence_epoch)
        or result.generation != generation_after.generation
        or result.fence_epoch != generation_after.fence_epoch
        or result.revision != generation_after.revision
        or (
            blocked_retry_state == "pending_apply"
            and (
                generation_before.revision != store_revision_before
                or generation_after.revision != store_revision_before + 1
            )
        )
        or (
            blocked_retry_state == "command_replay_required"
            and generation_after.to_dict() != generation_before.to_dict()
        )
    ):
        raise OperatorError(
            f"{alias} current-head blocked-retry command was not exactly admitted"
        )
    return {
        "task_alias": alias,
        "task_cid": task_cid,
        "post_recovery_requirement": (
            CURRENT_HEAD_BLOCKED_RETRY_POST_RECOVERY_REQUIREMENT
        ),
        "expected_retrying_task_body_id": _identity(expected_task_body),
        "fresh_portal_revalidation_requirement_id": (
            revalidation_requirement["requirement_id"]
        ),
        "authorization": {
            "client_id": client_id,
            "process_birth_id": identity.process_birth_id,
            "peer_pid": os.getpid(),
            "allowed_operations": list(allowed_operations),
            "allowed_command_operations": [HANDOFF_REPAIR_BLOCKED_RETRY_COMMAND],
            "entity_scopes": {"task_cid": task_cid},
            "revoked": True,
        },
        "command": result.to_dict(),
    }


def _apply_current_head_blocked_retry_batch(
    *,
    server: Any,
    board: Any,
    handoff: Any,
    sealed_source_head: str,
    sealed_source_tree: str,
    current_attempt_limit: int,
    blocked_retry_states: Mapping[str, str],
) -> dict[str, Any]:
    """Apply an exact four-task batch; mixed-prefix replay is intentional."""

    verified = _verified_current_head_blocked_retry_batch(
        handoff,
        sealed_source_head=sealed_source_head,
        sealed_source_tree=sealed_source_tree,
        current_attempt_limit=current_attempt_limit,
    )
    aliases = tuple(sorted(CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS))
    if (
        not isinstance(blocked_retry_states, Mapping)
        or set(blocked_retry_states) != set(aliases)
        or any(
            blocked_retry_states[alias]
            not in {"pending_apply", "command_replay_required"}
            for alias in aliases
        )
    ):
        raise OperatorError("current-head blocked-retry batch states are not exact")

    recoveries: list[dict[str, Any]] = []
    for entry in verified["entries"]:
        alias = str(entry["task_alias"])
        recoveries.append(
            _apply_current_head_blocked_retry_entry(
                server=server,
                board=board,
                batch_receipt_id=str(verified["batch_receipt_id"]),
                entry=entry,
                blocked_retry_state=str(blocked_retry_states[alias]),
            )
        )
    return {
        "schema": CURRENT_HEAD_BLOCKED_RETRY_BATCH_RESULT_SCHEMA,
        "operation": CURRENT_HEAD_BLOCKED_RETRY_BATCH_OPERATION,
        "batch_receipt_id": verified["batch_receipt_id"],
        "source_head": sealed_source_head,
        "repository_tree_id": sealed_source_tree,
        "recovery_count": len(recoveries),
        "post_recovery_requirement": (
            CURRENT_HEAD_BLOCKED_RETRY_POST_RECOVERY_REQUIREMENT
        ),
        "recoveries": recoveries,
    }


def _verify_continued_route_sidecars(
    *,
    board: Any,
    paths: Mapping[str, Path],
    continuation: Mapping[str, Any],
    stable_authority: Mapping[str, Any],
    blocked_retry_handoff: Mapping[str, Any] | None = None,
    blocked_retry_state: str = "",
    recovery_callback: Any | None = None,
) -> dict[str, Any]:
    """Fence every lane sidecar while applying the one sealed owner recovery."""

    try:
        import duckdb
    except Exception as exc:
        raise OperatorError("continued route sidecar verifier requires DuckDB") from exc

    expected_binding = str(continuation.get("stable_binding_id") or "")
    expected_lock = (expected_binding + "\n").encode("utf-8")
    lane_count = _exact_int(
        continuation.get("lane_count"),
        field="continued route lane_count",
        minimum=1,
    )
    if lane_count != int(board.max_lanes) or expected_binding != _semantic_identity(
        stable_authority
    ):
        raise OperatorError("continued route stable authority differs from its seal")

    held: list[int] = []
    sidecar_paths: list[tuple[int, Path, Path]] = []
    try:
        for lane_index in range(lane_count):
            lane = paths["runtime"] / "state" / f"lane-{lane_index}"
            _ensure_private_runtime_directory(lane)
            prefix = f"pcsm_lane_{lane_index}_database"
            coordination = lane / f"{prefix}_coordination.duckdb"
            execution = lane / f"{prefix}_execution.duckdb"
            for sidecar in (coordination, execution):
                lock_path = sidecar.with_name(f".{sidecar.name}.writer.lock")
                held.append(_acquire_exact_sidecar_lock(lock_path, expected_lock))
            sidecar_paths.append((lane_index, coordination, execution))

        observations: list[dict[str, Any]] = []
        for lane_index, coordination, execution in sidecar_paths:
            coordination_stat = coordination.lstat()
            before = execution.lstat()
            if (
                not stat_module.S_ISREG(coordination_stat.st_mode)
                or coordination_stat.st_uid != os.geteuid()
                or coordination_stat.st_nlink != 1
                or stat_module.S_IMODE(coordination_stat.st_mode) != 0o600
                or not stat_module.S_ISREG(before.st_mode)
                or before.st_uid != os.geteuid()
                or before.st_nlink != 1
                or stat_module.S_IMODE(before.st_mode) != 0o600
            ):
                raise OperatorError(
                    "continued route sidecar is not an exact private file"
                )
            connection = None
            try:
                connection = duckdb.connect(str(execution), read_only=True)
                rows = connection.execute(
                    "SELECT key, value FROM daemon_execution_metadata "
                    "WHERE key IN "
                    "('typed_quack_stable_binding_id', "
                    "'typed_quack_stable_authority') ORDER BY key"
                ).fetchall()
                metadata = {str(key): str(value) for key, value in rows}
                status_rows = connection.execute(
                    "SELECT status, count(*) FROM database_task_attempts "
                    "GROUP BY status ORDER BY status LIMIT 32"
                ).fetchall()
            except Exception as exc:
                raise OperatorError(
                    "continued route execution sidecar cannot be verified"
                ) from exc
            finally:
                if connection is not None:
                    connection.close()
            after = execution.lstat()
            try:
                observed_authority = json.loads(
                    metadata.get("typed_quack_stable_authority", "")
                )
            except json.JSONDecodeError as exc:
                raise OperatorError(
                    "continued route sidecar authority is malformed"
                ) from exc
            if (
                set(metadata)
                != {
                    "typed_quack_stable_authority",
                    "typed_quack_stable_binding_id",
                }
                or metadata.get("typed_quack_stable_binding_id") != expected_binding
                or not isinstance(observed_authority, dict)
                or observed_authority != dict(stable_authority)
                or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
            ):
                raise OperatorError("continued route execution sidecar changed authority")
            observations.append(
                {
                    "lane_index": lane_index,
                    "attempt_status_counts": {
                        str(status): int(count) for status, count in status_rows
                    },
                }
            )

        if not isinstance(blocked_retry_handoff, Mapping):
            raise OperatorError("continued route has no blocked-retry handoff")
        if blocked_retry_state == "pending_apply":
            lane_zero = next(
                (
                    (coordination, execution)
                    for lane_index, coordination, execution in sidecar_paths
                    if lane_index == 0
                ),
                None,
            )
            if lane_zero is None:
                raise OperatorError("blocked-retry lane-0 sidecars are absent")
            sealed_evidence = _verify_blocked_retry_sidecar_evidence(
                blocked_retry_handoff=blocked_retry_handoff,
                coordination_path=lane_zero[0],
                execution_path=lane_zero[1],
            )
        elif blocked_retry_state == "command_replay_required":
            existing = blocked_retry_handoff.get("sidecar_evidence")
            if not isinstance(existing, Mapping):
                raise OperatorError("blocked-retry sealed evidence is absent")
            sealed_evidence = dict(existing)
        else:
            raise OperatorError("blocked-retry handoff state is not closed")
        if not callable(recovery_callback):
            raise OperatorError("blocked-retry recovery callback is absent")
        recovery = recovery_callback(
            blocked_retry_state=blocked_retry_state,
            sidecar_evidence=sealed_evidence,
        )
        if not isinstance(recovery, Mapping):
            raise OperatorError("blocked-retry recovery result is malformed")
        return {
            "stable_binding_id": expected_binding,
            "writer_lock_count": len(held),
            "execution_metadata_count": len(observations),
            "lanes": observations,
            "blocked_retry": {
                "handoff_state": blocked_retry_state,
                "sidecar_evidence_id": str(
                    sealed_evidence.get("evidence_id") or ""
                ),
                "recovery": dict(recovery),
            },
        }
    except FileNotFoundError as exc:
        raise OperatorError("continued route sidecar evidence is absent") from exc
    finally:
        for descriptor in reversed(held):
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


class _ExecutionRoutePolicyProvider:
    """Seal bootstrap tasks or continue the one receipt-bound route epoch."""

    def __init__(
        self,
        *,
        server: Any,
        board: Any,
        restart_admission: Mapping[str, Any],
    ) -> None:
        self.server = server
        self.board = board
        self.restart_admission = dict(restart_admission)
        self.database_verification: dict[str, Any] = {}
        self._lock = threading.Lock()

    def seal(self) -> Any:
        from ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client import (
            QuackStateClient,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.task_execution_route_policy import (
            GROK_CODEX_EXECUTION_MODE,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.typed_database_task_source import (
            TypedDatabaseTaskSource,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
            TypedStateOwnerConnection,
        )

        with self._lock:
            identity = self.server.identity
            if identity is None:
                raise OperatorError("state owner has no route-policy identity")
            client_id = "pcsm-state-owner:execution-route-policy"
            store_id = _control_plane_store_id(
                self.board.resolved_database_program()
            )
            allowed_operations = (
                "whoami_metadata",
                "load_store_generation",
                "executor_control_snapshot",
                "executor_task_projection_page",
                "executor_task_projection_by_identity",
                "executor_retry_cooldown_by_task",
            )
            token, grant = self.server.issue_typed_client_grant_record(
                client_id=client_id,
                process_birth_id=identity.process_birth_id,
                allowed_operations=allowed_operations,
                peer_pid=os.getpid(),
                ttl_seconds=300.0,
            )
            client = QuackStateClient(
                owner_id=client_id,
                store_id=store_id,
                process_birth_id=identity.process_birth_id,
                connection_factory=lambda _endpoint: TypedStateOwnerConnection(
                    socket_path=self.server.typed_command_socket_path(),
                    token=token,
                    client_id=client_id,
                    process_birth_id=identity.process_birth_id,
                    store_id=store_id,
                ),
            )
            try:
                client.attach(
                    self.board.resolved_database_program().quack_endpoint,
                    server_id=identity.server_id,
                )
                with TypedDatabaseTaskSource(client, owns_client=True) as source:
                    page = source.list_tasks(limit=500)
                    if page.next_cursor:
                        raise OperatorError(
                            "execution route exceeds the bounded typed task page"
                        )
                    modes = {
                        task.task_alias: GROK_CODEX_EXECUTION_MODE
                        for task in page.tasks
                    }
                    if self.restart_admission.get("mode") == "exact_bootstrap":
                        self.database_verification = _restart_database_verification(
                            source,
                            self.restart_admission,
                        )
                        return source.seal_execution_route_policy(modes)

                    repair = self.restart_admission.get("handoff_repair")
                    continuation = (
                        repair.get("execution_route_continuation")
                        if isinstance(repair, Mapping)
                        else None
                    )
                    if not isinstance(continuation, Mapping):
                        raise OperatorError(
                            "verified handoff has no execution-route continuation"
                        )
                    policy, advanced = _continued_execution_route_policy(
                        page.tasks,
                        continuation,
                    )
                    with TypedDatabaseTaskSource(
                        client,
                        execution_route_policy=policy,
                        owns_client=False,
                    ) as continued_source:
                        continued_page = continued_source.list_tasks(limit=500)
                        if (
                            continued_page.next_cursor
                            or tuple(task.task_cid for task in continued_page.tasks)
                            != tuple(task.task_cid for task in page.tasks)
                        ):
                            raise OperatorError(
                                "continued execution route changed task population"
                            )
                        for task in continued_page.tasks:
                            if int(task.revision) > int(
                                continuation.get("origin_task_revision") or 0
                            ):
                                continued_source.execution_route_binding_for_task(task)
                        self.database_verification = _restart_database_verification(
                            continued_source,
                            self.restart_admission,
                        )
                        repair_projection = self.database_verification.get(
                            "repair_source_task"
                        )
                        blocked_retry = repair.get("blocked_retry_handoff")
                        if (
                            not isinstance(repair_projection, Mapping)
                            or not isinstance(blocked_retry, Mapping)
                        ):
                            raise OperatorError(
                                "continued route has no blocked-retry projection"
                            )
                        blocked_retry_state = str(
                            repair_projection.get(
                                "blocked_retry_handoff_state"
                            )
                            or ""
                        )

                        session = client.session
                        store_identity = (
                            session.store_identity
                            if session is not None
                            else None
                        )
                        if store_identity is None:
                            raise OperatorError(
                                "continued execution route has no store identity"
                            )
                        stable_authority = {
                            "interface": (
                                "TypedDatabaseTaskSourceStableQuackAuthority@1"
                            ),
                            "store_id": store_identity.store_id,
                            "database_uuid": store_identity.database_uuid,
                            "schema_fingerprint": (
                                store_identity.schema_fingerprint
                            ),
                            "repository_id": store_identity.repository_id,
                            "schema_revision": int(
                                store_identity.schema_revision
                            ),
                            "route_policy_id": policy.policy_id,
                            "plan_root_cid": policy.plan_root_cid,
                            "repository_tree_id": policy.repository_tree_id,
                            "source_projection_cid": (
                                policy.source_projection_cid
                            ),
                        }
                        if stable_authority != dict(
                            continuation.get("stable_authority") or {}
                        ) or _semantic_identity(stable_authority) != str(
                            continuation.get("stable_binding_id") or ""
                        ):
                            raise OperatorError(
                                "continued execution route differs from live "
                                "store authority"
                            )

                        def recover_while_fenced(
                            *,
                            blocked_retry_state: str,
                            sidecar_evidence: Mapping[str, Any],
                        ) -> dict[str, Any]:
                            command_result = _apply_blocked_retry_recovery(
                                server=self.server,
                                board=self.board,
                                repair=repair,
                                blocked_retry_handoff=blocked_retry,
                                blocked_retry_state=blocked_retry_state,
                                sidecar_evidence=sidecar_evidence,
                            )
                            post_verification = (
                                _restart_database_verification(
                                    continued_source,
                                    self.restart_admission,
                                )
                            )
                            post_repair = post_verification.get(
                                "repair_source_task"
                            )
                            if (
                                not isinstance(post_repair, Mapping)
                                or post_repair.get(
                                    "blocked_retry_handoff_state"
                                )
                                != "command_replay_required"
                                or (
                                    blocked_retry_state == "pending_apply"
                                    and (
                                        post_repair.get("status")
                                        != blocked_retry.get("target_status")
                                        or post_repair.get("revision")
                                        != blocked_retry.get("target_revision")
                                        or post_repair.get(
                                            "receipt_operation"
                                        )
                                        != HANDOFF_REPAIR_BLOCKED_RETRY_OPERATION
                                    )
                                )
                            ):
                                raise OperatorError(
                                    "blocked-retry post-command task state is "
                                    "not exact"
                                )
                            batch_recovery: dict[str, Any] = {}
                            if self.restart_admission.get("mode") == (
                                "verified_current_head_blocked_retry_batch"
                            ):
                                descendant = self.restart_admission.get(
                                    "current_head_descendant_repair"
                                )
                                batch = (
                                    descendant.get("blocked_retry_batch")
                                    if isinstance(descendant, Mapping)
                                    else None
                                )
                                sealed_source_head = (
                                    descendant.get("sealed_source_head")
                                    if isinstance(descendant, Mapping)
                                    else None
                                )
                                sealed_source_tree = (
                                    descendant.get("sealed_source_tree")
                                    if isinstance(descendant, Mapping)
                                    else None
                                )
                                initial_states = self.database_verification.get(
                                    "current_head_blocked_retry_states"
                                )
                                pre_batch_states = post_verification.get(
                                    "current_head_blocked_retry_states"
                                )
                                if (
                                    not isinstance(batch, Mapping)
                                    or not isinstance(initial_states, Mapping)
                                    or dict(pre_batch_states or {})
                                    != dict(initial_states)
                                    or re.fullmatch(
                                        r"[0-9a-f]{40}",
                                        str(sealed_source_head or ""),
                                    )
                                    is None
                                    or re.fullmatch(
                                        r"[0-9a-f]{40}",
                                        str(sealed_source_tree or ""),
                                    )
                                    is None
                                ):
                                    raise OperatorError(
                                        "blocked-retry batch changed before its fence"
                                    )
                                live_sidecars = (
                                    _verify_current_head_blocked_retry_live_sidecars(
                                        batch
                                    )
                                )
                                owner_batch = (
                                    _apply_current_head_blocked_retry_batch(
                                        server=self.server,
                                        board=self.board,
                                        handoff=batch,
                                        sealed_source_head=str(
                                            sealed_source_head
                                        ),
                                        sealed_source_tree=str(
                                            sealed_source_tree
                                        ),
                                        current_attempt_limit=int(
                                            self.restart_admission.get(
                                                "max_task_attempts_after"
                                            )
                                            or 0
                                        ),
                                        blocked_retry_states=initial_states,
                                    )
                                )
                                post_verification = (
                                    _restart_database_verification(
                                        continued_source,
                                        self.restart_admission,
                                    )
                                )
                                final_states = post_verification.get(
                                    "current_head_blocked_retry_states"
                                )
                                if (
                                    not isinstance(final_states, Mapping)
                                    or set(final_states)
                                    != set(CURRENT_HEAD_BLOCKED_RETRY_EXPECTATIONS)
                                    or any(
                                        state != "command_replay_required"
                                        for state in final_states.values()
                                    )
                                ):
                                    raise OperatorError(
                                        "blocked-retry batch did not reach exact replay state"
                                    )
                                batch_recovery = {
                                    "live_sidecars": live_sidecars,
                                    "owner_commands": owner_batch,
                                }
                            post_page = continued_source.list_tasks(limit=500)
                            if (
                                post_page.next_cursor
                                or tuple(
                                    task.task_cid for task in post_page.tasks
                                )
                                != tuple(
                                    task.task_cid
                                    for task in continued_page.tasks
                                )
                            ):
                                raise OperatorError(
                                    "blocked-retry recovery changed the task "
                                    "population"
                                )
                            post_policy, post_advanced = (
                                _continued_execution_route_policy(
                                    post_page.tasks,
                                    continuation,
                                )
                            )
                            if (
                                post_policy.policy_id != policy.policy_id
                                or post_policy.public_summary()
                                != policy.public_summary()
                                or post_policy.source_projection_cid
                                != policy.source_projection_cid
                            ):
                                raise OperatorError(
                                    "blocked-retry recovery changed the carried "
                                    "execution route"
                                )
                            return {
                                "owner_command": command_result,
                                "current_head_blocked_retry_batch": batch_recovery,
                                "database_verification": post_verification,
                                "execution_route_policy": (
                                    post_policy.public_summary()
                                ),
                                "advanced_tasks": post_advanced,
                            }

                        sidecars = _verify_continued_route_sidecars(
                            board=self.board,
                            paths=_runtime_paths(self.board),
                            continuation=continuation,
                            stable_authority=stable_authority,
                            blocked_retry_handoff=blocked_retry,
                            blocked_retry_state=blocked_retry_state,
                            recovery_callback=recover_while_fenced,
                        )
                        recovery = (
                            sidecars.get("blocked_retry", {}).get(
                                "recovery"
                            )
                            if isinstance(
                                sidecars.get("blocked_retry"), Mapping
                            )
                            else None
                        )
                        if (
                            not isinstance(recovery, Mapping)
                            or not isinstance(
                                recovery.get("database_verification"),
                                Mapping,
                            )
                            or not isinstance(
                                recovery.get("advanced_tasks"), list
                            )
                        ):
                            raise OperatorError(
                                "blocked-retry post-command evidence is absent"
                            )
                        self.database_verification = dict(
                            recovery["database_verification"]
                        )
                        advanced = list(recovery["advanced_tasks"])

                        verification_body = dict(
                            self.database_verification
                        )
                        verification_body.pop("verification_id", None)
                        verification_body[
                            "execution_route_continuation"
                        ] = {
                            "schema": (
                                HANDOFF_EXECUTION_ROUTE_CONTINUATION_SCHEMA
                            ),
                            "policy": policy.public_summary(),
                            "source_projection_cid": (
                                policy.source_projection_cid
                            ),
                            "advanced_tasks": advanced,
                            "sidecars": sidecars,
                        }
                        verification_body["verification_id"] = _identity(
                            verification_body
                        )
                        self.database_verification = verification_body
                        return policy
            finally:
                try:
                    client.close()
                finally:
                    self.server.revoke_typed_client_grant(grant.grant_id)


class _ExecutorBootstrapBroker:
    """Issue distinct exact-birth typed grants to the four canonical lanes."""

    def __init__(
        self,
        *,
        channel: socket.socket,
        server: Any,
        board: Any,
        paths: Mapping[str, Path],
        initial_execution_route_policy: Any,
    ) -> None:
        self.channel = channel
        self.server = server
        self.board = board
        self.paths = paths
        self.execution_route_policy = initial_execution_route_policy
        self.allowed_client_ids = _executor_client_ids(board)
        self.allowed_supervisor_client_ids = frozenset(
            _supervisor_client_bindings(board)
        )
        self.stopping = threading.Event()
        self.failure = ""
        self._accepted: socket.socket | None = None
        self._lock = threading.Lock()
        self._grants: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._thread = threading.Thread(
            target=self._run,
            name="pcsm-executor-bootstrap",
            daemon=True,
        )

    @property
    def evidence_path(self) -> Path:
        return self.paths["runtime"] / "evidence" / "runtime" / "executor-bootstrap.json"

    def start(self) -> None:
        self._thread.start()

    def _fail(self, exc: BaseException | str) -> None:
        self.failure = exc if isinstance(exc, str) else type(exc).__name__
        master_pid_path = (
            self.paths["runtime"] / "state" / "configured-board-master.pid"
        )
        deadline = time.monotonic() + 10.0
        while not self.stopping.is_set() and time.monotonic() < deadline:
            if _read_pid(master_pid_path) == os.getpid():
                os.kill(os.getpid(), signal.SIGTERM)
                return
            time.sleep(0.05)

    def stop(self) -> None:
        self.stopping.set()
        with self._lock:
            accepted = self._accepted
        if accepted is not None:
            try:
                accepted.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                accepted.close()
            except OSError:
                pass
        try:
            self.channel.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.channel.close()
        except OSError:
            pass
        self._thread.join(timeout=5.0)
        with self._lock:
            grants = tuple(self._grants.values())
            self._grants.clear()
        for item in grants:
            grant_id = str(item.get("grant_id") or "")
            if grant_id:
                self.server.revoke_typed_client_grant(grant_id)
        if self._thread.is_alive():
            raise OperatorError("executor bootstrap broker did not stop")

    def _validate_parent(
        self,
        *,
        peer_pid: int,
        bootstrap_fd: int,
        client_id: str,
    ) -> None:
        from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
            read_process_birth,
        )

        executor_bindings = _executor_client_bindings(self.board)
        supervisor_bindings = _supervisor_client_bindings(self.board)
        is_executor = client_id in executor_bindings
        lane_index = (
            executor_bindings.get(client_id)
            if is_executor
            else supervisor_bindings.get(client_id)
        )
        if lane_index is None:
            raise OperatorError("bootstrap client has no admitted lane binding")
        peer_birth = read_process_birth(peer_pid)
        if peer_birth is None or int(peer_birth.parent_pid) <= 1:
            raise OperatorError("bootstrap peer has no live supervisor ancestry")
        if is_executor:
            supervisor_pid = int(peer_birth.parent_pid)
            supervisor_birth = read_process_birth(supervisor_pid)
            if supervisor_birth is None or int(supervisor_birth.parent_pid) != os.getpid():
                raise OperatorError(
                    "executor is outside the admitted multi-supervisor tree"
                )
        else:
            supervisor_pid = peer_pid
            if int(peer_birth.parent_pid) != os.getpid():
                raise OperatorError(
                    "supervisor is outside the admitted multi-supervisor tree"
                )
        argv = _process_argv(supervisor_pid)
        expected_entry = str(
            (ROOT / "scripts/ops/agent_supervisor/implementation_supervisor_entry.py")
            .resolve()
        )
        if expected_entry not in argv:
            raise OperatorError("executor parent is not the configured supervisor entry")
        if _argv_values(argv, "--board-namespace") != (self.board.board_namespace,):
            raise OperatorError("executor parent board namespace differs")
        if _argv_values(argv, "--state-owner-bootstrap-fd") != (str(bootstrap_fd),):
            raise OperatorError("executor parent bootstrap descriptor differs")
        owner_session_id = client_id.removeprefix(
            "database-implementation-daemon:"
            if is_executor
            else "database-implementation-supervisor:"
        )
        expected_count = str(max(1, int(self.board.max_lanes)))
        if _argv_values(argv, "--database-owner-session-id") != (
            owner_session_id,
        ):
            raise OperatorError("executor parent owner session differs from its lane")
        if _argv_values(argv, "--task-shard-count") != (expected_count,) or (
            _argv_values(argv, "--task-shard-index") != (str(lane_index),)
        ):
            raise OperatorError("executor parent shard differs from its lane")
        if is_executor:
            daemon_argv = _process_argv(peer_pid)
            if _argv_values(daemon_argv, "--owner-session-id") != (
                owner_session_id,
            ):
                raise OperatorError("executor owner session differs from its lane")
            if _argv_values(daemon_argv, "--task-shard-count") != (
                expected_count,
            ) or _argv_values(daemon_argv, "--task-shard-index") != (
                str(lane_index),
            ):
                raise OperatorError("executor shard differs from its lane")

    def _admit(
        self,
        request: Mapping[str, Any],
        *,
        peer_pid: int,
        peer_uid: int,
    ) -> dict[str, Any]:
        from ipfs_accelerate_py.agent_supervisor.merge.database_worktree_registry import (
            process_birth_id,
        )
        from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
            OwnerLiveness,
            ProcessBirthIdentity,
            owner_liveness,
            read_process_birth,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.state_owner_bootstrap import (
            STATE_OWNER_BOOTSTRAP_REQUEST_SCHEMA,
            STATE_OWNER_BOOTSTRAP_RESPONSE_SCHEMA,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.typed_database_task_source import (
            _DAEMON_REQUIRED_OWNER_COMMAND_OPERATIONS,
            _DAEMON_REQUIRED_OWNER_OPERATIONS,
        )

        required = {
            "schema",
            "pid",
            "process_birth",
            "process_birth_id",
            "client_id",
            "store_id",
        }
        if set(request) != required or request.get("schema") != (
            STATE_OWNER_BOOTSTRAP_REQUEST_SCHEMA
        ):
            raise OperatorError("executor bootstrap request differs from its closed schema")
        pid = int(request.get("pid") or 0)
        raw_birth = request.get("process_birth")
        if pid <= 1 or not isinstance(raw_birth, Mapping):
            raise OperatorError("executor bootstrap request has no process birth")
        if pid != peer_pid or peer_uid != os.geteuid():
            raise OperatorError("executor bootstrap SO_PEERCRED identity differs")
        observed = read_process_birth(pid)
        supplied = ProcessBirthIdentity.from_dict(dict(raw_birth))
        supplied_birth_id = str(request.get("process_birth_id") or "")
        if (
            observed is None
            or observed != supplied
            or process_birth_id(observed) != supplied_birth_id
        ):
            raise OperatorError("executor bootstrap process birth is stale")
        client_id = str(request.get("client_id") or "")
        store_id = _control_plane_store_id(self.board.resolved_database_program())
        is_executor = client_id in self.allowed_client_ids
        is_supervisor = client_id in self.allowed_supervisor_client_ids
        if (
            not (is_executor or is_supervisor)
            or request.get("store_id") != store_id
        ):
            raise OperatorError("executor bootstrap scope differs from its admission")
        self._validate_parent(
            peer_pid=pid,
            bootstrap_fd=self.channel.fileno(),
            client_id=client_id,
        )

        with self._lock:
            prior = dict(self._grants.get(client_id) or {})
        prior_birth = prior.get("process_birth")
        if isinstance(prior_birth, Mapping):
            prior_identity = ProcessBirthIdentity.from_dict(dict(prior_birth))
            if owner_liveness(prior_identity) is not OwnerLiveness.DEAD:
                raise OperatorError("prior lane executor remains live during rotation")
            prior_grant_id = str(prior.get("grant_id") or "")
            if prior_grant_id:
                self.server.revoke_typed_client_grant(prior_grant_id)

        # A route policy is immutable for one materialized plan epoch. Claims and
        # lifecycle writes advance the task-store revision, but they do not change
        # the admitted task population. Re-sealing here would make a restarted
        # process disagree with the lane's stable Quack sidecar authority. A
        # population-changing refill must instead quiesce the lanes, seal a new
        # policy, and relaunch them as an explicit epoch transition.
        execution_route_policy = self.execution_route_policy
        allowed_operations = (
            tuple(sorted(_DAEMON_REQUIRED_OWNER_OPERATIONS))
            if is_executor
            else (
                "executor_control_snapshot",
                "executor_task_projection_by_identity",
                "executor_task_projection_page",
                "load_store_generation",
                "whoami_metadata",
            )
        )
        allowed_command_operations = (
            tuple(sorted(_DAEMON_REQUIRED_OWNER_COMMAND_OPERATIONS))
            if is_executor
            else ()
        )
        token, grant = self.server.issue_typed_client_grant_record(
            client_id=client_id,
            process_birth_id=supplied_birth_id,
            allowed_operations=allowed_operations,
            allowed_command_operations=allowed_command_operations,
            peer_pid=pid,
            ttl_seconds=INTERNAL_CLIENT_GRANT_TTL_SECONDS,
        )
        identity = self.server.identity
        if identity is None:
            self.server.revoke_typed_client_grant(grant.grant_id)
            raise OperatorError("state owner lost identity during bootstrap")
        record = {
            "client_id": client_id,
            "process_birth": supplied.to_dict(),
            "process_birth_id": supplied_birth_id,
            "parent_pid": int(supplied.parent_pid),
            "admitted_at_ns": time.time_ns(),
            "execution_route_policy_id": execution_route_policy.policy_id,
            "credential_transport": "private_inherited_socket",
            "client_role": "executor" if is_executor else "supervisor_read",
        }
        try:
            with self._lock:
                self._grants[client_id] = {**record, "grant_id": grant.grant_id}
                self._history.append(record)
                self._history = self._history[-128:]
                evidence = {
                    "schema": EXECUTOR_BOOTSTRAP_SCHEMA,
                    "ready": True,
                    "accepted_lane_count": sum(
                        client in self.allowed_client_ids for client in self._grants
                    ),
                    "accepted_supervisor_reader_count": sum(
                        client in self.allowed_supervisor_client_ids
                        for client in self._grants
                    ),
                    "expected_lane_count": len(self.allowed_client_ids),
                    "server_id": identity.server_id,
                    "state_owner_process_birth_id": identity.process_birth_id,
                    "execution_route_policy": execution_route_policy.public_summary(),
                    "current": [
                        {
                            key: value
                            for key, value in item.items()
                            if key != "grant_id"
                        }
                        for item in self._grants.values()
                    ],
                    "history": list(self._history),
                }
                _atomic_json(self.evidence_path, evidence)
        except BaseException:
            self.server.revoke_typed_client_grant(grant.grant_id)
            raise
        return {
            "schema": STATE_OWNER_BOOTSTRAP_RESPONSE_SCHEMA,
            "ok": True,
            "endpoint": self.board.resolved_database_program().quack_endpoint,
            "socket_path": str(self.server.typed_command_socket_path()),
            "store_id": store_id,
            "server_id": identity.server_id,
            "client_id": client_id,
            "process_birth_id": supplied_birth_id,
            "token": token,
            "execution_route_policy": execution_route_policy.to_dict(),
        }

    def _run(self) -> None:
        import struct

        from ipfs_accelerate_py.agent_supervisor.task_sources.state_owner_bootstrap import (
            _receive_frame,
            _send_frame,
        )

        self.channel.settimeout(1.0)
        while not self.stopping.is_set():
            accepted: socket.socket | None = None
            try:
                accepted, _address = self.channel.accept()
                with self._lock:
                    self._accepted = accepted
                accepted.settimeout(30.0)
                peer = accepted.getsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_PEERCRED,
                    struct.calcsize("3i"),
                )
                peer_pid, peer_uid, _peer_gid = struct.unpack("3i", peer)
                response = self._admit(
                    _receive_frame(accepted),
                    peer_pid=int(peer_pid),
                    peer_uid=int(peer_uid),
                )
                _send_frame(accepted, response)
            except TimeoutError:
                # accept() uses a 1s poll timeout.  A peer that connected but
                # stalled on its request must not SIGTERM the supervisor; the
                # lane retries bootstrap on the next rotation.
                continue
            except OSError as exc:
                if not self.stopping.is_set() and accepted is None:
                    self._fail(exc)
                    return
            except BaseException as exc:
                if accepted is None:
                    self._fail(exc)
                    return
            finally:
                if accepted is not None:
                    with self._lock:
                        if self._accepted is accepted:
                            self._accepted = None
                    try:
                        accepted.close()
                    except OSError:
                        pass


def _bootstrap_listener() -> socket.socket:
    """Create one private inherited Linux rendezvous listener."""

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    identity = hashlib.sha256(
        f"{ROOT}:{os.getpid()}:{time.time_ns()}".encode()
    ).hexdigest()[:32]
    listener.bind("\x00ipfs-accelerate-pcsm-" + identity)
    listener.listen(16)
    return listener


def _quarantine_stale_executor_bootstrap(paths: Mapping[str, Path]) -> None:
    evidence = paths["runtime"] / "evidence" / "runtime" / "executor-bootstrap.json"
    if not evidence.exists():
        return
    if evidence.is_symlink() or not evidence.is_file():
        raise OperatorError("executor bootstrap evidence is not a regular file")
    quarantine = evidence.with_name(
        f"executor-bootstrap.superseded.{time.time_ns()}.json"
    )
    evidence.replace(quarantine)


def _owner_liveness(status_payload: Mapping[str, Any]) -> str:
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        OwnerLiveness,
        ProcessBirthIdentity,
        owner_liveness,
    )

    identity = status_payload.get("identity")
    if not isinstance(identity, Mapping):
        return "absent"
    birth_payload = identity.get("process_birth")
    if not isinstance(birth_payload, Mapping):
        return "unknown"
    try:
        observed = owner_liveness(ProcessBirthIdentity.from_dict(birth_payload))
    except Exception:
        return "unknown"
    if observed is OwnerLiveness.ALIVE:
        return "alive"
    if observed is OwnerLiveness.DEAD:
        return "dead"
    return "unknown"


def _task_status(connection: Any) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY status"
    ).fetchall()
    counts = {str(row[0]): int(row[1]) for row in rows}
    # The current Quack table transport supports simple scans but can reject a
    # correlated NOT EXISTS plan as unimplemented.  Read the three canonical
    # relations separately and calculate this read-only projection locally;
    # task/dependency/block rows remain authoritative in DuckDB.
    task_rows = connection.execute(
        "SELECT task_cid, task_alias, ordinal, status "
        "FROM tasks ORDER BY ordinal, task_alias"
    ).fetchall()
    dependency_rows = connection.execute(
        "SELECT task_cid, dependency_task_cid FROM task_dependencies"
    ).fetchall()
    blocked_rows = connection.execute(
        "SELECT task_cid FROM task_blocks WHERE state = 'active'"
    ).fetchall()
    status_by_cid = {str(row[0]): str(row[3]) for row in task_rows}
    dependencies_by_cid: dict[str, list[str]] = {}
    for row in dependency_rows:
        dependencies_by_cid.setdefault(str(row[0]), []).append(str(row[1]))
    actively_blocked = {str(row[0]) for row in blocked_rows}
    ready_ids = [
        str(row[1])
        for row in task_rows
        if str(row[3]) in READY_STATUSES
        and str(row[0]) not in actively_blocked
        and all(
            status_by_cid.get(dependency) in COMPLETED_STATUSES
            for dependency in dependencies_by_cid.get(str(row[0]), ())
        )
    ][:100]
    active_rows = connection.execute(
        "SELECT task_alias FROM tasks WHERE status IN (?, ?, ?) "
        "ORDER BY ordinal, task_alias LIMIT 100",
        list(ACTIVE_STATUSES),
    ).fetchall()
    return {
        "status_counts": counts,
        "dependency_ready_task_ids": ready_ids,
        "active_task_ids": [str(row[0]) for row in active_rows],
        "blocked_count": int(counts.get("blocked", 0)),
        "terminal_count": sum(counts.get(item, 0) for item in TERMINAL_STATUSES),
        "task_count": sum(counts.values()),
    }


def _supervisor_status(
    board: Any,
    paths: Mapping[str, Path],
    owner: Mapping[str, Any],
) -> dict[str, Any]:
    state_dir = paths["runtime"] / "state"
    master_pid_path = state_dir / "configured-board-master.pid"
    master_pid = _read_pid(master_pid_path)
    identity = owner.get("identity")
    process_birth = identity.get("process_birth") if isinstance(identity, Mapping) else None
    owner_pid = int(process_birth.get("pid") or 0) if isinstance(process_birth, Mapping) else 0
    owner_server_id = str(identity.get("server_id") or "") if isinstance(identity, Mapping) else ""
    owner_process_birth_id = (
        str(identity.get("process_birth_id") or "")
        if isinstance(identity, Mapping)
        else ""
    )
    lanes: list[dict[str, Any]] = []
    freshness_limit = max(
        120.0,
        float(board.payload.get("check_interval_seconds") or 20.0) * 4.0,
    )
    for index in range(max(1, int(board.max_lanes))):
        lane_dir = state_dir / f"lane-{index}"
        supervisor_pid = _read_pid(lane_dir / f"pcsm_lane_{index}_supervisor.pid")
        daemon_pid = _read_pid(lane_dir / f"pcsm_lane_{index}_managed_daemon.pid")
        status_path = lane_dir / f"pcsm_lane_{index}_supervisor_status.json"
        lane_status: dict[str, Any] = {}
        projection_fresh = False
        projection_bound = False
        if status_path.is_file():
            try:
                observed = _json_object(status_path)
                updated_at = str(observed.get("updated_at") or "")
                try:
                    parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    age_seconds = max(
                        0.0,
                        datetime.now(UTC).timestamp() - parsed.timestamp(),
                    )
                except (TypeError, ValueError):
                    age_seconds = float("inf")
                projection_fresh = age_seconds <= freshness_limit
                projection_bound = (
                    int(observed.get("supervisor_pid") or 0) == supervisor_pid
                    and int(observed.get("daemon_pid") or 0) == daemon_pid
                    and observed.get("supervisor_pid_alive") is True
                    and observed.get("daemon_pid_alive") is True
                    and str(observed.get("status") or "")
                    not in {"blocked", "failed", "quarantined", "stopped"}
                )
                lane_status = {
                    key: observed.get(key)
                    for key in (
                        "status",
                        "updated_at",
                        "restart_count",
                        "daemon_running",
                    )
                    if key in observed
                }
                lane_status["age_seconds"] = age_seconds
            except OperatorError:
                lane_status = {"status": "malformed"}
        lanes.append(
            {
                "lane_index": index,
                "supervisor_pid": supervisor_pid,
                "supervisor_alive": (
                    _pid_alive(supervisor_pid)
                    and projection_fresh
                    and projection_bound
                ),
                "daemon_pid": daemon_pid,
                "daemon_alive": (
                    _pid_alive(daemon_pid)
                    and projection_fresh
                    and projection_bound
                ),
                "projection": lane_status,
            }
        )
    bootstrap_path = paths["runtime"] / "evidence" / "runtime" / "executor-bootstrap.json"
    bootstrap: dict[str, Any] = {"ready": False, "accepted_lane_count": 0}
    if bootstrap_path.is_file():
        try:
            observed_bootstrap = _json_object(bootstrap_path)
            bootstrap = {
                "ready": observed_bootstrap.get("ready") is True,
                "accepted_lane_count": int(
                    observed_bootstrap.get("accepted_lane_count") or 0
                ),
                "expected_lane_count": int(
                    observed_bootstrap.get("expected_lane_count") or 0
                ),
                "execution_route_policy": observed_bootstrap.get(
                    "execution_route_policy"
                ),
                "server_id": str(observed_bootstrap.get("server_id") or ""),
                "state_owner_process_birth_id": str(
                    observed_bootstrap.get("state_owner_process_birth_id") or ""
                ),
            }
        except (OperatorError, TypeError, ValueError):
            bootstrap = {"ready": False, "accepted_lane_count": 0}
    expected = max(1, int(board.max_lanes))
    live_lanes = sum(item["supervisor_alive"] for item in lanes)
    live_daemons = sum(item["daemon_alive"] for item in lanes)
    return {
        "ready": (
            _pid_alive(master_pid)
            and master_pid == owner_pid
            and live_lanes == expected
            and live_daemons == expected
            and bootstrap.get("ready") is True
            and int(bootstrap.get("accepted_lane_count") or 0) == expected
            and bootstrap.get("server_id") == owner_server_id
            and bootstrap.get("state_owner_process_birth_id")
            == owner_process_birth_id
        ),
        "master_pid": master_pid,
        "master_alive": _pid_alive(master_pid),
        "same_process_as_state_owner": bool(master_pid and master_pid == owner_pid),
        "expected_lane_count": expected,
        "live_lane_count": live_lanes,
        "live_daemon_count": live_daemons,
        "lanes": lanes,
        "executor_bootstrap": bootstrap,
    }


def status(config_path: Path) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        open_duckdb_connection,
    )

    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    state_status_path = paths["owner"] / "quack-state-server.status.json"
    owner_status: dict[str, Any] = {}
    if state_status_path.is_file():
        try:
            owner_status = _json_object(state_status_path)
        except OperatorError:
            owner_status = {"lifecycle": "malformed"}
    liveness = _owner_liveness(owner_status)
    lifecycle = str(owner_status.get("lifecycle") or "absent")
    live_ready = lifecycle == "ready" and liveness == "alive"
    task_projection: dict[str, Any] = {
        "available": False,
        "reason_code": "control_plane_unavailable",
    }
    connection = None
    try:
        if live_ready:
            read_replica = owner_status.get("read_replica")
            read_replica = read_replica if isinstance(read_replica, Mapping) else {}
            expected_replica = paths["database"].with_name(
                f"{paths['database'].stem}.read-replica{paths['database'].suffix}"
            )
            observed_path = Path(str(read_replica.get("path") or ""))
            if (
                read_replica.get("authority") != "non_authoritative_read_replica"
                or read_replica.get("live") is not True
                or observed_path != expected_replica
                or not expected_replica.is_file()
            ):
                raise OperatorError("current state-owner read projection is unavailable")
            import duckdb

            connection = duckdb.connect(str(expected_replica), read_only=True)
            task_projection = {
                "available": True,
                "transport": "quack_owner_checkpointed_read_replica",
                "authoritative": False,
                "authority": "DuckDB/DatabaseTaskSource@1 via live Quack owner",
                "scheduler_gate": False,
                "refresh_sequence": int(read_replica.get("refresh_sequence") or 0),
                **_task_status(connection),
            }
        elif paths["database"].is_file() and liveness in {"absent", "dead"}:
            connection = open_duckdb_connection(paths["database"])
            task_projection = {
                "available": True,
                "transport": "direct_offline",
                "authoritative": True,
                **_task_status(connection),
            }
    except Exception as exc:
        task_projection = {
            "available": False,
            "reason_code": "control_plane_probe_failed",
            "error_class": type(exc).__name__,
        }
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    ducklake: dict[str, Any] = {
        "status": "absent",
        "authoritative": False,
        "scheduler_gate": False,
    }
    if paths["ducklake_receipt"].is_file():
        try:
            observed = _json_object(paths["ducklake_receipt"])
            ducklake = {
                "status": str(observed.get("status") or "unknown"),
                "authoritative": False,
                "scheduler_gate": False,
                "projection_receipt_id": str(
                    observed.get("projection_receipt_id") or ""
                ),
            }
        except OperatorError:
            ducklake["status"] = "malformed"
    supervisor = _supervisor_status(board, paths, owner_status)
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "status",
        "materialized": paths["database"].is_file()
        and paths["bootstrap_receipt"].is_file(),
        "state_owner": {
            "ready": live_ready,
            "lifecycle": lifecycle,
            "liveness": liveness,
            "identity": owner_status.get("identity"),
        },
        "supervisor": supervisor,
        "task_authority": task_projection,
        "ducklake_projection": ducklake,
    }


def _pid_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    return int(raw) if raw.isdigit() else 0


def _write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(f"{int(pid)}\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _python_environment() -> dict[str, str]:
    environment = dict(os.environ)
    ordered: list[str] = []
    for item in (
        str(ACCEL_ROOT),
        str(ROOT),
        *environment.get("PYTHONPATH", "").split(os.pathsep),
    ):
        if item and item not in ordered:
            ordered.append(item)
    environment["PYTHONPATH"] = os.pathsep.join(ordered)
    return environment


def start_state_owner_daemon(config_path: Path) -> dict[str, Any]:
    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise OperatorError("materialize the sealed PCSM board before starting Quack")
    current = status(config_path)
    if (
        current["state_owner"]["ready"] is True
        and current["supervisor"]["ready"] is True
    ):
        return {
            "schema": OPERATOR_SCHEMA,
            "command": OWNER_DAEMON_COMMAND,
            "already_running": True,
            "ready": True,
        }
    if current["state_owner"]["ready"] is True:
        raise OperatorError(
            "a Quack owner exists outside the canonical combined supervisor launch"
        )
    pid_path = paths["runtime"] / "state" / "pcsm-state-owner.pid"
    prior_pid = _read_pid(pid_path)
    if _pid_alive(prior_pid):
        raise OperatorError("a state-owner process exists but is not live-ready")
    log_path = paths["runtime"] / "logs" / "pcsm-supervisor.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--config",
        str(config_path),
        "launch-supervisor",
    ]
    with log_path.open("ab", buffering=0) as log_handle:
        process = subprocess.Popen(
            argv,
            cwd=ROOT,
            env=_python_environment(),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    _write_pid(pid_path, process.pid)
    deadline = time.monotonic() + 180.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise OperatorError("detached PCSM supervisor exited before readiness")
        observed = status(config_path)
        if (
            observed["state_owner"]["ready"] is True
            and observed["supervisor"]["ready"] is True
            and observed["task_authority"].get("available") is True
        ):
            return {
                "schema": OPERATOR_SCHEMA,
                "command": OWNER_DAEMON_COMMAND,
                "already_running": False,
                "detached": True,
                "ready": True,
                "pid": process.pid,
                "pid_path": str(pid_path.relative_to(ROOT)),
                "log_path": str(log_path.relative_to(ROOT)),
            }
        time.sleep(0.25)
    try:
        process.terminate()
    except OSError:
        pass
    raise OperatorError("detached PCSM supervisor did not become ready")


def launch_supervisor(
    config_path: Path,
    *,
    dry_run: bool = False,
    duration_seconds: float = float("inf"),
) -> int:
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        configured_board_launch_plan,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        main as configured_board_main,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner import (
        main as multi_supervisor_main,
    )

    board, config = _load_config(config_path)
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise OperatorError("materialize the sealed PCSM board before launch")
    restart_admission = _owner_restart_admission(board, config, paths)
    common = ["--repo-root", str(ROOT), "--config", str(config_path)]
    preflight = int(configured_board_main([*common, "preflight"]))
    if preflight != 0:
        return preflight
    preflight_head, preflight_tree = _assert_clean_current_tree(config)
    if (
        preflight_head != restart_admission["current_source_head"]
        or preflight_tree != restart_admission["current_source_tree"]
    ):
        raise OperatorError("owner restart source changed during preflight")
    if dry_run:
        plan = configured_board_launch_plan(
            board,
            implement=True,
            detach=False,
            duration_seconds=duration_seconds,
        )
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": "launch-supervisor",
                    "dry_run": True,
                    "board_namespace": plan["board_namespace"],
                    "lanes": plan["lanes"],
                    "authority_mode": plan["database_program"]["authority_mode"],
                    "task_source_kind": plan["database_program"]["task_source_kind"],
                    "credential_transport": "private_inherited_socket",
                    "restart_admission_mode": restart_admission["mode"],
                    "restart_admission_id": restart_admission["admission_id"],
                    "max_task_attempts_before": restart_admission[
                        "max_task_attempts_before"
                    ],
                    "max_task_attempts_after": restart_admission[
                        "max_task_attempts_after"
                    ],
                },
                sort_keys=True,
            )
        )
        return 0
    if duration_seconds != float("inf") and duration_seconds <= 0:
        raise OperatorError("supervisor duration must be positive")

    prior_owner = _owner_restart_prior_status(
        paths["owner"] / "quack-state-server.status.json"
    )
    _require_prior_owner_continuity(restart_admission, prior_owner)
    _ensure_private_runtime_directory(paths["runtime"])
    _ensure_private_runtime_directory(paths["runtime"] / "state")
    _quarantine_stale_executor_bootstrap(paths)
    server = _build_state_owner(board, paths)
    listener: socket.socket | None = None
    broker: _ExecutorBootstrapBroker | None = None
    prior_environment = dict(os.environ)
    result = 1
    try:
        identity = server.start()
        ready = server.ready()
        route_policy_provider = _ExecutionRoutePolicyProvider(
            server=server,
            board=board,
            restart_admission=restart_admission,
        )
        route_policy = route_policy_provider.seal()
        after_head, after_tree = _assert_clean_current_tree(config)
        if (
            after_head != restart_admission["current_source_head"]
            or after_tree != restart_admission["current_source_tree"]
        ):
            raise OperatorError("owner restart source changed during admission")
        restart_receipt = _owner_restart_receipt(
            restart_admission,
            identity,
            expected_store_id=_control_plane_store_id(
                board.resolved_database_program()
            ),
            prior_owner=prior_owner,
            database_verification=route_policy_provider.database_verification,
        )
        restart_receipt_path = (
            paths["runtime"]
            / "evidence"
            / "runtime"
            / "owner-restarts"
            / (
                f"{int(identity.generation):020d}-"
                f"{restart_receipt['receipt_id'].removeprefix('sha256:')}.json"
            )
        )
        _atomic_json(restart_receipt_path, restart_receipt)
        listener = _bootstrap_listener()
        broker = _ExecutorBootstrapBroker(
            channel=listener,
            server=server,
            board=board,
            paths=paths,
            initial_execution_route_policy=route_policy,
        )
        broker.start()
        plan = configured_board_launch_plan(
            board,
            implement=True,
            detach=False,
            duration_seconds=duration_seconds,
        )
        for lane_index in range(int(plan["lanes"])):
            _ensure_private_runtime_directory(
                paths["runtime"] / "state" / f"lane-{lane_index}"
            )
        runner_args = list(plan["argv"])
        for value in (
            "--database-owner-session-id",
            EXECUTOR_OWNER_SESSION_BASE,
            "--state-owner-bootstrap-fd",
            str(listener.fileno()),
            "--state-owner-bootstrap-store-id",
            _control_plane_store_id(board.resolved_database_program()),
        ):
            runner_args.append(f"--common-arg={value}")
        environment = _python_environment()
        environment.update(
            {str(key): str(value) for key, value in plan["environment"].items()}
        )
        for secret_name in (
            "IPFS_ACCELERATE_AGENT_QUACK_TOKEN",
            "IPFS_ACCELERATE_AGENT_STATE_OWNER_SOCKET",
            "IPFS_ACCELERATE_AGENT_TYPED_STATE_OWNER_TOKEN",
            "IPFS_ACCELERATE_AGENT_TYPED_STATE_OWNER_SOCKET",
        ):
            environment.pop(secret_name, None)
        os.environ.clear()
        os.environ.update(environment)
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": "launch-supervisor",
                    "ready": True,
                    "identity": identity.to_dict(),
                    "live": ready,
                    "lanes": int(plan["lanes"]),
                    "execution_route_policy": route_policy.public_summary(),
                    "owner_restart_receipt": restart_receipt,
                    "owner_restart_receipt_path": str(
                        restart_receipt_path.relative_to(ROOT)
                    ),
                    "credential_transport": "private_inherited_socket",
                    "raw_token_in_argv_or_environment": False,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        result = int(multi_supervisor_main(runner_args))
        if broker.failure:
            raise OperatorError(
                f"executor bootstrap broker failed closed: {broker.failure}"
            )
        return result
    finally:
        os.environ.clear()
        os.environ.update(prior_environment)
        if broker is not None:
            try:
                broker.stop()
            except Exception:
                if result == 0:
                    raise
        elif listener is not None:
            listener.close()
        server.stop()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="repository-relative or absolute configured-board JSON",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "materialize",
        help="seal the committed Markdown bootstrap into DuckDB and DuckLake",
    )
    commands.add_parser(
        "state-owner",
        help="serve the materialized DuckDB authority through fenced loopback Quack",
    )
    commands.add_parser(
        OWNER_DAEMON_COMMAND,
        help="start the session-independent Quack owner and configured supervisor",
    )
    status_parser = commands.add_parser(
        "status",
        help="report owner liveness and durable task readiness without exposing tokens",
    )
    status_parser.add_argument(
        "--require-ready",
        action="store_true",
        help="exit nonzero unless Quack is live and task authority is queryable",
    )
    launch_parser = commands.add_parser(
        "launch-supervisor",
        help="preflight and launch the existing configured-board supervisor",
    )
    launch_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="render and validate the launch without starting workers",
    )
    launch_parser.add_argument(
        "--duration-seconds",
        type=float,
        default=float("inf"),
        help="optional positive supervisor runtime bound",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    config_path = arguments.config
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    try:
        if arguments.command == "materialize":
            result = materialize(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.command == "state-owner":
            return state_owner(config_path)
        if arguments.command == OWNER_DAEMON_COMMAND:
            result = start_state_owner_daemon(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.command == "status":
            result = status(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            if arguments.require_ready and not (
                result["state_owner"]["ready"]
                and result["supervisor"]["ready"]
                and result["task_authority"].get("available") is True
            ):
                return 1
            return 0
        if arguments.command == "launch-supervisor":
            return launch_supervisor(
                config_path,
                dry_run=bool(arguments.dry_run),
                duration_seconds=float(arguments.duration_seconds),
            )
        raise OperatorError(f"unsupported command: {arguments.command}")
    except OperatorError as exc:
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": str(arguments.command),
                    "ok": False,
                    "error_class": type(exc).__name__,
                    "error": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        # Third-party transport exception text is not a trusted secret-
        # redaction surface, so unexpected failures publish only their class.
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": str(arguments.command),
                    "ok": False,
                    "error_class": type(exc).__name__,
                    "error": "operation failed closed",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
