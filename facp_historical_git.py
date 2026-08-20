"""Git helpers for validating immutable Formal Assurance campaign evidence.

FACP receipts bind the exact repository state that produced them.  Once later
tasks or an integration merge advance a repository, validation must read the
recorded Git object instead of silently reinterpreting the receipt against the
current working tree.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def git_output(repository: Path, *arguments: str) -> str:
    """Run a read-only Git query and return its stripped standard output."""

    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def current_head(repository: Path) -> str:
    """Return the exact checked-out commit for *repository*."""

    return git_output(repository, "rev-parse", "HEAD")


def assert_historical_ancestor(
    repository: Path,
    recorded_commit: str,
    current_commit: str | None = None,
) -> str:
    """Require a receipt commit to exist and remain in current ancestry.

    Returns the resolved current commit so callers can independently compare it
    with a superproject gitlink.  Equality is intentionally not required: a
    later commit makes the receipt historical, not false and not current.
    """

    assert FULL_SHA_RE.fullmatch(recorded_commit), recorded_commit
    resolved_current = current_commit or current_head(repository)
    assert FULL_SHA_RE.fullmatch(resolved_current), resolved_current
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "cat-file",
            "-e",
            f"{recorded_commit}^{{commit}}",
        ],
        check=True,
        capture_output=True,
    )
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "merge-base",
            "--is-ancestor",
            recorded_commit,
            resolved_current,
        ],
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 0, (
        f"recorded evidence commit {recorded_commit} is not an ancestor of "
        f"current commit {resolved_current} in {repository}"
    )
    return resolved_current


def blob_bytes(repository: Path, commit: str, path: str) -> bytes:
    """Read *path* from the immutable tree at *commit*."""

    assert_historical_ancestor(repository, commit)
    completed = subprocess.run(
        ["git", "-C", str(repository), "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def blob_text(repository: Path, commit: str, path: str) -> str:
    """Read UTF-8 source text from the immutable tree at *commit*."""

    return blob_bytes(repository, commit, path).decode("utf-8")


def tree_path_exists(repository: Path, commit: str, path: str) -> bool:
    """Return whether *path* is tracked in the recorded Git tree."""

    assert_historical_ancestor(repository, commit)
    completed = subprocess.run(
        ["git", "-C", str(repository), "cat-file", "-e", f"{commit}:{path}"],
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


def superproject_gitlink(repository: Path, treeish: str, path: str) -> str:
    """Return the submodule commit recorded at *path* in *treeish*."""

    row = git_output(repository, "ls-tree", treeish, "--", path)
    fields = row.split()
    assert len(fields) >= 3 and fields[0] == "160000" and fields[1] == "commit", row
    return fields[2]
