#!/usr/bin/env python3
"""Trusted-runner input gate; private deny index must never be a provider-context mount.

This file validates bytes. Network namespace/mount enforcement is a separate runner obligation.
"""
import hashlib
import json
from pathlib import Path
import re
import unicodedata


def digest_text(text):
    words = re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())
    return hashlib.sha256(" ".join(words).encode()).hexdigest()


def scan_sources(path, deny):
    seen = set()
    rows = 0
    for line in Path(path).open():
        record = json.loads(line)
        normalized = digest_text(record["text"])
        identity = hashlib.sha256(record["record_id"].encode()).hexdigest()
        if normalized in deny["normalized_source_sha256"] or identity in deny["source_id_sha256"]:
            raise ValueError("Input denied: private final-test source identity/content detected")
        seen.add(normalized)
        rows += 1
    return {"source_records": rows, "unique_source_units": len(seen), "private_final_matches": 0}


def admit(root, role, source_path, private_deny_index, expected_splits_sha256):
    roles = {"training": "train", "teacher_fitting": "train", "model_selection": "selection", "fixed_canary": "fixed_canary"}
    if role not in roles:
        raise ValueError("Role denied: sealed final evaluation requires a separate locked harness")
    root = Path(root).resolve()
    source = Path(source_path)
    if source.is_symlink():
        raise ValueError("Symlink source inputs denied")
    manifest = root / "papers/completion/autoformalization/data/splits.json"
    if not re.fullmatch(r"[0-9a-f]{64}", expected_splits_sha256) or hashlib.sha256(manifest.read_bytes()).hexdigest() != expected_splits_sha256:
        raise ValueError("Split manifest differs from trusted frozen receipt hash")
    splits = json.loads(manifest.read_text())
    declared = splits["exports"][roles[role]]
    allowed = root / declared["path"]
    if source.resolve() != allowed.resolve() or not source.is_file():
        raise ValueError("Source path not admitted for declared role")
    raw_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if raw_hash != declared["sha256"] or source.stat().st_size != declared["bytes"]:
        raise ValueError("Source bytes differ from frozen role export")
    deny = json.loads(Path(private_deny_index).read_text())
    result = scan_sources(source, deny)
    return {"role": role, "frozen_export_hash_verified": True, "source_scan": result, "network_or_mount_enforcement_claimed": False}
