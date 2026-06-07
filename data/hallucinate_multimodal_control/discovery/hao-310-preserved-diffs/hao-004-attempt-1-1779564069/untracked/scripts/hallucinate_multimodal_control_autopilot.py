#!/usr/bin/env python3
"""Run the Hallucinate multimodal-control supervisor in implementation mode."""

from __future__ import annotations

import sys


def with_autopilot_defaults(argv: list[str]) -> list[str]:
    args = list(argv)
    if "--implement" in args or "--no-implement" in args:
        return args
    return ["--implement", *args]


def main(argv: list[str] | None = None) -> None:
    args = with_autopilot_defaults(list(sys.argv[1:] if argv is None else argv))
    from hallucinate_multimodal_control_todo_supervisor import main as supervisor_main

    supervisor_main(args)


if __name__ == "__main__":
    main()
