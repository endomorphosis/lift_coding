#!/usr/bin/env python3
"""Create a separate AF004 partition-checkpoint completion candidate; no live state writes."""
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

os.umask(0o077)
STAGE = Path(__file__).resolve().parent
REPO = STAGE.parents[3]
PARTIAL = STAGE.parent / "af004_corpus_candidate/candidate"
CANDIDATE = STAGE / "candidate"
PREFIX = Path("papers/completion/autoformalization")
SNAP_REL = PREFIX / "receipts/snapshots/AF-004"
NEW_REL = SNAP_REL / "checkpoint-completion"
HEAD = "70af4e50576ea005527bc1fa154d7164f0cffcca"
FROZEN_SPLITS = "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read(path):
    return json.loads(path.read_text())


def main():
    assert not CANDIDATE.exists(), "Preserve every staged version; use a new candidate directory for any rerun"
    assert sha(PARTIAL / PREFIX / "data/splits.json") == FROZEN_SPLITS
    partial_review = read(STAGE.parent / "af004_corpus_candidate/review.json")
    assert len(partial_review["files"]) == 30
    for item in partial_review["files"]:
        assert sha(PARTIAL / item["path"]) == item["sha256"]
    shutil.copytree(PARTIAL, CANDIDATE)
    out, new = CANDIDATE / PREFIX, CANDIDATE / NEW_REL
    new.mkdir(parents=True)
    save(new / "preserved-partial-files.json", {"source_commit": HEAD, "artifacts": partial_review["files"], "partial_candidate_review_sha256": sha(STAGE.parent / "af004_corpus_candidate/review.json")})
    for name in ["data/corpus_manifest.json", "data/splits.json", "data/teacher_manifest.json", "evidence/split_audit.json"]:
        dest = new / "original-partial" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / name, dest)
    boundary = STAGE.parent / "af004_container_boundary_probe"
    for name in ["report.json", "probe-receipt.json", "probe_command.py", "probe.stdout.log", "probe.stderr.log", "host-sentinel-proof.json"]:
        dest = new / "container-boundary" / name
        dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(boundary / name, dest)
    science = STAGE.parent / "af004_scientific_review"
    for name in ["review.json", "review.md"]:
        dest = new / "scientific-review" / name
        dest.parent.mkdir(exist_ok=True)
        shutil.copyfile(science / name, dest)
    shutil.copyfile(STAGE / "qualify_partition_checkpoint.py", new / "qualify_partition_checkpoint.py")
    shutil.copyfile(Path(__file__), new / "stage_candidate.py")
    qualification = {
        "status": "qualified", "scope": "AF004 data-partition checkpoint only",
        "source_commit": HEAD, "frozen_splits_sha256": FROZEN_SPLITS,
        "historical_status_resolution": "The immutable splits manifest retains its pre-qualification candidate status. This new attestation and split audit resolve that historical status without changing any split bytes, salt, membership, source export or counts.",
        "group_definition": "Whole CFR parts and MPEP chapters at their source editions; whole USC/guidance editions; transitive union of detected identity/derivative/exact/near-duplicate/paraphrase relationships.20operational source-family/time groups does not mean20publishers or statistically independent editions.",
        "access_scope": "Actual reconstructed Codex container private-tree exclusion plus actually invoked trusted role/hash/digest gate. Unknown and sealed-final roles fail closed. AF007/008 must integrate the gate and partition-specific access before any training/scoring; no current runner or public-network denial is claimed.",
        "boundary_report_sha256": sha(new / "container-boundary/report.json"),
        "scientific_review_sha256": sha(new / "scientific-review/review.json"),
        "annotation": "AF005 owns independent candidate-blind annotation/adjudication.1913unique final candidates are not1913adjudicated units or measured outcomes.",
    }
    downstream = {
        "AF005_annotation_and_preoutcome_sampling": [
            "Freeze count-aware selection of at least100unique natural units spanning at least20operational groups before annotation selection or scored outputs. Include at least one selected unit per group; some groups cannot supply five unique units.",
            "Freeze the estimand and source/group weights. Preserve selected eligibility/status denominators and domain/time coverage; do not assume the sampled subset retains all4macro-editions automatically.",
            "Acquire real candidate-blind independent annotations, disagreement and adjudication records. Automatic teacher/IR values and rights reviews are not semantic gold.",
        ],
        "AF007_AF008_runner_admission": [
            "Keep all training, teacher fitting, model/hyperparameter selection, canary, retrieval and patch channels fail closed until role-specific frozen export checks and private heldout identity/content denial are wired and exercised. Unknown roles are denied; the private deny index never enters provider context.",
            "Only a separately authorized sealed final harness may receive final material after checkpoint/configuration/patch lock. Preserve append-only raw results and prevent them feeding development.",
            "The actual Codex filesystem probe establishes private-path exclusion for the reconstructed container. Grok was source-reviewed, not dynamically probed. Bridge networking remains enabled; neither internet retrieval nor pretraining contamination is excluded.",
        ],
        "statistics": [
            "Retain the preregistered95% source-family/time-group cluster bootstrap with10000resamples and separate seed summaries; disclose correlation across4macro-editions rather than implying20independently sampled corpora.",
            "One final component contains1738of1921records. Deduplicate8aliases to1913units, freeze group/source weighting before outcomes, and do not let the giant component erase the20-group floor.",
            "Any supplementary hierarchy-aware/macro-edition sensitivity analysis or estimand amendment must be declared before affected outcomes; no unsupported power or independent-edition uncertainty claims.",
        ],
        "population_limits": [
            "Development remains69training/15selection/38canary unique CFR units at2024-07-01; the final pool is1913units/20groups within4macro-editions. No unseen-edition, forward-temporal, broad cross-domain training or statistical independence claim.",
            "Coding requirements/implementation and natural traces remain provenance-qualified acquisition obligations, not empirical zeros or deleted scope. Admit additional cohorts only through separately versioned pre-outcome decisions; preserve this salt and partition.",
        ],
    }
    for name in ["data/corpus_manifest.json", "data/teacher_manifest.json", "evidence/split_audit.json"]:
        payload = read(out / name)
        payload["status"] = "data_partition_checkpoint_qualified"
        payload["partition_checkpoint"] = qualification
        if name.endswith("split_audit.json"):
            payload["blockers_before_AF004_acceptance"] = []
            payload["checks"]["scoped_provider_mount_deny_test"] = "passed_actual_reconstructed_Codex_filesystem_boundary"
            payload["checks"]["trusted_role_admission"] = "passed_actual_export_and_private_digest_negative_checks"
            payload["checks"]["independent_agent_contract_review"] = "qualified_operational_groups_with_macro_edition_limits"
            payload["downstream_handoff"] = downstream
        save(out / name, payload)
    save(new / "downstream-handoff.json", downstream)
    # Retained immutable current-output snapshots; old30files are still present unchanged.
    task = next(t for t in read(REPO / PREFIX / "tasks.json")["tasks"] if t["id"] == "AF-004")
    outputs = {}
    for relative in task["deliverables"]:
        dest = new / "qualified-outputs" / relative.split("autoformalization/", 1)[1]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CANDIDATE / relative, dest)
        outputs[relative] = str(dest.relative_to(CANDIDATE))
    argv = ["/usr/bin/python3.12", str(NEW_REL / "qualify_partition_checkpoint.py")]
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=CANDIDATE, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=60)
    finished = dt.datetime.now(dt.timezone.utc).isoformat()
    (new / "checkpoint-validation.stdout.log").write_text(result.stdout)
    (new / "checkpoint-validation.stderr.log").write_text(result.stderr)
    save(STAGE / "validation-run.json", {"argv": argv, "cwd": str(CANDIDATE), "started_at": started, "finished_at": finished, "exit_code": result.returncode})
    assert result.returncode == 0, "Read retained checkpoint validation stderr"
    artifact_map = {str(p.relative_to(CANDIDATE)): sha(p) for p in sorted((CANDIDATE / SNAP_REL).rglob("*")) if p.is_file()}
    ev = lambda name: str(NEW_REL / name)
    explanations = [
        "Inventory accounts for2174observed legal/policy rows,131reserved exclusions,2043eligible records/2035distinct normalized units, exact grouped split counts,5excluded synthetic fixtures, and explicitly unqualified coding/trace populations. Final per-record membership stays private; public counts/commitments preserve source/time and group accounting.",
        "Whole-part/chapter adjacency, identity/exact/source-hash links, all-pair five-token shingle screening and fixed full-text MiniLM window screening produce28transitive components with zero detected cross-split edges. Thresholds and one-shot salt were not retried;20final operational groups remain whole. Imperfect semantic recall and4macro-edition dependence are documented.",
        "Actual reconstructed Codex container probe denies private research paths with positive workspace/toolchain controls. Actual trusted role-admission checks bind immutable split/export hashes and reject final identities/content (including renamed final records), selection-as-training, altered manifest hashes, patch and unsealed final roles. Private IDs/bodies are absent from staged provider artifacts. All future channels remain closed until AF007/008wiring; bridge/public/pretraining exposure is not claimed absent.",
        "Source/revision/license declarations and all four manifests are hash-bound. The pinned real MiniLM producer actually ran only a preseal grouping screen; its private vector commitment is retained. Hashed-term projections and mocks are excluded from semantic-teacher claims; independent gold, trained/proof targets and all research outcomes remain unmeasured in downstream tasks.",
    ]
    evidence = [
        [outputs[task["deliverables"][0]], outputs[task["deliverables"][1]], ev("checkpoint-validation.stdout.log")],
        [outputs[task["deliverables"][3]], str(SNAP_REL / "lexical_graph_audit.json"), str(SNAP_REL / "paraphrase_graph_audit.json"), ev("scientific-review/review.json")],
        [ev("container-boundary/report.json"), ev("container-boundary/probe-receipt.json"), ev("container-boundary/probe.stdout.log"), ev("checkpoint-validation.stdout.log"), str(SNAP_REL / "data_admission.py"), ev("downstream-handoff.json")],
        [outputs[task["deliverables"][0]], outputs[task["deliverables"][2]], ev("checkpoint-validation.stdout.log")],
    ]
    receipt = {"schema": "paper-task-evidence/v1", "task_id": "AF-004", "status": "complete", "completed_at": finished,
        "completion_scope": "Versioned data-partition checkpoint only; does not complete empirical research, human annotation, runner wiring or any paper benchmark.",
        "source_versions": {"integrated_partial_source_commit": HEAD, "frozen_splits_sha256": FROZEN_SPLITS, "private_membership_commitment_sha256": read(out / "data/splits.json")["partition_membership_commitment_sha256"], "upstream_dataset_revision": "86c77cb650d30ee366983d1b2e25cd85e8c22e34", "grouping_plan_sha256": sha(CANDIDATE / SNAP_REL / "grouping_plan.json"), "selected_encoder_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41", "actual_container_probe": ev("container-boundary/report.json"), "independent_agent_review": ev("scientific-review/review.json")},
        "artifacts": artifact_map, "outputs": outputs,
        "criteria": [{"criterion": criterion, "status": "met", "explanation": explanations[i], "evidence": evidence[i]} for i, criterion in enumerate(task["acceptance_criteria"])],
        "commands": [{"argv": argv, "cwd": ".", "script_artifact": ev("qualify_partition_checkpoint.py"), "exit_code": 0, "log": ev("checkpoint-validation.stdout.log"), "started_at": started, "finished_at": finished, "scope": "Actual fresh trusted partition/role-admission/privacy validation against frozen artifacts and private commitments; verifies retained actual container evidence without rerunning Docker or invoking providers."}],
        "limitations": ["No research evaluations, semantic adjudication, human review, trained-model fitting or final-test scoring performed.", "20operational source-family/time groups are not20publishers or statistically independent macro-editions.", "Future AF007/008runners and all data channels remain fail closed until explicitly wired and exercised; only locked authorized final harness may access final data.", "Actual filesystem reconstruction qualifies Codex; Grok was not dynamically probed. Public bridge-network access and model pretraining exposure remain possible.", "Coding/implementation/trace populations and100independently adjudicated final units remain explicit downstream obligations."]}
    save(out / "receipts/AF-004.json", receipt)
    verifier_spec = importlib.util.spec_from_file_location("af004_strict_receipt_check", REPO / "scripts/paper_supervisors.py")
    verifier = importlib.util.module_from_spec(verifier_spec)
    verifier_spec.loader.exec_module(verifier)
    verifier.ROOT = CANDIDATE
    verified = verifier._verify_task_contract("autoformalization", task, check_current=True)
    save(STAGE / "strict-verification.json", {"passed": True, "receipt_sha256": sha(out / "receipts/AF-004.json"), "verifier_sha256": sha(REPO / "scripts/paper_supervisors.py"), "artifact_count": len(verified["artifacts"]), "check_current": True})
    save(STAGE / "review.json", {"status": "ready_for_root_review", "candidate_root": str(CANDIDATE), "source_commit": HEAD, "frozen_splits_sha256": FROZEN_SPLITS, "receipt_sha256": sha(out / "receipts/AF-004.json"), "partial_candidate_unchanged": True, "native_state_or_live_lane_writes": 0, "files": [{"path": str(p.relative_to(CANDIDATE)), "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(out.rglob("*")) if p.is_file()], "scope": receipt["completion_scope"]})
    print(json.dumps({"receipt_sha256": sha(out / "receipts/AF-004.json"), "strict_verification": "passed", "artifact_count": len(artifact_map), "source_commit": HEAD, "frozen_splits_sha256": FROZEN_SPLITS, "native_writes": 0}))


if __name__ == "__main__":
    main()
