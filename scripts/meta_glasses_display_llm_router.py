#!/usr/bin/env python3
"""Use the accelerator LLM helper to prepare display-widget task proposals."""

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
    task_board_stem="18-swissknife-meta-glasses-display-widgets",
    task_board_dir="implementation_plan/docs",
    artifact_namespace="meta_glasses_display_widgets",
    task_header_prefix="## MGW-",
    prompt_intro="You are helping implement the HandsFree/Swissknife Meta glasses display-widget roadmap.",
    domain_outputs=("data contracts or APIs to add",),
    test_output="mocks/fixtures/tests needed to run without hardware",
    no_open_task_message="Display-widget task board has no open task.",
    description=(
        "Generate an implementation proposal for a Meta glasses display-widget "
        "task-board item with llm_router."
    ),
    task_id_help="Specific MGW task id. Defaults to the first open task.",
    task_board_option="--task-board-path",
    hidden_standard_task_board_option=True,
)


def main(argv: list[str] | None = None) -> int:
    return TASK_PROPOSAL_RUNNER.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
