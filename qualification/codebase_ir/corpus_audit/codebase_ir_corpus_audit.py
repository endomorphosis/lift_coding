#!/usr/bin/env python3
"""Bounded, read-only source split audit, with no native imports or fitting."""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import math
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

INPUT_SCHEMA = "codebase-ir-corpus-audit-input@1"
REPORT_SCHEMA = "codebase-ir-corpus-audit-report@1"
ROLES = ("train", "tune", "canary", "final")
NATIVE_LINEAGE_SCHEMA = "codebase-source-feature-lineage@1"
NATIVE_TARGET_SCHEMA = "codebase-ir-source-bound-feature-targets@1"
NATIVE_BINDING_SCHEMA = "codebase-ir-feature-source-binding@1"
NATIVE_FALSE = {
    "qualified", "admitted", "formalized", "promotion_performed", "proof_authority",
    "source_runtime_semantics_verified", "behavioral_satisfaction", "admission_authority",
    "completion_authority",
}
NATIVE_PROVENANCE_FIELDS = {
    "schema", "head", "selections", "parent_version_id", "continuation",
    "training_targets", "tuning_targets", "canary_targets", "replay_targets",
    "ancestral_training", "current_evaluation_bindings", "implementation",
    "contract_sha256", "feature_space_sha256", "canary_monitoring", "replay_monitoring",
    *NATIVE_FALSE,
}
NATIVE_ENVELOPE_FIELDS = {
    "schema_version", "domain_id", "source_digest", "projections", "validation",
    "unsupported", "qualification_gaps", "ready_for_training", "qualified", "admitted",
    "formalized",
}
UNIT_FIELDS = {
    "id", "role", "repository_id", "path", "revision", "content_sha256", "source",
    "dependencies", "dependencies_complete", "related_revisions", "revision_relations_complete",
}
METADATA_FIELDS = {
    "dependencies", "dependencies_complete", "related_revisions", "revision_relations_complete",
}


class AuditInputError(ValueError):
    """An input is malformed, ambiguous, unbound, or over budget."""


@dataclass(frozen=True)
class Limits:
    max_json_bytes: int = 16 * 1024 * 1024
    max_total_json_bytes: int = 32 * 1024 * 1024
    max_json_nodes: int = 200_000
    max_json_depth: int = 64
    max_units: int = 512
    max_native_records: int = 16
    max_source_bytes: int = 64 * 1024
    max_total_source_bytes: int = 4 * 1024 * 1024
    max_ast_nodes: int = 4096
    max_ast_depth: int = 64
    max_links: int = 8192
    max_history: int = 512

    def __post_init__(self) -> None:
        if any(type(value) is not int or value <= 0 for value in asdict(self).values()):
            raise AuditInputError("limits must be positive exact integers")


DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class Unit:
    id: str
    role: str
    repository_id: str
    path: str
    revision: str
    content_sha256: str
    normalized_ast_sha256: str | None
    size_bytes: int | None
    dependencies: tuple[str, ...]
    dependencies_complete: bool
    related_revisions: tuple[str, ...]
    revision_relations_complete: bool
    origin: str
    source_bytes_verified: bool

    def identity(self) -> tuple[str, str, str]:
        return self.repository_id, self.path, self.content_sha256

    def report(self) -> dict[str, Any]:
        value = asdict(self)
        value["dependencies"] = list(self.dependencies)
        value["related_revisions"] = list(self.related_revisions)
        return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditInputError(message)


def _closed(value: Any, fields: set[str], label: str) -> dict:
    _require(type(value) is dict and set(value) == fields, f"closed {label} fields required")
    return value


def _text(value: Any, label: str, maximum: int = 256) -> str:
    try:
        valid = (type(value) is str and bool(value) and value == value.strip()
                 and len(value.encode("utf-8")) <= maximum
                 and not any(ord(character) < 32 for character in value))
    except UnicodeError:
        valid = False
    _require(valid, f"invalid bounded {label}")
    return value


def _digest(value: Any, label: str) -> str:
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             f"lowercase SHA-256 required for {label}")
    return value


def _relative_path(value: Any, label: str) -> str:
    value = _text(value, label, 1024)
    path = PurePosixPath(value)
    _require(not path.is_absolute() and path.as_posix() == value and ".." not in path.parts
             and "\\" not in value and value != ".", f"canonical relative {label} required")
    return value


def _bool(value: Any, label: str) -> bool:
    _require(type(value) is bool, f"explicit boolean required for {label}")
    return value


def _references(value: Any, label: str, limits: Limits) -> tuple[str, ...]:
    _require(type(value) is list and len(value) <= limits.max_links, f"bounded {label} list required")
    result = tuple(_text(item, label) for item in value)
    _require(len(set(result)) == len(result), f"duplicate {label} reference")
    return tuple(sorted(result))


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise AuditInputError("bounded finite UTF-8 JSON required") from exc


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _raw_source_cid(value: bytes) -> str:
    """CIDv1/raw/sha2-256 lowercase base32 for the declared source profile."""
    encoded = base64.b32encode(b"\x01\x55\x12\x20" + hashlib.sha256(value).digest())
    return "b" + encoded.decode("ascii").rstrip("=").lower()


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key[:128]}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise AuditInputError(f"nonfinite JSON number: {value}")


def _json_bound(value: Any, limits: Limits) -> None:
    pending, count = [(value, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        _require(count <= limits.max_json_nodes and depth <= limits.max_json_depth,
                 "JSON node/depth budget exceeded")
        if type(node) is dict:
            pending.extend((child, depth + 1) for child in node.values())
        elif type(node) is list:
            pending.extend((child, depth + 1) for child in node)
        elif type(node) is str:
            try:
                node.encode("utf-8")
            except UnicodeError as exc:
                raise AuditInputError("JSON contains invalid Unicode") from exc
        elif type(node) is float:
            _require(math.isfinite(node), "nonfinite JSON number")


def _load_json(raw: bytes, limits: Limits) -> dict:
    _require(len(raw) <= limits.max_json_bytes, "JSON byte budget exceeded")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_pairs,
                           parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, AuditInputError):
            raise
        raise AuditInputError("invalid UTF-8 JSON") from exc
    _require(type(value) is dict, "JSON object required")
    _json_bound(value, limits)
    return value


def _read_bounded(path: Path, maximum: int) -> bytes:
    """Reject special files and final-component symlinks before bounded reads."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            _require(stat.S_ISREG(metadata.st_mode), "regular input file required")
            _require(metadata.st_size <= maximum, "input file byte budget exceeded")
            raw = stream.read(maximum + 1)
    except OSError as exc:
        raise AuditInputError(f"cannot read input file: {path.name}") from exc
    _require(len(raw) <= maximum, "input file byte budget exceeded")
    return raw


def _input_file(root: Path, value: Any) -> Path:
    relative = _relative_path(value, "input file")
    path = root / relative
    try:
        _require(path.resolve().is_relative_to(root.resolve()), "input file escapes manifest directory")
    except (OSError, RuntimeError) as exc:
        raise AuditInputError("invalid input file path") from exc
    return path


def normalized_ast_digest(raw: bytes, limits: Limits = DEFAULT_LIMITS) -> str:
    """Discard locations/comments/formatting; retain names, operators and values."""
    _require(len(raw) <= limits.max_source_bytes, "source byte budget exceeded")
    try:
        text = raw.decode("utf-8")
        tree = ast.parse(text, mode="exec", type_comments=True)
    except (UnicodeError, SyntaxError, ValueError, RecursionError) as exc:
        raise AuditInputError("well-formed UTF-8 Python source required") from exc
    pending, count = [(tree, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        _require(count <= limits.max_ast_nodes and depth <= limits.max_ast_depth,
                 "AST node/depth budget exceeded")
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    try:
        normalized = ast.dump(tree, annotate_fields=True, include_attributes=False).encode("utf-8")
    except (RecursionError, UnicodeError) as exc:
        raise AuditInputError("AST normalization budget exceeded") from exc
    return _sha(normalized)


class _Loader:
    def __init__(self, root: Path, limits: Limits):
        self.root, self.limits = root, limits
        self.source_bytes = 0
        self.json_bytes = 0
        self.links = 0
        self.units: dict[str, Unit] = {}
        self.sources: dict[tuple[str, str, str], bytes] = {}
        self.issues: list[dict[str, str]] = []
        self.history: set[tuple[str, str, str]] = set()
        self.parents: dict[str, str | None] = {}
        self.native_histories: dict[str, set[tuple[str, str, str]]] = {}
        self.native_training: dict[str, set[tuple[str, str, str]]] = {}
        self.native_inventory: list[dict[str, str]] = []

    def issue(self, code: str, *, unit_id: str = "", reference: str = "") -> None:
        self.issues.append({"code": code, "unit_id": unit_id, "reference": reference})

    def json_file(self, relative: Any, expected: Any) -> dict:
        expected = _digest(expected, "export file")
        raw = _read_bounded(_input_file(self.root, relative), self.limits.max_json_bytes)
        _require(_sha(raw) == expected, "export file digest differs from manifest")
        self.json_bytes += len(raw)
        _require(self.json_bytes <= self.limits.max_total_json_bytes, "total JSON byte budget exceeded")
        return _load_json(raw, self.limits)

    def add_unit(self, row: dict, raw: bytes, origin: str) -> None:
        unit_id = _text(row["id"], "unit ID")
        _require(unit_id not in self.units, "duplicate unit ID")
        _require(len(self.units) < self.limits.max_units, "unit budget exceeded")
        role = row["role"]
        _require(type(role) is str and role in ROLES, "explicit train/tune/canary/final role required")
        repository = _text(row["repository_id"], "repository ID")
        path = _relative_path(row["path"], "source path")
        _require(path.endswith(".py"), "Python source path required")
        revision = _text(row["revision"], "revision")
        digest = _digest(row["content_sha256"], "source content")
        _require(_sha(raw) == digest, "source content digest differs from exact bytes")
        self.source_bytes += len(raw)
        _require(self.source_bytes <= self.limits.max_total_source_bytes, "total source byte budget exceeded")
        ast_digest = normalized_ast_digest(raw, self.limits)
        dependencies = _references(row["dependencies"], "dependency", self.limits)
        revisions = _references(row["related_revisions"], "related revision", self.limits)
        self.links += len(dependencies) + len(revisions)
        _require(self.links <= self.limits.max_links, "total link budget exceeded")
        unit = Unit(unit_id, role, repository, path, revision, digest, ast_digest, len(raw),
                    dependencies, _bool(row["dependencies_complete"], "dependencies_complete"),
                    revisions, _bool(row["revision_relations_complete"], "revision_relations_complete"),
                    origin, True)
        self.units[unit_id] = unit
        self.sources[unit.identity()] = raw

    def manual_unit(self, row: Any) -> None:
        row = _closed(row, UNIT_FIELDS, "unit")
        unit_id = _text(row["id"], "unit ID")
        _require(not unit_id.startswith(("native/", "ancestral/")), "reserved unit ID prefix")
        source = row["source"]
        _require(type(source) is dict and set(source) in ({"bytes_hex"}, {"file"}),
                 "one exact source bytes_hex/file binding required")
        if "bytes_hex" in source:
            raw = self.hex_source(source["bytes_hex"])
        else:
            raw = _read_bounded(_input_file(self.root, source["file"]), self.limits.max_source_bytes)
        self.add_unit(row, raw, "manifest")

    def hex_source(self, value: Any) -> bytes:
        _require(type(value) is str and len(value) <= self.limits.max_source_bytes * 2,
                 "bounded source bytes_hex required")
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise AuditInputError("invalid source bytes_hex") from exc
        _require(raw.hex() == value, "canonical lowercase exact source bytes_hex required")
        return raw

    def history_row(self, row: Any, *, native: bool = False) -> None:
        field = "source_digest" if native else "content_sha256"
        row = _closed(row, {"repository_id", "path", field}, "ancestral training identity")
        identity = (_text(row["repository_id"], "ancestral repository"),
                    _relative_path(row["path"], "ancestral source path"),
                    _digest(row[field], "ancestral content"))
        _require(identity[1].endswith(".py"), "Python ancestral source path required")
        self.history.add(identity)
        _require(len(self.history) <= self.limits.max_history, "ancestral identity budget exceeded")

    def native_record(self, record: Any) -> None:
        record = _closed(record, {"version_id", "file", "sha256", "unit_metadata"}, "native export")
        version = _text(record["version_id"], "native version ID", 128)
        _require("/" not in version and version not in self.parents, "unique slash-free native version ID required")
        exported = self.json_file(record["file"], record["sha256"])
        if exported.get("schema") == NATIVE_LINEAGE_SCHEMA:
            provenance = exported
        else:
            _require(type(exported.get("report")) is dict, "native checkpoint report required")
            provenance = exported["report"].get("codebase_provenance")
        provenance = _closed(provenance, NATIVE_PROVENANCE_FIELDS, "native provenance")
        _require(provenance["schema"] == NATIVE_LINEAGE_SCHEMA
                 and all(provenance[name] is False for name in NATIVE_FALSE),
                 "versioned nonauthoritative native provenance required")
        parent = provenance["parent_version_id"]
        if parent is not None:
            parent = _text(parent, "native parent version ID", 128)
        _require(provenance["continuation"] == ("fresh_feature_basis" if parent is None
                                               else "exact_frozen_basis_adam_resume"),
                 "explicit native continuation policy required")
        self.parents[version] = parent
        self.native_training[version] = set()
        head = provenance["head"]
        _require(type(head) is dict and type(head.get("repository_id")) is str,
                 "native provenance head required")
        _text(head["repository_id"], "native repository ID")
        metadata = record["unit_metadata"]
        _require(type(metadata) is dict and len(metadata) <= self.limits.max_units,
                 "bounded native unit_metadata object required")
        used_metadata = set()
        selections = provenance["selections"]
        _require(type(selections) is list and 3 <= len(selections) <= 16,
                 "bounded native selections required")
        selected_paths, selected_roles = set(), set()
        for selection in selections:
            selection = _closed(selection, {"path", "role", "contracts"}, "native selection")
            path = _relative_path(selection["path"], "native selected path")
            _require(path not in selected_paths and type(selection["role"]) is str
                     and selection["role"] in {"train", "tune", "canary"},
                     "unique explicit native selections required")
            _require(type(selection["contracts"]) is list and len(selection["contracts"]) <= 8,
                     "bounded native selected contracts required")
            selected_paths.add(path)
            selected_roles.add(selection["role"])
        _require(selected_roles == {"train", "tune", "canary"}, "all native source split roles required")
        for field, role in (("training_targets", "train"), ("tuning_targets", "tune"),
                            ("canary_targets", "canary"), ("replay_targets", "train")):
            batch = provenance[field]
            _require(type(batch) is list and 1 <= len(batch) <= 32, "bounded native target batch required")
            for index, target in enumerate(batch):
                unit_id = f"native/{version}/{field}/{index}"
                unit_row, raw = self.native_target(target, unit_id, role)
                _require(unit_row["repository_id"] == head["repository_id"],
                         "native target/provenance repository mismatch")
                if unit_id in metadata:
                    extra = _closed(metadata[unit_id], METADATA_FIELDS, "native unit metadata")
                    unit_row.update(extra)
                    used_metadata.add(unit_id)
                self.add_unit(unit_row, raw, field)
                if field == "training_targets":
                    self.native_training[version].add(self.units[unit_id].identity())
        _require(used_metadata == set(metadata), "native metadata references unknown unit ID")
        history = provenance["ancestral_training"]
        _require(type(history) is list and len(history) <= self.limits.max_history,
                 "bounded native ancestral history required")
        self.native_histories[version] = set()
        for row in history:
            self.history_row(row, native=True)
            self.native_histories[version].add((row["repository_id"], row["path"], row["source_digest"]))
        if parent is None:
            _require(not history, "native root cannot claim ancestral training")
        self.native_inventory.append({"version_id": version, "sha256": record["sha256"],
                                      "parent_version_id": parent})

    def native_target(self, target: Any, unit_id: str, role: str) -> tuple[dict, bytes]:
        target = _closed(target, NATIVE_ENVELOPE_FIELDS, "native domain target envelope")
        _require(target["schema_version"] == "autoencoder-domain-targets/v1"
                 and target["domain_id"] == "codebase_ir"
                 and all(target[name] is False for name in ("qualified", "admitted", "formalized")),
                 "nonauthoritative CodebaseIR target required")
        for field in ("projections", "unsupported", "qualification_gaps"):
            _require(type(target[field]) is list, "native envelope inventories required")
        _bool(target["ready_for_training"], "native training readiness")
        validation = target["validation"]
        _require(type(validation) is list and len(validation) == 1
                 and type(validation[0]) is dict
                 and validation[0].get("validator_id") == "codebase_ir.exact_native_target_replay@1",
                 "single native CodebaseIR replay declaration required")
        details = validation[0].get("details")
        _require(type(details) is dict and details.get("target_schema") == NATIVE_TARGET_SCHEMA,
                 "native source target details required")
        binding = _closed(details.get("source_binding"),
                          {"schema", "head", "repository_id", "path", "source_key", "entry", "unit",
                           "source_cid", "content_sha256", "ast_cid", "source_revision"}, "native source binding")
        _require(binding["schema"] == NATIVE_BINDING_SCHEMA, "native source binding schema required")
        raw = self.hex_source(details.get("source_bytes_hex"))
        repository = _text(binding.get("repository_id"), "bound native repository")
        path = _relative_path(binding.get("path"), "bound native path")
        digest = _digest(binding.get("content_sha256"), "bound native source")
        _require(_sha(raw) == digest, "native source content differs from embedded bytes")
        head = _closed(binding["head"], {"schema", "repository_id", "generation", "manifest_cid",
                                        "snapshot_cid", "ast_revision_id", "receipt_cid"}, "native source head")
        _require(head["schema"] == "codebase-head@1" and head["repository_id"] == repository,
                 "native source repository/head mismatch")
        _require(type(head["generation"]) is int and 0 < head["generation"] < 2 ** 63,
                 "native source head generation required")
        for name in ("manifest_cid", "snapshot_cid", "receipt_cid"):
            _text(head[name], "native " + name)
        _require(head["ast_revision_id"] == f"rev:{repository}:snapshot:{head['snapshot_cid']}",
                 "native AST head revision mismatch")
        entry = binding["entry"]
        _require(type(entry) is dict and entry.get("path") == path
                 and type(entry.get("size_bytes")) is int and entry["size_bytes"] == len(raw),
                 "native source entry/path/size mismatch")
        _require(entry.get("source_cid") == binding["source_cid"] == _raw_source_cid(raw)
                 and entry.get("raw_path_hex") == path.encode("utf-8").hex()
                 and binding["source_key"] == "raw:" + entry["raw_path_hex"],
                 "native source entry identity mismatch")
        unit = _closed(binding["unit"], {"schema", "source_key", "entry_cid", "ast_cid", "parse_status"},
                       "native structural unit")
        _require(unit["schema"] == "codebase-ir-structural-unit@1"
                 and unit["source_key"] == binding["source_key"]
                 and unit["entry_cid"] == entry.get("entry_cid")
                 and unit["ast_cid"] == binding["ast_cid"], "native structural/source binding mismatch")
        _text(unit["entry_cid"], "native entry CID")
        _require(type(unit["parse_status"]) is str
                 and unit["parse_status"] in {"ok", "partial", "failed", "opaque", "unindexed"},
                 "explicit native parse status required")
        _require((unit["ast_cid"] is None) == (unit["parse_status"] in {"opaque", "unindexed"}),
                 "native structural AST availability mismatch")
        if unit["ast_cid"] is not None:
            _text(unit["ast_cid"], "native AST CID")
        revision = _text(binding.get("source_revision"), "native source revision")
        _require(type(head.get("snapshot_cid")) is str and revision == "snapshot:" + head["snapshot_cid"],
                 "native source revision/head mismatch")
        contracts = details.get("authored_contracts")
        _require(type(contracts) is list, "native authored contract inventory required")
        expected_target_digest = _sha(_canonical({"target_schema": NATIVE_TARGET_SCHEMA,
                                                  "source_binding": binding,
                                                  "authored_contracts": contracts}))
        _require(target["source_digest"] == expected_target_digest, "native target source digest mismatch")
        return ({"id": unit_id, "role": role, "repository_id": repository, "path": path,
                 "revision": revision, "content_sha256": digest, "dependencies": [],
                 "dependencies_complete": False, "related_revisions": [],
                 "revision_relations_complete": False}, raw)

    def finish_history(self) -> None:
        for index, identity in enumerate(sorted(self.history)):
            _require(len(self.units) < self.limits.max_units, "unit budget exceeded by ancestral history")
            raw = self.sources.get(identity)
            unit_id = f"ancestral/{index}"
            witnesses = sorted((unit for unit in self.units.values() if unit.identity() == identity
                                and unit.source_bytes_verified), key=lambda unit: unit.id)
            if raw is None:
                self.issue("ancestral_source_unavailable", unit_id=unit_id,
                           reference="|".join(identity))
            self.units[unit_id] = Unit(unit_id, "train", *identity[:2],
                                      witnesses[0].revision if witnesses else "ancestral:identity-only",
                                      identity[2], None if raw is None else normalized_ast_digest(raw, self.limits),
                                      None if raw is None else len(raw),
                                      tuple(sorted({ref for unit in witnesses for ref in unit.dependencies})),
                                      bool(witnesses) and all(unit.dependencies_complete for unit in witnesses),
                                      tuple(sorted({ref for unit in witnesses for ref in unit.related_revisions})),
                                      bool(witnesses) and all(unit.revision_relations_complete for unit in witnesses),
                                      "ancestral_training", raw is not None)
            # Reuse only metadata attached to an exact verified source identity.
        for version, parent in sorted(self.parents.items()):
            if parent is not None and parent not in self.parents:
                self.issue("native_parent_unavailable", reference=parent)
            elif parent is not None:
                expected = self.native_histories[parent] | self.native_training[parent]
                _require(self.native_histories[version] == expected,
                         "native ancestry training identities differ from exported parent")
            seen, current = set(), version
            while current in self.parents:
                _require(current not in seen, "cyclic native ancestry")
                seen.add(current)
                current = self.parents[current]


class _Union:
    def __init__(self, names: list[str]):
        self.parent = {name: name for name in names}

    def find(self, name: str) -> str:
        self.parent.setdefault(name, name)
        current = name
        while self.parent[current] != current:
            current = self.parent[current]
        root = current
        while self.parent[name] != name:
            parent = self.parent[name]
            self.parent[name] = root
            name = parent
        return root

    def join(self, left: str, right: str) -> None:
        left, right = self.find(left), self.find(right)
        if left != right:
            smaller, larger = sorted((left, right))
            self.parent[larger] = smaller

    def groups(self, names: list[str]) -> list[list[str]]:
        buckets: dict[str, list[str]] = {}
        for name in sorted(names):
            buckets.setdefault(self.find(name), []).append(name)
        return sorted((group for group in buckets.values() if len(group) > 1), key=lambda row: row)


def _group_leaks(units: dict[str, Unit], loader: _Loader) -> list[dict]:
    names = sorted(units)
    combined = _Union(names)
    leaks = []
    edges: set[tuple[str, str, str]] = set()
    for kind, key in (("exact_bytes", lambda item: item.content_sha256),
                      ("normalized_ast", lambda item: item.normalized_ast_sha256),
                      ("same_repository_path", lambda item: (item.repository_id, item.path))):
        union, buckets = _Union(names), {}
        for name in names:
            value = key(units[name])
            if value is not None:
                buckets.setdefault(value, []).append(name)
        for group in buckets.values():
            for name in group[1:]:
                union.join(group[0], name)
                combined.join(group[0], name)
                edges.add((kind, group[0], name))
        leaks.extend(_leaks_for(kind, union.groups(names), units))
    for kind, field in (("related_revision", "related_revisions"),
                        ("dependency_connected", "dependencies")):
        union = _Union(names)
        for name in names:
            for reference in getattr(units[name], field):
                if reference not in units:
                    loader.issue("unresolved_" + field, unit_id=name, reference=reference)
                union.join(name, reference)
                combined.join(name, reference)
                edges.add((kind, name, reference))
        leaks.extend(_leaks_for(kind, union.groups(names), units))
    for group in combined.groups(names):
        roles = sorted({units[name].role for name in group})
        if len(roles) > 1:
            known = set(group)
            # Include declared unresolved edges reached by the component as witnesses.
            root = combined.find(group[0])
            witnesses = [{"kind": kind, "from": left, "to": right}
                         for kind, left, right in sorted(edges)
                         if combined.find(left) == root and combined.find(right) == root]
            leaks.append({"kind": "combined_connected", "unit_ids": sorted(known),
                          "roles": roles, "edges": witnesses})
    return sorted(leaks, key=lambda row: (row["kind"], row["unit_ids"]))


def _leaks_for(kind: str, groups: list[list[str]], units: dict[str, Unit]) -> list[dict]:
    return [{"kind": kind, "unit_ids": group, "roles": sorted({units[name].role for name in group})}
            for group in groups if len({units[name].role for name in group}) > 1]


def audit_manifest(path: str | Path, limits: Limits = DEFAULT_LIMITS) -> dict[str, Any]:
    """Return deterministic findings for an explicitly declared immutable corpus."""
    path = Path(path)
    raw = _read_bounded(path, limits.max_json_bytes)
    manifest = _load_json(raw, limits)
    manifest = _closed(manifest, {"schema", "units", "native_records", "ancestral_training",
                                  "ancestry_complete"}, "audit manifest")
    _require(manifest["schema"] == INPUT_SCHEMA, "versioned audit input schema required")
    ancestry_complete = _bool(manifest["ancestry_complete"], "ancestry_complete")
    units, native_records, history = (manifest[name] for name in ("units", "native_records", "ancestral_training"))
    _require(type(units) is list and len(units) <= limits.max_units, "bounded unit list required")
    _require(type(native_records) is list and len(native_records) <= limits.max_native_records,
             "bounded native record list required")
    _require(type(history) is list and len(history) <= limits.max_history, "bounded ancestral history required")
    _require(bool(units or native_records), "at least one source unit or native export required")
    loader = _Loader(path.parent, limits)
    loader.json_bytes = len(raw)
    _require(loader.json_bytes <= limits.max_total_json_bytes, "total JSON byte budget exceeded")
    for row in units:
        loader.manual_unit(row)
    for row in native_records:
        loader.native_record(row)
    for row in history:
        loader.history_row(row)
    loader.finish_history()
    present_roles = sorted({unit.role for unit in loader.units.values()})
    for role in ROLES:
        if role not in present_roles:
            loader.issue("split_role_unavailable", reference=role)
    if not ancestry_complete:
        loader.issue("ancestry_not_declared_complete")
    for name, unit in sorted(loader.units.items()):
        if not unit.dependencies_complete:
            loader.issue("dependencies_not_declared_complete", unit_id=name)
        if not unit.revision_relations_complete:
            loader.issue("revision_relations_not_declared_complete", unit_id=name)
    leaks = _group_leaks(loader.units, loader)
    issues = sorted({tuple(sorted(row.items())) for row in loader.issues})
    complete = not issues
    status = "leaks_found" if leaks else "clean" if complete else "incomplete"
    return {
        "schema": REPORT_SCHEMA, "status": status, "complete_for_declared_scope": complete,
        "leak_free_within_declared_scope": complete and not leaks,
        "input_sha256": _sha(raw), "roles_present": present_roles,
        "normalization": "module Python AST; attributes/ordinary comments/formatting removed; names/operators/literals/type metadata retained",
        "python_ast_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "native_replay_performed": False, "training_executed": False,
        "proof_authority": False, "promotion_authority": False,
        "limits": asdict(limits), "units": [loader.units[name].report() for name in sorted(loader.units)],
        "native_exports": sorted(loader.native_inventory, key=lambda row: row["version_id"]),
        "issues": [dict(row) for row in issues], "leaks": leaks,
    }


def write_private_report(path: str | Path, report: dict) -> None:
    """Write a new regular report with owner-only permissions; never overwrite."""
    raw = _canonical(report) + b"\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
    except OSError as exc:
        raise AuditInputError("report must be a new writable file in an existing private output directory") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="closed source/role manifest, with optional native exports")
    parser.add_argument("--output", required=True, type=Path, help="new owner-only JSON report; existing files rejected")
    arguments = parser.parse_args(argv)
    try:
        report = audit_manifest(arguments.manifest)
        write_private_report(arguments.output, report)
    except AuditInputError as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 3
    print(f"{report['status']}: {len(report['leaks'])} cross-role groups; {len(report['issues'])} completeness issues")
    return {"clean": 0, "leaks_found": 1, "incomplete": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
