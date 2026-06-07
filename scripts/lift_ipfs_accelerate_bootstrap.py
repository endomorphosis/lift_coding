"""Lift-local import bootstrap for scripts backed by ipfs_accelerate."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class LiftIpfsAccelerateBootstrap:
    """Resolved lift repo paths needed before importing ipfs_accelerate_py."""

    script_repo_root: Path
    package_root: Path
    script_dir: Path


def _prepend_sys_path(paths: Iterable[Path | str]) -> None:
    values = [str(path) for path in paths]
    for value in values:
        while value in sys.path:
            sys.path.remove(value)
    for value in reversed(values):
        sys.path.insert(0, value)


def bootstrap_ipfs_accelerate(
    script_file: Path | str,
    *,
    include_script_dir: bool = False,
) -> LiftIpfsAccelerateBootstrap:
    """Make lift's checked-out ipfs_accelerate package importable."""

    script_path = Path(script_file).resolve()
    script_repo_root = script_path.parents[1]
    script_dir = script_path.parent
    package_root = script_repo_root / "external" / "ipfs_accelerate"
    paths: list[Path] = [package_root]
    if include_script_dir:
        paths.append(script_dir)
    _prepend_sys_path(paths)
    return LiftIpfsAccelerateBootstrap(
        script_repo_root=script_repo_root,
        package_root=package_root,
        script_dir=script_dir,
    )
