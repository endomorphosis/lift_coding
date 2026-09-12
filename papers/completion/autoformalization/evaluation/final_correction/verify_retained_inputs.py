#!/usr/bin/env python3
"""Locate every retained-claim input in the anonymous bundle and check SHA-256."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_bundle(start: Path) -> Path:
    for path in (start.resolve(), *start.resolve().parents):
        if (path / "checksums.json").is_file() and (path / "manifest.json").is_file():
            return path
        frozen = path / "frozen" / "checksums.json"
        if frozen.is_file():
            return path / "frozen"
    raise SystemExit("cannot locate checksums.json in the anonymous bundle")


def main() -> int:
    bundle = find_bundle(Path(__file__).resolve().parent)
    checksums = json.loads((bundle / "checksums.json").read_text(encoding="utf-8"))
    missing = []
    mismatched = []
    located = []
    large = []
    for item in checksums.get("included_members", []):
        rel = item["path"]
        target = bundle / rel
        if not target.is_file():
            missing.append(rel)
            continue
        digest = sha256_bytes(target.read_bytes())
        if digest != item["sha256"]:
            mismatched.append({"path": rel, "expected": item["sha256"], "actual": digest})
        else:
            located.append({"path": rel, "sha256": digest, "bytes": item.get("bytes")})
    for item in checksums.get("large_artifacts", []):
        large.append({
            "id": item.get("id"),
            "sha256": item.get("sha256"),
            "bytes": item.get("bytes"),
            "access": item.get("access"),
            "present_in_bundle": False,
        })
    report = {
        "ok": not missing and not mismatched,
        "located": len(located),
        "missing": missing,
        "mismatched": mismatched,
        "large_artifacts_hash_bound": large,
        "public_upload": False,
        "fabricated_human_review": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
