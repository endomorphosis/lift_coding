"""Restore complete canonical Git blob trees in prepared leaf worktrees.

This supplemental generation preserves every merge/history commit, unique
branch-only additions, and all original worktrees. It creates no publication or
training authorization. Canonical generator templates are not standalone Python.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import warnings
from pathlib import Path

BASE = Path("/home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/canonical_git")
MANIFEST_SHA = {"datasets": "489a687b8067172762bf4a9e068507760a5f59c0bb36e89f00c3007bfa0d1e09"}
PLAN_SHA = "58469aa56ade5f6c3e52858b918ebe6a342336745ad392181b6fbf536a42ff55"
PREPARED_SHA = "5cf2b6a93148e8f39dfc7aa2b6f5ba9da5e493eb1ef50824cde0d3902afbcf92"
FROZEN_BASE_OWNER_SHA = "5edf7bccc177c10f488f073a22cdb606b8df130c38496f091039f765750185aa"


def git(repository, *args, data=None, accepted=(0,)):
    result = subprocess.run(["git", "-c", "gc.auto=0", "-c", "core.hooksPath=/dev/null",
                             "-c", "commit.gpgsign=false", *args], cwd=repository, input=data,
                            capture_output=True, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    if result.returncode not in accepted:
        raise ValueError("Git supplemental operation failed: " + result.stderr.decode("utf-8", "replace")[-2000:])
    return result


def binding(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    value = {key: item for key, item in value.items() if key != "content_sha256"}
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    value["content_sha256"] = hashlib.sha256(raw).hexdigest()
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def tree(repository, reference):
    result = {}
    for entry in git(repository, "ls-tree", "-r", "-z", reference).stdout.split(b"\0"):
        if entry:
            metadata, path = entry.split(b"\t", 1)
            mode, kind, oid = metadata.decode().split()
            result[os.fsdecode(path)] = {"mode": mode, "kind": kind, "git_oid": oid}
    return result


def syntax_findings(repository, baseline, tip, canonical):
    changed = git(repository, "diff", "--name-only", "-z", baseline, tip, "--", "*.py").stdout
    current = tree(repository, tip)
    process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=repository,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    inherited, invalid, skipped, examined = [], [], [], 0
    try:
        for raw_path in changed.split(b"\0"):
            if not raw_path:
                continue
            path = os.fsdecode(raw_path)
            entry = current.get(path)
            if entry is None or entry["kind"] != "blob" or entry["mode"] not in {"100644", "100755"}:
                continue
            parts = set(Path(path).parts)
            if parts & {"fixtures", "testdata", "vendor", "_vendor", "templates"}:
                skipped.append(path)
                continue
            process.stdin.write(entry["git_oid"].encode() + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[:2] != [entry["git_oid"].encode(), b"blob"]:
                raise ValueError("syntax blob lookup mismatch")
            data = process.stdout.read(int(header[2]))
            if process.stdout.read(1) != b"\n":
                raise ValueError("syntax blob terminator missing")
            examined += 1
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    ast.parse(data, filename=path)
            except (SyntaxError, UnicodeError, ValueError) as error:
                finding = {"path": path, "git_oid": entry["git_oid"], "error": str(error)}
                if canonical.get(path, {}).get("git_oid") == entry["git_oid"]:
                    inherited.append(finding)
                else:
                    invalid.append(finding)
        process.stdin.close()
        if process.wait() != 0:
            raise ValueError("syntax batch lookup failed")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    return {"newly_invalid_executable_source": invalid, "inherited_canonical_syntax_findings": inherited,
            "excluded_fixture_vendor_and_template_paths": skipped, "examined_python_blob_count": examined,
            "scope": "Changed raw Git Python blobs relative to selected origin baseline; inherited errors require identical canonical OIDs. No all-source parse claim."}


def restore(name):
    old_directory = BASE / "main-preparation" / name
    old_prepared_path = old_directory / "integration-fast-03/prepared.json"
    old_plan_path = old_directory / "plan.json"
    if binding(old_prepared_path)["sha256"] != PREPARED_SHA or binding(old_plan_path)["sha256"] != PLAN_SHA:
        raise ValueError("selected datasets integration generation changed")
    old_prepared = json.loads(old_prepared_path.read_bytes())
    plan = json.loads(old_plan_path.read_bytes())
    manifest_path = BASE / "full-tree-pins-current" / (name + ".json")
    if binding(manifest_path)["sha256"] != MANIFEST_SHA[name]:
        raise ValueError("selected fulltree manifest changed")
    manifest = json.loads(manifest_path.read_bytes())
    source = manifest["authoritative_source"]
    canonical = {row["path"]: row for row in source["selected_files"] if row["state"] == "present"}
    snapshot_tree = tree(plan["canonical_repository"], source["snapshot_commit"])
    expected_blobs = {path: entry for path, entry in snapshot_tree.items() if entry["kind"] == "blob"}
    if set(canonical) != set(expected_blobs) or any(canonical[path]["mode"] != row["mode"] or
            canonical[path]["git_oid"] != row["git_oid"] for path, row in expected_blobs.items()):
        raise ValueError("fulltree manifest differs from canonical snapshot")
    canonical_links = {path: {**row, "path": path} for path, row in snapshot_tree.items() if row["mode"] == "160000"}
    declared_links = {row["path"]: row for row in manifest["canonical_gitlinks_deferred"]}
    if set(canonical_links) != set(declared_links) or any(row["git_oid"] != declared_links[path]["git_oid"]
            or declared_links[path]["mode"] != "160000" for path, row in canonical_links.items()):
        raise ValueError("canonical Gitlink manifest differs from snapshot")
    canonical_blob_count = len(canonical)
    canonical.update(canonical_links)
    worktree = Path(old_prepared["fresh_worktree"])
    before = git(worktree, "rev-parse", "HEAD").stdout.decode().strip()
    if before != old_prepared["integrated_tip"]:
        raise ValueError("prepared integration tip changed before restoration")
    original_repository = Path(plan["canonical_repository"])
    original_head = git(original_repository, "rev-parse", "HEAD").stdout
    index_path = Path(os.fsdecode(git(original_repository, "rev-parse", "--git-path", "index").stdout.strip()))
    if not index_path.is_absolute():
        index_path = original_repository / index_path
    original_index = binding(index_path)
    existing = tree(worktree, "HEAD")
    changed = [row for path, row in canonical.items() if existing.get(path, {}).get("git_oid") != row["git_oid"]
               or existing.get(path, {}).get("mode") != row["mode"]]
    deleted = [row["path"] for row in source["selected_files"] if row["state"] == "deleted"]
    conflicts = [path for path in existing if any(str(parent) in canonical for parent in Path(path).parents
                if str(parent) != ".")]
    # Explicit conflicting descendants are the only branch additions removed.
    for start in range(0, len(conflicts), 128):
        git(worktree, "rm", "-f", "--ignore-unmatch", "--", *conflicts[start:start + 128])
    for start in range(0, len(deleted), 128):
        git(worktree, "rm", "-f", "--ignore-unmatch", "--", *deleted[start:start + 128])
    index_rows = [row["mode"].encode() + b" " + row["git_oid"].encode() + b"\t" + os.fsencode(row["path"]) + b"\0"
                  for row in changed]
    index_rows.extend(b"0 " + b"0" * 40 + b"\t" + os.fsencode(path) + b"\0" for path in deleted)
    if index_rows:
        git(worktree, "update-index", "-z", "--index-info", data=b"".join(index_rows))
    changed_blobs = [row for row in changed if row["mode"] != "160000"]
    if changed_blobs:
        git(worktree, "checkout-index", "--force", "-z", "--stdin", data=b"".join(os.fsencode(row["path"]) + b"\0" for row in changed_blobs))
    if git(worktree, "diff", "--cached", "--quiet", accepted=(0, 1)).returncode:
        git(worktree, "commit", "-m", "Restore complete pinned canonical source tree after archival history integration")
    tip = git(worktree, "rev-parse", "HEAD").stdout.decode().strip()
    final_tree = tree(worktree, tip)
    if any(final_tree.get(path, {}).get("git_oid") != row["git_oid"] or final_tree.get(path, {}).get("mode") != row["mode"]
           for path, row in canonical.items()) or any(path in final_tree for path in deleted):
        raise ValueError("complete canonical restoration failed")
    git(worktree, "merge-base", "--is-ancestor", before, tip)
    if git(original_repository, "rev-parse", "HEAD").stdout != original_head or binding(index_path) != original_index:
        raise ValueError("original canonical HEAD or index changed")
    directory = BASE / "main-restoration" / name
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    findings = syntax_findings(worktree, plan["origin_main_sha256_or_git_oid"], tip, canonical)
    plan["authoritative_full_tree_snapshot"] = {"snapshot_commit": source["snapshot_commit"],
                                              "manifest_binding": binding(manifest_path)}
    plan["restored_prepared_tip"] = tip
    plan_binding = write(directory / "plan-v2.json", plan)
    prepared = {**old_prepared, "schema": "worktree-main-integration-fulltree-prepublication/v2", "integrated_tip": tip,
                "prior_prepared_binding": binding(old_prepared_path), "prior_plan_binding": binding(old_plan_path),
                "fulltree_manifest_binding": binding(manifest_path), "full_canonical_blob_path_count": canonical_blob_count,
                "restored_canonical_path_count": len(changed_blobs),
                "canonical_gitlink_path_count": len(canonical_links),
                "canonical_gitlink_restore_count": len(changed) - len(changed_blobs),
                "complete_canonical_gitlink_paths_preserved": True,
                "submodule_clone_or_checkout_executed": False, "removed_conflicting_branch_descendants": conflicts,
                "complete_canonical_snapshot_blobs_preserved": True, "intentional_deleted_paths_preserved": True,
                "prior_integrated_tip_ancestor": True, "original_head_and_index_preserved": True,
                "all_selected_heads_ancestors": True, "python_syntax_errors": findings["newly_invalid_executable_source"],
                "syntax_qualification": findings, "all_source_python_parses_claimed": False,
                "eligible_for_root_prepublication_review": not findings["newly_invalid_executable_source"],
                "plan_binding": plan_binding, "origin_push_executed": False, "training_executed": False}
    selected = write(directory / "prepared-v2.json", prepared)
    print(json.dumps({"name": name, "tip": tip, "restored": len(changed), "inherited_syntax": len(findings["inherited_canonical_syntax_findings"]),
                      "new_syntax_errors": len(findings["newly_invalid_executable_source"]), "prepared_binding": selected}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", choices=list(MANIFEST_SHA), required=True)
    args = parser.parse_args()
    if hashlib.sha256(Path(__file__).with_name("restore_leaf_trees.py").read_bytes()).hexdigest() != FROZEN_BASE_OWNER_SHA:
        raise ValueError("frozen original restorer changed")
    os.umask(0o077)
    for name in args.targets:
        restore(name)


if __name__ == "__main__":
    main()
