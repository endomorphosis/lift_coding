#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare virtual-AI-OS task proposals."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.task_proposal_router import (  # noqa: E402
    build_repo_task_proposal_route_runner,
)


TASK_PROPOSAL_RUNNER = build_repo_task_proposal_route_runner(
    repo_root=REPO_ROOT,
    task_board_stem="19-virtual-ai-os-submodule-integration",
    task_board_dir="implementation_plan/docs",
    artifact_namespace="virtual_ai_os",
    task_header_prefix="## VAI-",
    prompt_intro="You are helping implement the HandsFree virtual AI operating system roadmap.",
    domain_outputs=("runtime and cross-repo contracts to add",),
    no_open_task_message="No open task found in virtual-AI-OS task board.",
    description="Generate an implementation proposal for a virtual-AI-OS task-board item with llm_router.",
    task_id_help="Specific VAI task id. Defaults to the first ready task.",
)


def main(argv: list[str] | None = None) -> int:
    return TASK_PROPOSAL_RUNNER.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
