#!/usr/bin/env python3
"""Manage isolated SwissKnife supervisor lanes and serialized integration.

Each lane owns a top-level worktree branch and a matching SwissKnife submodule
branch. Supervisors run from those lane roots and may use task worktrees below
their own lane. The ``merge`` command is the only supported path back into the
shared integration checkout; it holds an exclusive file lock while validating
and merging a single lane.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = REPO_ROOT / "tmp" / "swissknife_lane_worktrees"
MANIFEST_PATH = STATE_DIR / "lanes.json"
LOCK_PATH = STATE_DIR / "integration-merge.lock"
REQUIRED_SUBMODULES = ("swissknife", "external/ipfs_accelerate", "external/ipfs_datasets")


@dataclass(frozen=True)
class Lane:
    name: str

    @property
    def root_branch(self) -> str:
        return f"automation/swissknife-{self.name}-lane"

    @property
    def swissknife_branch(self) -> str:
        return f"automation/swissknife-{self.name}-lane"

    @property
    def path(self) -> Path:
        return REPO_ROOT.parent / f"{REPO_ROOT.name}-swissknife-{self.name}-lane"

    @property
    def swissknife_path(self) -> Path:
        return self.path / "swissknife"

    @property
    def task_worktree_root(self) -> Path:
        return self.path / "tmp" / "supervisor-task-worktrees" / self.name


LANES = {name: Lane(name) for name in ("all-tools", "refactor")}


class LaneError(RuntimeError):
    """A requested lane operation cannot safely proceed."""


def run(command: list[str], *, cwd: Path = REPO_ROOT, capture: bool = True) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=capture,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise LaneError(f"command failed ({result.returncode}): {' '.join(command)}\n{details}")
    return result.stdout.strip()


def git(args: list[str], *, cwd: Path = REPO_ROOT) -> str:
    return run(["git", *args], cwd=cwd)


def git_ref_exists(ref: str, *, cwd: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def working_tree_clean(path: Path) -> bool:
    return not git(["status", "--porcelain"], cwd=path)


def configure_local_submodule_sources(lane: Lane) -> None:
    """Clone lane submodules from local object stores, never from the network."""

    for relative in REQUIRED_SUBMODULES:
        source = REPO_ROOT / relative
        if not source.exists():
            raise LaneError(f"required local submodule source is unavailable: {source}")
        git(["config", f"submodule.{relative}.url", str(source)], cwd=lane.path)


def ensure_lane(lane: Lane, *, dry_run: bool) -> dict[str, str]:
    if lane.path.exists():
        if not (lane.path / ".git").exists():
            raise LaneError(f"lane path exists but is not a Git worktree: {lane.path}")
    elif dry_run:
        return {
            "lane": lane.name,
            "root_branch": lane.root_branch,
            "swissknife_branch": lane.swissknife_branch,
            "path": str(lane.path),
            "task_worktree_root": str(lane.task_worktree_root),
            "action": "would_create",
        }
    elif git_ref_exists(f"refs/heads/{lane.root_branch}", cwd=REPO_ROOT):
        git(["worktree", "add", str(lane.path), lane.root_branch])
    else:
        git(["worktree", "add", "-b", lane.root_branch, str(lane.path), "HEAD"])

    if dry_run:
        return {
            "lane": lane.name,
            "root_branch": lane.root_branch,
            "swissknife_branch": lane.swissknife_branch,
            "path": str(lane.path),
            "task_worktree_root": str(lane.task_worktree_root),
            "action": "already_exists",
        }

    configure_local_submodule_sources(lane)
    git(
        [
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "update",
            "--init",
            "--no-fetch",
            "--",
            *REQUIRED_SUBMODULES,
        ],
        cwd=lane.path,
    )
    if not lane.swissknife_path.exists():
        raise LaneError(f"SwissKnife submodule was not initialized: {lane.swissknife_path}")

    base_ref = git(["rev-parse", "HEAD"], cwd=lane.swissknife_path)
    branch_ref = f"refs/heads/{lane.swissknife_branch}"
    if git_ref_exists(branch_ref, cwd=lane.swissknife_path):
        current_ref = git(["rev-parse", branch_ref], cwd=lane.swissknife_path)
        if current_ref != base_ref:
            raise LaneError(
                f"SwissKnife lane branch {lane.swissknife_branch} already exists at {current_ref}, "
                f"but this lane is pinned to {base_ref}. Reconcile it before reusing the lane."
            )
        git(["switch", lane.swissknife_branch], cwd=lane.swissknife_path)
    else:
        git(["switch", "-c", lane.swissknife_branch, base_ref], cwd=lane.swissknife_path)

    lane.task_worktree_root.mkdir(parents=True, exist_ok=True)
    return {
        "lane": lane.name,
        "root_branch": lane.root_branch,
        "swissknife_branch": lane.swissknife_branch,
        "path": str(lane.path),
        "task_worktree_root": str(lane.task_worktree_root),
        "root_head": git(["rev-parse", "HEAD"], cwd=lane.path),
        "swissknife_head": git(["rev-parse", "HEAD"], cwd=lane.swissknife_path),
        "action": "ready",
    }


def write_manifest() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "swissknife-supervisor-lanes/v1",
        "integration_checkout": str(REPO_ROOT),
        "integration_branch": git(["branch", "--show-current"]).strip(),
        "lanes": [
            {
                "name": lane.name,
                "path": str(lane.path),
                "root_branch": lane.root_branch,
                "swissknife_path": str(lane.swissknife_path),
                "swissknife_branch": lane.swissknife_branch,
                "task_worktree_root": str(lane.task_worktree_root),
            }
            for lane in LANES.values()
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def lane_status(lane: Lane) -> dict[str, object]:
    if not lane.path.exists():
        return {"lane": lane.name, "ready": False, "reason": "worktree_missing"}
    if not lane.swissknife_path.exists():
        return {"lane": lane.name, "ready": False, "reason": "swissknife_submodule_missing"}
    root_branch = git(["branch", "--show-current"], cwd=lane.path)
    swissknife_branch = git(["branch", "--show-current"], cwd=lane.swissknife_path)
    return {
        "lane": lane.name,
        "ready": root_branch == lane.root_branch and swissknife_branch == lane.swissknife_branch,
        "path": str(lane.path),
        "root_branch": root_branch,
        "root_head": git(["rev-parse", "HEAD"], cwd=lane.path),
        "root_clean": working_tree_clean(lane.path),
        "swissknife_branch": swissknife_branch,
        "swissknife_head": git(["rev-parse", "HEAD"], cwd=lane.swissknife_path),
        "swissknife_clean": working_tree_clean(lane.swissknife_path),
        "task_worktree_root": str(lane.task_worktree_root),
    }


def validate_lane(lane: Lane) -> None:
    status = lane_status(lane)
    if not status.get("ready"):
        raise LaneError(f"lane is not ready: {json.dumps(status, sort_keys=True)}")
    if not status.get("root_clean") or not status.get("swissknife_clean"):
        raise LaneError(
            f"lane has uncommitted changes and cannot enter integration: {json.dumps(status, sort_keys=True)}"
        )
    git(["diff", "--check"], cwd=lane.path)
    git(["diff", "--check"], cwd=lane.swissknife_path)


@contextmanager
def integration_lock() -> Iterator[None]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LaneError("another lane validation or merge owns the integration lock") from exc
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def run_validation_command(lane: Lane, command: str) -> None:
    result = subprocess.run(["bash", "-lc", command], cwd=lane.path, text=True, check=False)
    if result.returncode != 0:
        raise LaneError(f"lane validation failed with exit code {result.returncode}: {command}")


def merge_lane(lane: Lane, *, validation_command: str, apply: bool) -> dict[str, object]:
    if not validation_command.strip():
        raise LaneError("--validation-command is required so validation is serialized with the merge")
    with integration_lock():
        validate_lane(lane)
        if not working_tree_clean(REPO_ROOT):
            raise LaneError("integration checkout is dirty; commit or recover it before merging a lane")
        if not working_tree_clean(REPO_ROOT / "swissknife"):
            raise LaneError("integration SwissKnife submodule is dirty; commit or recover it before merging a lane")
        if not apply:
            return {
                "lane": lane.name,
                "validated": True,
                "merged": False,
                "reason": "dry_run",
                "branch": lane.root_branch,
                "validation_command": validation_command,
            }
        run_validation_command(lane, validation_command)
        merge = subprocess.run(
            ["git", "merge", "--no-ff", "--no-edit", lane.root_branch],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if merge.returncode != 0:
            subprocess.run(["git", "merge", "--abort"], cwd=REPO_ROOT, text=True, check=False)
            raise LaneError(f"merge failed and was aborted:\n{(merge.stderr or merge.stdout).strip()}")
        return {
            "lane": lane.name,
            "validated": True,
            "merged": True,
            "branch": lane.root_branch,
            "integration_head": git(["rev-parse", "HEAD"]),
        }


def parser() -> argparse.ArgumentParser:
    parsed = argparse.ArgumentParser(description=__doc__)
    subparsers = parsed.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create or verify lane worktrees and branches")
    init.add_argument("--lane", choices=(*LANES, "all"), default="all")
    init.add_argument("--dry-run", action="store_true")

    status = subparsers.add_parser("status", help="print lane branch and cleanliness status")
    status.add_argument("--lane", choices=(*LANES, "all"), default="all")

    merge = subparsers.add_parser("merge", help="validate one lane and merge it under the integration lock")
    merge.add_argument("--lane", choices=tuple(LANES), required=True)
    merge.add_argument("--validation-command", required=True)
    merge.add_argument("--apply", action="store_true", help="perform the merge; default is a locked dry run")
    return parsed


def selected_lanes(name: str) -> list[Lane]:
    return list(LANES.values()) if name == "all" else [LANES[name]]


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "init":
            result = [ensure_lane(lane, dry_run=args.dry_run) for lane in selected_lanes(args.lane)]
            if not args.dry_run:
                write_manifest()
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "status":
            print(json.dumps([lane_status(lane) for lane in selected_lanes(args.lane)], indent=2))
            return 0
        result = merge_lane(LANES[args.lane], validation_command=args.validation_command, apply=args.apply)
        print(json.dumps(result, indent=2))
        return 0
    except LaneError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
