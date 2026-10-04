"""Package a separately qualified isolated HF-reference history for review.

Original unpublished OIDs are preserved locally. This profile checks mapped
ancestry and selected source content; it does not claim original OID ancestry.
No publication, model execution, or original source modification occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import types
from pathlib import Path

OWNER_SHA = "ba103b5581f20f69f4c09930cdc233cfdd6a021d1162158fc1d94158d190fb0d"


def owner():
    path = Path(__file__).with_name("convert_history_hf_references.py")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != OWNER_SHA:
        raise ValueError("frozen HF history converter changed")
    module = types.ModuleType("frozen_hf_history_converter")
    module.__file__ = str(path)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def check_original_state(before, after):
    for key in ("head", "index", "selected_working_file_bytes"):
        if before[key] != after[key]:
            raise ValueError("original HEAD, index, or selected file bytes changed")
    old = dict(row.split(" ", 1) for row in before["refs"])
    new = dict(row.split(" ", 1) for row in after["refs"])
    if any(new.get(ref) != oid for ref, oid in old.items()):
        raise ValueError("a captured original ref moved or disappeared")
    return sorted(set(after["refs"]) - set(before["refs"]))


def prepare(directory, hf_publication_receipt_binding):
    module = owner()
    conversion_pin = module.binding(directory / "conversion.json")
    conversion = module.selected_json(conversion_pin)
    if conversion != module.seal(conversion):
        raise ValueError("conversion receipt seal differs")
    preflight = module.selected_json(conversion["preflight_binding"])
    original_plan = module.selected_json(preflight["selected_plan_binding"])
    original_prepared = module.selected_json(preflight["selected_prepared_binding"])
    # This binding selects the uploader's durable verification receipt. The
    # publisher separately checks its contents and immutable revision joins.
    module.selected_json(hf_publication_receipt_binding)
    original_manifest_pin = original_plan["authoritative_full_tree_snapshot"]["manifest_binding"]
    original_manifest = module.selected_json(original_manifest_pin)
    original_snapshot = original_manifest["snapshot_commit"]
    mapped_snapshot = conversion["commit_map"].get(original_snapshot, original_snapshot)
    repository = Path(conversion["isolated_repository"])
    original_tree = module.tree(repository, original_snapshot)
    mapped_tree = module.tree(repository, mapped_snapshot)
    if original_tree != mapped_tree:
        raise ValueError("this publication packaging profile requires an unchanged canonical snapshot tree")
    module.git(repository, "merge-base", "--is-ancestor", mapped_snapshot, conversion["converted_tip"])
    if module.tree(repository, conversion["original_tip"]) != module.tree(repository, conversion["converted_tip"]):
        raise ValueError("current final source tree differs")
    check_original_state(preflight["original_state"], module.source_state(module.SOURCE, original_plan["authoritative_source"]["selected_files"]))
    output = directory / "publication-selection"
    output.mkdir(mode=0o700, exist_ok=False)
    worktree = directory / "publication-worktree"
    branch = conversion["converted_ref"].removeprefix("refs/heads/")
    module.git(repository, "worktree", "add", str(worktree), branch)
    snapshot_ref = "refs/heads/publication/canonical-hf-references-20261004/accelerate"
    module.git(repository, "update-ref", snapshot_ref, mapped_snapshot, "0" * 40)
    manifest = {
        "schema": "converted-canonical-snapshot-blob-pins/v1",
        "repository": original_plan["canonical_repository"],
        "original_snapshot_commit": original_snapshot, "mapped_snapshot_commit": mapped_snapshot,
        "original_manifest_binding": original_manifest_pin, "conversion_receipt_binding": conversion_pin,
        "canonical_blob_path_count": original_manifest["canonical_blob_path_count"],
        "canonical_gitlinks_deferred": original_manifest["canonical_gitlinks_deferred"],
        "explicit_hf_substitutions": [], "final_canonical_snapshot_tree_exactly_preserved": True,
        "origin_push_executed": False, "training_executed": False,
    }
    manifest_pin = module.write(output / "converted-fulltree-manifest.json", manifest)
    plan = {key: value for key, value in original_plan.items() if key != "content_sha256"}
    plan.update({"fresh_worktree": str(worktree), "integration_branch": branch,
                 "baseline_remote_ref": "refs/published-github/heads/main", "heads": conversion["mapped_selected_heads"],
                 "authoritative_source": {**plan["authoritative_source"], "snapshot_commit": mapped_snapshot},
                 "authoritative_full_tree_snapshot": {"snapshot_commit": mapped_snapshot, "manifest_binding": manifest_pin},
                 "restored_prepared_tip": conversion["converted_tip"], "history_conversion_profile": conversion["schema"],
                 "conversion_receipt_binding": conversion_pin, "hf_publication_receipt_binding": hf_publication_receipt_binding,
                 "hf_artifact_publication_receipts": [hf_publication_receipt_binding]})
    plan_pin = module.write(output / "plan-v3.json", plan)
    prepared = {
        "schema": "worktree-main-integration-hf-reference-prepublication/v3",
        "canonical_repository": plan["canonical_repository"], "fresh_worktree": str(worktree),
        "normalized_origin": plan["normalized_origin"], "integrated_tip": conversion["converted_tip"],
        "baseline_origin_main": plan["origin_main_sha256_or_git_oid"], "baseline_remote_ref": plan["baseline_remote_ref"],
        "selected_head_count": len(plan["heads"]), "syntax_qualification": original_prepared["syntax_qualification"],
        "python_syntax_errors": [], "eligible_for_root_prepublication_review": True,
        "plan_binding": plan_pin, "fulltree_manifest_binding": manifest_pin,
        "full_canonical_blob_path_count": manifest["canonical_blob_path_count"],
        "conversion_receipt_binding": conversion_pin,
        "hf_publication_receipt_binding": hf_publication_receipt_binding,
        "prior_plan_binding": preflight["selected_plan_binding"], "prior_prepared_binding": preflight["selected_prepared_binding"],
        "original_integrated_tip": conversion["original_tip"], "mapped_prior_integrated_tip": conversion["converted_tip"],
        "original_integrated_tip_ancestor": False, "mapped_prior_integrated_tip_ancestor": True,
        "all_mapped_selected_heads_ancestors": True, "original_rewritten_commit_oids_remote_ancestry_claimed": False,
        "original_repository_state_preserved": True, "original_head_and_index_preserved": True,
        "complete_canonical_snapshot_blobs_preserved": True, "intentional_deleted_paths_preserved": True,
        "complete_canonical_gitlink_paths_preserved": True, "final_current_tree_exactly_preserved": True,
        "all_source_python_parses_claimed": False, "history_rewritten": True, "force_push_used": False,
        "original_worktrees_replaced": False, "submodule_clone_or_checkout_executed": False,
        "origin_push_executed": False, "git_lfs_migration_executed": False, "git_lfs_upload_executed": False,
        "training_executed": False,
    }
    prepared_pin = module.write(output / "prepared-v3.json", prepared)
    external_refs = check_original_state(preflight["original_state"], module.source_state(module.SOURCE, original_plan["authoritative_source"]["selected_files"]))
    return {"plan_binding": plan_pin, "prepared_binding": prepared_pin, "manifest_binding": manifest_pin,
            "tip": conversion["converted_tip"], "worktree": str(worktree), "external_added_refs_not_selected": external_refs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--hf-publication-receipt-binding", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    print(json.dumps(prepare(args.directory, json.loads(args.hf_publication_receipt_binding.read_bytes()))), flush=True)


if __name__ == "__main__":
    main()
