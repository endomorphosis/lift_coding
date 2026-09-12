#!/usr/bin/env python3
"""Build the AF-023 anonymous reproducibility package."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipInfo

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
PAPER = REPO_ROOT / "papers" / "completion" / "autoformalization"
ARTIFACT = PAPER / "artifact"
SUBMISSION = PAPER / "submission"
EVIDENCE = PAPER / "evidence"
ZIP_ROOT = "autoformalization-anonymous-reproducibility"
ZIP_STAMP = (2026, 1, 1, 0, 0, 0)
MAX_ZIP_BYTES = 100 * 1024 * 1024
TRANSPORT_ZIP_BYTES = 16_000_000

IDENTIFYING = re.compile(
    r"(?i)(\bbarberb\b|lift_coding|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|"
    r"overleaf\.com|BEGIN [A-Z ]*PRIVATE|x-api-key|Authorization:\s*Bearer|"
    r"sk-[A-Za-z0-9]{16,})"
)

INCLUDE_REL = [
    "config/experiment_plan.json",
    "config/metrics.json",
    "config/pipeline_arms.json",
    "config/retrieval_manifest.json",
    "config/structural_evidence_scope.json",
    "data/annotation_guidelines.md",
    "data/annotation_packets.jsonl",
    "data/corpus_manifest.json",
    "data/gold_facets.jsonl",
    "data/minimal_pairs.jsonl",
    "data/policy_code_trace_cases.json",
    "data/proof_feedback_manifest.json",
    "data/retrieval_judgments.jsonl",
    "data/review_packet_schema.json",
    "data/splits.json",
    "evaluation/analyze_results.py",
    "evaluation/reference_results.json",
    "evaluation/reference_semantics.py",
    "evaluation/result_schema.json",
    "evaluation/run_benchmark.py",
    "evidence/annotation_provenance.json",
    "evidence/final_correction/actual_execution.json",
    "evidence/final_correction/feedback_status.json",
    "evidence/author_feedback_status.json",
    "evidence/bibliography_audit.md",
    "evidence/claim_task_map.json",
    "evidence/compiler_patch.diff",
    "evidence/final_claim_audit.json",
    "evidence/leakage_control_report.json",
    "evidence/native_training/adoption_scalar_summary.json",
    "checkpoints/baselines/manifest.json",
    "manuscript/empirical_scope.tex",
    "protocol.md",
    "results/hypothesis_report.md",
    "results/summary.json",
    "results/table11_training.tex",
    "results/table13_assistance.tex",
    "results/table6_pipeline.tex",
    "runs/bridge_validation/results.jsonl",
    "runs/costs/results.jsonl",
    "runs/domain_transfer/results.jsonl",
    "runs/native_training/results.jsonl",
    "runs/pipeline_comparison/manifest.json",
    "runs/pipeline_comparison/results.jsonl",
    "runs/planning/results.jsonl",
    "runs/premise_selection/results.jsonl",
    "runs/proof_assistance/results.jsonl",
    "runs/proof_heads/results.jsonl",
    "runs/retrieval/results.jsonl",
    "runs/training_baselines/manifest.json",
    "runs/training_baselines/results.jsonl",
]

DIRTY_HASH_ONLY = [
    "config/environment_manifest.json",
    "config/training_backend.json",
    "checkpoints/native_training/manifest.json",
    "data/native_training_teacher_manifest.json",
    "data/teacher_manifest.json",
    "evidence/consumer_activation.json",
    "evidence/guidance_export.json",
    "evidence/repair_validation.json",
    "evidence/rollback_receipt.json",
    "evidence/source_audit_private.json",
    "runs/compiler_repair/results.jsonl",
    "runs/guidance_promotion/results.jsonl",
    "runs/native_training/manifest.json",
]

REPORTED_TABLES = {
    "summary.json": "d369e99ec3bcc9d1bbd12361ca73300d2297b5363806be77dcd2625889bb2276",
    "table11_training.tex": "b30c46c02a85acb43dbe46e6a4008bff6d0416bb6f32bbc2c9dc90e4f8714a14",
    "table13_assistance.tex": "dab02cc945ce5db5efb16685daa2d6ca4cfaef9b03a6f96781c7829611322117",
    "table6_pipeline.tex": "a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49"
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def dumps(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def scan_text(label: str, text: str) -> list[str]:
    hits = []
    for match in IDENTIFYING.finditer(text):
        hits.append(f"{label}:{match.start()}:{match.group(0)[:80]}")
    return hits


def native_training_notes() -> dict:
    manifest = json.loads((PAPER / "runs/native_training/manifest.json").read_text(encoding="utf-8"))
    scalars = json.loads((PAPER / "evidence/native_training/adoption_scalar_summary.json").read_text(encoding="utf-8"))
    arms = manifest.get("arms") or {}
    aggregates = scalars.get("aggregates") or []
    t2 = arms.get("T2") or {}
    packed = t2.get("packed_cpu") or []
    return {
        "schema": "autoformalization-anonymous-native-training-notes/v1",
        "original_manifest_sha256": sha256_file(PAPER / "runs/native_training/manifest.json"),
        "operator_local_paths_redacted": True,
        "dataset_id": manifest.get("dataset_id") or scalars.get("dataset_id"),
        "config_id": manifest.get("config_id") or scalars.get("config_id"),
        "executed_arms": sorted(str(key) for key, value in arms.items() if isinstance(value, dict) and value.get("executed")),
        "t2_packed_cpu_reports": len(packed),
        "t2_parameter_changed": any(item.get("parameter_changed") is True for item in packed if isinstance(item, dict)),
        "aggregate_rows": len(aggregates),
        "claim_admissible": any(row.get("claim_admissible") is True for row in aggregates if isinstance(row, dict)),
        "fills_table11_held_out_fidelity": False,
        "population": "AF-004 train 69 + selection 15; final-test locked",
    }


def environment_pin() -> dict:
    env = json.loads((PAPER / "config/environment_manifest.json").read_text(encoding="utf-8"))
    producer = env["selected_entry_points"]["embedding_producer"]
    files = [{"path": item["path"], "sha256": item["sha256"], "size": item["size"]} for item in producer["files"]]
    return {
        "schema": "autoformalization-anonymous-environment-pin/v1",
        "original_environment_manifest_sha256": sha256_file(PAPER / "config/environment_manifest.json"),
        "operator_local_paths_redacted": True,
        "interpreter": "/usr/bin/python3.12",
        "python_version": "3.12.3",
        "path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "packages": env["interpreter"]["packages"],
        "embedding_producer": {
            "model_id": producer["model_id"],
            "revision": producer["revision"],
            "files": files,
            "loader": producer["loader"],
            "pooling": producer["pooling"],
            "max_length": producer["max_length"],
            "local_files_only": True,
            "device": "cpu",
        },
        "native_checkers_on_sealed_path": {
            "coqc": False, "cvc5": False, "elan": False, "eprover": False,
            "isabelle": False, "lake": False, "lean": False, "vampire": False, "z3": False,
        },
        "note": "Operator-local HOME, cache, and binary paths were redacted. Exact public-model file checksums are retained.",
    }


def role_current_hash(rel: str | None) -> tuple[str | None, int | None]:
    if not rel:
        return None, None
    path = REPO_ROOT / "external" / "ipfs_datasets" / rel
    if not path.is_file():
        return None, None
    return sha256_file(path), path.stat().st_size


def build_s01_s40_map() -> dict:
    audit = json.loads((EVIDENCE / "source_audit_private.json").read_text(encoding="utf-8"))
    roles = []
    for item in audit["roles"]:
        current, size = role_current_hash(item.get("path"))
        audited = item.get("blob_sha256")
        included = False
        access = {
            "strategy": "hash_bound_anonymous_artifact_store_on_request",
            "included_in_supplement": included,
            "publication_status": "not_uploaded",
            "reviewer_access": (
                "Content-addressed implementation bytes may be provided through the venue's "
                "anonymous supplementary channel on request. No public URL is published."
            ),
        }
        if item.get("mapping_status") == "unresolved":
            access["strategy"] = "unresolved_no_current_bytes"
        role = {
            "id": item["id"],
            "role": item["role"],
            "mapping_status": item["mapping_status"],
            "evidence_class": item["evidence_class"],
            "lines": item.get("lines"),
            "audited_blob_sha256": audited,
            "current_blob_sha256": current,
            "current_bytes": size,
            "current_matches_audit": bool(audited and current and audited == current),
            "boundary": item.get("boundary"),
            "recovery_task": item.get("recovery_task"),
            "anonymous_file": f"implementation/{item['id']}.src",
            "included_in_supplement": included,
            "access": access,
        }
        roles.append(role)
    return {
        "schema": "autoformalization-anonymous-s01-s40-map/v1",
        "task_id": "AF-023",
        "visibility": "anonymous-submission",
        "private_ledger_excluded": True,
        "repository_identities_excluded": True,
        "manuscript_snapshot": "unknown and not inferred from the current checkout",
        "role_count": len(roles),
        "resolved_current_module": sum(1 for role in roles if role["mapping_status"] == "resolved_current_module"),
        "unresolved": sum(1 for role in roles if role["mapping_status"] == "unresolved"),
        "current_matches_audit": sum(1 for role in roles if role["current_matches_audit"]),
        "later_patched_roles": [role["id"] for role in roles if role["current_blob_sha256"] and not role["current_matches_audit"]],
        "roles": roles,
        "note": (
            "Public artifacts use S01-S40 identifiers only. Private repository roots, git remotes, "
            "and operator working-copy identities remain in the internal AF-003 ledger and are not exported."
        ),
    }


def minilm_artifacts() -> list[dict]:
    pin = environment_pin()
    artifacts = []
    for item in pin["embedding_producer"]["files"]:
        strategy = (
            "included_in_supplement" if item["size"] < 500_000
            else "public_model_hub_anonymous_download"
        )
        artifacts.append({
            "id": f"minilm:{item['path']}",
            "kind": "public_embedding_model_file",
            "path": item["path"],
            "sha256": item["sha256"],
            "bytes": item["size"],
            "model_id": pin["embedding_producer"]["model_id"],
            "revision": pin["embedding_producer"]["revision"],
            "access": {
                "strategy": strategy,
                "publication_status": "not_uploaded_by_this_package",
                "reviewer_access": (
                    "Anonymous download of the public sentence-transformers/all-MiniLM-L6-v2 "
                    f"revision {pin['embedding_producer']['revision']} with the listed file checksum. "
                    "No author-hosted URL is published."
                ),
            },
            "required_to_regenerate_reported_tables": False,
        })
    return artifacts


def native_checkpoint_artifacts() -> list[dict]:
    manifest = json.loads((PAPER / "checkpoints/native_training/manifest.json").read_text(encoding="utf-8"))
    artifacts = []
    for item in manifest.get("final_checkpoints") or []:
        name = Path(item["path"]).name
        artifacts.append({
            "id": f"native-checkpoint:{name}",
            "kind": "native_training_state",
            "anonymous_name": name,
            "sha256": item["sha256"],
            "bytes": item["bytes"],
            "access": {
                "strategy": "hash_bound_anonymous_artifact_store_on_request",
                "publication_status": "not_uploaded",
                "reviewer_access": (
                    "States exceed the 100 MB supplement limit. Exact SHA-256 values are recorded. "
                    "Bytes may be provided through the venue anonymous channel on request. "
                    "They are not required to regenerate reported Tables 6/11/13."
                ),
            },
            "required_to_regenerate_reported_tables": False,
            "historical_pre_adoption_manifest_flag": bool(manifest.get("scientific_completion_admitted")),
            "saved_training_retained_byte_qualified": True,
            "primary_final_test_or_fidelity_claim_admitted": False,
        })
    return artifacts


def baseline_checkpoint_artifacts() -> list[dict]:
    manifest = json.loads((PAPER / "checkpoints/baselines/manifest.json").read_text(encoding="utf-8"))
    artifacts = []
    seen = set()
    for run in manifest.get("runs") or []:
        for key in ("initial_checkpoint_sha256", "final_checkpoint_sha256"):
            digest = run.get(key)
            if not digest or digest in seen:
                continue
            seen.add(digest)
            artifacts.append({
                "id": f"baseline-checkpoint:{digest[:12]}",
                "kind": "sample_memory_or_codec_state",
                "sha256": digest,
                "bytes": None,
                "arm_id": run.get("arm_id"),
                "access": {
                    "strategy": "hash_bound_anonymous_artifact_store_on_request",
                    "publication_status": "not_uploaded",
                    "reviewer_access": (
                        "Checkpoint identity is the SHA-256 recorded in the baseline manifest. "
                        "Raw state files are not in the supplement. Table 11 held-out fidelity remains unmeasured."
                    ),
                },
                "required_to_regenerate_reported_tables": False,
            })
    return artifacts


def dirty_artifacts() -> list[dict]:
    artifacts = []
    actual_sources = json.loads((PAPER / "evidence/final_correction/actual_execution.json").read_text())["original_input_sha256"]
    for rel in sorted(set(DIRTY_HASH_ONLY) | (set(actual_sources) - set(INCLUDE_REL))):
        path = PAPER / rel
        artifacts.append({
            "id": rel,
            "kind": "operator_local_or_private_ledger",
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "access": {
                "strategy": "excluded_operator_local_paths",
                "publication_status": "not_uploaded",
                "reviewer_access": (
                    "Original bytes may contain operator-local paths, runtime receipts, or the private S01-S40 ledger. "
                    "They are withheld from the anonymous ZIP. The SHA-256 is recorded. "
                    "Table regeneration uses the included frozen results and clean manifests. The actual-execution scalar projection retains exact original hashes; original execution replay is not performed by the table regenerator."
                ),
            },
            "required_to_regenerate_reported_tables": False,
        })
    return artifacts


def build_readme(manifest: dict) -> str:
    tables = manifest["reported_tables"]
    zip_cmd = "python3.12 -S regenerate_tables.py --check"
    locate_cmd = "python3.12 -S verify_retained_inputs.py"
    repo_cmd = (
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin "
        "/usr/bin/python3.12 -S papers/completion/autoformalization/evaluation/analyze_results.py --check"
    )
    lines = [
        "# Anonymous implementation and reproducibility package",
        "",
        "This bundle supports double-blind review of the compiler-guided autoformalization study.",
        "It contains frozen retained-claim inputs, table regenerators, S01-S40 content hashes, and",
        "hash-bound references for artifacts that exceed the 100 MB workshop supplement limit.",
        "Private repository identities, operator HOME paths, credentials, and the AF-003 ledger",
        "are excluded. No public upload or workshop submission is performed by this package.",
        "Independent human source-facet review was not collected and is not fabricated.",
        "",
        "## Environment",
        "",
        "- Interpreter: `/usr/bin/python3.12`",
        "- `PATH`: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`",
        "- Standard library only for table regeneration. No model call, training, or native checker is required.",
        "- The stdlib table-reproduction PATH is not the research runtime. Actual research Lean feedback and T2/T3 training completed; final-test useful-proof cells remain unrun/unavailable.",
        "",
        "## Regenerate reported tables",
        "",
        "Unpack `supplement.zip` and run:",
        "",
        "```",
        zip_cmd,
        locate_cmd,
        "```",
        "",
        "Expected SHA-256 values:",
        "",
    ]
    for name, digest in tables.items():
        lines.append(f"- `{name}`: `{digest}`")
    lines.extend([
        "",
        "If the paper tree is available, the original AF-021 regenerator may be replayed:",
        "",
        "```",
        repo_cmd,
        "```",
        "",
        "Unrun and unavailable cells are not measured zeros. Independent source-semantic fidelity",
        "remains unmeasured. Teacher/prover/reconstruction scores are not original-source gold.",
        "",
        "## Locate retained-claim inputs",
        "",
        "`manifest.json` and `checksums.json` list every retained input. Files included in this ZIP",
        "live under `frozen/` with the SHA-256 recorded in `checksums.json`. Large checkpoints and",
        "the public MiniLM weights are hash-bound; see `large_artifacts` in `manifest.json`.",
        "",
        "## S01-S40 mapping",
        "",
        "`S01_S40_map.json` maps each manuscript source role to audited and current content hashes,",
        "evidence class, and an anonymous access strategy. Private repository roots are omitted.",
        "S14 and S32 remain unresolved. Roles S23, S24, and S26-S28/S31 were later patched; both",
        "the AF-003 audit hash and the current hash are recorded.",
        "",
        "## Native source/API guide",
        "",
        "S01-S40 hashes identify current source roles; actual training separately binds its execution revision. The actual model is AdaptiveModalAutoencoder(state=state), with state reconstructed by ModalAutoencoderTrainingState.from_dict. Export calls export_deterministic_ir_guidance_features. These are source-checked API names, not a model-load or successful-promotion example. The actual consumer records no_candidate and no applied learned features; arbitrary activation flags are not efficacy.",
        "",
        "## Actual execution and scope",
        "",
        "The final correction retains actual three-seed T2/T3 updates and 114 AF013 native diagnostics. The original checker/container OOM remains failed; a separate retained-byte checker qualified the saved states. T4/E remain unactivated. T2 perfect reconstruction is target-assisted, not source-free generalization. See frozen/evidence/final_correction/actual_execution.json for scalar counts, resource limits, separate costs, prior failures and source hashes.",
        "",
        "## Large artifacts",
        "",
        "Native packed-CPU states are about 5.8 GB each and are not shipped. MiniLM",
        "`model.safetensors` is 90,868,376 bytes and is obtained from the public Hub revision",
        "pinned in the environment pin, not from an author URL. Exact checksums are listed.",
        "These bytes are not required to regenerate Tables 6, 11, and 13.",
        "",
        "## What this package does not claim",
        "",
        "- No public upload, OpenReview/workshop submission, or publication occurred here.",
        "- No fabricated independent human review, agreement statistic, or source-fidelity score.",
        "- Arm E is not promoted. T4 is unactivated. Final-test 1913 units remain locked.",
        "",
        "## Commands that are not empirical results",
        "",
        "LaTeX compilation of the manuscript is not a substitute for the table-hash checks above.",
        "",
    ])
    return "\n".join(lines)


def add_zip_member(zf: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = ZipInfo(arcname.replace("\\", "/"), date_time=ZIP_STAMP)
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def build() -> dict:
    hits: list[str] = []
    for rel in INCLUDE_REL:
        text = (PAPER / rel).read_text(encoding="utf-8")
        hits.extend(scan_text(rel, text))
    if hits:
        raise SystemExit("identifying content in selected include set:\n" + "\n".join(hits[:20]))

    s01 = build_s01_s40_map()
    notes = native_training_notes()
    pin = environment_pin()
    included = []
    members: dict[str, bytes] = {}
    for rel in INCLUDE_REL:
        data = (PAPER / rel).read_bytes()
        arc = f"frozen/{rel}"
        members[arc] = data
        included.append({"path": arc, "sha256": sha256_bytes(data), "bytes": len(data), "source": rel})

    extra_json = {
        "frozen/native_training_notes.json": dumps(notes).encode("utf-8"),
        "frozen/environment_pin.json": dumps(pin).encode("utf-8"),
    }
    for arc, data in extra_json.items():
        members[arc] = data
        included.append({"path": arc, "sha256": sha256_bytes(data), "bytes": len(data), "source": "derived_anonymous"})

    regen = (HERE / "regenerate_tables.py").read_bytes()
    verify = (HERE / "verify_retained_inputs.py").read_bytes()
    members["regenerate_tables.py"] = regen
    members["verify_retained_inputs.py"] = verify
    included.append({"path": "regenerate_tables.py", "sha256": sha256_bytes(regen), "bytes": len(regen), "source": "AF-023"})
    included.append({"path": "verify_retained_inputs.py", "sha256": sha256_bytes(verify), "bytes": len(verify), "source": "AF-023"})

    large = minilm_artifacts() + native_checkpoint_artifacts() + baseline_checkpoint_artifacts() + dirty_artifacts()
    for role in s01["roles"]:
        if role["audited_blob_sha256"]:
            large.append({
                "id": f"role:{role['id']}",
                "kind": "s01_s40_implementation",
                "sha256": role["current_blob_sha256"] or role["audited_blob_sha256"],
                "audited_blob_sha256": role["audited_blob_sha256"],
                "current_blob_sha256": role["current_blob_sha256"],
                "bytes": role["current_bytes"],
                "access": role["access"],
                "required_to_regenerate_reported_tables": False,
            })

    checksums = {
        "schema": "autoformalization-anonymous-checksums/v1",
        "task_id": "AF-023",
        "reported_tables": REPORTED_TABLES,
        "included_members": included,
        "large_artifacts": [
            {k: item[k] for k in ("id", "sha256", "bytes", "access") if k in item}
            for item in large
        ],
    }

    retained = []
    for item in included:
        retained.append({
            "path": item["source"] if item["source"] not in {"derived_anonymous", "AF-023"} else item["path"],
            "bundle_path": item["path"],
            "sha256": item["sha256"],
            "bytes": item["bytes"],
            "access": {"strategy": "included_in_supplement", "publication_status": "not_uploaded"},
        })
    for item in large:
        retained.append({
            "path": item["id"],
            "sha256": item.get("sha256"),
            "bytes": item.get("bytes"),
            "access": item["access"],
        })

    manifest = {
        "schema": "autoformalization-anonymous-artifact-manifest/v1",
        "task_id": "AF-023",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "visibility": "anonymous-submission",
        "workshop_limits": {
            "supplement_zip_max_bytes": MAX_ZIP_BYTES,
            "transport_zip_max_bytes": TRANSPORT_ZIP_BYTES,
        },
        "reproduction": {
            "interpreter": "/usr/bin/python3.12",
            "path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            "standard_library_only": True,
            "commands": [
                {
                    "argv": ["/usr/bin/python3.12", "-S", "regenerate_tables.py", "--check"],
                    "cwd": ZIP_ROOT,
                    "purpose": "Regenerate Tables 6/11/13 from frozen retained-claim records and verify SHA-256",
                },
                {
                    "argv": ["/usr/bin/python3.12", "-S", "verify_retained_inputs.py"],
                    "cwd": ZIP_ROOT,
                    "purpose": "Locate every included retained-claim input and verify SHA-256",
                },
                {
                    "argv": [
                        "/usr/bin/python3.12", "-S",
                        "papers/completion/autoformalization/evaluation/analyze_results.py", "--check",
                    ],
                    "cwd": "paper-tree",
                    "purpose": "Optional replay of the AF-021 regenerator when the paper tree is present",
                },
            ],
        },
        "reported_tables": REPORTED_TABLES,
        "analysis_id": json.loads((PAPER / "results/summary.json").read_text())["analysis_id"],
        "retained_claim_inputs": retained,
        "regenerators": [
            {"path": "regenerate_tables.py", "sha256": sha256_bytes(regen)},
            {"path": "evaluation/analyze_results.py", "sha256": sha256_file(PAPER / "evaluation/analyze_results.py")},
            {"path": "evaluation/run_benchmark.py", "sha256": sha256_file(PAPER / "evaluation/run_benchmark.py")},
        ],
        "large_artifacts": large,
        "excluded_from_anonymous_export": DIRTY_HASH_ONLY + [
            "evidence/source_audit_private.json#/private_ledger",
        ],
        "s01_s40": {
            "map": "S01_S40_map.json",
            "role_count": 40,
            "private_ledger_excluded": True,
        },
        "publication": {
            "public_upload": False,
            "workshop_submission": False,
            "openreview_upload": False,
            "author_hosted_url_published": False,
        },
        "human_review": {
            "independent_review_collected": False,
            "fabricated": False,
            "gold_records_with_values": 0,
        },
        "claim_limits": [
            "Independent human agreement and source-semantic fidelity are unmeasured.",
            "Unrun and unavailable are not measured zeros.",
            "Teacher, reconstruction, and prover success are not original-source gold.",
        ],
    }
    readme = build_readme(manifest)
    s01_bytes = dumps(s01).encode("utf-8")
    manifest_bytes = dumps(manifest).encode("utf-8")
    readme_bytes = readme.encode("utf-8")
    checksum_bytes = dumps(checksums).encode("utf-8")
    for name, data in {
        "README.md": readme_bytes,
        "manifest.json": manifest_bytes,
        "S01_S40_map.json": s01_bytes,
    }.items():
        members[name] = data
        included.append({"path": name, "sha256": sha256_bytes(data), "bytes": len(data), "source": "AF-023"})
    checksums["included_members"] = included
    checksum_bytes = dumps(checksums).encode("utf-8")
    members["checksums.json"] = checksum_bytes

    ARTIFACT.mkdir(parents=True, exist_ok=True)
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (ARTIFACT / "README.md").write_bytes(readme_bytes)
    (ARTIFACT / "manifest.json").write_bytes(manifest_bytes)
    (ARTIFACT / "S01_S40_map.json").write_bytes(s01_bytes)

    zip_path = SUBMISSION / "supplement.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for arc in sorted(members):
            add_zip_member(zf, f"{ZIP_ROOT}/{arc}", members[arc])
    zip_bytes = zip_path.stat().st_size
    if zip_bytes > MAX_ZIP_BYTES:
        raise SystemExit(f"supplement.zip {zip_bytes} exceeds 100 MB")
    if zip_bytes > TRANSPORT_ZIP_BYTES:
        raise SystemExit(f"supplement.zip {zip_bytes} exceeds 16 MB transport bound")

    exported = {
        "papers/completion/autoformalization/artifact/README.md": readme_bytes.decode("utf-8"),
        "papers/completion/autoformalization/artifact/manifest.json": manifest_bytes.decode("utf-8"),
        "papers/completion/autoformalization/artifact/S01_S40_map.json": s01_bytes.decode("utf-8"),
    }
    export_hits = []
    for label, text in exported.items():
        export_hits.extend(scan_text(label, text))
    with zipfile.ZipFile(zip_path) as zf:
        if zf.comment:
            export_hits.append("zip:comment")
        for info in zf.infolist():
            if info.date_time != ZIP_STAMP:
                export_hits.append(f"zip-timestamp:{info.filename}")
            payload = zf.read(info.filename)
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError:
                continue
            export_hits.extend(scan_text(info.filename, text))
    if export_hits:
        raise SystemExit("anonymization scan failed:\n" + "\n".join(export_hits[:30]))

    report = {
        "schema": "autoformalization-anonymization-report/v1",
        "task_id": "AF-023",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "double_blind": True,
        "patterns_scanned": [
            "operator usernames",
            "operator HOME and Users paths",
            "Overleaf project URLs",
            "private keys and bearer credentials",
            "private S01-S40 ledger fields",
        ],
        "exported_paths_audited": [
            "papers/completion/autoformalization/artifact/README.md",
            "papers/completion/autoformalization/artifact/manifest.json",
            "papers/completion/autoformalization/artifact/S01_S40_map.json",
            "papers/completion/autoformalization/submission/supplement.zip",
            "papers/completion/autoformalization/evidence/anonymization_report.json",
        ],
        "findings": [],
        "identifying_hits": [],
        "exclusions": DIRTY_HASH_ONLY,
        "redactions": [
            "Operator HOME, cache, and binary paths omitted from the environment pin.",
            "Native-training manifest operator paths replaced by compact anonymous notes.",
            "Private AF-003 repository ledger omitted from S01_S40_map.json.",
            "ZIP member timestamps fixed to 2026-01-01T00:00:00 and extra comment omitted.",
        ],
        "credentials": {
            "secrets_exported": False,
            "api_keys_exported": False,
            "private_keys_exported": False,
        },
        "human_review": {
            "independent_review_collected": False,
            "fabricated": False,
            "gold_records_with_values": 0,
        },
        "publication": {
            "public_upload": False,
            "workshop_submission": False,
            "openreview_upload": False,
            "author_hosted_url_published": False,
        },
        "supplement_zip_bytes": zip_bytes,
        "supplement_zip_sha256": sha256_file(zip_path),
        "supplement_zip_max_bytes": MAX_ZIP_BYTES,
        "within_workshop_limit": zip_bytes <= MAX_ZIP_BYTES,
        "large_artifacts_have_checksums": all(item.get("sha256") for item in large),
        "s01_s40_private_ledger_excluded": True,
        "ok": True,
    }
    report_bytes = dumps(report).encode("utf-8")
    report_hits = scan_text("anonymization_report.json", report_bytes.decode("utf-8"))
    if report_hits:
        raise SystemExit("anonymization report contains identifying content:\n" + "\n".join(report_hits))
    (EVIDENCE / "anonymization_report.json").write_bytes(report_bytes)
    return {
        "ok": True,
        "zip_bytes": zip_bytes,
        "zip_sha256": report["supplement_zip_sha256"],
        "members": len(members),
        "roles": s01["role_count"],
    }


def main() -> int:
    report = build()
    print(dumps(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
