#!/usr/bin/python3.12
"""Assemble the LA-023 text-bundle artifact, lockfile, recipe, and manifest.

The declared anonymous_supplement.zip path is a directory of UTF-8 files plus
a compact outcomes recipe. A packed ZIP is generated in-memory by the checker
and is not stored as a git binary.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers/completion/law_to_action").is_dir():
    ROOT = ROOT.parent
PAPER = ROOT / "papers/completion/law_to_action"
ARTIFACT = PAPER / "artifact"
SNAPSHOT = PAPER / "receipts/snapshots/LA-023"
HERE = Path(__file__).resolve().parent

SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
SEALED_PYTHON = "/usr/bin/python3.12"
PYTHON_SHA256 = "1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f"
IMPLEMENTATION_REVISION = "ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c"
HOME_RE = re.compile(r"/home/[A-Za-z0-9._-]+/")
VALIDATION_HOME_RE = re.compile(r"ipfs-accelerate-validation-home-[A-Za-z0-9._-]+")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
SCIENTIFIC_KEYS = (
    "attempt_id",
    "arm_id",
    "seed",
    "split",
    "oracle_label",
    "observed_forbidden_effect",
    "useful_work",
    "independent_human_gold",
    "operator_resource_qualified",
    "implementation_revision",
    "identity_digest",
    "observed_effect_count",
    "journal_event_count",
    "handler_calls",
    "decision",
    "terminal_outcome",
)
RATES = {
    "A0": {"forbidden": [90, 90], "useful": [90, 90]},
    "A1": {"forbidden": [90, 90], "useful": [90, 90]},
    "A2": {"forbidden": [90, 90], "useful": [90, 90]},
    "A3": {"forbidden": [33, 90], "useful": [90, 90]},
    "A4": {"forbidden": [0, 90], "useful": [90, 90]},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def anonymize_text(text: str) -> str:
    text = HOME_RE.sub("/home/anonymous/", text)
    text = VALIDATION_HOME_RE.sub("ipfs-accelerate-validation-home-REDACTED", text)
    text = EMAIL_RE.sub("anonymous@example.invalid", text)
    return text


def write_bytes(path: Path, data: bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if mode is not None:
        path.chmod(mode)


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {key: row[key] for key in SCIENTIFIC_KEYS if key in row}
    out.setdefault("independent_human_gold", False)
    return out


def compact_canonical() -> bytes:
    raw = PAPER / "results/fixed_actions_admitted/raw.jsonl"
    lines = []
    for line in raw.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = compact_row(json.loads(line))
        lines.append(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return ("\n".join(lines) + "\n").encode("utf-8")


def environment_lock() -> dict[str, Any]:
    cryptography_origin = "/usr/lib/python3/dist-packages/cryptography/__init__.py"
    pytest_origin = "/usr/local/lib/python3.12/dist-packages/pytest/__init__.py"
    sympy_origin = "/usr/lib/python3/dist-packages/sympy/__init__.py"
    return {
        "schema": "law-to-action-environment-lock/v1",
        "task": "LA-023",
        "locked_at": "2026-09-13T00:00:00+00:00",
        "implementation_revision": IMPLEMENTATION_REVISION,
        "authoritative_validation_environment": {
            "path": SEALED_PATH,
            "python": SEALED_PYTHON,
            "python_version": "Python 3.12.3",
            "python_sha256": PYTHON_SHA256,
            "home_prefix": "ipfs-accelerate-validation-home-",
            "xdg": {
                "cache": "$HOME/.cache",
                "config": "$HOME/.config",
                "data": "$HOME/.local/share",
                "state": "$HOME/.local/state",
            },
            "note": "Provider-inherited PATH and operator profile toolchains are ignored.",
        },
        "python_packages": [
            {
                "name": "cryptography",
                "version": "41.0.7",
                "origin": cryptography_origin,
                "origin_sha256": sha256_file(Path(cryptography_origin)) if Path(cryptography_origin).is_file() else None,
                "available_on_sealed_path": True,
            },
            {
                "name": "pytest",
                "version": "8.1.1",
                "origin": pytest_origin,
                "origin_sha256": sha256_file(Path(pytest_origin)) if Path(pytest_origin).is_file() else None,
                "available_on_sealed_path": True,
                "executable_on_sealed_path": False,
            },
            {
                "name": "sympy",
                "version": "1.12",
                "origin": sympy_origin,
                "origin_sha256": sha256_file(Path(sympy_origin)) if Path(sympy_origin).is_file() else None,
                "available_on_sealed_path": True,
                "role": "QF_BOOL SAT provider for the selected proof route; SAT/UNSAT cannot authorize theorem_proof allows",
            },
        ],
        "solvers": {
            "qf_bool_sympy_sat": {
                "available": True,
                "authority": "satisfiability",
                "fragment": "QF_BOOL",
                "required_for_bounded_reproduce": False,
            },
            "z3": {"available": False, "probe": "shutil.which and importlib under sealed PATH"},
            "cvc5": {"available": False, "probe": "shutil.which and importlib under sealed PATH"},
            "lean_lake": {"available": False},
            "coq_rocq": {"available": False},
            "isabelle": {"available": False},
            "vampire": {"available": False},
            "e_prover": {"available": False},
            "duckdb_module": {
                "available": False,
                "note": "file-backed DuckDB was used in the operator cells; the sealed validation interpreter has no duckdb module",
            },
        },
        "models": {
            "scientific_model_pinned": False,
            "status": "unrun_closed_loop_claims_withdrawn",
            "paid_provider_budget": 0,
        },
        "container_recipe": {
            "required_for": "LA-029 900-cell operator matrix only",
            "not_required_for_bounded_reproduce": ["docker", "operator private store", "study UCAN key"],
            "image_digest": "sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6",
            "docker": ["/usr/bin/docker", "--host", "unix:///var/run/docker.sock"],
            "limits": {
                "cpus": 1,
                "memory_bytes": 2147483648,
                "swap_bytes": 0,
                "pids": 16,
                "per_cell_wall_seconds": 20,
                "per_cell_cpu_seconds": 20,
                "global_measured_cpu_seconds": 18000,
            },
            "network": "disabled",
            "sealed_path_has_docker": False,
        },
        "source_pins": {
            "cve_snapshot": "d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2",
            "skillcenter_snapshot": "f9dd4fec3c86d85ebf116c7408ac5ce602c418a1",
            "sources_json_sha256": sha256_file(PAPER / "benchmark/manifests/sources.json"),
            "splits_json_sha256": sha256_file(PAPER / "benchmark/manifests/splits.json"),
            "provers_json_sha256": sha256_file(PAPER / "benchmark/manifests/provers.json"),
            "protocol_json_sha256": sha256_file(PAPER / "benchmark/protocol.json"),
        },
        "harness_pins": {
            "run.py_sha256": sha256_file(PAPER / "benchmark/run.py"),
            "handlers/effects.py_sha256": sha256_file(PAPER / "benchmark/handlers/effects.py"),
            "test_measurement_integrity.py_sha256": sha256_file(PAPER / "benchmark/tests/test_measurement_integrity.py"),
        },
        "result_pins": {
            "admitted_raw_sha256": sha256_file(PAPER / "results/fixed_actions_admitted/raw.jsonl"),
            "admitted_summary_sha256": sha256_file(PAPER / "results/fixed_actions_admitted/summary.json"),
            "arm_safety_utility_sha256": sha256_file(PAPER / "results/tables/arm_safety_utility.json"),
            "source_ir_metrics_sha256": sha256_file(PAPER / "results/source_ir/metrics.json"),
        },
    }


def reported_results() -> list[dict[str, Any]]:
    items = [
        ("papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/summary.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/costs.jsonl", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/run_manifest.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/resource_admission.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/claim_guidance.md", "included", True),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/cost_report.md", "anonymized_included", True),
        ("papers/completion/law_to_action/results/tables/arm_safety_utility.json", "included", True),
        ("papers/completion/law_to_action/results/tables/headline_claims.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/source_ir/metrics.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/source_ir/raw.jsonl", "repository_hashed", False),
        ("papers/completion/law_to_action/benchmark/manifests/sources.json", "included", True),
        ("papers/completion/law_to_action/benchmark/manifests/splits.json", "repository_hashed", False),
        ("papers/completion/law_to_action/benchmark/manifests/provers.json", "repository_hashed", False),
        ("papers/completion/law_to_action/benchmark/protocol.json", "repository_hashed", False),
        ("papers/completion/law_to_action/claim_evidence_matrix.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/worked_trace/trace.json", "repository_hashed", False),
        ("papers/completion/law_to_action/analysis/analyze.py", "repository_hashed", False),
        ("papers/completion/law_to_action/manuscript/main.tex", "repository_hashed", False),
        ("papers/completion/law_to_action/manuscript/results.tex", "repository_hashed", False),
        ("papers/completion/law_to_action/manuscript/limitations.tex", "repository_hashed", False),
    ]
    reported = []
    for path, inclusion, included in items:
        target = ROOT / path
        reported.append(
            {
                "path": path,
                "sha256": sha256_file(target),
                "size_bytes": target.stat().st_size,
                "inclusion": inclusion,
                "included_in_anonymous_bundle": included,
            }
        )
    reported.append(
        {
            "path": "papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl",
            "sha256": sha256_file(ROOT / "papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl"),
            "size_bytes": (ROOT / "papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl").stat().st_size,
            "inclusion": "recipe_included",
            "included_in_anonymous_bundle": True,
            "note": "900 compact scientific rows are regenerated from this hashed file by subset/outcomes.recipe.json; the envelopes are not dumped.",
        }
    )
    # The raw.jsonl row was already added as repository_hashed; keep a single
    # record with recipe_included overlay by replacing the first match.
    filtered = [item for item in reported if item["path"] != "papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl"]
    filtered.insert(0, reported[-1])
    return filtered[:-1] if reported[-1]["path"] == reported[0]["path"] else filtered


def retrievable_sources() -> list[dict[str, Any]]:
    sources = load_json(PAPER / "benchmark/manifests/sources.json")
    out = []
    for artifact in sources["source_artifacts"]:
        out.append(
            {
                "artifact_id": artifact["artifact_id"],
                "source_uri": artifact["source_uri"],
                "revision": artifact["revision"],
                "sha256": artifact["sha256"],
                "size_bytes": artifact["size_bytes"],
                "status": artifact["redistribution"]["status"],
                "included_bytes": artifact["redistribution"]["included_bytes"],
                "instructions": artifact["redistribution"]["instructions"],
            }
        )
    return out


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists() and dest.is_file():
        dest.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            write_bytes(target, path.read_bytes(), mode=path.stat().st_mode & 0o777)


def main() -> int:
    os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.mkdir(parents=True, exist_ok=True)

    readme = (ARTIFACT / "README.md").read_bytes()
    reproduce = (ARTIFACT / "reproduce.sh").read_bytes()
    checker = (HERE / "check_artifact.py").read_bytes()
    compact = compact_canonical()
    cost_original = (PAPER / "results/fixed_actions_admitted/cost_report.md").read_text(encoding="utf-8")
    cost_anon = anonymize_text(cost_original).encode("utf-8")
    lock = environment_lock()
    lock_bytes = dump_json(lock)
    recipe = {
        "schema": "law-to-action-compact-outcomes-recipe/v1",
        "task": "LA-023",
        "n": 900,
        "source_path": "papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl",
        "source_sha256": sha256_file(PAPER / "results/fixed_actions_admitted/raw.jsonl"),
        "compact_sha256": sha256_bytes(compact),
        "compact_bytes": len(compact),
        "scientific_keys": list(SCIENTIFIC_KEYS),
        "implementation_revision": IMPLEMENTATION_REVISION,
        "rates": RATES,
        "note": "Compact scientific rows are generated from the hashed admitted raw.jsonl. This recipe does not re-emit 900 envelopes.",
    }
    recipe_bytes = dump_json(recipe)

    members = {
        "README.md": readme,
        "environment.lock": lock_bytes,
        "reproduce.sh": reproduce,
        "scripts/check_artifact.py": checker,
        "subset/outcomes.recipe.json": recipe_bytes,
        "subset/arm_safety_utility.json": (PAPER / "results/tables/arm_safety_utility.json").read_bytes(),
        "subset/sources.json": (PAPER / "benchmark/manifests/sources.json").read_bytes(),
        "subset/claim_guidance.md": (PAPER / "results/fixed_actions_admitted/claim_guidance.md").read_bytes(),
        "logs/anonymized_cost_report.md": cost_anon,
        "harness/run.py": (PAPER / "benchmark/run.py").read_bytes(),
        "harness/handlers/__init__.py": (PAPER / "benchmark/handlers/__init__.py").read_bytes(),
        "harness/handlers/effects.py": (PAPER / "benchmark/handlers/effects.py").read_bytes(),
        "harness/tests/test_measurement_integrity.py": (PAPER / "benchmark/tests/test_measurement_integrity.py").read_bytes(),
    }
    payload_files = {name: sha256_bytes(data) for name, data in sorted(members.items())}
    bundle_manifest = {
        "schema": "law-to-action-bundle-manifest/v1",
        "task": "LA-023",
        "implementation_revision": IMPLEMENTATION_REVISION,
        "files": payload_files,
        "bundle_manifest_note": "This file is excluded from files{} to avoid a circular digest.",
        "supplement_form": "directory_bundle",
    }
    members["bundle.manifest.json"] = dump_json(bundle_manifest)

    bundle_dir = ARTIFACT / "anonymous_supplement.zip"
    if bundle_dir.exists() and bundle_dir.is_file():
        bundle_dir.unlink()
    if bundle_dir.exists():
        for path in sorted(bundle_dir.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    for name, data in members.items():
        mode = 0o755 if name.endswith(".sh") or name.endswith(".py") else 0o644
        write_bytes(bundle_dir / name, data, mode=mode)

    write_bytes(ARTIFACT / "environment.lock", lock_bytes)
    write_bytes(ARTIFACT / "reproduce.sh", reproduce, mode=0o755)
    write_bytes(ARTIFACT / "README.md", readme)

    artifact_files = {
        "README.md": {"sha256": sha256_bytes(readme), "size_bytes": len(readme)},
        "environment.lock": {"sha256": sha256_bytes(lock_bytes), "size_bytes": len(lock_bytes)},
        "reproduce.sh": {"sha256": sha256_bytes(reproduce), "size_bytes": len(reproduce)},
        "anonymous_supplement.zip": {
            "form": "directory_bundle",
            "sha256": None,
            "note": "UTF-8 directory bundle; packed ZIP is generated in-memory by check_artifact.py and is not stored as a git binary.",
        },
    }
    results = []
    seen_raw = False
    for item in [
        ("papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl", "recipe_included", True),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/summary.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/costs.jsonl", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/run_manifest.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/resource_admission.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/claim_guidance.md", "included", True),
        ("papers/completion/law_to_action/results/fixed_actions_admitted/cost_report.md", "anonymized_included", True),
        ("papers/completion/law_to_action/results/tables/arm_safety_utility.json", "included", True),
        ("papers/completion/law_to_action/results/tables/headline_claims.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/source_ir/metrics.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/source_ir/raw.jsonl", "repository_hashed", False),
        ("papers/completion/law_to_action/benchmark/manifests/sources.json", "included", True),
        ("papers/completion/law_to_action/benchmark/manifests/splits.json", "repository_hashed", False),
        ("papers/completion/law_to_action/benchmark/manifests/provers.json", "repository_hashed", False),
        ("papers/completion/law_to_action/benchmark/protocol.json", "repository_hashed", False),
        ("papers/completion/law_to_action/claim_evidence_matrix.json", "repository_hashed", False),
        ("papers/completion/law_to_action/results/worked_trace/trace.json", "repository_hashed", False),
        ("papers/completion/law_to_action/analysis/analyze.py", "repository_hashed", False),
        ("papers/completion/law_to_action/manuscript/main.tex", "repository_hashed", False),
        ("papers/completion/law_to_action/manuscript/results.tex", "repository_hashed", False),
        ("papers/completion/law_to_action/manuscript/limitations.tex", "repository_hashed", False),
    ]:
        path, inclusion, included = item
        if path.endswith("raw.jsonl") and seen_raw:
            continue
        if path.endswith("raw.jsonl"):
            seen_raw = True
        target = ROOT / path
        entry = {
            "path": path,
            "sha256": sha256_file(target),
            "size_bytes": target.stat().st_size,
            "inclusion": inclusion,
            "included_in_anonymous_bundle": included,
        }
        if inclusion == "recipe_included":
            entry["note"] = "Compact scientific rows are regenerated from this hashed file by subset/outcomes.recipe.json."
        results.append(entry)

    manifest = {
        "schema": "law-to-action-artifact-manifest/v1",
        "task": "LA-023",
        "title": "From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents",
        "assembled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00"),
        "implementation_revision": IMPLEMENTATION_REVISION,
        "anonymous_supplement_zip": {
            "path": "papers/completion/law_to_action/artifact/anonymous_supplement.zip",
            "form": "directory_bundle",
            "member_prefix": "law_to_action_anonymous_supplement/",
            "note": "Declared path is a UTF-8 directory bundle. check_artifact.py packs a ZIP in memory for credential/member scans.",
        },
        "artifact_files": artifact_files,
        "bundle_files": payload_files,
        "reported_results": results,
        "retrievable_sources": retrievable_sources(),
        "commands": {
            "bounded_reproduce": "bash papers/completion/law_to_action/artifact/reproduce.sh",
            "unpacked_reproduce": "./reproduce.sh",
            "checker": "/usr/bin/python3.12 papers/completion/law_to_action/receipts/snapshots/LA-023/check_artifact.py --artifact papers/completion/law_to_action/artifact",
        },
        "anonymization": {
            "rules": [
                "Replace /home/<user>/ with /home/anonymous/",
                "Replace ipfs-accelerate-validation-home-<suffix> with ipfs-accelerate-validation-home-REDACTED",
                "Replace email addresses with anonymous@example.invalid",
            ],
            "scientific_outcome_fields_unaltered": True,
            "private_author_companion_packaged": False,
            "credentials_packaged": False,
            "excluded_paths": [
                "papers/completion/law_to_action/private/source_provenance.json",
                "operator private DuckDB",
                "study UCAN private key",
            ],
        },
        "headline_admitted_rates": RATES,
        "limitations": [
            "Bounded reproduction does not re-execute the 900 operator cells.",
            "Docker, Z3, cvc5, and duckdb are unavailable on the sealed validation PATH.",
            "Expert legal fidelity, human agreement, and closed-loop model claims remain unmeasured or withdrawn.",
            "The declared supplement path is a text directory bundle; a packed ZIP is generated in-memory during checks.",
        ],
    }
    write_bytes(ARTIFACT / "manifest.json", dump_json(manifest))

    outputs = SNAPSHOT / "outputs"
    if outputs.exists():
        for path in sorted(outputs.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    write_bytes(outputs / "README.md", readme)
    write_bytes(outputs / "environment.lock", lock_bytes)
    write_bytes(outputs / "reproduce.sh", reproduce, mode=0o755)
    write_bytes(outputs / "manifest.json", (ARTIFACT / "manifest.json").read_bytes())
    write_bytes(outputs / "bundle.manifest.json", members["bundle.manifest.json"])
    copy_tree(bundle_dir, outputs / "anonymous_supplement.zip")
    write_bytes(SNAPSHOT / "check_artifact.py", checker, mode=0o755)

    print(
        json.dumps(
            {
                "status": "assembled",
                "supplement_form": "directory_bundle",
                "lock_sha256": sha256_bytes(lock_bytes),
                "manifest_sha256": sha256_file(ARTIFACT / "manifest.json"),
                "recipe_sha256": sha256_bytes(recipe_bytes),
                "compact_sha256": sha256_bytes(compact),
                "compact_bytes": len(compact),
                "members": sorted(members),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
