"""Supplement fulltree restoration with exact canonical Gitlink metadata.

No submodule clone, initialization, checkout, fetch, publication, or fit occurs.
The coordinator may later explicitly replace owned links with published tips.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import types
from pathlib import Path

BASE = Path("/home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/canonical_git")
OWNER_SHA = "5edf7bccc177c10f488f073a22cdb606b8df130c38496f091039f765750185aa"


def owner():
    path = Path(__file__).with_name("restore_leaf_trees.py")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != OWNER_SHA:
        raise ValueError("frozen tree restorer changed")
    module = types.ModuleType("frozen_tree_restorer")
    module.__file__ = str(path)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def restore(name):
    module = owner()
    old = BASE / "main-restoration" / name
    plan_path, prepared_path = old / "plan-v2.json", old / "prepared-v2.json"
    plan, prepared = json.loads(plan_path.read_text()), json.loads(prepared_path.read_text())
    selected = plan["authoritative_full_tree_snapshot"]["manifest_binding"]
    manifest_path = Path(selected["path"])
    data = manifest_path.read_bytes()
    if len(data) != selected["bytes"] or hashlib.sha256(data).hexdigest() != selected["sha256"]:
        raise ValueError("selected complete canonical manifest changed")
    manifest = json.loads(data)
    repository, snapshot = Path(plan["canonical_repository"]), manifest["snapshot_commit"]
    snapshot_tree = module.tree(repository, snapshot)
    canonical_links = {path: entry for path, entry in snapshot_tree.items() if entry["mode"] == "160000"}
    declared_links = {row["path"]: row for row in manifest["canonical_gitlinks_deferred"]}
    if set(canonical_links) != set(declared_links) or any(row["git_oid"] != declared_links[path]["git_oid"] or
            declared_links[path]["mode"] != "160000" for path, row in canonical_links.items()):
        raise ValueError("canonical Gitlink manifest mismatch")
    worktree = Path(prepared["fresh_worktree"])
    before = module.git(worktree, "rev-parse", "HEAD").stdout.decode().strip()
    if before != prepared["integrated_tip"]:
        raise ValueError("prepared fulltree tip changed")
    original_head = module.git(repository, "rev-parse", "HEAD").stdout
    index_path = Path(os.fsdecode(module.git(repository, "rev-parse", "--git-path", "index").stdout.strip()))
    if not index_path.is_absolute():
        index_path = repository / index_path
    original_index = module.binding(index_path)
    actual = module.tree(worktree, before)
    changed = {path: row for path, row in canonical_links.items() if actual.get(path) != row}
    conflicts = [path for path in actual if any(str(parent) in changed for parent in Path(path).parents
                                               if str(parent) != ".")]
    for start in range(0, len(conflicts), 128):
        module.git(worktree, "rm", "--cached", "-f", "--ignore-unmatch", "--", *conflicts[start:start + 128])
    rows = [b"160000 " + row["git_oid"].encode() + b"\t" + os.fsencode(path) + b"\0" for path, row in changed.items()]
    if rows:
        module.git(worktree, "update-index", "-z", "--index-info", data=b"".join(rows))
    if module.git(worktree, "diff", "--cached", "--quiet", accepted=(0, 1)).returncode:
        module.git(worktree, "commit", "-m", "Preserve canonical submodule links after archival history integration")
    tip = module.git(worktree, "rev-parse", "HEAD").stdout.decode().strip()
    final = module.tree(worktree, tip)
    for row in manifest["authoritative_source"]["selected_files"]:
        if row["state"] == "deleted":
            if row["path"] in final:
                raise ValueError("intentional canonical deletion reappeared")
        elif final.get(row["path"], {}).get("git_oid") != row["git_oid"] or final[row["path"]]["mode"] != row["mode"]:
            raise ValueError("canonical blob changed during Gitlink restoration")
    if any(final.get(path) != row for path, row in canonical_links.items()):
        raise ValueError("canonical Gitlink restoration failed")
    module.git(worktree, "merge-base", "--is-ancestor", before, tip)
    if module.git(repository, "rev-parse", "HEAD").stdout != original_head or module.binding(index_path) != original_index:
        raise ValueError("original canonical HEAD or index changed")
    output = BASE / "main-gitlink-restoration" / name
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    plan["restored_prepared_tip"] = tip
    new_plan = module.write(output / "plan-v2.json", {key: value for key, value in plan.items() if key != "content_sha256"})
    prepared = {key: value for key, value in prepared.items() if key != "content_sha256"}
    prepared.update({"integrated_tip": tip, "prior_fulltree_prepared_binding": module.binding(prepared_path),
                     "canonical_gitlink_restore_count": len(changed), "canonical_gitlink_path_count": len(canonical_links),
                     "complete_canonical_gitlink_paths_preserved": True, "plan_binding": new_plan,
                     "submodule_clone_or_checkout_executed": False, "origin_push_executed": False, "training_executed": False})
    selected = module.write(output / "prepared-v2.json", prepared)
    print(json.dumps({"name": name, "tip": tip, "gitlinks_restored": len(changed), "gitlinks": len(canonical_links),
                      "prepared_binding": selected}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", choices=list(owner().MANIFEST_SHA), required=True)
    args = parser.parse_args()
    os.umask(0o077)
    for name in args.targets:
        restore(name)


if __name__ == "__main__":
    main()
