"""Resume a stopped private integration with batched conflict resolution.

Original live checkouts and indexes are untouched. The prior operation receipts
stay immutable; already resolved paths in an interrupted merge are explicitly
not reconstructed as fresh per-path provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

HELPER = Path(__file__).with_name("integrate_main.py")
HELPER_SHA = "98a07d90178b724ba28aeed8f7bc82e374ab0c93b172ff231b13f2283147e8a3"


def load_owner():
    if hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
        raise ValueError("frozen integration owner differs")
    spec = importlib.util.spec_from_file_location("frozen_integration_owner", HELPER)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    return owner


def batched_merge(owner, repo, selected, directory):
    head, kind = selected["oid"], selected["kind"]
    pending = owner.run(repo, ["rev-parse", "--verify", "--quiet", "MERGE_HEAD"], accepted=(0, 1))
    was_pending = pending.returncode == 0
    if was_pending and pending.stdout.decode().strip() != head:
        raise ValueError("interrupted merge head differs from exact next plan entry")
    if not was_pending and owner.run(repo, ["merge-base", "--is-ancestor", head, "HEAD"], accepted=(0, 1)).returncode == 0:
        return {"head": head, "kind": kind, "status": "already_ancestor", "conflicts": []}
    before = owner.text(repo, ["rev-parse", "HEAD"])
    if not was_pending:
        owner.run(repo, ["merge", "--no-ff", "--no-commit", "--allow-unrelated-histories", head], accepted=(0, 1))
    stages = owner.conflicts(repo)
    stage = "3" if kind == "canonical_current_source" else "2"
    deleted, ordinary, links, resolutions = [], [], [], []
    for path, choices in sorted(stages.items()):
        chosen = choices.get(stage)
        if chosen is None:
            deleted.append(path)
        elif chosen["mode"] == "160000":
            links.append((path, chosen))
        else:
            ordinary.append(path)
        resolutions.append({"path": path, "stages": choices, "selected_stage": stage, "selected": chosen})
    for start in range(0, len(deleted), 256):
        owner.run(repo, ["rm", "-rf", "--ignore-unmatch", "--", *deleted[start:start + 256]])
    for start in range(0, len(ordinary), 256):
        paths = ordinary[start:start + 256]
        owner.run(repo, ["checkout", "--theirs" if stage == "3" else "--ours", "--", *paths])
        owner.run(repo, ["add", "--", *paths])
    # Small gitlink set; ordinary source conflicts are resolved in batches.
    for path, chosen in links:
        owner.run(repo, ["update-index", "--add", "--cacheinfo", chosen["mode"], chosen["oid"], path])
    if owner.conflicts(repo):
        raise ValueError("unresolved index conflicts remain")
    owner.run(repo, ["commit", "-m", "Integrate preserved source history with batched conflict resolution",
                     "-m", "Source commit: " + head + "\nSource role: " + kind])
    return {"head": head, "kind": kind, "status": "merged", "before": before,
            "after": owner.text(repo, ["rev-parse", "HEAD"]), "conflicts": resolutions,
            "resumed_existing_merge": was_pending,
            "prior_partial_merge_resolution_details_reconstructed": False if was_pending else None,
            "resolution_policy": "canonical current source takes precedence; otherwise integrated current source"}


def resume(owner, plan, prior, output):
    repo = Path(plan["fresh_worktree"])
    if owner.text(repo, ["symbolic-ref", "--short", "HEAD"]) != plan["integration_branch"]:
        raise ValueError("selected private integration branch differs")
    if owner.normalized_origin(owner.text(repo, ["remote", "get-url", "origin"])) != plan["normalized_origin"]:
        raise ValueError("selected owned origin differs")
    records = []
    for path in sorted(prior.glob("merge-*.json")):
        index = len(records)
        if path.name != "merge-" + str(index).zfill(4) + ".json":
            raise ValueError("prior operation receipt gap")
        record = json.loads(path.read_text())
        if record["head"] != plan["heads"][index]["oid"]:
            raise ValueError("prior merge receipt differs from selected plan")
        owner.run(repo, ["merge-base", "--is-ancestor", record["head"], "HEAD"])
        records.append(record)
    owner.save(output / "resume-start.json", {"prior_receipt_directory": str(prior), "completed_prior_records": len(records),
        "selected_plan_head_count": len(plan["heads"]), "private_head_at_resume": owner.text(repo, ["rev-parse", "HEAD"]),
        "unmerged_path_count_at_resume": len(owner.conflicts(repo)), "owner_source_sha256": HELPER_SHA,
        "original_checkout_mutated": False, "prior_receipts_overwritten": False})
    for index in range(len(records), len(plan["heads"])):
        record = batched_merge(owner, repo, plan["heads"][index], output)
        records.append(record)
        owner.save(output / ("merge-" + str(index).zfill(4) + ".json"), record)
        print(json.dumps({"index": index, "status": record["status"], "conflict_count": len(record["conflicts"])}), flush=True)
    tip = owner.text(repo, ["rev-parse", "HEAD"])
    for selected in plan["heads"]:
        owner.run(repo, ["merge-base", "--is-ancestor", selected["oid"], tip])
    # Complete pinned source restoration and syntax classification are a separate
    # mandatory prepublication stage, performed by the reviewed tree restorer.
    report = {"schema": "worktree-main-integration-prepublication/v1", "canonical_repository": plan["canonical_repository"],
        "normalized_origin": plan["normalized_origin"], "fresh_worktree": str(repo),
        "baseline_origin_main": plan["origin_main_sha256_or_git_oid"], "baseline_remote_ref": plan.get("baseline_remote_ref", "origin/main"),
        "integrated_tip": tip, "selected_head_count": len(plan["heads"]), "all_selected_heads_ancestors": True,
        "merge_records": records, "published_gitlinks": [], "python_syntax_errors": [],
        "eligible_for_root_prepublication_review": False, "mandatory_fulltree_restoration_pending": True,
        "original_worktrees_replaced": False, "history_rewritten": False, "force_push_used": False, "origin_push_executed": False,
        "resume_receipt_directory": str(output), "prior_receipt_directory": str(prior),
        "interrupted_merge_resolution_provenance_scope": "Only remaining unmerged stages recorded; prior partially resolved paths are not reconstructed."}
    print(json.dumps({"prepared_binding": owner.save(output / "prepared.json", report)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha", required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = args.plan.read_bytes()
    if hashlib.sha256(data).hexdigest() != args.plan_sha:
        raise ValueError("externally selected plan differs")
    if args.output.exists():
        raise ValueError("fresh resume output required")
    args.output.mkdir(parents=True, mode=0o700)
    os.umask(0o077)
    resume(load_owner(), json.loads(data), args.prior, args.output)


if __name__ == "__main__":
    main()
