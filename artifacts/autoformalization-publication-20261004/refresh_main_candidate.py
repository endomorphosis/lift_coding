"""Merge an advanced remote main into a fresh, fully restored publication candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
OWNER = BASE / "canonical_git/restore_leaf_trees.py"
OWNER_SHA = "5edf7bccc177c10f488f073a22cdb606b8df130c38496f091039f765750185aa"


def git(repo, *args, data=None, accepted=(0,)):
    result = subprocess.run(["git", "-c", "gc.auto=0", "-c", "submodule.recurse=false", "-C", str(repo), *args],
        input=data, capture_output=True, timeout=180,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_MERGE_AUTOEDIT": "no"})
    if result.returncode not in accepted:
        raise ValueError("private candidate operation failed: " + result.stderr.decode("utf-8", "replace")[-2000:])
    return result


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def binding(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def selected(path, sha):
    if binding(path)["sha256"] != sha:
        raise ValueError("externally selected candidate input differs")
    return json.loads(path.read_bytes())


def save(path, value):
    value = {k: v for k, v in value.items() if k != "content_sha256"}
    value["content_sha256"] = hashlib.sha256(raw(value)).hexdigest()
    with path.open("xb") as stream:
        stream.write(raw(value) + b"\n")
    return binding(path)


def refresh(args):
    if hashlib.sha256(OWNER.read_bytes()).hexdigest() != OWNER_SHA:
        raise ValueError("frozen restoration owner differs")
    owner = runpy.run_path(str(OWNER), run_name="candidate_restore_library")
    plan = selected(args.plan, args.plan_sha)
    prepared = selected(args.prepared, args.prepared_sha)
    old = Path(plan["fresh_worktree"])
    if git(old, "rev-parse", "HEAD").stdout.decode().strip() != prepared["integrated_tip"]:
        raise ValueError("selected original candidate advanced")
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    git(old, "fetch", "--no-tags", "--no-auto-maintenance", "--recurse-submodules=no", "origin",
        "+refs/heads/*:refs/remotes/origin/*")
    advertised = git(old, "ls-remote", "--heads", "origin", "refs/heads/main").stdout.decode().split()
    if len(advertised) != 2 or advertised[0] != git(old, "rev-parse", "refs/remotes/origin/main").stdout.decode().strip():
        raise ValueError("main advanced during baseline selection; preserve and refresh again")
    baseline = advertised[0]
    work = args.output / "publication-worktree"
    git(old, "worktree", "add", "-b", args.branch, str(work), prepared["integrated_tip"])
    merge = git(work, "merge", "--no-ff", "--no-edit", baseline, accepted=(0, 1))
    conflicts = {}
    for entry in git(work, "ls-files", "-u", "-z").stdout.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.split()
        conflicts.setdefault(path, {})[int(stage)] = (mode, oid)
    chosen, deleted = [], []
    for path, stages in conflicts.items():
        if 2 in stages:
            mode, oid = stages[2]
            chosen.append((path, mode, oid))
        else:
            deleted.append(path)
    for start in range(0, len(deleted), 128):
        git(work, "rm", "-f", "--ignore-unmatch", "--", *[os.fsdecode(p) for p in deleted[start:start + 128]])
    if chosen:
        git(work, "update-index", "-z", "--index-info", data=b"".join(m + b" " + oid + b"\t" + p + b"\0" for p, m, oid in chosen))
        blobs = [p for p, mode, _ in chosen if mode != b"160000"]
        if blobs:
            git(work, "checkout-index", "--force", "-z", "--stdin", data=b"\0".join(blobs) + b"\0")
    if git(work, "ls-files", "-u", "-z").stdout:
        raise ValueError("unresolved refreshed merge")
    if merge.returncode:
        git(work, "commit", "-m", "Merge current published main into retained source history")
    full_binding = plan["authoritative_full_tree_snapshot"]["manifest_binding"]
    full = selected(Path(full_binding["path"]), full_binding["sha256"])
    original_full = full
    if full["schema"] == "converted-canonical-snapshot-blob-pins/v1":
        original_pin = full["original_manifest_binding"]
        original_full = selected(Path(original_pin["path"]), original_pin["sha256"])
    canonical = owner["tree"](work, plan["authoritative_full_tree_snapshot"]["snapshot_commit"])
    for proposal in plan.get("published_gitlinks", []):
        if canonical.get(proposal["path"], {}).get("mode") != "160000":
            raise ValueError("published gitlink proposal cannot replace a source blob")
        canonical[proposal["path"]] = {"mode": "160000", "kind": "commit", "git_oid": proposal["oid"]}
    current = owner["tree"](work, "HEAD")
    deletions = [row["path"] for row in original_full["authoritative_source"]["selected_files"] if row["state"] == "deleted"]
    blocking = [name for name in current if any(str(parent) in canonical for parent in Path(name).parents if str(parent) != ".")]
    for start in range(0, len(blocking) + len(deletions), 128):
        paths = (blocking + deletions)[start:start + 128]
        git(work, "rm", "-f", "--ignore-unmatch", "--", *paths)
    changes = [(name, entry) for name, entry in canonical.items() if current.get(name) != entry]
    if changes:
        git(work, "update-index", "-z", "--index-info", data=b"".join(entry["mode"].encode() + b" " + entry["git_oid"].encode()
            + b"\t" + os.fsencode(name) + b"\0" for name, entry in changes))
        blobs = [name for name, entry in changes if entry["mode"] != "160000"]
        if blobs:
            git(work, "checkout-index", "--force", "-z", "--stdin", data=b"".join(os.fsencode(name) + b"\0" for name in blobs))
    if git(work, "diff", "--cached", "--quiet", accepted=(0, 1)).returncode:
        git(work, "commit", "-m", "Restore complete selected canonical source after main refresh")
    tip = git(work, "rev-parse", "HEAD").stdout.decode().strip()
    after = owner["tree"](work, tip)
    if any(after.get(name) != entry for name, entry in canonical.items()) or any(name in after for name in deletions):
        raise ValueError("complete refreshed canonical source restoration failed")
    for ancestor in (baseline, prepared["integrated_tip"]):
        git(work, "merge-base", "--is-ancestor", ancestor, tip)
    syntax = owner["syntax_findings"](work, baseline, tip, canonical)
    plan.update(fresh_worktree=str(work), integration_branch=args.branch,
                origin_main_sha256_or_git_oid=baseline, baseline_remote_ref="origin/main")
    plan_binding = save(args.output / "plan.json", plan)
    prepared.update(fresh_worktree=str(work), integrated_tip=tip, baseline_origin_main=baseline,
        baseline_remote_ref="origin/main", plan_binding=plan_binding, syntax_qualification=syntax,
        python_syntax_errors=syntax["newly_invalid_executable_source"],
        eligible_for_root_prepublication_review=not syntax["newly_invalid_executable_source"],
        refreshed_prior_plan_binding=binding(args.plan), refreshed_prior_prepared_binding=binding(args.prepared))
    prepared_binding = save(args.output / "prepared.json", prepared)
    print(json.dumps({"plan_binding": plan_binding, "prepared_binding": prepared_binding, "tip": tip,
        "baseline": baseline, "conflicts": len(conflicts), "new_invalid_source": len(syntax["newly_invalid_executable_source"])}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha", required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    parser.add_argument("--prepared-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--branch", required=True)
    os.umask(0o077)
    refresh(parser.parse_args())
