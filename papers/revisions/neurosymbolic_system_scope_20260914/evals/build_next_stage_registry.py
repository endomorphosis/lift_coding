#!/usr/bin/env python3
"""Inventory PUBLIC pre-fix candidates; never load oracle or reference patches.

This is a recruitment/precondition inspection, not a model or scorer run.
The public NS-005 provenance explicitly places hidden payloads outside tasks.jsonl.
Only its public fields are copied; fix-commit/oracle metadata is not projected.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PAPER = ROOT / ".worktrees/vericodegen-neurosymbolic_supervision-2026/papers/completion/neurosymbolic_supervision"
CACHE = ROOT / "papers/completion/runtime_bootstrap/unblock_20260912/ns_baselines/source_cache"


def sha(data): return hashlib.sha256(data).hexdigest()
def canon(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def is_test(path):
    p = Path(path)
    return p.name.startswith("test_") or p.name == "conftest.py" or any(part in ("test", "tests", "testing") for part in p.parts[:-1])


def package_roots(paths):
    roots = set()
    for value in paths:
        parts = Path(value).parts
        if len(parts) > 2 and parts[0] == "src": roots.add("/".join(parts[:2]) + "/")
        elif len(parts) > 1: roots.add(parts[0] + "/")
    return roots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "next_stage_candidate_registry.json")
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit("registry already exists; choose a fresh --output path")
    public_path = PAPER / "benchmark/tasks.jsonl"
    split_path = PAPER / "benchmark/splits.json"
    provenance_path = PAPER / "benchmark/provenance.md"
    rows = [json.loads(line) for line in public_path.read_text().splitlines()]
    split = json.loads(split_path.read_text())
    bindings = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (Path(__file__), public_path, split_path, provenance_path)}
    historical = []
    for task in rows:
        if task.get("role") != "live_historical_repair": continue
        task_id = task["task_id"]
        snapshot = task["source_snapshot"]
        archive_path = CACHE / task_id / "prefix.tar.gz"
        tree_path = CACHE / task_id / "tree"
        files = {}
        tree_mismatches = []
        if archive_path.exists():
            with tarfile.open(archive_path, "r:gz") as archive:
                for member in archive.getmembers():
                    if not member.isfile(): continue
                    parts = Path(member.name).parts
                    assert len(parts) > 1 and ".." not in parts and not member.name.startswith("/")
                    path = "/".join(parts[1:])
                    body = archive.extractfile(member).read()
                    files[path] = {"sha256": sha(body), "bytes": len(body)}
                    tree_file = tree_path / path
                    if not tree_file.is_file() or tree_file.is_symlink() or sha(tree_file.read_bytes()) != sha(body):
                        tree_mismatches.append(path)
        checks = []
        for source in snapshot["files"]:
            actual = files.get(source["path"])
            checks.append({"path": source["path"], "passed": bool(actual and actual["sha256"] == source["sha256"] and actual["bytes"] == source["byte_length"])})
        admitted = snapshot["admitted_paths"]
        roots = package_roots(admitted)
        dependency_candidates = [path for path in sorted(files) if path.endswith(".py") and path not in admitted and not is_test(path) and any(path.startswith(root) for root in roots)]
        recipe = PAPER / "receipts/snapshots/NS-005/proposal_snapshots" / task_id / "snapshot_recipe.json"
        if recipe.exists(): bindings[str(recipe.relative_to(ROOT))] = sha(recipe.read_bytes())
        historical.append({"task_id": task_id, "family_id": task["family_id"], "role": "existing_genuine_historical_repair", "original_split": task["split"], "new_study_role": "development_only", "fresh_confirmatory_eligible": False,
                           "exposure_basis": "Previously frozen/qualified public NS-005 cohort; original development/pilot or already exposed final family. No new untouched status inferred from absence of a specific run receipt.",
                           "future_procedure_learning_allowed_by_existing_split": task["family_id"] not in split["learning_holdout_families"],
                           "upstream_repo": snapshot["upstream_repo"], "pre_fix_commit": snapshot["pre_fix_commit"], "issue_title": task["issue"]["title"], "public_specification": task["issue"]["specification"], "public_issue_sha256": sha(canon(task["issue"])),
                           "license": task["provenance"]["license"], "admitted_paths": admitted, "snapshot_recipe": str(recipe.relative_to(ROOT)), "snapshot_sha256": snapshot["snapshot_sha256"],
                           "public_archive": {"path": str(archive_path.relative_to(ROOT)), "exists": archive_path.exists(), "sha256": sha(archive_path.read_bytes()) if archive_path.exists() else None, "regular_file_count": len(files), "member_inventory_sha256": sha(canon(files))},
                           "public_tree": {"path": str(tree_path.relative_to(ROOT)), "all_archive_members_match": bool(files) and not tree_mismatches, "mismatching_or_missing_members": tree_mismatches},
                           "prefixed_archive_commit_claim": snapshot["pre_fix_commit"], "cryptographic_upstream_git_tree_revalidated_now": False,
                           "repair_surface_checks": checks, "repair_surface_verified_now": bool(checks) and all(c["passed"] for c in checks),
                           "public_python_files": sum(path.endswith(".py") for path in files), "public_test_python_files": sum(path.endswith(".py") and is_test(path) for path in files),
                           "unchanged_package_python_candidates": dependency_candidates, "unchanged_package_python_candidate_count": len(dependency_candidates), "native_dependency_admissions_recomputed": False, "context_substitution_eligibility": "unknown_pending_complete_declared_scope_scan_and_real_admission",
                           "historical_issue_count": 1, "genuine_multi_issue_trajectory_recruited": False, "new_oracle_qualification_executed": False,
                           "proposed_finite_development_cohort": task["split"] == "development"})
    profiles = {
        "root_accelerate": ROOT / "external/ipfs_accelerate",
        "root_datasets": ROOT / "external/ipfs_datasets",
        "complete_aseh": ROOT / ".worktrees/agent-supervisor-efficiency-and-state-hardening-v1",
        "aseh_nested_datasets": ROOT / ".worktrees/agent-supervisor-efficiency-and-state-hardening-v1/ipfs_datasets_py",
        "procedure_cegis": ROOT / ".worktrees/proof-carrying-procedure-compiler-v1",
        "procedure_nested_datasets": ROOT / ".worktrees/proof-carrying-procedure-compiler-v1/ipfs_datasets_py",
        "historical_ns_accelerate": ROOT / ".worktrees/vericodegen-neurosymbolic_supervision-2026/external/ipfs_accelerate",
        "historical_ns_datasets": ROOT / ".worktrees/vericodegen-neurosymbolic_supervision-2026/external/ipfs_datasets",
    }
    modules = ["ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py", "ipfs_accelerate_py/agent_supervisor/semantic_state/context_pack.py", "ipfs_accelerate_py/agent_supervisor/semantic_state/session.py", "ipfs_accelerate_py/agent_supervisor/autonomous_repair/formal_assurance_cegis.py", "ipfs_accelerate_py/agent_supervisor/procedure_compiler/cegis.py", "ipfs_accelerate_py/agent_supervisor/procedure_compiler/registry.py", "ipfs_accelerate_py/agent_supervisor/validation/compositional_verification_vertical.py", "ipfs_datasets_py/logic/software_contracts/semantic_state/api.py", "ipfs_datasets_py/logic/software_contracts/composition.py", "ipfs_datasets_py/logic/zkp/incremental_sealing/__init__.py"]
    profile_rows = {}
    for label, path in profiles.items():
        present = {name: sha((path / name).read_bytes()) for name in modules if (path / name).is_file()}
        commit = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
        profile_rows[label] = {"path": str(path.relative_to(ROOT)), "head": commit.stdout.strip() if commit.returncode == 0 else None, "selected_module_hashes": present, "missing_selected_paths": [name for name in modules if name not in present], "import_compatibility_not_tested_by_this_registry": True}
    result = {"schema": "ns-next-stage-public-candidate-registry/v1", "registry_builder_sha256": sha(Path(__file__).read_bytes()), "input_bindings": bindings, "historical_candidates": historical,
              "counts": {"existing_genuine_historical_families": len(historical), "available_public_archives": sum(r["public_archive"]["exists"] for r in historical), "verified_repair_surfaces": sum(r["repair_surface_verified_now"] for r in historical), "archive_tree_agreements": sum(r["public_tree"]["all_archive_members_match"] for r in historical), "preliminary_fixture_only_rows": sum(r.get("role") == "preliminary_fixture_only" for r in rows), "qualification_only_rows": sum(r.get("role") in {"boundary_qualification", "table12_mutation_qualification"} for r in rows), "holdout_rule_only_rows": sum(r.get("role") == "nonretained_holdout_assignment" for r in rows), "unused_eligible_families_in_original_registry": len(split["unused_eligible_families"]), "fresh_confirmatory_families_recruited": 0, "genuine_multi_issue_trajectories_recruited": 0},
              "next_development_task_ids": [r["task_id"] for r in historical if r["proposed_finite_development_cohort"]], "next_cohort_status": "four existing original-development candidates verified as public-source inputs; new integrated execution, augmented lifecycle scripts and scoring eligibility not yet frozen",
              "source_profiles": profile_rows, "single_integrated_runtime_manifest": None, "live_dispatch_authorized_by_this_registry": False, "provider_calls": 0, "hidden_oracle_payloads_read": False, "target_patch_payloads_read": False,
              "limitations": ["Package dependency candidates are path-based discovery, not relevance or substitution admissions.", "Archive bytes and pinned repair surface were verified; full upstream Git tree provenance was not independently rebuilt now.", "No existing family or holdout-rule placeholder is counted as a new confirmatory recruitment.", "Prior eligibility/oracle status is historical metadata, not a new current scorer qualification.", "Source module presence/hashes do not establish cross-profile compatibility or integrated execution."]}
    args.output.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps({"output": str(args.output), "counts": result["counts"], "next_development_task_ids": result["next_development_task_ids"]}, indent=2))


if __name__ == "__main__": main()
