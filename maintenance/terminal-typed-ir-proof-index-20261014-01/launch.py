"""Bootstrap the exact policy overlay before an explicit successor script."""
from __future__ import annotations

from pathlib import Path
import runpy
import sys

from scheduler_overlay import load_overlay

ROOT = Path(__file__).resolve().parent


def main() -> None:
    sys.dont_write_bytecode = True
    args = sys.argv[1:]
    if not args:
        raise SystemExit("explicit local script or --module pytest required")
    if args[:2] == ["--module", "pytest"]:
        load_overlay()
        sys.argv = ["pytest", *args[2:]]
        runpy.run_module("pytest", run_name="__main__", alter_sys=True)
        return
    if Path(args[0]).name != args[0] or not args[0].endswith(".py"):
        raise SystemExit("one explicit local successor script required")
    target = ROOT / args[0]
    if target.resolve(strict=True) != target or target.name == "launch.py":
        raise SystemExit("canonical local successor target required")
    load_overlay()
    sys.argv = [str(target), *args[1:]]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
