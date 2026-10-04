#!/usr/bin/env python3
"""Trusted curator check of the frozen partition checkpoint, not a research evaluation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile

ROOT = Path.cwd()
BASE = ROOT / "papers/completion/autoformalization"
SNAP = BASE / "receipts/snapshots/AF-004"
NEW = SNAP / "checkpoint-completion"
PRIVATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026/research-inputs/autoformalization/af004-v1"
FROZEN_SPLITS = "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    splits_path = BASE / "data/splits.json"
    assert sha(splits_path) == FROZEN_SPLITS
    splits = read(splits_path)
    private = read(PRIVATE / "partitions.private.json")
    assert sha(PRIVATE / "partitions.private.json") == splits["partition_membership_commitment_sha256"]
    baseline = read(NEW / "preserved-partial-files.json")
    for item in baseline["artifacts"]:
        # Three current manifests are versioned; all previous snapshot bytes and frozen splits remain intact.
        original = ROOT / item["path"]
        if item["path"].endswith(("data/corpus_manifest.json", "data/teacher_manifest.json", "evidence/split_audit.json")):
            original = NEW / "original-partial" / item["path"].split("autoformalization/", 1)[1]
        assert sha(original) == item["sha256"]
    membership = private["membership"]
    assert {s: len(v) for s, v in membership.items()} == {"train": 69, "selection": 15, "fixed_canary": 38, "final_test": 1921}
    final_ids = {r["record_id"] for r in membership["final_test"]}
    assert len({r["normalized_source_unit_sha256"] for r in membership["final_test"]}) == 1913
    assert len({r["component"] for r in membership["final_test"]}) == 20
    spec = importlib.util.spec_from_file_location("af004_frozen_admission", SNAP / "data_admission.py")
    admission = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(admission)
    deny_path = PRIVATE / "holdout_deny_index.private.json"
    admitted = []
    for role, split in [("training", "train"), ("teacher_fitting", "train"), ("model_selection", "selection"), ("fixed_canary", "fixed_canary")]:
        admitted.append(admission.admit(ROOT, role, ROOT / splits["exports"][split]["path"], deny_path, FROZEN_SPLITS))
    negatives = []
    def rejects(name, call):
        try:
            call()
        except ValueError:
            negatives.append(name)
        else:
            raise AssertionError("Partition gate accepted forbidden input: " + name)
    train = ROOT / splits["exports"]["train"]["path"]
    rejects("selection_as_training", lambda: admission.admit(ROOT, "training", ROOT / splits["exports"]["selection"]["path"], deny_path, FROZEN_SPLITS))
    rejects("changed_trusted_manifest_hash", lambda: admission.admit(ROOT, "training", train, deny_path, "0" * 64))
    rejects("undeclared_patch_generation_role", lambda: admission.admit(ROOT, "patch_generation", train, deny_path, FROZEN_SPLITS))
    rejects("unsealed_final_evaluation_role", lambda: admission.admit(ROOT, "final_evaluation", train, deny_path, FROZEN_SPLITS))
    deny = read(deny_path)
    rejects("actual_final_source_input", lambda: admission.scan_sources(PRIVATE / "final_test.private.jsonl", deny))
    with (PRIVATE / "final_test.private.jsonl").open() as handle:
        final = json.loads(next(handle))
    final["record_id"] = "admission-negative-renamed-record"
    with tempfile.TemporaryDirectory(prefix="admission-check-", dir=PRIVATE) as temporary:
        disguised = Path(temporary) / "renamed-final.jsonl"
        disguised.write_text(json.dumps(final) + "\n")
        disguised.chmod(0o600)
        rejects("renamed_actual_final_content", lambda: admission.scan_sources(disguised, deny))
    probe = read(NEW / "container-boundary/report.json")
    receipt = read(NEW / "container-boundary/probe-receipt.json")
    assert probe["probe_exit_code"] == 0 and receipt["success"] is True
    assert probe["body_reads"] == probe["directory_entries_enumerated"] == probe["provider_invocations"] == 0
    assert all(c["open_succeeded"] == c["expected_accessible"] for c in probe["checks"])
    assert probe["private_tree_inside_any_retained_bind_source"] is False
    assert probe["configuration_equivalence"]["all27_non_auth_bind_sources_destinations_and_access_modes"] is True
    assert receipt["probe_result"]["all_checks_match"] is True
    for name in ["probe-receipt.json", "probe_command.py", "probe.stdout.log", "host-sentinel-proof.json"]:
        assert sha(NEW / "container-boundary" / name) == probe["evidence_files_sha256"][name]
    science = read(NEW / "scientific-review/review.json")
    assert sha(NEW / "scientific-review/review.json") == "4508a8ed6d640210d033583f6d07c55d376d81317319e08488e2be57db9a9971"
    assert sha(NEW / "scientific-review/review.md") == "f8a5025bab62771b7da6cc93bd78e077cf2bcad6c9503d35efb090622f74907e"
    # Exclude source IDs/bodies from all candidate artifacts, including newly retained evidence.
    files = [p for p in BASE.rglob("*") if p.is_file() and p.name != "checkpoint-validation.stdout.log"]
    payloads = [p.read_bytes() for p in files]
    assert not any(identity.encode() in payload for identity in final_ids for payload in payloads)
    assert not any(p.is_symlink() or p.resolve().is_relative_to(PRIVATE.resolve()) for p in files)
    final_bodies = {json.loads(line)["text"].encode() for line in (PRIVATE / "final_test.private.jsonl").open()}
    assert not any(body in payload for body in final_bodies for payload in payloads if len(body) <= len(payload))
    for rel in ["data/corpus_manifest.json", "data/teacher_manifest.json", "evidence/split_audit.json"]:
        assert read(BASE / rel)["partition_checkpoint"]["status"] == "qualified"
    print(json.dumps({"schema": "af004-partition-checkpoint-qualification/v1", "passed": True, "source_commit": "70af4e50576ea005527bc1fa154d7164f0cffcca", "frozen_splits_sha256": FROZEN_SPLITS, "private_membership_commitment_verified": True, "all_30_partial_candidate_files_preserved_or_historically_archived": True, "role_admission_passes": admitted, "negative_admission_cases_rejected": negatives, "private_final_ids_or_complete_source_bodies_disclosed": False, "actual_container_filesystem_probe_evidence_verified": True, "network_denial_claimed": False, "grok_dynamic_probe_claimed": False, "independent_agent_scientific_review_hash_verified": True, "human_annotation_or_research_evaluation_claimed": False, "future_runner_status": "fail_closed_until_AF007_AF008_wiring_and_sealed_final_authorization", "final_source_records": 1921, "final_unique_source_units": 1913, "final_operational_groups": 20}, sort_keys=True))


if __name__ == "__main__":
    main()
