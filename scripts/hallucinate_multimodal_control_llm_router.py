#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare Hallucinate multimodal-control task proposals."""

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
    task_board_stem="MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL",
    task_board_dir="hallucinate_app/docs",
    artifact_namespace="hallucinate_multimodal_control",
    task_header_prefix="## HAO-",
    prompt_intro="You are helping implement the Hallucinate App multimodal control-surface roadmap.",
    domain_outputs=("descriptor/runtime contracts to add",),
    no_open_task_message="No open task found in Hallucinate multimodal-control task board.",
    description=(
        "Generate an implementation proposal for a Hallucinate multimodal-control "
        "task-board item with llm_router."
    ),
    task_id_help="Specific HAO task id. Defaults to the first ready task.",
    include_dry_run_flag=True,
)


def main(argv: list[str] | None = None) -> int:
    return TASK_PROPOSAL_RUNNER.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
