#!/usr/bin/env python3
"""AF-023 acceptance checks for the anonymous reproducibility package."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

IDENTIFYING = re.compile(
    r"(?i)(\bbarberb\b|lift_coding|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|"
    r"overleaf\.com|BEGIN [A-Z ]*PRIVATE|x-api-key|Authorization:\s*Bearer|"
    r"sk-[A-Za-z0-9]{16,})"
)
MAX_ZIP = 100 * 1024 * 1024
EXPECTED_TABLES = {
    "table6_pipeline.tex": "a2ebba34895da30b383954e93ec582d2738a212d15de7b329fecf5a4d0c7aa49",
    "table11_training.tex": "dcb2582f2c091a48b3c26bb1b1698e1287d70d77cc2c3824b4f1f822bd2d6e74",
    "table13_assistance.tex": "655dfb58c0c1a960b636dbe35292ee243fbcb197fad1108f8a047742e2f62d3f",
}
PUBLICATION_NEEDLES = (
    "uploaded to arxiv",
    "submitted to openreview",
    "workshop submission completed",
    "authors approved",
    "paper was published",
)
REVIEW_NEEDLES = (
    "independent annotators agreed",
    "kappa =",
    "inter-annotator agreement of",
    "human review collected",
)


def find_repo_root(start: Path) -> Path:
    marker = Path("papers/completion/autoformalization/config/environment_manifest.json")
    for path in (start, *start.parents):
        if (path / marker).is_file():
            return path
    raise SystemExit("cannot locate repository root from check_outputs.py")


HERE = Path(__file__).resolve().parent
REPO_ROOT = find_repo_root(HERE)
PAPER = REPO_ROOT / "papers/completion/autoformalization"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    readme = PAPER / "artifact/README.md"
    manifest_path = PAPER / "artifact/manifest.json"
    s01_path = PAPER / "artifact/S01_S40_map.json"
    zip_path = PAPER / "submission/supplement.zip"
    report_path = PAPER / "evidence/anonymization_report.json"
    for path in (readme, manifest_path, s01_path, zip_path, report_path):
        if not path.is_file():
            errors.append(f"missing {path}")
    if errors:
        print("AF-023 check failed:\n- " + "\n- ".join(errors))
        return 1

    manifest = load_json(manifest_path)
    s01 = load_json(s01_path)
    report = load_json(report_path)
    readme_text = readme.read_text(encoding="utf-8")

    if s01.get("schema") != "autoformalization-anonymous-s01-s40-map/v1":
        errors.append("S01_S40_map.json schema mismatch")
    roles = s01.get("roles") or []
    if [role.get("id") for role in roles] != [f"S{i:02d}" for i in range(1, 41)]:
        errors.append("S01-S40 map does not contain S01 through S40 in order")
    if s01.get("private_ledger_excluded") is not True:
        errors.append("private ledger was not excluded from the anonymous map")

    def contains_key(obj, key: str) -> bool:
        if isinstance(obj, dict):
            if key in obj:
                return True
            return any(contains_key(value, key) for value in obj.values())
        if isinstance(obj, list):
            return any(contains_key(value, key) for value in obj)
        return False

    if contains_key(s01, "private_ledger"):
        errors.append("private_ledger key leaked into S01_S40_map.json")
    if any(role.get("path") for role in roles):
        errors.append("S01_S40_map.json still contains private repository paths")

    if manifest.get("schema") != "autoformalization-anonymous-artifact-manifest/v1":
        errors.append("manifest schema mismatch")
    if manifest.get("publication", {}).get("public_upload") is not False:
        errors.append("manifest does not deny public upload")
    if manifest.get("human_review", {}).get("fabricated") is not False:
        errors.append("manifest does not deny fabricated human review")
    tables = manifest.get("reported_tables") or {}
    for name, digest in EXPECTED_TABLES.items():
        if tables.get(name) != digest:
            errors.append(f"manifest table hash drifted for {name}")
    if "regenerate_tables.py --check" not in readme_text:
        errors.append("README missing regenerate_tables.py command")
    if "verify_retained_inputs.py" not in readme_text:
        errors.append("README missing verify_retained_inputs.py command")
    if "analyze_results.py --check" not in readme_text:
        errors.append("README missing analyze_results.py command")

    zip_size = zip_path.stat().st_size
    if zip_size > MAX_ZIP:
        errors.append(f"supplement.zip is {zip_size} bytes, exceeds 100 MB")
    if report.get("supplement_zip_bytes") != zip_size:
        errors.append("anonymization report zip size does not match supplement.zip")
    if report.get("supplement_zip_sha256") != sha256_file(zip_path):
        errors.append("anonymization report zip hash does not match supplement.zip")
    if report.get("double_blind") is not True:
        errors.append("anonymization report is not marked double-blind")
    if report.get("credentials", {}).get("secrets_exported") is not False:
        errors.append("anonymization report did not clear secrets")
    if report.get("publication", {}).get("public_upload") is not False:
        errors.append("anonymization report does not deny public upload")
    if report.get("human_review", {}).get("fabricated") is not False:
        errors.append("anonymization report does not deny fabricated review")
    if report.get("s01_s40_private_ledger_excluded") is not True:
        errors.append("anonymization report did not exclude the private ledger")
    if not report.get("large_artifacts_have_checksums"):
        errors.append("large artifacts are missing checksums")

    large = manifest.get("large_artifacts") or []
    if not large:
        errors.append("manifest has no large-artifact access strategy")
    for item in large:
        if not item.get("sha256") or len(str(item.get("sha256"))) != 64:
            errors.append(f"large artifact missing sha256: {item.get('id')}")
        access = item.get("access") or {}
        if access.get("publication_status") not in {
            "not_uploaded", "not_uploaded_by_this_package",
        }:
            errors.append(f"large artifact uploaded or unpublished status missing: {item.get('id')}")
        if not access.get("strategy"):
            errors.append(f"large artifact missing access strategy: {item.get('id')}")

    exported_texts = {
        "README.md": readme_text,
        "manifest.json": manifest_path.read_text(encoding="utf-8"),
        "S01_S40_map.json": s01_path.read_text(encoding="utf-8"),
        "anonymization_report.json": report_path.read_text(encoding="utf-8"),
    }
    for label, text in exported_texts.items():
        lower = text.lower()
        for needle in PUBLICATION_NEEDLES:
            if needle in lower:
                errors.append(f"{label} claims publication: {needle}")
        for needle in REVIEW_NEEDLES:
            if needle in lower and "not collected" not in lower:
                errors.append(f"{label} appears to fabricate human review: {needle}")
        for match in IDENTIFYING.finditer(text):
            errors.append(f"{label} identifying content: {match.group(0)[:80]}")

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        required = [
            "autoformalization-anonymous-reproducibility/README.md",
            "autoformalization-anonymous-reproducibility/manifest.json",
            "autoformalization-anonymous-reproducibility/S01_S40_map.json",
            "autoformalization-anonymous-reproducibility/checksums.json",
            "autoformalization-anonymous-reproducibility/regenerate_tables.py",
            "autoformalization-anonymous-reproducibility/verify_retained_inputs.py",
            "autoformalization-anonymous-reproducibility/frozen/results/summary.json",
            "autoformalization-anonymous-reproducibility/frozen/data/splits.json",
            "autoformalization-anonymous-reproducibility/frozen/evaluation/analyze_results.py",
        ]
        for name in required:
            if name not in names:
                errors.append(f"supplement.zip missing {name}")
        if zf.comment:
            errors.append("supplement.zip has a comment")
        for info in zf.infolist():
            if ".." in Path(info.filename).parts:
                errors.append(f"unsafe zip member {info.filename}")
            payload = zf.read(info.filename)
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for match in IDENTIFYING.finditer(text):
                errors.append(f"{info.filename} identifying content: {match.group(0)[:80]}")

        with tempfile.TemporaryDirectory(prefix="af023-unzip-") as tmp:
            zf.extractall(tmp)
            root = Path(tmp) / "autoformalization-anonymous-reproducibility"
            regen = root / "regenerate_tables.py"
            verify = root / "verify_retained_inputs.py"
            import subprocess
            python = "/usr/bin/python3.12"
            for script, extra in ((regen, ["--check"]), (verify, [])):
                proc = subprocess.run(
                    [python, "-S", str(script), *extra],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode != 0:
                    errors.append(f"{script.name} failed: {proc.stderr or proc.stdout}")
                    continue
                payload = json.loads(proc.stdout)
                if payload.get("ok") is not True:
                    errors.append(f"{script.name} reported ok=false")
                if script.name == "regenerate_tables.py":
                    for name, digest in EXPECTED_TABLES.items():
                        actual = (payload.get("tables") or {}).get(name, {}).get("sha256")
                        if actual != digest:
                            errors.append(f"ZIP regeneration hash mismatch for {name}")
                if script.name == "verify_retained_inputs.py" and payload.get("located", 0) < 40:
                    errors.append("ZIP retained-input locator found too few members")

    splits = PAPER / "data/splits.json"
    if splits.is_file():
        digest = sha256_file(splits)
        if digest != "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27":
            errors.append("paper-tree splits.json digest drifted from the AF-021 pin")

    if errors:
        print("AF-023 check failed:\n- " + "\n- ".join(errors))
        return 1
    print(json.dumps({
        "ok": True,
        "roles": len(roles),
        "supplement_zip_bytes": zip_size,
        "tables": EXPECTED_TABLES,
        "public_upload": False,
        "fabricated_human_review": False,
        "private_ledger_excluded": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
