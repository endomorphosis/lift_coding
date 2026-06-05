#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare virtual-AI-OS task proposals."""

from __future__ import annotations

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import build_repo_script_bootstrap  # noqa: E402
from ipfs_accelerate_py.agent_supervisor.task_proposal_router import (  # noqa: E402
    build_repo_task_proposal_route_runner,
)


_SCRIPT_BOOTSTRAP = build_repo_script_bootstrap(__file__)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root
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
