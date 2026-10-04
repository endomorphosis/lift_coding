"""One explicit branch-cutoff recovery in an isolated publication repository.

The original 223 heads plus one newly observed owned branch are retained.
Subsequent external ref additions are disclosed, never selected implicitly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import types
from pathlib import Path

BASE = Path(__file__).parent
ALGORITHM_SHA = "ba103b5581f20f69f4c09930cdc233cfdd6a021d1162158fc1d94158d190fb0d"
RESTORER_SHA = "5edf7bccc177c10f488f073a22cdb606b8df130c38496f091039f765750185aa"
NEW_HEAD = "c5e099195ef509503891a8a2b3df5739c8bf7ee6"
NEW_REF = "refs/heads/codex/terminal-ir-publication-20261004-accelerate-01"


def load(name, digest):
    path = BASE / name
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("selected frozen source changed")
    module = types.ModuleType("isolated_" + name.replace(".", "_"))
    module.__file__ = str(path)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def preserved(before, after):
    for key in ("head", "index", "selected_working_file_bytes"):
        if before[key] != after[key]:
            raise ValueError("original HEAD, index, or selected source bytes changed")
    old = dict(row.split(" ", 1) for row in before["refs"])
    new = dict(row.split(" ", 1) for row in after["refs"])
    if any(new.get(ref) != oid for ref, oid in old.items()):
        raise ValueError("a captured original ref moved or disappeared")
    return sorted(set(after["refs"]) - set(before["refs"]))


def recover(output):
    module = load("convert_history_hf_references.py", ALGORITHM_SHA)
    restorer = load("restore_leaf_trees.py", RESTORER_SHA)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    original_plan_pin, original_prepared_pin = module.binding(module.PLAN), module.binding(module.PREPARED)
    original_plan, original_prepared = module.selected_json(original_plan_pin), module.selected_json(original_prepared_pin)
    if module.git(module.SOURCE, "rev-parse", NEW_REF).decode().strip() != NEW_HEAD:
        raise ValueError("explicit additional cutoff branch advanced")
    before = module.source_state(module.SOURCE, original_plan["authoritative_source"]["selected_files"])
    remote = module.git(module.SOURCE, "remote", "get-url", "origin").decode().strip()
    advertised = module.git(module.SOURCE, "ls-remote", "--refs", "origin").decode().splitlines()
    repository = output / "isolated.git"
    module.git(module.SOURCE, "clone", "--bare", "--shared", "--no-hardlinks", str(module.SOURCE), str(repository))
    module.git(repository, "remote", "set-url", "origin", remote)
    module.git(repository, "fetch", "--no-tags", "--recurse-submodules=no", "origin", "+refs/*:refs/published-github/*")
    refs, published = [], []
    for row in advertised:
        oid, ref = row.split("\t")
        private_ref = "refs/published-github/" + ref.removeprefix("refs/")
        if module.git(repository, "rev-parse", private_ref).decode().strip() != oid:
            raise ValueError("published ref selection changed during capture")
        commit = module.git(repository, "rev-parse", "--verify", private_ref + "^{commit}", accepted=(0, 128)).decode().strip()
        published.append(commit)
        refs.append({"ref": ref, "git_oid": oid, "isolated_ref": private_ref, "commit_oid": commit})
    if module.git(module.SOURCE, "ls-remote", "--refs", "origin").decode().splitlines() != advertised:
        raise ValueError("live published ref selection changed during capture")
    worktree = output / "source-supplement-worktree"
    branch = "publication/hf-source-supplement-20261004/accelerate"
    module.git(repository, "worktree", "add", "-b", branch, str(worktree), module.EXPECTED_TIP)
    module.git(worktree, "merge", "--no-ff", "--no-commit", "-X", "ours", NEW_HEAD, accepted=(0, 1))
    previous_tree = module.tree(worktree, module.EXPECTED_TIP)
    conflicts = {os.fsdecode(row.split(b"\t", 1)[1]) for row in module.git(worktree, "ls-files", "-u", "-z").split(b"\0") if row}
    if conflicts:
        module.git(worktree, "rm", "--cached", "-f", "--ignore-unmatch", "--", *sorted(conflicts))
        repair = [previous_tree[path]["mode"].encode() + b" " + previous_tree[path]["git_oid"].encode() + b"\t" + os.fsencode(path) + b"\0"
                  for path in sorted(conflicts) if path in previous_tree]
        if repair:
            module.git(worktree, "update-index", "-z", "--index-info", data=b"".join(repair))
    manifest_pin = original_plan["authoritative_full_tree_snapshot"]["manifest_binding"]
    manifest = module.selected_json(manifest_pin)
    canonical = module.tree(repository, manifest["snapshot_commit"])
    current = module.tree(repository, module.git(worktree, "write-tree").decode().strip())
    descendants = [path for path in current if any(str(parent) in canonical for parent in Path(path).parents if str(parent) != ".")]
    for offset in range(0, len(descendants), 128):
        module.git(worktree, "rm", "--cached", "-f", "--ignore-unmatch", "--", *descendants[offset:offset + 128])
    deleted = [row["path"] for row in manifest["authoritative_source"]["selected_files"] if row["state"] == "deleted"]
    rows = [row["mode"].encode() + b" " + row["git_oid"].encode() + b"\t" + os.fsencode(path) + b"\0" for path, row in canonical.items()]
    rows.extend(b"0 " + b"0" * 40 + b"\t" + os.fsencode(path) + b"\0" for path in deleted)
    module.git(worktree, "update-index", "-z", "--index-info", data=b"".join(rows))
    tree_oid = module.git(worktree, "write-tree").decode().strip()
    tip = module.git(worktree, "-c", "user.name=Workspace publication", "-c", "user.email=publication@example.invalid",
                     "commit-tree", tree_oid, "-p", module.EXPECTED_TIP, "-p", NEW_HEAD,
                     data=b"Preserve one explicit additional branch cutoff with canonical source authority\n").decode().strip()
    module.git(worktree, "update-ref", "refs/heads/" + branch, tip, module.EXPECTED_TIP)
    module.git(worktree, "reset", "--hard", tip)
    actual = module.tree(worktree, tip)
    if any(actual.get(path) != row for path, row in canonical.items()) or any(path in actual for path in deleted):
        raise ValueError("complete canonical source authority restoration failed")
    heads = [*original_plan["heads"], {"kind": "explicit_additional_cutoff_history", "oid": NEW_HEAD, "selected_refs": [NEW_REF]}]
    for head in heads:
        module.git(worktree, "merge-base", "--is-ancestor", head["oid"], tip)
    findings = restorer.syntax_findings(worktree, original_plan["origin_main_sha256_or_git_oid"], tip, canonical)
    if findings["newly_invalid_executable_source"]:
        raise ValueError("newly invalid executable source in cutoff supplement")
    plan = {key: value for key, value in original_plan.items() if key != "content_sha256"}
    plan.update({"fresh_worktree": str(worktree), "integration_branch": branch, "heads": heads, "restored_prepared_tip": tip})
    plan_pin = module.write(output / "supplement-plan-v2.json", plan)
    prepared = {key: value for key, value in original_prepared.items() if key != "content_sha256"}
    prepared.update({"fresh_worktree": str(worktree), "integrated_tip": tip, "selected_head_count": len(heads),
                     "plan_binding": plan_pin, "syntax_qualification": findings, "python_syntax_errors": [],
                     "prior_plan_binding": original_plan_pin, "prior_prepared_binding": original_prepared_pin,
                     "additional_cutoff_head": NEW_HEAD, "eligible_for_root_prepublication_review": True})
    prepared_pin = module.write(output / "supplement-prepared-v2.json", prepared)
    extra_refs = preserved(before, module.source_state(module.SOURCE, original_plan["authoritative_source"]["selected_files"]))
    preflight = {"schema": "isolated-hf-history-reference-preflight/v1", "original_repository": str(module.SOURCE),
                 "isolated_repository": str(repository), "selected_plan_binding": plan_pin, "selected_prepared_binding": prepared_pin,
                 "original_tip": tip, "published_refs": refs, "published_commit_exclusions": sorted(set(published)),
                 "original_state": before, "original_state_preserved": True, "external_added_refs_not_selected": extra_refs,
                 "selected_branch_cutoff": "original223_plus_one_explicit_additional_head", "scope": "Fresh isolated cutoff supplement before conversion.",
                 "git_lfs_migration_executed": False, "origin_push_executed": False, "hf_upload_executed": False, "training_executed": False}
    preflight_pin = module.write(output / "preflight.json", preflight)
    original_artifact_pin = module.binding(BASE / "hf-history-conversion-01/artifact-selection.json")
    artifacts = module.selected_json(original_artifact_pin)
    references = {row["original_path"]: {"schema": "immutable-hf-large-artifact-reference/v1", **row,
                  "content_kind": "generated_nonweight_data", "original_raw_payload_omitted_from_this_git_tree": True} for row in artifacts["rows"]}
    if set(references) != set(module.ASSETS) or any((row["source_git_blob_oid"], row["bytes"], row["sha256"]) != module.ASSETS[path]
                                                   for path, row in references.items()):
        raise ValueError("exact frozen oversized asset selections required")
    result = module.rewrite_unpublished(repository, tip, preflight["published_commit_exclusions"], references)
    mapped = [{**row, "original_oid": row["oid"], "oid": result["commit_map"].get(row["oid"], row["oid"])} for row in heads]
    for row in mapped:
        module.git(repository, "merge-base", "--is-ancestor", row["oid"], result["tip"])
    module.git(repository, "merge-base", "--is-ancestor", plan["origin_main_sha256_or_git_oid"], result["tip"])
    if module.tree(repository, tip) != module.tree(repository, result["tip"]):
        raise ValueError("converted current source tree differs")
    objects = module.git(repository, "rev-list", "--objects", result["tip"], "--not", *preflight["published_commit_exclusions"])
    metadata = module.git(repository, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                          data=b"\n".join(row.split(b" ", 1)[0] for row in objects.splitlines()) + b"\n")
    if any(row.split()[1] == b"blob" and int(row.split()[2]) > 100 * 1024 * 1024 for row in metadata.splitlines()):
        raise ValueError("oversized unpublished blobs remain")
    extra_refs = preserved(before, module.source_state(module.SOURCE, plan["authoritative_source"]["selected_files"]))
    converted_ref = "refs/heads/publication/hf-references-20261004/accelerate"
    module.git(repository, "update-ref", converted_ref, result["tip"], "0" * 40)
    report = {"schema": "isolated-hf-history-reference-conversion/v1", "preflight_binding": preflight_pin,
              "artifact_selection_binding": original_artifact_pin, "original_tip": tip, "converted_tip": result["tip"],
              "converted_ref": converted_ref, "isolated_repository": str(repository), "commit_map": result["commit_map"],
              "tree_map": result["tree_map"], "mapped_selected_heads": mapped, "replaced_tree_occurrences": result["replaced_tree_occurrences"],
              "references": references, "reference_blob_oids": result["reference_blob_oids"], "all_mapped_selected_heads_ancestors": True,
              "published_main_unchanged_and_ancestor": True, "final_current_tree_exactly_preserved": True,
              "original_repository_state_preserved": True, "external_added_refs_not_selected": extra_refs,
              "newly_reachable_oversized_git_blob_count": 0, "original_rewritten_commit_oids_remote_ancestry_claimed": False,
              "signature_headers_modified": False, "git_lfs_migration_executed": False, "git_lfs_upload_executed": False,
              "origin_push_executed": False, "hf_upload_executed": False, "training_executed": False,
              "scope": "Exact oversized historical path/blob substitutions after one explicit branch cutoff; original captured refs preserved; later external ref additions disclosed."}
    return module.write(output / "conversion.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    print(json.dumps(recover(args.output)), flush=True)


if __name__ == "__main__":
    main()
