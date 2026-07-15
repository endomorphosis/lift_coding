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
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from swissknife_checkout_lease_guard import (
    SwissKnifeLeaseGuardError,
    require_swissknife_checkout_lease,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = REPO_ROOT / "tmp" / "swissknife_lane_worktrees"
MANIFEST_PATH = STATE_DIR / "lanes.json"
LOCK_PATH = STATE_DIR / "integration-merge.lock"
REQUIRED_SUBMODULES = ("swissknife", "external/ipfs_accelerate", "external/ipfs_datasets")
BROWSER_TOOLCHAIN_VERIFIER = Path("scripts/verify-browser-toolchain.mjs")
BROWSER_TOOLCHAIN_RECEIPT_DIR = Path("tmp/browser-validation-toolchain")
BROWSER_TOOLCHAIN_RECEIPT_SCHEMA = "swissknife.browser-validation-toolchain.v1"
SHARED_SWISSKNIFE_DEPENDENCY_PATHS = (
    (Path("swissknife/node_modules"), True),
    (Path("swissknife/web/node_modules"), False),
    (Path("swissknife/ipfs_accelerate_js/node_modules"), False),
)


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
INTEGRATION_BOARDS = {
    "all-tools-integration": (
        "implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md"
    ),
    "refactor-integration": (
        "implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md"
    ),
}


class LaneError(RuntimeError):
    """A requested lane operation cannot safely proceed."""


@dataclass(frozen=True)
class BrowserToolchainResolution:
    """A verified Node executable and the receipt produced for it."""

    node_executable: Path
    receipt_path: Path
    receipt: dict[str, object]


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


def validate_browser_toolchain_receipt(
    receipt: object,
    *,
    node_executable: Path,
    receipt_path: Path,
) -> dict[str, object]:
    """Reject incomplete, stale, or unrelated verifier output."""

    def invalid(reason: str) -> LaneError:
        return LaneError(
            "browser toolchain verifier produced an invalid receipt "
            f"({reason}): {receipt_path}"
        )

    if not isinstance(receipt, dict):
        raise invalid("root is not an object")
    if receipt.get("schema") != BROWSER_TOOLCHAIN_RECEIPT_SCHEMA:
        raise invalid("schema is missing or unsupported")
    if receipt.get("ok") is not True:
        raise invalid("verification was not successful")

    node = receipt.get("node")
    if not isinstance(node, dict):
        raise invalid("node identity is missing")
    recorded_executable = node.get("resolvedExecutable")
    semantic_version = node.get("semanticVersion")
    if not isinstance(recorded_executable, str) or not Path(recorded_executable).is_absolute():
        raise invalid("resolved Node executable is missing or not absolute")
    if Path(os.path.abspath(recorded_executable)) != node_executable:
        raise invalid("resolved Node executable does not match the selected runtime")
    if not isinstance(semantic_version, str) or not re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", semantic_version
    ):
        raise invalid("Node semantic version is missing or invalid")

    package_manager = receipt.get("packageManager")
    if not isinstance(package_manager, dict) or package_manager.get("name") != "npm":
        raise invalid("npm identity is missing")
    npm_version = package_manager.get("semanticVersion")
    if not isinstance(npm_version, str) or not re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", npm_version
    ):
        raise invalid("npm semantic version is missing or invalid")

    lockfile = receipt.get("lockfile")
    fingerprint = lockfile.get("fingerprint") if isinstance(lockfile, dict) else None
    if not isinstance(fingerprint, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
        raise invalid("lockfile fingerprint is missing or invalid")
    return receipt


def verify_browser_toolchain(lane: Lane, *, receipt_name: str) -> BrowserToolchainResolution:
    """Resolve PATH's Node and verify it using the SwissKnife repository policy.

    The selected executable is passed by its absolute lexical path as both the
    process and the verifier's explicit check target.  Keeping the lexical path
    (rather than resolving symlinks in Python) lets the shared verifier reject
    misleading version-labelled symlink directories.
    """

    node = shutil.which("node")
    if not node:
        raise LaneError(
            "browser validation requires Node on PATH; install a release supported "
            "by swissknife/.nvmrc and retry"
        )
    node_executable = Path(os.path.abspath(node))
    verifier = lane.swissknife_path / BROWSER_TOOLCHAIN_VERIFIER
    if not verifier.is_file():
        raise LaneError(f"browser toolchain verifier is unavailable: {verifier}")

    receipt_path = lane.path / BROWSER_TOOLCHAIN_RECEIPT_DIR / f"{receipt_name}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.unlink(missing_ok=True)
    command = [
        str(node_executable),
        str(BROWSER_TOOLCHAIN_VERIFIER),
        "--check-node-executable",
        str(node_executable),
        "--receipt",
        str(receipt_path),
    ]
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join(
        part for part in (str(node_executable.parent), environment.get("PATH", "")) if part
    )
    try:
        result = subprocess.run(
            command,
            cwd=lane.swissknife_path,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise LaneError(
            f"could not execute the resolved browser-validation Node {node_executable}: {exc}"
        ) from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise LaneError(
            "browser toolchain verification failed "
            f"({result.returncode}) for {node_executable}:\n{details}"
        )
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LaneError(
            f"browser toolchain verifier did not produce a valid receipt: {receipt_path}"
        ) from exc
    validated_receipt = validate_browser_toolchain_receipt(
        receipt,
        node_executable=node_executable,
        receipt_path=receipt_path,
    )
    return BrowserToolchainResolution(node_executable, receipt_path, validated_receipt)


def configure_local_submodule_sources(lane: Lane) -> None:
    """Clone lane submodules from local object stores, never from the network."""

    for relative in REQUIRED_SUBMODULES:
        source = REPO_ROOT / relative
        if not source.exists():
            raise LaneError(f"required local submodule source is unavailable: {source}")
        git(["config", f"submodule.{relative}.url", str(source)], cwd=lane.path)


def link_shared_swissknife_dependencies(lane: Lane) -> list[str]:
    """Make integration-checkout dependencies available to a supervisor lane.

    The implementation daemon creates task worktrees below a lane and links
    their ``node_modules`` from the lane root.  Consequently, the lane itself
    must expose the installed dependencies from the integration checkout.
    Keep the links ephemeral: they are ignored build inputs, never repository
    configuration or a workstation-specific tracked path.
    """

    linked: list[str] = []
    for relative, required in SHARED_SWISSKNIFE_DEPENDENCY_PATHS:
        source_path = REPO_ROOT / relative
        try:
            source = source_path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            if required:
                raise LaneError(
                    "SwissKnife dependencies are unavailable in the integration checkout; "
                    f"run npm ci in {REPO_ROOT / 'swissknife'} before starting a lane"
                ) from exc
            continue
        if not source.is_dir():
            if required:
                raise LaneError(f"SwissKnife dependency path is not a directory: {source}")
            continue

        target = lane.path / relative
        try:
            target.relative_to(source)
        except ValueError:
            pass
        else:
            raise LaneError(f"refusing self-referential dependency link: {target} -> {source}")

        if target.is_symlink():
            try:
                if target.resolve(strict=True) == source:
                    linked.append(relative.as_posix())
                    continue
            except (OSError, RuntimeError):
                pass
            target.unlink()
        elif target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        linked.append(relative.as_posix())
    return linked


def ensure_lane(lane: Lane, *, dry_run: bool) -> dict[str, object]:
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
    if (lane.swissknife_path / ".git").exists() and not working_tree_clean(lane.swissknife_path):
        raise LaneError(
            f"SwissKnife lane checkout is dirty; refusing submodule update: {lane.swissknife_path}"
        )
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

    shared_dependency_paths = link_shared_swissknife_dependencies(lane)

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
    toolchain = verify_browser_toolchain(lane, receipt_name="lane-startup")
    return {
        "lane": lane.name,
        "root_branch": lane.root_branch,
        "swissknife_branch": lane.swissknife_branch,
        "path": str(lane.path),
        "task_worktree_root": str(lane.task_worktree_root),
        "root_head": git(["rev-parse", "HEAD"], cwd=lane.path),
        "swissknife_head": git(["rev-parse", "HEAD"], cwd=lane.swissknife_path),
        "browser_toolchain_receipt": str(toolchain.receipt_path),
        "browser_toolchain": toolchain.receipt,
        "shared_dependency_paths": shared_dependency_paths,
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
                "browser_toolchain_receipt": str(
                    lane.path / BROWSER_TOOLCHAIN_RECEIPT_DIR / "lane-startup.json"
                ),
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


def run_validation_command(
    lane: Lane,
    command: str,
    *,
    toolchain: BrowserToolchainResolution | None = None,
) -> BrowserToolchainResolution:
    link_shared_swissknife_dependencies(lane)
    if toolchain is None:
        toolchain = verify_browser_toolchain(lane, receipt_name="clean-checkout-validation")
    environment = os.environ.copy()
    node_directory = str(toolchain.node_executable.parent)
    environment["PATH"] = os.pathsep.join(
        part for part in (node_directory, environment.get("PATH", "")) if part
    )
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-c", command],
        cwd=lane.path,
        env=environment,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise LaneError(f"lane validation failed with exit code {result.returncode}: {command}")
    return toolchain


def merge_lane(lane: Lane, *, validation_command: str, apply: bool) -> dict[str, object]:
    if apply:
        lease_lane = f"{lane.name}-integration"
        require_swissknife_checkout_lease(
            ["--implement"],
            allowed_lanes={lease_lane: INTEGRATION_BOARDS[lease_lane]},
        )
    if not validation_command.strip():
        raise LaneError(
            "--validation-command is required so validation is serialized with the merge"
        )
    with integration_lock():
        validate_lane(lane)
        if not working_tree_clean(REPO_ROOT):
            raise LaneError(
                "integration checkout is dirty; commit or recover it before merging a lane"
            )
        if not working_tree_clean(REPO_ROOT / "swissknife"):
            raise LaneError(
                "integration SwissKnife submodule is dirty; commit or recover it before merging a lane"
            )
        toolchain = verify_browser_toolchain(lane, receipt_name="clean-checkout-validation")
        if not apply:
            return {
                "lane": lane.name,
                "validated": True,
                "merged": False,
                "reason": "dry_run",
                "branch": lane.root_branch,
                "validation_command": validation_command,
                "browser_toolchain_receipt": str(toolchain.receipt_path),
                "browser_toolchain": toolchain.receipt,
            }
        run_validation_command(lane, validation_command, toolchain=toolchain)
        merge = subprocess.run(
            ["git", "merge", "--no-ff", "--no-edit", lane.root_branch],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if merge.returncode != 0:
            subprocess.run(["git", "merge", "--abort"], cwd=REPO_ROOT, text=True, check=False)
            raise LaneError(
                f"merge failed and was aborted:\n{(merge.stderr or merge.stdout).strip()}"
            )
        return {
            "lane": lane.name,
            "validated": True,
            "merged": True,
            "branch": lane.root_branch,
            "integration_head": git(["rev-parse", "HEAD"]),
            "browser_toolchain_receipt": str(toolchain.receipt_path),
            "browser_toolchain": toolchain.receipt,
        }


def parser() -> argparse.ArgumentParser:
    parsed = argparse.ArgumentParser(description=__doc__)
    subparsers = parsed.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create or verify lane worktrees and branches")
    init.add_argument("--lane", choices=(*LANES, "all"), default="all")
    init.add_argument("--dry-run", action="store_true")

    status = subparsers.add_parser("status", help="print lane branch and cleanliness status")
    status.add_argument("--lane", choices=(*LANES, "all"), default="all")

    merge = subparsers.add_parser(
        "merge", help="validate one lane and merge it under the integration lock"
    )
    merge.add_argument("--lane", choices=tuple(LANES), required=True)
    merge.add_argument("--validation-command", required=True)
    merge.add_argument(
        "--apply", action="store_true", help="perform the merge; default is a locked dry run"
    )
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
        result = merge_lane(
            LANES[args.lane], validation_command=args.validation_command, apply=args.apply
        )
        print(json.dumps(result, indent=2))
        return 0
    except (LaneError, SwissKnifeLeaseGuardError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
