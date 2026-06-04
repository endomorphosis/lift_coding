#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare Hallucinate multimodal-control task proposals."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_runtime_environment_callbacks,
    task_board_filename as _task_board_filename,
    task_board_path_option as _task_board_path_option,
)

TASK_BOARD_STEM = "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL"
DEFAULT_TASK_BOARD_PATH = (
    REPO_ROOT / "hallucinate_app" / "docs" / _task_board_filename(TASK_BOARD_STEM)
)
TASK_BOARD_PATH_OPTION = _task_board_path_option()
PLAN_PATH = REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md"
ARTIFACT_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "llm_router"

from ipfs_accelerate_py.agent_supervisor.task_proposal_router import (  # noqa: E402
    run_configured_task_proposal_router_cli,
)


_RUNTIME_ENVIRONMENT = build_runtime_environment_callbacks(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT))
_bootstrap_imports = _RUNTIME_ENVIRONMENT.enter


def main(argv: list[str] | None = None) -> int:
    return run_configured_task_proposal_router_cli(
        argv,
        repo_root=REPO_ROOT,
        task_board_path=DEFAULT_TASK_BOARD_PATH,
        task_header_prefix="## HAO-",
        plan_path=PLAN_PATH,
        artifact_dir=ARTIFACT_DIR,
        prompt_intro="You are helping implement the Hallucinate App multimodal control-surface roadmap.",
        requested_outputs=(
            "exact files to edit",
            "descriptor/runtime contracts to add",
            "tests and fixtures needed",
            "validation commands",
            "risks or blockers",
        ),
        no_open_task_message="No open task found in Hallucinate multimodal-control task board.",
        description=(
            "Generate an implementation proposal for a Hallucinate multimodal-control "
            "task-board item with llm_router."
        ),
        task_id_help="Specific HAO task id. Defaults to the first ready task.",
        task_board_option=TASK_BOARD_PATH_OPTION,
        include_dry_run_flag=True,
        bootstrap=_bootstrap_imports,
    )


if __name__ == "__main__":
    raise SystemExit(main())
