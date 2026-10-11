"""Prepare one byte-authenticated workspace archive after immutable publication.

No model, test, network or Git operation is performed. Every published file is
mapped to retained local bytes or its exact immutable Hub identity. Full raw
checkpoint containers remain on the Hub; the source/audit closure is retained.
Only explicitly declared release files and supplementary receipts are read.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote

F = Path(__file__).resolve().parent
ARMS = ("bce", "positive_margin")
COHORTS = ("fresh_final", "earlier_scope", "earlier_trigger", "earlier_support_action", "earlier_support_gate")
REPO = "Publicus/legal-ir-autoencoder"
PREFIX = "experiments/positive-retention-20261011/run-01"
ARCHIVE_NAME = "legal-positive-retention-20261011"
REQUIRED_SOURCE = (
    "source/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_retention_gate.py",
    "source/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_retention_selection.py",
    "source/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_decoder.py",
    "source/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_proposal.py",
    "source/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_trigger_readout.py",
    "source/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_support_action.py",
    "source/ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_support_gate.py",
    "source/ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py",
    "source/ipfs_datasets_py/logic/deontic/utils/deontic_parser.py",
    "source/tests/unit/logic/test_legal_scope_retention_gate.py",
    "source/tests/unit/logic/test_legal_scope_retention_selection.py",
    "source/tests/unit/logic/test_legal_scope_support_gate.py",
)
EXTRA_REQUIRED = (
    "audit_trial.py", "selected-checkpoint-replay.json", "replay_retention_gate.py",
    "replay-helper-build.json", "replay-source-review.json", "protocol-review.json",
    "trial-artifact-audit.json", "results-resource-review.json", "release-preparation.json", "publication-preflight-review.json",
    "incoming-progress-review.json", "incoming-main-integration.json", "workspace-latest-integration.json",
    "resource-observation-phase-correction.json", "resource-preservation-projection.json",
    "prepare_workspace_archive-draft-01.py", "archive-helper-build-draft-01.json",
    "prepare_workspace_archive-draft-02.py", "archive-helper-build-draft-02.json",
    "archive-guard-preflight.json", "archive-recovery-preflight.json",
    "prepare_workspace_archive.py", "archive-helper-build.json",
)
RECOVERY_FILES = (
    "hub-upload-error.json", "hub-upload-reconciliation.json", "hub-upload-batch-proposal.json",
    "hub-upload-batch-events.jsonl", "hub-upload-batch-recovery.json", "recover_hub_upload.py",
    "hub-recovery-source-review.json",
)
RAW_SCHEMAS = frozenset(("legal-scope-span-decoder-checkpoint/v1", "legal-scope-trigger-readout-checkpoint/v1",
                         "legal-scope-support-action-checkpoint/v1", "legal-scope-support-gate-checkpoint/v1",
                         "legal-scope-retention-gate-checkpoint/v1"))
SECRET_PATTERNS = (
    re.compile(rb"(?<![A-Za-z0-9_])hf_[A-Za-z0-9]{30,}"),
    re.compile(rb"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(rb"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{50,}"),
    re.compile(rb"(?<![A-Za-z0-9_])sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ordinary_path(path, *, exists=True):
    path = Path(path).absolute()
    for component in (path, *path.parents):
        require(not component.is_symlink(), "symlink path refused: " + str(component))
    return path.resolve(strict=exists)


def relative(value):
    require(type(value) is str and value and str(PurePosixPath(value)) == value
            and not value.startswith("/") and ".." not in PurePosixPath(value).parts
            and not any(character in value for character in ("*", "?", "[", "]", "\\", "\x00")),
            "bounded ordinary relative path required")
    return value


def byte_pin(raw):
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def file_pin(path):
    path = ordinary_path(path)
    require(path.is_file(), "ordinary file required: " + str(path))
    return {"path": str(path), **byte_pin(path.read_bytes())}


def same_bytes(left, right):
    return left["bytes"] == right["bytes"] and left["sha256"] == right["sha256"]


def pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def parse_json(raw):
    return json.loads(raw, object_pairs_hook=pairs_without_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read_json(path):
    return parse_json(ordinary_path(path).read_bytes())


def require_reference(reference):
    require(type(reference) is dict and set(reference) == {"path", "bytes", "sha256"}
            and file_pin(reference["path"]) == reference, "exact artifact reference differs")
    return Path(reference["path"])


def nodes(value):
    pending = [value]
    while pending:
        node = pending.pop()
        yield node
        if type(node) is dict:
            pending.extend(node.values())
        elif type(node) is list:
            pending.extend(node)


def contains_pin(value, expected):
    return any(type(node) is dict and "bytes" in node and "sha256" in node
               and same_bytes(node, expected) for node in nodes(value))


def has_raw_checkpoint_payload(node):
    """A schema mention is metadata; tensor/optimizer dictionaries are payload."""
    return type(node) is dict and (
        "gate_state" in node or "json_utf8" in node
        or (node.get("schema") in RAW_SCHEMAS
            and any(type(node.get(name)) is dict for name in
                    ("optimizer", "state", "state_dict", "head_state", "model_state",
                     "tensor_state", "tensors", "weights"))))


def checked_copy_bytes(path):
    path = ordinary_path(path)
    require(path.is_file(), "ordinary copy source required")
    require(path.name not in (".env", ".netrc", "id_rsa", "id_ed25519")
            and path.suffix.lower() not in (".pem", ".key", ".pyc", ".pt", ".pth", ".bin", ".safetensors", ".ckpt", ".onnx"),
            "credential, binary-weight or generated-code file refused")
    raw = path.read_bytes()
    require(not any(pattern.search(raw) for pattern in SECRET_PATTERNS),
            "credential/private-key pattern found; content omitted from error")
    if path.suffix == ".json":
        data = parse_json(raw)
        require(not any(has_raw_checkpoint_payload(node) for node in nodes(data)),
                "embedded raw checkpoint weights refused outside immutable Hub mapping")
    return raw


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def encoded_json(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def verify_declared_tree(stage, files):
    """List only directories derived from manifest paths; never walk worktrees."""
    children = {"": set()}
    for name in files:
        parts = PurePosixPath(relative(name)).parts
        for index, part in enumerate(parts):
            parent = "/".join(parts[:index])
            children.setdefault(parent, set()).add(part)
            if index < len(parts)-1:
                children.setdefault("/".join(parts[:index+1]), set())
    for parent, names in children.items():
        directory = ordinary_path(stage / parent)
        require(directory.is_dir() and {item.name for item in directory.iterdir()} == names,
                "release directory has undeclared/missing paths: " + parent)
        for name in names:
            child = directory / name
            require(not child.is_symlink(), "release symlink refused")
            rel = str(child.relative_to(stage))
            require(child.is_file() if rel in files else child.is_dir(), "release path kind differs: " + rel)


def require_review(path, label):
    data = read_json(path)
    require(type(data) is dict and data.get("passed") is True
            and ("blocking_findings" not in data or data["blocking_findings"] == []),
            "passing actual " + label + " review required")
    return data


def require_replay(path, results_ref, producers):
    data = read_json(path)
    require(data["schema"] == "support-retention-read-only-complete-replay/v1" and data["status"] == "passed"
            and data["complete_outputs_exact"] == 1280 and data["cohorts_per_arm"] == 5
            and data["rows_per_cohort"] == 128 and data["additional_optimizer_updates"] == 0
            and data["target_reference_files_opened"] is False and data["default_promotion"] is False
            and data["producer_pins"] == producers and data["training_results"] == results_ref,
            "complete exact selected replay binding required")
    require(set(data["arms"]) == set(ARMS), "both replay arms required")
    for arm in ARMS:
        record = data["arms"][arm]
        require(record["objective"] == arm and record["support_steps"] == 0
                and record["complete_output_exact"] == 640 and set(record["cohorts"]) == set(COHORTS)
                and record["new_gate_full_Adam_and_counters_unchanged"] is True
                and record["parent_full_checkpoint_bytes_unchanged"] is True
                and record["model_parent_tensors_modes_flags_and_rng_unchanged"] is True,
                "complete replay state custody differs")
    require_reference(data["source"])
    return data


def require_recovered_error(root, declared, manifest_path, commit, publication_review):
    """Accept a preserved uncertain error only through this completed reviewed chain."""
    error_path = root / "hub-upload-error.json"
    if not error_path.exists():
        require(not (root / "hub-upload-batch-recovery.json").exists()
                and "batch_commits" not in commit, "recovered publication must preserve its original error")
        return None
    error = read_json(error_path)
    reconciliation = read_json(root / "hub-upload-reconciliation.json")
    proposal = read_json(root / "hub-upload-batch-proposal.json")
    recovery = read_json(root / "hub-upload-batch-recovery.json")
    source_review = require_review(root / "hub-recovery-source-review.json", "recovery source")
    parent, revision = commit["parent"], commit["revision"]
    require(error["schema"] == "positive-retention-Hub-uncertain-outcome/v1"
            and error["repo"] == REPO and error["prefix"] == PREFIX and error["parent_commit"] == parent
            and error["error_type"] == "SSLError" and error["automatic_retry"] is False,
            "exact preserved first upload failure required")
    require(reconciliation["schema"] == "positive-retention-Hub-first-attempt-reconciliation/v1"
            and reconciliation["remote_head"] == reconciliation["original_observed_parent"] == parent
            and reconciliation["new_prefix_file_count"] == 0 and reconciliation["new_prefix_paths"] == []
            and reconciliation["prior_changed_paths"] == [] and reconciliation["remote_head_unchanged"] is True
            and reconciliation["automatic_retry_performed"] is False and reconciliation["first_attempt_error"] == error,
            "first failure must be reconciled to unchanged parent and absent prefix before recovery")
    require(proposal["schema"] == "positive-retention-parent-guarded-batch-proposal/v1"
            and proposal["repo"] == REPO and proposal["prefix"] == PREFIX and proposal["original_parent"] == parent
            and proposal["overwrite_or_delete_allowed"] is False and proposal["manifest_last"] is True
            and proposal["recovered_initial_failure_sha256"] == file_pin(error_path)["sha256"]
            and proposal["reconciliation_sha256"] == file_pin(root / "hub-upload-reconciliation.json")["sha256"]
            and proposal["helper_sha256"] == file_pin(root / "recover_hub_upload.py")["sha256"]
            and proposal["release_manifest_sha256"] == file_pin(manifest_path)["sha256"]
            and set(proposal["files"]) == set(declared) and len(declared) == 311,
            "recovery proposal must bind error, reconciliation, helper and all exact release bytes")
    require(all(same_bytes(proposal["files"][name], identity) for name, identity in declared.items()),
            "recovery proposal file identity differs")
    require(source_review["schema"] == "positive-retention-Hub-batch-recovery-static-review/v1"
            and source_review["findings"] == [] and source_review["repo"] == REPO and source_review["prefix"] == PREFIX
            and source_review["helper"] == file_pin(root / "recover_hub_upload.py")
            and source_review["release_manifest"] == file_pin(manifest_path), "exact independently reviewed recovery helper required")
    require(recovery["schema"] == "positive-retention-parent-guarded-batch-recovery/v1"
            and recovery["passed"] is True and recovery["findings"] == []
            and recovery["original_parent"] == parent and recovery["final_revision"] == revision
            and recovery["batch_count"] == 30
            and all(recovery[name] is True for name in ("original_failure_preserved", "reconciliation_proved_remote_unchanged",
                "initial_prefix_absent", "parent_guard_every_batch", "no_target_overwrites_or_deletions",
                "every_prior_identity_preserved", "all311_new_identities_verified", "all8_checkpoint_downloads_exact"))
            and recovery["proposal_sha256"] == file_pin(root / "hub-upload-batch-proposal.json")["sha256"]
            and recovery["event_journal_sha256"] == file_pin(root / "hub-upload-batch-events.jsonl")["sha256"],
            "complete successful recovery receipt required")
    batches, chain = proposal["batches"], recovery["batch_commits"]
    paths = [name for batch in batches for name in batch]
    require(len(batches) == len(chain) == 30 and all(type(batch) is list and batch for batch in batches)
            and len(paths) == len(set(paths)) == len(declared) and set(paths) == set(declared)
            and batches[-1] == ["release-manifest.json"] and commit["batch_commits"] == chain,
            "thirty unique manifest-last recovery batches must exactly cover the release")
    events = [parse_json(line) for line in ordinary_path(root / "hub-upload-batch-events.jsonl").read_bytes().splitlines()]
    require(len(events) == 60, "all sixty before/after recovery events required")
    expected_parent = parent
    seen_revisions = set()
    for index, (batch, link) in enumerate(zip(batches, chain)):
        require(set(link) == {"batch", "parent", "revision", "paths"} and link["batch"] == index
                and link["parent"] == expected_parent and link["paths"] == batch
                and re.fullmatch(r"[0-9a-f]{40,64}", link["revision"])
                and link["revision"] not in seen_revisions, "recovery parent/revision chain differs")
        base = {"batch": index, "parent": expected_parent, "paths": batch}
        require(events[2*index] == {**base, "stage": "before_commit", "raw_bytes": sum(declared[name]["bytes"] for name in batch)}
                and events[2*index+1] == {**base, "stage": "after_commit", "revision": link["revision"]},
                "recovery event journal differs from exact parent-guarded commit chain")
        expected_parent = link["revision"]
        seen_revisions.add(expected_parent)
    require(expected_parent == revision and publication_review["passed"] is True
            and publication_review["schema"] == "positive-retention-Hub-actual-publication-independent-review/v1"
            and publication_review["phase"] == "publication-completed" and publication_review["findings"] == []
            and publication_review["repo"] == REPO and publication_review["prefix"] == PREFIX
            and publication_review["parent"] == parent and publication_review["revision"] == revision
            and publication_review["batch_count"] == 30 and publication_review["batch_events"] == 60
            and publication_review["batch_commits"] == chain
            and all(publication_review["actual_publication_checks"][name] is True for name in (
                "failed_first_commit_reconciled_original_head_and_zero_prefix", "all30_journal_links_match_commit_and_recovery_receipts",
                "fresh_official_commit_graph_matches_all30_links_and_originalparent", "all311_new_file_identities_verified_at_exact_immutable_commit",
                "all2856_prior_file_size_Git_blob_and_LFS_identities_unchanged", "original_failure_error_and_parent_proposal_reconciliation_preserved")),
            "passing actual independent publication review must bind the full recovered chain")
    evidence = {name: file_pin(root / name) for name in (*RECOVERY_FILES, "hub-upload-parent.json", "hub-upload-proposal.json")}
    require(all(publication_review["artifacts"].get(record["path"]) == {key: record[key] for key in ("bytes", "sha256")}
                for record in evidence.values()), "actual publication review must pin every original failure/recovery artifact byte-exactly")
    return {"original_error_preserved_and_resolved": True, "original_parent": parent, "final_revision": revision,
            "batch_count": 30, "event_count": 60, "evidence": evidence}


def prepare(args):
    root, stage, workspace = (ordinary_path(path) for path in (args.artifacts_root, args.release, args.workspace_root))
    require(workspace.is_dir() and (workspace / ".git").exists()
            and workspace != root and workspace != root.parent.parent, "explicit isolated workspace checkout required")
    destination = ordinary_path(workspace / "artifacts" / ARCHIVE_NAME, exists=False)
    require(not destination.exists(), "fresh archive destination required")
    receipt_path = ordinary_path(args.receipt, exists=False) if args.receipt else None
    require(receipt_path is None or (not receipt_path.exists() and not receipt_path.is_relative_to(destination)),
            "optional new build receipt must be outside the fresh archive")
    manifest_path = stage / "release-manifest.json"
    manifest = read_json(manifest_path)
    require(manifest["schema"] == "positive-retention-release-manifest/v1" and manifest["repo"] == REPO
            and manifest["prefix"] == PREFIX and manifest["self_excluded"] == "release-manifest.json",
            "this release manifest target required")
    require(manifest["selected_updates_per_arm"] == {arm: 0 for arm in ARMS}
            and manifest["selected_fitted_gain"] == {arm: False for arm in ARMS}
            and manifest["actual_independent_fits"] == 2 and manifest["actual_updates_per_arm"] == 240
            and manifest["default_promotion"] is False and manifest["source_only"] is True
            and manifest["latent_conditioned"] is False and manifest["legal_gold"] is False
            and manifest["native_runtime_qualified"] is False and manifest["formal_output"] is None
            and manifest["admission_masks"] == "all five zero",
            "actual negative-outcome release required")
    declared = {relative(name): {key: record[key] for key in ("bytes", "sha256")}
                for name, record in manifest["files"].items()}
    require(1 <= len(declared) <= 1024 and sum(record["bytes"] for record in declared.values()) <= 536870912,
            "bounded release manifest required")
    declared["release-manifest.json"] = byte_pin(manifest_path.read_bytes())
    verify_declared_tree(stage, declared)
    for name, identity in declared.items():
        require(same_bytes(file_pin(stage / name), identity), "release bytes differ: " + name)
    require(set(REQUIRED_SOURCE) <= set(declared), "complete old/new source and tests must be declared")
    roles = read_json(stage / manifest["checkpoint_inventory"])["checkpoint_files"]
    weight_paths = {"checkpoints/" + arm + "/checkpoint-" + str(step) + ".json" for arm in ARMS for step in (0, 120, 240)}
    weight_paths |= {"checkpoints/" + arm + "/checkpoint.json" for arm in ARMS}
    require(set(roles) == weight_paths and manifest["numerical_checkpoint_files"] == 8,
            "all six original checkpoint states and two selected aliases required")
    for name, role in roles.items():
        require(same_bytes(role, declared[name]) and role["default_promotion"] is False, "checkpoint role identity differs")
    weight_paths.add("inputs/parent-checkpoint.json")
    require(weight_paths <= set(declared), "exact frozen parent container missing")
    original_map = read_json(stage / manifest["original_artifact_map"])
    require(original_map["schema"] == "positive-retention-original-artifact-map/v1", "original-to-release map required")
    mapped_release_paths = set()
    for original, record in original_map["originals"].items():
        require(type(original) is str and record["release_paths"], "original map binding required")
        for name in record["release_paths"]:
            require(name in declared and same_bytes(record, declared[name]), "original map identity differs")
            mapped_release_paths.add(name)
    require(mapped_release_paths == set(declared)-{"release-manifest.json", manifest["original_artifact_map"]},
            "original map must cover every non-self release artifact")
    for name in ("evidence/model-tests.xml", "evidence/selection-tests.xml", "evidence/validation.json",
                 "evidence/experiment-plan.json", "evidence/run_retention_experiment.py",
                 "guardian/group-rss-observations.jsonl", "guardian/group-rss-summary.json",
                 "guardian/full-resource-artifact-pins.json", "guardian/resource-preservation-projection.json"):
        require(name in declared, "required saved validation/runner/resource artifact missing")
    results_path = stage / "results/training-results.json"
    results = read_json(results_path)
    require(results["schema"] == "support-retention-training-results/v1" and results["status"] == "completed"
            and results["actual_optimizer_updates"] == results["support_head_updates"] == 480
            and results["action_head_updates"] == 0 and results["source_only"] is True
            and results["latent_conditioned"] is False and results["legal_gold"] is False
            and results["semantic_admission"] is False and results["Lake_executed"] is False,
            "actual completed scientific boundary differs")
    require(set(results["scores"]) == set(COHORTS), "all five scored cohorts required")
    original_results = read_json(require_reference(read_json(args.local_replay)["training_results"]))
    require(original_results == results, "released results differ from local replay's actual results")
    results_ref = read_json(args.local_replay)["training_results"]
    for arm in ARMS:
        require(results["arms"][arm]["selected"]["completed_updates"] == 0
                and results["arms"][arm]["selection_decision"]["selected_fitted_gain"] is False,
                "cold fallback outcome differs")
        for cohort in COHORTS:
            require("results/" + arm + "/" + cohort + "-predictions.json" in declared, "complete selected cohort panel missing")
        for name in ("losses.json", "selected.json", "selection-decision.json", "last-TRAIN-predictions.json",
                     "selection-predictions-0.json", "selection-predictions-120.json", "selection-predictions-240.json"):
            require("results/" + arm + "/" + name in declared, "complete TRAIN/selection closure missing")
    for cohort in COHORTS:
        require("results/parent-" + cohort + "-predictions.json" in declared, "same-panel parent cohort missing")
    for name in ("summary.json", "training-schedule.json", "selection-baseline-floors.json", "parent-TRAIN-score.json",
                 "parent-TRAIN-predictions.json", "both-selected-before-final-and-retention.json",
                 "all-final-and-retention-predictions-before-reference-joins.json"):
        require("results/" + name in declared, "complete durable result closure missing")
    for category in ("corpus", "corpus-draft-01"):
        names = {name for name in declared if name.startswith("evidence/" + category + "/")}
        require(len(names) == 9 and all("evidence/" + category + "/" + name in names for name in
            ("train-inputs.json", "train-references.json", "selection-inputs.json", "selection-references.json",
             "final-inputs.json", "final-references.json", "corpus-protocol.json", "corpus-manifest.json", "training-schedule.json")),
            "complete final and draft corpus/objective history required")
    guardian_exit_path = stage / "guardian/guardian-exit.json"
    guardian_exit = read_json(guardian_exit_path)
    require(guardian_exit["returncode"] == guardian_exit["child_returncode"] == 0
            and guardian_exit["artifacts_durable"] is True and guardian_exit["resource_reservation_released"] is True,
            "actual durable guardian completion and owned release required")
    rss = read_json(stage / "guardian/group-rss-summary.json")
    require(rss["sampled_peak_only"] is True and rss["absolute_peak_measured"] is False
            and rss["continuous_coverage_claimed"] is False and rss["kernel_hard_cap"] is False,
            "sampled resource scope differs")
    private_resources = read_json(stage / "guardian/full-resource-artifact-pins.json")
    require(private_resources["schema"] == "positive-retention-resource-local-retention/v1"
            and private_resources["foreign_state_rewrite_or_release"] is False,
            "public resource pins with privately retained full ledgers required")
    private_resource_pins = list(private_resources["full_artifact_pins"].values())
    results_review = require_review(args.results_review, "independent results")
    resource_review = require_review(args.resource_review, "independent resource")
    release_review = require_review(args.release_review, "release")
    publication_review = require_review(args.publication_review, "publication")
    require(contains_pin(results_review, results_ref), "results review does not bind actual completed results")
    require(contains_pin(resource_review, file_pin(guardian_exit_path)) or contains_pin(resource_review, file_pin(stage / "guardian/group-rss-summary.json")),
            "resource review does not bind actual guardian/RSS receipts")
    require(contains_pin(release_review, file_pin(manifest_path)), "release review does not bind actual release manifest")
    commit, readback, downloads = (read_json(path) for path in (args.hub_commit, args.hub_readback, args.hub_downloads))
    revision = commit["revision"]
    require(commit["repo"] == REPO and commit["prefix"] == PREFIX and re.fullmatch(r"[0-9a-f]{40,64}", revision),
            "exact immutable Hub upload identity required")
    require(readback["schema"] == "positive-retention-Hub-readback/v1" and readback["passed"] is True
            and readback["repo"] == REPO and readback["prefix"] == PREFIX and readback["revision"] == revision
            and readback["parent"] == commit["parent"] and readback["prior_file_identities_preserved"] is True
            and readback["all_new_git_or_LFS_identities_verified"] is True
            and readback["all_eight_checkpoints_downloaded_byte_exact"] is True
            and readback["both_selected_aliases_downloaded_byte_exact"] is True
            and readback["default_or_ModelManager_promotion"] is False, "complete publication readback required")
    published = {record["path"]: record for record in readback["files"]}
    require(len(published) == len(readback["files"]) == readback["new_file_count"] == len(declared)
            and set(published) == {PREFIX + "/" + name for name in declared}, "every actual published file must be declared")
    for name, identity in declared.items():
        record = published[PREFIX + "/" + name]
        require(same_bytes(record, identity) and record["git_or_LFS_identity_verified"] is True, "published byte identity differs")
    require(downloads["schema"] == "positive-retention-all-Hub-checkpoints/v1" and downloads["passed"] is True
            and downloads["repo"] == REPO and downloads["prefix"] == PREFIX and downloads["revision"] == revision
            and downloads["original_states"] == 6 and downloads["selected_aliases"] == 2 and downloads["checkpoint_files"] == 8,
            "all eight immutable checkpoint downloads required")
    download_records = {record["path"]: record for record in downloads["files"]}
    require(set(download_records) == set(roles) and len(download_records) == len(downloads["files"]) == 8,
            "eight unique downloaded checkpoint identities required")
    mirror = ordinary_path(readback["selected_alias_mirror"])
    for name, record in download_records.items():
        require(record["downloaded_bytes_exact"] is True and same_bytes(record, declared[name])
                and same_bytes(file_pin(mirror / "all-checkpoints" / name.removeprefix("checkpoints/")), declared[name]),
                "immutable downloaded checkpoint bytes differ")
    require(contains_pin(publication_review, file_pin(args.hub_readback))
            or any(node == revision for node in nodes(publication_review)), "publication review does not bind this immutable revision/readback")
    recovered_error = require_recovered_error(root, declared, manifest_path, commit, publication_review)
    local_replay = require_replay(args.local_replay, results_ref, results["producer_pins"])
    hub_replay = require_replay(args.hub_replay, results_ref, results["producer_pins"])
    require(same_bytes(local_replay["source"], hub_replay["source"]), "local and Hub replay helpers differ")
    for arm in ARMS:
        require(Path(hub_replay["arms"][arm]["checkpoint"]["path"]).resolve() == mirror / arm / "checkpoint.json"
                and file_pin(mirror / arm / "checkpoint.json") == hub_replay["arms"][arm]["checkpoint"]
                and same_bytes(hub_replay["arms"][arm]["checkpoint"], declared["checkpoints/" + arm + "/checkpoint.json"]),
                "Hub replay did not execute the exact downloaded selected alias")
    # Authenticate everything before creating any workspace artifact.
    copies = {}
    released_files = {}
    for name, identity in sorted(declared.items()):
        url = "https://huggingface.co/" + REPO + "/resolve/" + revision + "/" + quote(PREFIX + "/" + name, safe="/")
        record = {**identity, "hub_resolve_url": url, "published_path": PREFIX + "/" + name}
        if name in weight_paths:
            record.update(storage="Hub-only", reason="Full raw checkpoint container excluded from root Git")
        else:
            local_name = "published-README.md" if name == "README.md" else name
            raw = checked_copy_bytes(stage / name)
            require(byte_pin(raw) == identity, "nonweight release changed during archive preparation")
            copies[local_name] = {"source": str(stage / name), **identity}
            record.update(storage="local", local_path=local_name)
        released_files[name] = record
    supplements = {"evidence/postpublication/" + name: root / name for name in EXTRA_REQUIRED}
    for label, path in (("results-review.json", args.results_review), ("resource-review.json", args.resource_review),
                        ("release-review.json", args.release_review), ("publication-review.json", args.publication_review),
                        ("hub-upload-commit.json", args.hub_commit), ("hub-readback-verification.json", args.hub_readback),
                        ("hub-all-checkpoint-downloads.json", args.hub_downloads), ("hub-checkpoint-replay.json", args.hub_replay)):
        supplements["evidence/postpublication/" + label] = path
    for name in ("hub-upload-parent.json", "hub-upload-proposal.json"):
        supplements["evidence/postpublication/" + name] = root / name
    if recovered_error is not None:
        supplements.update({"evidence/postpublication/" + name: root / name for name in RECOVERY_FILES})
    for path in args.evidence:
        target = "evidence/additional/" + Path(path).name
        require(target not in supplements, "duplicate explicit supplementary basename")
        supplements[target] = path
    for name, source in supplements.items():
        relative(name)
        require(name not in copies, "supplementary copy destination collision")
        raw = checked_copy_bytes(source)
        require(not any(same_bytes(byte_pin(raw), record) for record in private_resource_pins),
                "full private cross-agent resource ledger cannot be retained in root Git")
        copies[name] = {"source": str(ordinary_path(source)), **byte_pin(raw)}
    require(sum(record["bytes"] for record in copies.values()) <= 536870912, "bounded nonweight archive required")
    require(not any(same_bytes(record, private) for record in copies.values() for private in private_resource_pins),
            "declared publication unexpectedly contains a full private resource ledger")
    lines = ["# Positive retention study: both selected cold fallback", "",
        "This completed authored source-text experiment ran two matched 3,169-parameter gates for 240 support-only updates each. BCE and BCE plus the TRAIN-only positive margin penalty both selected their actual cold update 0 checkpoint. No selected fitted improvement or default replacement was demonstrated.", "",
        "| Arm | Selected update | Fresh final whole exact /64 | Fresh final unsupported emissions /64 |",
        "| --- | ---: | ---: | ---: |"]
    for arm in ARMS:
        score = results["scores"]["fresh_final"][arm]
        lines.append("| " + arm + " | 0 | " + str(score["positive_exact_count"]) + " | " + str(score["negative_emitted_proposal_count"]) + " |")
    lines += ["", "The parent scores on this same fresh panel are " + str(results["scores"]["fresh_final"]["parent"]["positive_exact_count"]) + "/64 whole exact and " + str(results["scores"]["fresh_final"]["parent"]["negative_emitted_proposal_count"]) + "/64 unsupported emissions. All earlier final cohorts are exposed retention evidence, and the new final is now exposed. Rejected trained states remain research artifacts; aliases are copies rather than additional fits.", "",
        "Every published file is mapped in `retention-manifest.json` to byte-exact local content or an immutable Hub URL with size and SHA-256. The six original states, two selected aliases and full frozen parent container remain Hub-only; no raw checkpoint weights are retained in root Git. All other released source, tests, helper code, final/draft corpus history, complete TRAIN/selection/five-cohort panels, losses, decisions and durable barriers are retained locally. `published-README.md` preserves the exact release README.", "",
        "Saved validation XML and independent result/resource/publication reviews are retained without rerunning tests or models. Local and exact downloaded selected states each reproduce all 1,280 saved outputs while preserving full Adam, progress, nested parent bytes, tensors, modes, flags and CPU RNG. The guardian recorded durable completion and release of its own reservation. RSS peaks are sampled group observations, with no absolute peak, continuous coverage or kernel-cap claim.", "",
        "Full shared resource ledgers remain private local artifacts. Their exact identities, the public foreign-preservation projection and the observation phase correction are retained; this archive does not expose the cross-agent ledger bodies.", "",
        "[Immutable published release](https://huggingface.co/" + REPO + "/tree/" + revision + "/" + PREFIX + ")", "",
        "These models consume source text and a caller attachment premise and emit engineered single-rule occurrence proposals with zero admission masks and null formal output. Authored exactness is not independently reviewed legal fidelity. Genuine 8D/384D/768D latent decoding/conditioning, reviewed US Code semantic targets and coverage, native logic-family lowering, actual `lake build legal` qualification, and legal/proof authority remain open requirements. Prior completed native 384 recipes retain their own task/codec/checkpoint lineage; this trial does not rerun or promote them.", "",
        "Historical absolute paths are provenance. The retained original-artifact map and manifest provide explicit byte bindings for checked path rebinding; the archive does not assert a generic portable training runtime. The archiver executed no model, test, Git or network operation and did not stage or commit files.", ""]
    if recovered_error is not None:
        lines += ["Publication preserves the initial TLS failure and its unchanged-remote reconciliation. Thirty parent-guarded append commits, all sixty before/after events, exact final readback/download/replay receipts and the passing independent publication review authenticate the completed recovery. The original error was retained.", ""]
    readme_raw = "\n".join(lines).encode("utf-8")
    destination.mkdir(parents=True)
    sync_directory(destination.parent)
    local_files = {}
    for name, record in sorted(copies.items()):
        raw = checked_copy_bytes(record["source"])
        require(byte_pin(raw) == {key: record[key] for key in ("bytes", "sha256")}, "copy source drifted")
        target = destination / name
        write_bytes(target, raw)
        require(same_bytes(file_pin(target), record), "retained archive bytes differ")
        local_files[name] = {key: record[key] for key in ("bytes", "sha256")}
    write_bytes(destination / "README.md", readme_raw)
    local_files["README.md"] = byte_pin(readme_raw)
    retention = {"schema": "positive-retention-workspace-retention-manifest/v1", "hub_repo": REPO,
        "hub_prefix": PREFIX, "hub_revision": revision, "hub_revision_pending": False,
        "released_files": released_files, "local_files": dict(sorted(local_files.items())),
        "released_file_count": len(released_files), "local_released_files": len(released_files)-len(weight_paths),
        "Hub_only_released_files": len(weight_paths), "raw_checkpoint_files_copied": 0,
        "release_manifest": file_pin(manifest_path), "original_artifact_map": manifest["original_artifact_map"],
        "supplementary_originals": {name: file_pin(source) for name, source in sorted(supplements.items())},
        "selected_updates_per_arm": {arm: 0 for arm in ARMS}, "selected_fitted_gain": {arm: False for arm in ARMS},
        "complete_selected_local_replay_outputs": 1280, "complete_selected_Hub_replay_outputs": 1280,
        "default_promotion": False, "native_runtime_qualified": False, "legal_gold": False,
        "recovered_publication_error": recovered_error,
        "source_only": True, "latent_conditioned": False, "formal_output": None, "admission_masks": "all five zero",
        "manifest_self_excluded": True, "archiver": file_pin(Path(__file__)),
        "archiver_actions": {"Git_operations": 0, "network_operations": 0, "models_or_tests": 0,
                             "source_or_checkpoint_edits": 0, "resource_leases": 0, "only_new_owned_archive_created": True}}
    write_bytes(destination / "retention-manifest.json", encoded_json(retention))
    for name, record in released_files.items():
        require(revision in record["hub_resolve_url"], "mutable Hub link refused")
        if record["storage"] == "local":
            require(same_bytes(file_pin(destination / record["local_path"]), record), "released local mapping differs")
    require(all(file_pin(Path(record["source"]))["sha256"] == record["sha256"] for record in copies.values()),
            "archive source changed before completion")
    receipt = {"schema": "positive-retention-workspace-archive-build/v1", "passed": True,
        "archive_root": str(destination), "retention_manifest": file_pin(destination / "retention-manifest.json"),
        "release_file_count": len(released_files), "local_released_files": len(released_files)-len(weight_paths),
        "Hub_only_released_files": len(weight_paths), "archive_files_including_manifest": len(local_files)+1,
        "archive_total_bytes": sum(record["bytes"] for record in local_files.values()) + (destination / "retention-manifest.json").stat().st_size,
        "raw_checkpoint_files_copied": 0, "hub_revision": revision,
        "both_selected_actual_cold0": True, "default_promotion": False,
        "source_only_archive_creation_no_Git_or_Hub_actions": True}
    if receipt_path is not None:
        write_bytes(receipt_path, encoded_json(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--results-review", type=Path, required=True)
    parser.add_argument("--resource-review", type=Path, required=True)
    parser.add_argument("--release-review", type=Path, required=True)
    parser.add_argument("--publication-review", type=Path, required=True)
    parser.add_argument("--hub-replay", type=Path, required=True)
    parser.add_argument("--artifacts-root", type=Path, default=F)
    parser.add_argument("--local-replay", type=Path, default=F / "selected-checkpoint-replay.json")
    parser.add_argument("--hub-commit", type=Path, default=F / "hub-upload-commit.json")
    parser.add_argument("--hub-readback", type=Path, default=F / "hub-readback-verification.json")
    parser.add_argument("--hub-downloads", type=Path, default=F / "hub-all-checkpoint-downloads.json")
    parser.add_argument("--evidence", type=Path, action="append", default=[])
    parser.add_argument("--receipt", type=Path, help="Optional new machine-readable build receipt")
    print(json.dumps(prepare(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
