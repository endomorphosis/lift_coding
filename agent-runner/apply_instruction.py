#!/usr/bin/env python3
"""Apply code changes described in an agent task instruction.

This script enables a deterministic agent-runner mode where the dispatch issue
includes one or more fenced code blocks containing a unified diff.

Supported formats:
- ```diff\n...\n```
- ```patch\n...\n```

The patches are applied with `git apply --index` (staged) from within the target
repo working directory.

Exit codes:
- 0: success (including "no patches found")
- 2: patches were found but failed to apply
- 3: not in a git repository
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path


_FENCED_BLOCK_RE = re.compile(
    r"```(?P<lang>[A-Za-z0-9_+-]*)\n(?P<body>.*?)\n```\s*", re.DOTALL
)


def extract_fenced_blocks(text: str, allowed_langs: set[str]) -> list[str]:
    patches: list[str] = []
    for match in _FENCED_BLOCK_RE.finditer(text):
        lang = (match.group("lang") or "").strip().lower()
        body = match.group("body")
        if lang in allowed_langs:
            patches.append(body)
    return patches


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def ensure_git_repo(repo_dir: Path) -> bool:
    result = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo_dir)
    return result.returncode == 0 and result.stdout.strip() == "true"


def apply_unified_diff(repo_dir: Path, diff_text: str) -> tuple[bool, str]:
    """Apply a unified diff to repo_dir, staging changes.

    Returns (success, message)."""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".diff") as temp_file:
        temp_file.write(diff_text)
        temp_path = temp_file.name

    try:
        # --index stages changes; --whitespace=nowarn avoids noisy failures on EOL.
        result = _run(
            ["git", "apply", "--index", "--whitespace=nowarn", temp_path], cwd=repo_dir
        )
        if result.returncode != 0:
            msg = (result.stderr or result.stdout or "").strip()
            return False, msg or "git apply failed"
        return True, "applied"
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instruction-file", required=True)
    parser.add_argument("--repo-dir", default=".")
    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    instruction_path = Path(args.instruction_file)

    instruction_text = instruction_path.read_text(encoding="utf-8", errors="replace")

    if not ensure_git_repo(repo_dir):
        print("error: repo-dir is not a git working tree", flush=True)
        return 3

    patches = extract_fenced_blocks(instruction_text, {"diff", "patch"})

    if not patches:
        print("no patches found", flush=True)
        return 0

    for idx, patch in enumerate(patches, start=1):
        ok, msg = apply_unified_diff(repo_dir, patch)
        if not ok:
            print(f"patch {idx} failed: {msg}", flush=True)
            return 2

    print(f"applied {len(patches)} patch block(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
