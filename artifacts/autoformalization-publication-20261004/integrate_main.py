"""Integrate selected publication commits in fresh worktrees without rewriting history."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = Path(__file__).resolve().parent


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def save(path, value):
    data = raw(value) + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def run(repo, args, *, accepted=(0,), timeout=180):
    command = ["git", "-c", "gc.auto=0", "-C", str(repo), *args]
    result = subprocess.run(command, capture_output=True, timeout=timeout,
                            env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_MERGE_AUTOEDIT": "no"})
    if result.returncode not in accepted:
        raise RuntimeError("Git command failed: " + json.dumps(command) + "\n" + result.stderr.decode("utf-8", "replace")[-8000:])
    return result


def text(repo, args):
    return run(repo, args).stdout.decode().strip()


def conflicts(repo):
    entries = {}
    for entry in run(repo, ["ls-files", "--unmerged", "-z"]).stdout.split(b"\0"):
        if not entry:
            continue
        properties, name = entry.split(b"\t", 1)
        mode, oid, stage = properties.decode().split()
        path = name.decode("utf-8", "surrogateescape")
        entries.setdefault(path, {})[stage] = {"mode": mode, "oid": oid}
    return entries


def normalized_origin(remote):
    value = remote.strip().removesuffix(".git").removesuffix("/")
    for prefix in ("https://", "http://", "ssh://git@", "git@"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return value.replace("github.com:", "github.com/")


def merge(repo, head, kind, directory):
    if run(repo, ["merge-base", "--is-ancestor", head, "HEAD"], accepted=(0, 1)).returncode == 0:
        return {"head": head, "kind": kind, "status": "already_ancestor", "conflicts": []}
    before = text(repo, ["rev-parse", "HEAD"])
    result = run(repo, ["merge", "--no-ff", "--no-commit", "--allow-unrelated-histories", head], accepted=(0, 1))
    unresolved = conflicts(repo)
    selected_stage = "3" if kind == "canonical_current_source" else "2"
    resolutions = []
    for path, stages in sorted(unresolved.items()):
        selected = stages.get(selected_stage)
        if selected is None:
            run(repo, ["rm", "-f", "--ignore-unmatch", "--", path])
        elif selected["mode"] == "160000":
            run(repo, ["update-index", "--add", "--cacheinfo", selected["mode"], selected["oid"], path])
        else:
            run(repo, ["checkout", "--theirs" if selected_stage == "3" else "--ours", "--", path])
            run(repo, ["add", "--", path])
        resolutions.append({"path": path, "stages": stages, "selected_stage": selected_stage,
                            "selected": selected, "policy": "canonical_current_source" if selected_stage == "3" else "preserve_integrated_current_source"})
    if conflicts(repo):
        raise ValueError("unresolved Git index conflicts remain")
    pending = run(repo, ["rev-parse", "--verify", "--quiet", "MERGE_HEAD"], accepted=(0, 1))
    if pending.returncode != 0:
        raise RuntimeError("merge did not produce an auditable merge state: " + result.stderr.decode("utf-8", "replace")[-4000:])
    with tempfile.NamedTemporaryFile(mode="w", dir=directory, prefix="merge-message-", suffix=".txt") as message:
        message.write("Integrate preserved source history and worktree changes\n\n"
                      + "Source commit: " + head + "\nSource role: " + kind + "\n"
                      + "Conflicts retain current integrated source; canonical current source takes precedence.\n")
        message.flush()
        run(repo, ["commit", "--file", message.name])
    return {"head": head, "kind": kind, "status": "merged", "before": before,
            "after": text(repo, ["rev-parse", "HEAD"]), "conflicts": resolutions}


def integrate(plan, directory):
    canonical = Path(plan["canonical_repository"]).resolve()
    expected_origin = plan["normalized_origin"]
    remote = text(canonical, ["remote", "get-url", "origin"])
    if normalized_origin(remote) != expected_origin or not expected_origin.startswith("github.com/endomorphosis/"):
        raise ValueError("selected owned origin differs")
    baseline_ref = plan.get("baseline_remote_ref", "origin/main")
    if baseline_ref not in {"origin/main", "origin/master"}:
        raise ValueError("selected remote baseline must be main or master")
    baseline = text(canonical, ["rev-parse", baseline_ref])
    if baseline != plan["origin_main_sha256_or_git_oid"]:
        raise ValueError("origin/main advanced before integration; select a new plan")
    worktree = Path(plan["fresh_worktree"]).absolute()
    if worktree.exists():
        raise ValueError("fresh integration worktree required")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    run(canonical, ["worktree", "add", "-b", plan["integration_branch"], str(worktree), baseline])
    records = []
    for index, selected in enumerate(plan["heads"]):
        record = merge(worktree, selected["oid"], selected["kind"], directory)
        records.append(record)
        save(directory / ("merge-" + str(index).zfill(4) + ".json"), record)
        print(json.dumps({"repository": expected_origin, "head": selected["oid"], "index": index,
                          "status": record["status"], "conflict_count": len(record["conflicts"])}), flush=True)
    authoritative = plan.get("authoritative_source", {})
    restored = []
    source_commit = authoritative.get("snapshot_commit")
    for selected in authoritative.get("selected_files", []):
        path = worktree / selected["path"]
        if selected["state"] in {"absent", "deleted"}:
            if path.exists() or path.is_symlink():
                run(worktree, ["rm", "-f", "--ignore-unmatch", "--", selected["path"]])
                restored.append(selected["path"])
            continue
        observed = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes() if path.is_file() else None
        mode = "120000" if path.is_symlink() else "100755" if path.is_file() and path.stat().st_mode & stat.S_IXUSR else "100644"
        if observed is None or hashlib.sha256(observed).hexdigest() != selected["sha256"] or mode != selected["mode"]:
            run(worktree, ["checkout", source_commit, "--", selected["path"]])
            restored.append(selected["path"])
        observed = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        if hashlib.sha256(observed).hexdigest() != selected["sha256"]:
            raise ValueError("authoritative current source differs: " + selected["path"])
    if restored and run(worktree, ["diff", "--cached", "--quiet"], accepted=(0, 1)).returncode:
        run(worktree, ["commit", "-m", "Preserve pinned canonical source after history integration"])
    gitlinks = []
    for selected in plan.get("published_gitlinks", []):
        run(worktree, ["update-index", "--add", "--cacheinfo", "160000", selected["oid"], selected["path"]])
        gitlinks.append(selected)
    if gitlinks and run(worktree, ["diff", "--cached", "--quiet"], accepted=(0, 1)).returncode:
        run(worktree, ["commit", "-m", "Record published submodule source commits"])
    selected_tip = text(worktree, ["rev-parse", "HEAD"])
    for selected in plan["heads"]:
        run(worktree, ["merge-base", "--is-ancestor", selected["oid"], selected_tip])
    syntax_errors = []
    for name in run(worktree, ["diff", "--name-only", "-z", baseline, selected_tip, "--", "*.py"]).stdout.split(b"\0"):
        if not name:
            continue
        relative = name.decode("utf-8", "surrogateescape")
        path = worktree / relative
        if not path.is_file() or any(part in {"fixtures", "testdata", "vendor", "_vendor"} for part in Path(relative).parts):
            continue
        try:
            ast.parse(path.read_bytes(), filename=relative)
        except (SyntaxError, UnicodeError, ValueError) as error:
            syntax_errors.append({"path": relative, "error": str(error)})
    report = {"schema": "worktree-main-integration-prepublication/v1", "created_utc": datetime.now(UTC).isoformat(),
              "canonical_repository": str(canonical), "normalized_origin": expected_origin,
              "fresh_worktree": str(worktree), "baseline_origin_main": baseline, "integrated_tip": selected_tip,
              "selected_head_count": len(plan["heads"]), "all_selected_heads_ancestors": True,
              "baseline_remote_ref": baseline_ref, "authoritative_file_count": len(authoritative.get("selected_files", [])),
              "authoritative_paths_restored": restored, "pinned_canonical_source_preserved": True,
              "overlapping_worktree_contents": "Conflict resolution retains integrated source, followed by canonical source pins; every selected commit remains reachable.",
              "merge_records": records, "published_gitlinks": gitlinks, "python_syntax_errors": syntax_errors,
              "original_worktrees_replaced": False, "history_rewritten": False, "force_push_used": False,
              "origin_push_executed": False, "eligible_for_root_prepublication_review": not syntax_errors}
    binding = save(directory / "prepared.json", report)
    print(json.dumps({"prepared_binding": binding, "syntax_error_count": len(syntax_errors), "tip": selected_tip}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = args.plan.read_bytes()
    if hashlib.sha256(data).hexdigest() != args.plan_sha:
        raise ValueError("externally selected integration plan differs")
    plan = json.loads(data)
    if args.output.exists():
        raise ValueError("fresh integration receipt directory required")
    args.output.mkdir(parents=True, mode=0o700)
    integrate(plan, args.output)


if __name__ == "__main__":
    main()
