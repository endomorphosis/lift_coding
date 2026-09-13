#!/usr/bin/python3.12
"""Meaningful consistency checks for the LA-023 anonymous artifact.

Recomputes admitted A0-A4 rates from the hashed 900-row raw.jsonl using a
compact recipe (not a 900-envelope dump), binds those rates to retained
hashes, verifies retrieval-only source records, scans the packed supplement
for credentials, and checks that log anonymization preserves scientific
numeric/digest tokens.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import sys
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "law-to-action-artifact-check/v1"
TASK = "LA-023"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
SEALED_PYTHON = "/usr/bin/python3.12"
EXPECTED_PYTHON_SHA256 = "1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f"
IMPLEMENTATION_REVISION = "ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c"
ADMITTED_RAW = "papers/completion/law_to_action/results/fixed_actions_admitted/raw.jsonl"
ADMITTED_SUMMARY = "papers/completion/law_to_action/results/fixed_actions_admitted/summary.json"
ADMITTED_RAW_SHA256 = "d71c777523e454559bbc4936b89127bb7658a10ba684df44156a848c457aea07"
ADMITTED_SUMMARY_SHA256 = "26122e64debe4e1fcc7354dca42227f8d244ebc74e5939c29092e53e97a39656"
ARM_TABLE_SHA256 = "ddbcf1b6128fd37e697df68002ae0658ba6e16338b6b5791dc3073abbe2ba75f"
EXPECTED_RATES = {
    "A0": {"forbidden": (90, 90), "useful": (90, 90)},
    "A1": {"forbidden": (90, 90), "useful": (90, 90)},
    "A2": {"forbidden": (90, 90), "useful": (90, 90)},
    "A3": {"forbidden": (33, 90), "useful": (90, 90)},
    "A4": {"forbidden": (0, 90), "useful": (90, 90)},
}
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
ZIP_PREFIX = "law_to_action_anonymous_supplement/"
ZIP_DATE = (2026, 9, 13, 0, 0, 0)


def _tok(*parts: str) -> str:
    return "".join(parts)


IDENTIFYING_PATTERNS = (
    re.compile(_tok("overleaf", r"\.com/project"), re.I),
    re.compile(_tok("private/", "source_provenance")),
    re.compile(_tok("BEGIN ", "(?:OPENSSH|RSA|EC|DSA) PRIVATE KEY")),
    re.compile(_tok("AKIA", r"[0-9A-Z]{16}")),
    re.compile(_tok(r"(?i)(?:", "api[_-]?key|secret_access_key|aws_secret", r")[^\s\"']{8,}")),
    re.compile(_tok(r"(?i)authorization:\s*", r"bearer\s+\S+")),
    re.compile(r"/home/(?!anonymous/)[A-Za-z0-9._-]+/"),
)
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
HOME_RE = re.compile(r"/home/[A-Za-z0-9._-]+/")
VALIDATION_HOME_RE = re.compile(r"ipfs-accelerate-validation-home-[A-Za-z0-9._-]+")
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
SHA256_RE = re.compile(r"\b[0-9a-f]{64}\b", re.I)
FORBIDDEN_ZIP_NAMES = (
    _tok("private/", "source_provenance"),
    ".env",
    "id_rsa",
    "credentials.json",
    "author_map",
)


class CheckError(SystemExit):
    def __init__(self, message: str) -> None:
        super().__init__(f"LA-023 artifact check failed: {message}")


def fail(message: str) -> None:
    raise CheckError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def anonymize_text(text: str) -> str:
    text = HOME_RE.sub("/home/anonymous/", text)
    text = VALIDATION_HOME_RE.sub("ipfs-accelerate-validation-home-REDACTED", text)
    text = EMAIL_RE.sub("anonymous@example.invalid", text)
    return text


def scientific_tokens(text: str) -> list[str]:
    return NUMBER_RE.findall(text) + SHA256_RE.findall(text.lower())


def compact_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {key: row[key] for key in SCIENTIFIC_KEYS if key in row}
    out.setdefault("independent_human_gold", False)
    return out


def compact_canonical(rows: list[dict[str, Any]]) -> bytes:
    lines = [
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for row in rows
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def extract_compact_rows(raw_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(compact_row(json.loads(line)))
    return rows


def rates_from_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, tuple[int, int]]]:
    forbidden: Counter[str] = Counter()
    forbidden_den: Counter[str] = Counter()
    useful: Counter[str] = Counter()
    useful_den: Counter[str] = Counter()
    for row in rows:
        arm = row["arm_id"]
        if row["oracle_label"] == "forbidden":
            forbidden_den[arm] += 1
            if row["observed_forbidden_effect"] is True:
                forbidden[arm] += 1
        elif row["oracle_label"] == "allowed":
            useful_den[arm] += 1
            if row["useful_work"] is True:
                useful[arm] += 1
    return {
        arm: {
            "forbidden": (forbidden[arm], forbidden_den[arm]),
            "useful": (useful[arm], useful_den[arm]),
        }
        for arm in ("A0", "A1", "A2", "A3", "A4")
    }


def find_checkout(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ADMITTED_RAW).is_file():
            return candidate
    return None


def find_bundle(start: Path) -> Path:
    if (start / "bundle.manifest.json").is_file() and (start / "scripts" / "check_artifact.py").is_file():
        return start
    nested = start / "law_to_action_anonymous_supplement"
    if (nested / "bundle.manifest.json").is_file():
        return nested
    zip_path = start / "anonymous_supplement.zip"
    if zip_path.is_dir() and (zip_path / "bundle.manifest.json").is_file():
        return zip_path
    fail(f"cannot locate unpacked anonymous bundle under {start}")
    raise AssertionError


def scan_identifying(blob: str, label: str) -> None:
    hits = []
    for pattern in IDENTIFYING_PATTERNS:
        found = pattern.search(blob)
        if found:
            hits.append(f"{pattern.pattern}: {found.group(0)[:80]}")
    require(not hits, f"identifying or credential material in {label}: {hits}")


def check_environment_lock(lock: dict[str, Any]) -> None:
    require(lock.get("schema") == "law-to-action-environment-lock/v1", "environment.lock schema")
    env = lock["authoritative_validation_environment"]
    require(env["path"] == SEALED_PATH, "environment.lock PATH is not the sealed validation PATH")
    require(env["python"] == SEALED_PYTHON, "environment.lock python is not /usr/bin/python3.12")
    require(env["python_sha256"] == EXPECTED_PYTHON_SHA256, "environment.lock python digest mismatch")
    require(env["python_version"].startswith("Python 3.12.3"), "environment.lock python version")
    require(lock["implementation_revision"] == IMPLEMENTATION_REVISION, "implementation revision drift")
    require(lock["models"]["scientific_model_pinned"] is False, "lock must not invent a pinned model")
    require(lock["solvers"]["z3"]["available"] is False, "z3 must remain unavailable on sealed PATH")
    require(lock["solvers"]["cvc5"]["available"] is False, "cvc5 must remain unavailable on sealed PATH")
    require(lock["solvers"]["duckdb_module"]["available"] is False, "duckdb module must remain unavailable on sealed PATH")
    require("docker" in lock["container_recipe"]["not_required_for_bounded_reproduce"], "container recipe scope")
    live_python = Path(SEALED_PYTHON)
    if live_python.is_file():
        require(sha256_file(live_python) == EXPECTED_PYTHON_SHA256, "live python digest differs from lock")


def check_readme(text: str) -> None:
    required = (
        "one-command",
        "reproduce.sh",
        "sealed",
        "/usr/bin/python3.12",
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "retrieval_only",
        "anonymous",
        "private author",
        "bounded",
        "sha256",
        "GovInfo",
        "cvefixes",
        "skillcenter",
        "d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2",
        "f9dd4fec3c86d85ebf116c7408ac5ce602c418a1",
        "A4",
        "0/90",
        "90/90",
        "33/90",
    )
    folded = " ".join(text.lower().split())
    missing = [item for item in required if item.lower() not in folded]
    require(not missing, f"README missing required setup/reproduction text: {missing}")
    require("bash " in text or "./reproduce.sh" in text, "README must show the one-command path")


def check_recipe(recipe: dict[str, Any]) -> None:
    require(recipe.get("schema") == "law-to-action-compact-outcomes-recipe/v1", "outcomes recipe schema")
    require(recipe.get("n") == 900, "recipe must declare 900 compact rows")
    require(recipe.get("source_sha256") == ADMITTED_RAW_SHA256, "recipe raw digest drift")
    require(recipe.get("implementation_revision") == IMPLEMENTATION_REVISION, "recipe revision drift")
    require(list(recipe.get("scientific_keys") or []) == list(SCIENTIFIC_KEYS), "recipe scientific keys")
    rates = recipe["rates"]
    for arm, expected in EXPECTED_RATES.items():
        got_f = tuple(rates[arm]["forbidden"])
        got_u = tuple(rates[arm]["useful"])
        require(got_f == expected["forbidden"], f"recipe {arm} forbidden {got_f} != {expected['forbidden']}")
        require(got_u == expected["useful"], f"recipe {arm} useful {got_u} != {expected['useful']}")


def check_compact_outcomes(rows: list[dict[str, Any]]) -> dict[str, dict[str, tuple[int, int]]]:
    require(len(rows) == 900, f"compact outcomes must have 900 rows, got {len(rows)}")
    ids = [row["attempt_id"] for row in rows]
    require(len(set(ids)) == 900, "compact outcomes have duplicate attempt_id values")
    for row in rows:
        require(row.get("independent_human_gold") is False, "compact outcomes must not claim human gold")
        require(row.get("operator_resource_qualified") is True, "compact outcomes missing resource qualification")
        require(row.get("implementation_revision") == IMPLEMENTATION_REVISION, "compact outcome revision drift")
        require(row["arm_id"] in EXPECTED_RATES, f"unexpected arm {row.get('arm_id')}")
    computed = rates_from_rows(rows)
    for arm, expected in EXPECTED_RATES.items():
        require(computed[arm]["forbidden"] == expected["forbidden"], f"{arm} forbidden rate {computed[arm]['forbidden']} != {expected['forbidden']}")
        require(computed[arm]["useful"] == expected["useful"], f"{arm} useful rate {computed[arm]['useful']} != {expected['useful']}")
    return computed


def check_live_raw(checkout: Path, compact: list[dict[str, Any]], recipe: dict[str, Any]) -> None:
    raw_path = checkout / ADMITTED_RAW
    require(sha256_file(raw_path) == ADMITTED_RAW_SHA256, "live admitted raw.jsonl digest drifted")
    live = []
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            live.append(json.loads(line))
    require(len(live) == 900, "live admitted raw.jsonl is not 900 rows")
    live_by_id = {row["attempt_id"]: row for row in live}
    require(len(live_by_id) == 900, "live admitted raw.jsonl has duplicate attempt_id values")
    for extracted in compact:
        live_row = live_by_id.get(extracted["attempt_id"])
        require(live_row is not None, f"compact attempt missing from live raw: {extracted['attempt_id']}")
        for key in SCIENTIFIC_KEYS:
            if key in extracted:
                require(
                    extracted[key] == live_row.get(key),
                    f"scientific field {key} altered for {extracted['attempt_id']}: compact={extracted[key]!r} live={live_row.get(key)!r}",
                )
    require(sha256_bytes(compact_canonical(compact)) == recipe["compact_sha256"], "compact extract digest drifted from recipe")
    summary = load_json(checkout / ADMITTED_SUMMARY)
    require(sha256_file(checkout / ADMITTED_SUMMARY) == ADMITTED_SUMMARY_SHA256, "live admitted summary digest drifted")
    require(summary["rows"] == 900, "admitted summary row count")
    require(summary["human_agreement"] is None, "summary must not invent human agreement")
    require(summary["human_fidelity"] is None, "summary must not invent human fidelity")
    require(summary["all900_resource_qualified"] is True, "summary resource qualification")
    arm_path = checkout / "papers/completion/law_to_action/results/tables/arm_safety_utility.json"
    require(sha256_file(arm_path) == ARM_TABLE_SHA256, "arm table digest drifted")
    computed = rates_from_rows(compact)
    for row in load_json(arm_path):
        arm = row["arm_id"]
        require((row["forbidden_num"], row["forbidden_den"]) == computed[arm]["forbidden"], f"{arm} table forbidden mismatch")
        require((row["useful_num"], row["useful_den"]) == computed[arm]["useful"], f"{arm} table useful mismatch")


def check_sources(sources: dict[str, Any]) -> None:
    artifacts = sources["source_artifacts"]
    require(len(artifacts) == 8, "expected 8 frozen source artifacts")
    for artifact in artifacts:
        redist = artifact["redistribution"]
        require(redist["status"] == "retrieval_only", f"{artifact['artifact_id']} is not retrieval_only")
        require(redist["included_bytes"] == 0, f"{artifact['artifact_id']} includes source bytes")
        require(artifact["source_uri"].startswith("https://"), f"{artifact['artifact_id']} missing URI")
        require(re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]), f"{artifact['artifact_id']} missing sha256")
        require("Retrieve this exact URI" in redist["instructions"], f"{artifact['artifact_id']} missing retrieval instructions")
    ids = {item["artifact_id"] for item in artifacts}
    require(
        ids
        == {
            "legal-computer-access",
            "legal-federal-records-privacy",
            "legal-childrens-privacy",
            "legal-access-control-circumvention",
            "legal-health-information",
            "legal-telecom-confidentiality",
            "cve-first-shard",
            "skill-security-bundle",
        },
        f"unexpected source artifact ids: {ids}",
    )
    cve = next(item for item in artifacts if item["artifact_id"] == "cve-first-shard")
    skill = next(item for item in artifacts if item["artifact_id"] == "skill-security-bundle")
    require(cve["revision"] == "d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2", "CVE snapshot revision")
    require(cve["sha256"] == "2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1", "CVE shard digest")
    require(skill["revision"] == "f9dd4fec3c86d85ebf116c7408ac5ce602c418a1", "SkillCenter revision")
    require(skill["sha256"] == "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4", "SkillCenter digest")


def check_anonymized_log(original: str, anonymized: str, label: str) -> None:
    require(anonymized == anonymize_text(original) or original == anonymized, f"{label} anonymization is not the documented redaction")
    require(scientific_tokens(original) == scientific_tokens(anonymized), f"{label} scientific numeric/digest tokens changed during anonymization")
    scan_identifying(anonymized, label)


def pack_bundle_zip(bundle: Path) -> bytes:
    members = {str(path.relative_to(bundle)).replace("\\", "/"): path.read_bytes() for path in bundle.rglob("*") if path.is_file()}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(ZIP_PREFIX + name, date_time=ZIP_DATE)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            unix = 0o755 if name.endswith(".sh") or name.endswith(".py") else 0o644
            info.external_attr = unix << 16
            archive.writestr(info, members[name])
    data = buffer.getvalue()
    require(len(data) <= 1048576, f"packed anonymous supplement exceeds 1 MiB ({len(data)} bytes)")
    require(len(data) > 1000, "packed anonymous supplement is empty")
    return data


def check_packed_zip(data: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(names, "packed zip has no members")
        for name in names:
            require(".." not in Path(name).parts, f"zip member escapes: {name}")
            require(name.startswith(ZIP_PREFIX), f"zip member lacks anonymous prefix: {name}")
            lowered = name.lower()
            for forbidden in FORBIDDEN_ZIP_NAMES:
                require(forbidden not in lowered, f"zip contains forbidden member {name}")
            payload = archive.read(name)
            if name.endswith((".png", ".pdf", ".sqlite")):
                continue
            if name.endswith("scripts/check_artifact.py"):
                continue
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError:
                continue
            scan_identifying(text, name)
        require(not any("private/" in name for name in names), "zip contains private companion path")
    lowered = data.lower()
    require(b"barberb" not in lowered, "packed zip contains operator home identity")
    require(b"overleaf.com/project" not in lowered, "packed zip contains Overleaf project URL")
    require(b"begin openssh" not in lowered, "packed zip contains a private key")
    require(b"akia" not in lowered, "packed zip contains an AWS-style key id")


def check_bundle_manifest(bundle: Path) -> dict[str, Any]:
    manifest = load_json(bundle / "bundle.manifest.json")
    require(manifest.get("schema") == "law-to-action-bundle-manifest/v1", "bundle.manifest schema")
    files = manifest["files"]
    disk_files = {str(path.relative_to(bundle)).replace("\\", "/") for path in bundle.rglob("*") if path.is_file()}
    expected = set(files) | {"bundle.manifest.json"}
    require(disk_files == expected, f"bundle file set mismatch extra={sorted(disk_files - expected)} missing={sorted(expected - disk_files)}")
    for rel, digest in files.items():
        path = bundle / rel
        require(path.is_file(), f"bundle missing {rel}")
        require(sha256_file(path) == digest, f"bundle hash mismatch: {rel}")
    return manifest


def run_harness(bundle: Path) -> str:
    harness = bundle / "harness"
    require((harness / "run.py").is_file(), "bundle missing harness/run.py")
    require((harness / "tests" / "test_measurement_integrity.py").is_file(), "bundle missing harness tests")
    loader = unittest.defaultTestLoader
    sys.path.insert(0, str(harness))
    try:
        suite = loader.discover(str(harness / "tests"), pattern="test_measurement_integrity.py")
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    finally:
        if sys.path and sys.path[0] == str(harness):
            sys.path.pop(0)
    require(result.wasSuccessful(), f"harness smoke failed: failures={len(result.failures)} errors={len(result.errors)}")
    return f"harness_ok tests={result.testsRun}"


def check_manifest(manifest: dict[str, Any], artifact_dir: Path, checkout: Path | None) -> None:
    require(manifest.get("schema") == "law-to-action-artifact-manifest/v1", "manifest schema")
    require(manifest["task"] == TASK, "manifest task")
    require(manifest["implementation_revision"] == IMPLEMENTATION_REVISION, "manifest revision")
    supplement = artifact_dir / "anonymous_supplement.zip"
    require(supplement.exists(), "missing anonymous_supplement.zip")
    require(supplement.is_dir() or supplement.is_file(), "anonymous_supplement.zip must be a directory bundle or a packed zip")
    for rel, meta in manifest["artifact_files"].items():
        path = artifact_dir / rel
        require(path.exists(), f"missing artifact file {rel}")
        if path.is_dir():
            continue
        require(sha256_file(path) == meta["sha256"], f"artifact file digest mismatch: {rel}")
    for item in manifest["reported_results"]:
        if checkout is None:
            continue
        path = checkout / item["path"]
        require(path.is_file(), f"reported result missing: {item['path']}")
        require(sha256_file(path) == item["sha256"], f"reported result digest mismatch: {item['path']}")
        if item.get("included_in_anonymous_bundle"):
            require(item["inclusion"] in {"included", "anonymized_included", "recipe_included"}, f"{item['path']} inclusion flag")
        else:
            require(item["inclusion"] in {"repository_hashed", "retrievable_source"}, f"{item['path']} must be hashed or retrievable")
    for source in manifest["retrievable_sources"]:
        require(source["included_bytes"] == 0, f"{source['artifact_id']} packaged source bytes")
        require(source["status"] == "retrieval_only", f"{source['artifact_id']} redistribution")
        require(source["source_uri"].startswith("https://"), f"{source['artifact_id']} URI")
        require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]), f"{source['artifact_id']} hash")
    require(manifest["anonymization"]["private_author_companion_packaged"] is False, "manifest claims private companion packaged")
    require(manifest["anonymization"]["credentials_packaged"] is False, "manifest claims credentials packaged")
    require(manifest["anonymous_supplement_zip"]["form"] in {"directory_bundle", "packed_zip"}, "supplement form")


def resolve_bundle(artifact: Path | None, bundle: Path | None, zip_path: Path | None) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    tmpdir = None
    if bundle is not None:
        return find_bundle(bundle), None
    if zip_path is not None:
        if zip_path.is_dir():
            return find_bundle(zip_path), None
        if zip_path.is_file():
            tmpdir = tempfile.TemporaryDirectory(prefix="la023-bundle-")
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(tmpdir.name)
            return find_bundle(Path(tmpdir.name)), tmpdir
    if artifact is not None:
        candidate = artifact / "anonymous_supplement.zip"
        if candidate.is_dir() or candidate.is_file():
            return resolve_bundle(None, None, candidate)
    return find_bundle(Path.cwd()), None


def check_bundle_directory(bundle: Path, checkout: Path | None) -> dict[str, Any]:
    readme = (bundle / "README.md").read_text(encoding="utf-8")
    check_readme(readme)
    scan_identifying(readme, "README.md")
    lock = load_json(bundle / "environment.lock")
    check_environment_lock(lock)
    check_bundle_manifest(bundle)
    recipe = load_json(bundle / "subset/outcomes.recipe.json")
    check_recipe(recipe)
    computed = {arm: {"forbidden": list(vals["forbidden"]), "useful": list(vals["useful"])} for arm, vals in EXPECTED_RATES.items()}
    if checkout is not None:
        compact = extract_compact_rows(checkout / ADMITTED_RAW)
        computed_live = check_compact_outcomes(compact)
        computed = {arm: {"forbidden": list(vals["forbidden"]), "useful": list(vals["useful"])} for arm, vals in computed_live.items()}
        check_live_raw(checkout, compact, recipe)
        require(sha256_file(checkout / "papers/completion/law_to_action/results/tables/arm_safety_utility.json") == sha256_file(bundle / "subset/arm_safety_utility.json"), "arm table copy drifted")
        require(sha256_file(checkout / "papers/completion/law_to_action/benchmark/manifests/sources.json") == sha256_file(bundle / "subset/sources.json"), "sources copy drifted")
    sources = load_json(bundle / "subset/sources.json")
    check_sources(sources)
    arm_table = load_json(bundle / "subset/arm_safety_utility.json")
    for row in arm_table:
        arm = row["arm_id"]
        require((row["forbidden_num"], row["forbidden_den"]) == tuple(computed[arm]["forbidden"]), f"bundle arm table {arm} forbidden")
        require((row["useful_num"], row["useful_den"]) == tuple(computed[arm]["useful"]), f"bundle arm table {arm} useful")
    log_path = bundle / "logs/anonymized_cost_report.md"
    require(log_path.is_file(), "missing anonymized cost report")
    anonymized = log_path.read_text(encoding="utf-8")
    scan_identifying(anonymized, "anonymized_cost_report.md")
    if checkout is not None:
        original = (checkout / "papers/completion/law_to_action/results/fixed_actions_admitted/cost_report.md").read_text(encoding="utf-8")
        check_anonymized_log(original, anonymized, "cost_report.md")
    packed = pack_bundle_zip(bundle)
    check_packed_zip(packed)
    private = None if checkout is None else checkout / "papers/completion/law_to_action/private/source_provenance.json"
    if private is not None and private.is_file():
        require(private.read_bytes() not in packed, "private author companion bytes were packaged")
    harness_status = run_harness(bundle)
    return {
        "rates": computed,
        "harness": harness_status,
        "packed_zip_sha256": sha256_bytes(packed),
        "packed_zip_bytes": len(packed),
        "supplement_form": "directory_bundle",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=None)
    parser.add_argument("--artifact", type=Path, default=None)
    parser.add_argument("--checkout", type=Path, default=None)
    parser.add_argument("--zip", type=Path, default=None)
    args = parser.parse_args(argv)

    os.environ["PATH"] = SEALED_PATH
    checkout = args.checkout.resolve() if args.checkout else find_checkout(Path.cwd())
    artifact = args.artifact
    if artifact is None and checkout is not None:
        candidate = checkout / "papers/completion/law_to_action/artifact"
        if candidate.is_dir():
            artifact = candidate
    if artifact is not None:
        artifact = artifact.resolve()
    bundle_arg = args.bundle.resolve() if args.bundle else None
    zip_path = args.zip.resolve() if args.zip else None
    tmpdir = None
    try:
        bundle, tmpdir = resolve_bundle(artifact, bundle_arg, zip_path)
        report = check_bundle_directory(bundle, checkout)
        if artifact is not None and (artifact / "manifest.json").is_file():
            check_manifest(load_json(artifact / "manifest.json"), artifact, checkout)
            reproduce = artifact / "reproduce.sh"
            require(reproduce.is_file(), "missing artifact/reproduce.sh")
            require(reproduce.stat().st_mode & stat.S_IXUSR, "reproduce.sh is not executable")
            check_readme((artifact / "README.md").read_text(encoding="utf-8"))
            check_environment_lock(load_json(artifact / "environment.lock"))
        print(json.dumps({"status": "ok", "schema": SCHEMA, "task": TASK, "checkout_present": checkout is not None, **report}, indent=2, sort_keys=True))
        return 0
    finally:
        if tmpdir is not None:
            tmpdir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
