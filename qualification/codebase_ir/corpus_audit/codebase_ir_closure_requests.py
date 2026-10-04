#!/usr/bin/env python3
"""Recover pinned owner facts and request missing native split closure evidence."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_corpus_audit as audit
import codebase_ir_source_metadata as metadata

REPORT_SCHEMA = "codebase-ir-native-closure-requests@1"
FACTS_SCHEMA = "codebase-ir-retained-owner-facts@1"
MANIFEST_FIELDS = {"schema", "authority", "snapshot", "semantic_state", "ast_revision_id", "units", "coverage"}
AST_SCHEMA = "ipfs-datasets.software-contracts.ast-ir@1.0.0"


@dataclass(frozen=True)
class RecoveryLimits:
    max_owner_files: int = 128
    max_owner_bytes: int = 16 * 1024 * 1024
    max_manifest_entries: int = 256
    max_git_objects: int = 128
    max_git_object_bytes: int = 1024 * 1024
    max_git_seconds: int = 30
    max_git_child_seconds: int = 5

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()),
                       "positive exact recovery budgets required")


DEFAULT_RECOVERY_LIMITS = RecoveryLimits()


def structured_cid(value: dict) -> str:
    """Recompute the declared software-contract CIDv1/dag-json/sha2-256 profile."""
    pending = [value]
    while pending:
        item = pending.pop()
        audit._require(item is None or type(item) in {dict, list, str, int, bool},
                       "owner structured CID profile forbids floats/host values")
        if type(item) is dict:
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    digest = hashlib.sha256(audit._canonical(value)).digest()
    return "b" + base64.b32encode(b"\x01\xa9\x02\x12\x20" + digest).decode().rstrip("=").lower()


def _profile_cid(cid: str, *, source=False):
    audit._text(cid, "owner CID")
    audit._require(re.fullmatch(r"b[a-z2-7]+", cid) is not None, "canonical owner base32 CID required")
    try:
        encoded = cid[1:].upper()
        raw = base64.b32decode(encoded + "=" * ((-len(encoded)) % 8))
    except ValueError as exc:
        raise audit.AuditInputError("invalid owner CID encoding") from exc
    prefix = b"\x01\x55\x12\x20" if source else b"\x01\xa9\x02\x12\x20"
    audit._require(raw.startswith(prefix) and len(raw) == len(prefix) + 32,
                   "reviewed owner CID codec/hash profile required")
    audit._require("b" + base64.b32encode(raw).decode().rstrip("=").lower() == cid,
                   "canonical owner CID encoding required")


class _CAS:
    def __init__(self, root: Path | None, output: Path, limits: RecoveryLimits, audit_limits: audit.Limits):
        self.root, self.output, self.limits, self.audit_limits = root, output, limits, audit_limits
        self.cache, self.rows, self.frontiers = {}, [], []
        self.total_bytes = 0

    def get(self, cid: str, *, source=False, expected: bytes | None = None) -> bytes | None:
        _profile_cid(cid, source=source)
        key = (cid, source)
        if key in self.cache:
            raw = self.cache[key]
            if raw is not None and expected is not None:
                audit._require(raw == expected, "conflicting expected owner artifact bytes")
            return raw
        audit._require(len(self.cache) < self.limits.max_owner_files, "owner artifact file budget exceeded")
        relative = Path("source" if source else "structured") / cid[:4] / cid
        if self.root is None:
            self.frontiers.append({"code": "source_owner_cas_not_supplied", "cid": cid, "kind": relative.parts[0]})
            self.cache[key] = None
            return None
        remaining = self.limits.max_owner_bytes - self.total_bytes
        audit._require(remaining > 0, "owner artifact byte budget exhausted")
        try:
            raw = audit._read_bounded(self.root / relative, min(self.audit_limits.max_json_bytes, remaining))
        except audit.AuditInputError as exc:
            if "budget" in str(exc):
                raise audit.AuditInputError("owner artifact byte budget exceeded") from exc
            self.frontiers.append({"code": "source_owner_artifact_unavailable", "cid": cid,
                                   "kind": relative.parts[0], "relative_path": relative.as_posix()})
            self.cache[key] = None
            return None
        self.total_bytes += len(raw)
        audit._require(self.total_bytes <= self.limits.max_owner_bytes, "owner artifact byte budget exceeded")
        if source:
            valid = audit._raw_source_cid(raw) == cid
        else:
            value = audit._load_json(raw, self.audit_limits)
            valid = structured_cid(value) == cid and audit._canonical(value) == raw
        if not valid or (expected is not None and raw != expected):
            self.frontiers.append({"code": "source_owner_content_binding_drift", "cid": cid,
                                   "kind": relative.parts[0], "observed_sha256": audit._sha(raw)})
            self.cache[key] = None
            return None
        retained = self.output / "owner_cas" / relative
        retained.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata._write_bytes(retained, raw)
        self.rows.append({"cid": cid, "kind": relative.parts[0], "sha256": audit._sha(raw),
                          "size_bytes": len(raw), "retained_as": retained.relative_to(self.output).as_posix(),
                          "origin": (self.root / relative).as_posix(), "content_profile_verified": True})
        self.cache[key] = raw
        return raw


class _Git:
    def __init__(self, repository: Path | None, output: Path, limits: RecoveryLimits):
        self.repository, self.output, self.limits = repository, output, limits
        self.deadline = time.monotonic() + limits.max_git_seconds
        self.cache, self.rows, self.frontiers = {}, [], []

    def command(self, arguments: list[str], maximum: int) -> bytes:
        audit._require(time.monotonic() < self.deadline, "Git recovery deadline exceeded")
        env = dict(os.environ)
        env.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "",
                    "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GIT_PROTOCOL_FROM_USER": "0",
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull})
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
            env.pop(key, None)
        for key in list(env):
            if (key in {"GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_NAMESPACE", "GIT_REPLACE_REF_BASE"}
                    or re.fullmatch(r"GIT_CONFIG_(KEY|VALUE)_[0-9]+", key)):
                env.pop(key, None)
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(["git", "--no-optional-locks", "-c", "protocol.allow=never",
                                        "-C", str(self.repository), *arguments],
                                       env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = process.wait(timeout=min(self.limits.max_git_child_seconds,
                                                max(0.01, self.deadline - time.monotonic())))
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise audit.AuditInputError("bounded Git recovery child timed out") from exc
            stdout.seek(0)
            raw = stdout.read(maximum + 1)
            audit._require(code == 0 and len(raw) <= maximum, "Git object unavailable or output over budget")
            return raw

    def object(self, oid: str, kind: str) -> bytes | None:
        audit._require(type(oid) is str and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid) is not None,
                       "exact Git object identity required")
        if oid in self.cache:
            stored_kind, raw = self.cache[oid]
            audit._require(stored_kind == kind, "Git object kind binding differs")
            return raw
        audit._require(len(self.cache) < self.limits.max_git_objects, "Git object budget exceeded")
        if self.repository is None:
            self.frontiers.append({"code": "retained_git_repository_not_supplied", "oid": oid})
            self.cache[oid] = (kind, None)
            return None
        try:
            observed_kind = self.command(["cat-file", "-t", oid], 16).decode().strip()
            size_text = self.command(["cat-file", "-s", oid], 32).decode().strip()
            audit._require(observed_kind == kind and re.fullmatch(r"[0-9]+", size_text) is not None,
                           "Git object type/size binding differs")
            size = int(size_text)
            audit._require(size <= self.limits.max_git_object_bytes, "Git object byte budget exceeded")
            raw = self.command(["cat-file", kind, oid], size)
            audit._require(len(raw) == size, "Git object size changed during read")
            digest = hashlib.sha1 if len(oid) == 40 else hashlib.sha256
            audit._require(digest(f"{kind} {len(raw)}\0".encode() + raw).hexdigest() == oid,
                           "Git object digest differs")
        except (audit.AuditInputError, UnicodeError, OSError) as exc:
            self.frontiers.append({"code": "retained_git_object_unavailable", "oid": oid,
                                   "kind": kind, "reason": str(exc)[:256]})
            self.cache[oid] = (kind, None)
            return None
        retained = self.output / "git_objects" / oid
        retained.parent.mkdir(mode=0o700, exist_ok=True)
        metadata._write_bytes(retained, raw)
        self.rows.append({"oid": oid, "kind": kind, "sha256": audit._sha(raw), "size_bytes": len(raw),
                          "retained_as": retained.relative_to(self.output).as_posix()})
        self.cache[oid] = (kind, raw)
        return raw

    def tree(self, oid: str, prefix="", seen=None) -> dict[str, str]:
        seen = set() if seen is None else seen
        audit._require(oid not in seen, "cyclic retained Git tree")
        seen.add(oid)
        raw = self.object(oid, "tree")
        result = {}
        if raw is None:
            return result
        position, digest_width = 0, len(oid) // 2
        while position < len(raw):
            end = raw.find(b"\0", position)
            audit._require(end >= 0 and end + 1 + digest_width <= len(raw), "malformed Git tree object")
            header = raw[position:end]
            audit._require(b" " in header, "malformed Git tree entry")
            mode, name = header.split(b" ", 1)
            path = prefix + name.decode("utf-8")
            audit._relative_path(path, "Git tree source path")
            child = raw[end + 1:end + 1 + digest_width].hex()
            position = end + 1 + digest_width
            if mode in {b"40000", b"040000"}:
                result.update(self.tree(child, path + "/", seen.copy()))
            elif mode in {b"100644", b"100755"}:
                audit._require(path not in result, "duplicate Git tree source path")
                result[path] = child
            else:
                self.frontiers.append({"code": "git_entry_outside_regular_source_profile", "path": path,
                                       "mode": mode.decode("ascii", errors="replace")})
            audit._require(len(result) <= self.limits.max_manifest_entries, "Git tree inventory budget exceeded")
        return result


def _check_manifest(manifest: dict, head: dict, limits: RecoveryLimits) -> dict:
    audit._closed(manifest, MANIFEST_FIELDS, "embedded owner manifest")
    audit._require(manifest["schema"] == "codebase-ir-structural-manifest@1"
                   and manifest["authority"] == "structural_only"
                   and structured_cid(manifest) == head["manifest_cid"], "embedded owner manifest/head CID mismatch")
    snapshot = manifest["snapshot"]
    audit._require(type(snapshot) is dict and snapshot.get("repository_id") == head["repository_id"],
                   "owner snapshot repository binding mismatch")
    audit._require(snapshot.get("snapshot_cid") == head["snapshot_cid"]
                   and structured_cid({key: value for key, value in snapshot.items() if key != "snapshot_cid"})
                   == head["snapshot_cid"], "owner snapshot/head CID mismatch")
    entries, units = snapshot.get("entries"), manifest["units"]
    audit._require(type(entries) is list and len(entries) <= limits.max_manifest_entries,
                   "owner manifest entry budget exceeded")
    audit._require(type(units) is list and len(units) == len(entries) and all(type(unit) is dict for unit in units),
                   "owner manifest unit inventory mismatch")
    audit._require(type(manifest["semantic_state"]) is dict
                   and type(manifest["semantic_state"].get("edges")) is list,
                   "owner semantic edge inventory required")
    keys = set()
    for entry in entries:
        audit._require(type(entry) is dict, "owner source entry required")
        path = audit._relative_path(entry.get("path"), "owner source path")
        audit._require(path not in keys, "duplicate owner source path")
        keys.add(path)
        audit._require(entry.get("raw_path_hex") == path.encode().hex(), "owner raw path binding mismatch")
        audit._require(structured_cid({key: value for key, value in entry.items() if key != "entry_cid"})
                       == entry.get("entry_cid"), "owner source entry CID mismatch")
        matches = [unit for unit in units if unit.get("source_key") == "raw:" + entry["raw_path_hex"]]
        audit._require(len(matches) == 1 and matches[0].get("entry_cid") == entry["entry_cid"],
                       "owner source/structural unit binding mismatch")
    audit._require(manifest["ast_revision_id"] == head["ast_revision_id"], "owner AST revision mismatch")
    return snapshot


def create_closure_requests(manifest_path: str | Path, output: str | Path, *, source_cas: Path | None = None,
                            git_repository: Path | None = None, qualification_report: Path | None = None,
                            limits: RecoveryLimits = DEFAULT_RECOVERY_LIMITS,
                            audit_limits: audit.Limits = audit.DEFAULT_LIMITS) -> dict:
    captured = metadata._Captured(Path(manifest_path), audit_limits)
    output = Path(output)
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as exc:
        raise audit.AuditInputError("fresh private output directory with existing parent required") from exc
    baseline = captured.audit_report
    audit.write_private_report(output / "baseline_audit_report.json", baseline)
    # Comparison reads only this first captured scope, including manual file sources.
    pinned = copy.deepcopy(captured.manifest)
    for row in pinned["units"]:
        unit = captured.loader.units[row["id"]]
        row["source"] = {"bytes_hex": captured.loader.sources[unit.identity()].hex()}
    if pinned["native_records"]:
        (output / "native_exports").mkdir(mode=0o700)
    for row in pinned["native_records"]:
        relative = f"native_exports/{row['sha256']}.json"
        destination = output / relative
        raw = captured.exports[row["version_id"]]
        if not destination.exists():
            metadata._write_bytes(destination, raw)
        else:
            audit._require(audit._read_bounded(destination, audit_limits.max_json_bytes) == raw,
                           "conflicting pinned export file identity")
        row["file"] = relative
    audit.write_private_report(output / "pinned_input.json", pinned)
    cas = _CAS(source_cas, output, limits, audit_limits)
    git = _Git(git_repository, output, limits)
    manifests, heads, receipts, targets, unit_heads = {}, {}, {}, [], {}
    for version, raw in sorted(captured.exports.items()):
        value = audit._load_json(raw, audit_limits)
        provenance = value if value.get("schema") == audit.NATIVE_LINEAGE_SCHEMA else value["report"]["codebase_provenance"]
        for field in ("training_targets", "tuning_targets", "canary_targets", "replay_targets"):
            for index, target in enumerate(provenance[field]):
                unit_id = f"native/{version}/{field}/{index}"
                details = target["validation"][0]["details"]
                binding, manifest, receipt = details["source_binding"], details.get("manifest"), details.get("publication_receipt")
                head = binding["head"]
                _check_manifest(manifest, head, limits)
                audit._require(type(receipt) is dict and structured_cid(receipt) == head["receipt_cid"],
                               "embedded source publication receipt CID mismatch")
                for name in ("repository_id", "generation", "manifest_cid", "snapshot_cid", "ast_revision_id"):
                    audit._require(receipt.get(name) == head[name], "source receipt/head field mismatch")
                previous = receipt.get("previous_head")
                if previous is not None:
                    audit._closed(previous, {"schema", "repository_id", "generation", "manifest_cid",
                                             "snapshot_cid", "ast_revision_id", "receipt_cid"}, "source previous head")
                audit._require((previous is None and head["generation"] == 1)
                               or (type(previous) is dict and previous.get("repository_id") == head["repository_id"]
                                   and type(previous.get("generation")) is int
                                   and previous["generation"] + 1 == head["generation"]),
                               "source receipt predecessor generation mismatch")
                ast_record = details.get("captured_ast")
                audit._require(type(ast_record) is dict and structured_cid(ast_record) == binding["ast_cid"],
                               "embedded captured AST CID mismatch")
                source_provenance = ast_record.get("provenance")
                audit._require(type(source_provenance) is dict
                               and source_provenance.get("repository_id") == head["repository_id"]
                               and source_provenance.get("repository_tree_cid") == head["snapshot_cid"]
                               and source_provenance.get("revision") == binding["source_revision"]
                               and source_provenance.get("path") == binding["path"]
                               and source_provenance.get("source_cid") == binding["source_cid"],
                               "captured AST source provenance mismatch")
                manifests[head["manifest_cid"]] = manifest
                heads[head["manifest_cid"]] = head
                receipts[head["receipt_cid"]] = receipt
                unit_heads[unit_id] = head
                targets.append({"unit_id": unit_id, "version_id": version, "batch_field": field, "index": index,
                                "target_source_digest": target["source_digest"], "head": head,
                                "head_sha256": audit._sha(audit._canonical(head)),
                                "source_binding": binding, "source_binding_sha256": audit._sha(audit._canonical(binding)),
                                "export_sha256": audit._sha(raw)})
    owner_facts, source_links, git_rows = [], [], []
    for cid, manifest in sorted(manifests.items()):
        head, snapshot = heads[cid], manifest["snapshot"]
        manifest_raw = cas.get(cid, expected=audit._canonical(manifest))
        units_by_key = {unit["source_key"]: unit for unit in manifest["units"]}
        git_inventory = {}
        commit_oid, tree_oid = snapshot.get("git_commit"), snapshot.get("git_tree")
        if commit_oid is not None and tree_oid is not None:
            commit = git.object(commit_oid, "commit")
            if commit is not None:
                lines = commit.decode("utf-8", errors="strict").split("\n\n", 1)[0].splitlines()
                audit._require(lines and lines[0] == "tree " + tree_oid, "Git commit/snapshot tree binding mismatch")
                parents = [line[7:] for line in lines if line.startswith("parent ")]
                git_inventory = git.tree(tree_oid)
                git_rows.append({"head_sha256": audit._sha(audit._canonical(head)), "git_commit": commit_oid,
                                 "git_tree": tree_oid, "commit_parent_oids": parents,
                                 "commit_is_root": not parents, "tracked_regular_path_count": len(git_inventory),
                                 "snapshot_mode": snapshot.get("mode"), "whole_revision_family_verified": False})
        for entry in snapshot["entries"]:
            source_cid, unit = entry.get("source_cid"), units_by_key["raw:" + entry["raw_path_hex"]]
            if source_cid is None or unit.get("ast_cid") is None:
                cas.frontiers.append({"code": "opaque_or_unindexed_owner_source", "path": entry["path"],
                                      "snapshot_cid": head["snapshot_cid"]})
                continue
            raw = cas.get(source_cid, source=True)
            ast_raw = cas.get(unit["ast_cid"])
            ast_record = None if ast_raw is None else audit._load_json(ast_raw, audit_limits)
            inventories = {}
            if ast_record is not None:
                provenance = ast_record.get("provenance")
                audit._require(ast_record.get("schema") == AST_SCHEMA and type(provenance) is dict
                               and provenance.get("repository_id") == head["repository_id"]
                               and provenance.get("path") == entry["path"]
                               and provenance.get("source_cid") == source_cid
                               and provenance.get("repository_tree_cid") == head["snapshot_cid"]
                               and provenance.get("revision") == "snapshot:" + head["snapshot_cid"],
                               "retained owner AST provenance mismatch")
                for name in ("imports", "calls", "effects", "unsupported", "diagnostics"):
                    audit._require(type(ast_record.get(name)) is list, "explicit owner AST inventory required")
                    inventories[name] = {"count": len(ast_record[name]), "sha256": audit._sha(audit._canonical(ast_record[name]))}
            if raw is not None:
                audit._require(type(entry.get("size_bytes")) is int and len(raw) == entry["size_bytes"],
                               "owner source size binding mismatch")
            git_blob = None
            if entry["path"] in git_inventory:
                git_blob = git.object(git_inventory[entry["path"]], "blob")
            overlay = raw is not None and git_blob is not None and raw != git_blob
            if snapshot.get("mode") == "git-clean" and raw is not None and git_blob is not None:
                audit._require(not overlay, "clean source snapshot differs from retained Git blob")
            owner_facts.append({"repository_id": head["repository_id"], "path": entry["path"], "head": head,
                                "head_sha256": audit._sha(audit._canonical(head)), "source_cid": source_cid,
                                "content_sha256": None if raw is None else audit._sha(raw),
                                "ast_cid": unit["ast_cid"], "entry_cid": entry["entry_cid"],
                                "manifest_cas_corroborated": manifest_raw is not None,
                                "source_cas_corroborated": raw is not None, "ast_cas_corroborated": ast_raw is not None,
                                "structural_inventories": inventories,
                                "semantic_edge_count": len(manifest["semantic_state"].get("edges", [])),
                                "authority": "structural_only", "native_closure_certified": False,
                                "git_blob_oid": git_inventory.get(entry["path"]),
                                "git_blob_content_sha256": None if git_blob is None else audit._sha(git_blob),
                                "source_matches_git_blob": None if raw is None or git_blob is None else not overlay,
                                "working_overlay_from_shared_git_commit": overlay})
    for cid, receipt in sorted(receipts.items()):
        previous = receipt.get("previous_head")
        if previous is not None:
            known = heads.get(previous["manifest_cid"])
            source_links.append({"receipt_cid": cid, "from_manifest_cid": receipt["manifest_cid"],
                                 "to_manifest_cid": previous["manifest_cid"],
                                 "previous_head_sha256": audit._sha(audit._canonical(previous)),
                                 "previous_head_available_and_equal": known == previous,
                                 "basis": "content_bound_source_publication_receipt; no execution attestation"})
    qualification = None
    if qualification_report is not None:
        raw = audit._read_bounded(qualification_report, audit_limits.max_json_bytes)
        value = audit._load_json(raw, audit_limits)
        source_heads = value.get("source_heads", {})
        audit._require(type(source_heads) is dict, "qualification source head inventory required")
        comparisons = []
        for label, head in sorted(source_heads.items()):
            audit._require(type(head) is dict, "qualification source head object required")
            comparisons.append({"label": label, "head_sha256": audit._sha(audit._canonical(head)),
                                "matches_captured_native_head": heads.get(head.get("manifest_cid")) == head})
        metadata._write_bytes(output / "retained_qualification_report.json", raw)
        qualification = {"origin": qualification_report.as_posix(), "sha256": audit._sha(raw),
                         "schema": value.get("schema"), "source_head_comparisons": comparisons,
                         "independent_execution_attestation_verified": False}
    grouped = {}
    units = captured.loader.units
    by_identity = {}
    for target in targets:
        unit = units[target["unit_id"]]
        by_identity.setdefault(unit.identity(), []).append(target)
    for issue in baseline["issues"]:
        if issue["code"] not in {"dependencies_not_declared_complete", "revision_relations_not_declared_complete"}:
            continue
        unit = units[issue["unit_id"]]
        key = unit.identity()
        row = grouped.setdefault(key, {"source_identity": {"repository_id": key[0], "path": key[1],
                                                            "content_sha256": key[2]},
                                       "affected_unit_ids": set(), "missing_claims": set(),
                                       "native_target_bindings": by_identity.get(key, [])})
        row["affected_unit_ids"].add(unit.id)
        row["missing_claims"].add(issue["code"])
    requests = []
    for _key, row in sorted(grouped.items()):
        row["affected_unit_ids"] = sorted(row["affected_unit_ids"])
        row["missing_claims"] = sorted(row["missing_claims"])
        row["request_id"] = "closure-request:" + audit._sha(audit._canonical(row["source_identity"]))
        row["proposed_owner_inputs"] = [
            {"kind": "source_owner_dependency_group_certificate", "required_bindings": [
                "exact source head/manifest/snapshot/source/AST identities", "declared extraction and dependency policy",
                "complete dependency group source membership", "resolved imports/calls/effects and retained frontiers",
                "owner evidence identity and checker/producer scope"]},
            {"kind": "source_owner_revision_family_certificate", "required_bindings": [
                "exact source/model ancestry and captured working overlays", "related revisions/renames and clone policy",
                "search universe and exclusions", "missing ancestors and dynamic frontiers", "owner evidence identity"]},
        ]
        row["locally_recovered_facts_are_closure_certificate"] = False
        requests.append(row)
    facts = {"schema": FACTS_SCHEMA, "native_targets": targets, "owner_facts": owner_facts,
             "retained_cas_artifacts": cas.rows, "retained_git_objects": git.rows,
             "git_snapshot_bindings": git_rows, "source_receipt_predecessors": source_links,
             "qualification_report": qualification,
             "recovery_frontiers": cas.frontiers + git.frontiers,
             "native_closure_certification_verified": False, "proof_authority": False}
    audit.write_private_report(output / "owner_facts.json", facts)
    # No reconstructed/static facts become closure flags. Preserve default exporter behavior.
    comparison = metadata.export_metadata(output / "pinned_input.json", output / "comparison", accept_supplied_scope=False,
                                          limits=audit_limits)
    report = {"schema": REPORT_SCHEMA, "status": "leaks_found" if baseline["leaks"] else "incomplete",
              "input_manifest_sha256": audit._sha(captured.raw), "baseline_audit_status": baseline["status"],
              "pinned_input_sha256": audit._sha((output / "pinned_input.json").read_bytes()),
              "baseline_closure_issue_count": len(baseline["issues"]), "closure_request_count": len(requests),
              "recovered_manifest_count": sum(1 for cid in manifests if cas.cache.get((cid, False)) is not None),
              "owner_fact_count": len(owner_facts), "native_closure_certification_verified": False,
              "closure_claims_applied": 0, "comparison_audit_status": comparison["candidate_audit_status"],
              "comparison_closure_issue_count": len(comparison["candidate_issues"]),
              "whole_repository_coverage": False, "unseen_rename_ancestry_verified": False,
              "native_registry_receipts_verified": False, "training_executed": False,
              "promotion_decisions_made": False, "proof_authority": False,
              "limits": asdict(limits), "closure_requests": requests,
              "other_missing_evidence": [row for row in baseline["issues"] if row["code"] not in {
                  "dependencies_not_declared_complete", "revision_relations_not_declared_complete"}],
              "recovery_frontier_count": len(facts["recovery_frontiers"]),
              "owner_facts_sha256": audit._sha((output / "owner_facts.json").read_bytes()),
              "scope": "read-only retained content/Git corroboration and owner handoff; closure remains unreviewed"}
    audit.write_private_report(output / "closure_requests.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-cas", type=Path)
    parser.add_argument("--git-repository", type=Path)
    parser.add_argument("--qualification-report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = create_closure_requests(args.manifest, args.output, source_cas=args.source_cas,
                                         git_repository=args.git_repository, qualification_report=args.qualification_report)
    except (audit.AuditInputError, OSError, UnicodeError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 3
    print(f"closure handoff created: {report['closure_request_count']} requests; "
          f"{report['recovered_manifest_count']} owner manifests; "
          f"{report['comparison_closure_issue_count']} unresolved issues; native closure certified: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
