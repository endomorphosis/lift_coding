#!/usr/bin/env python3
"""Capture the selected source-cohort subset of a retained reviewed native join."""
from __future__ import annotations

import argparse
import copy
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import codebase_ir_closure_requests as closure
import codebase_ir_closure_response as response
import codebase_ir_cohort_inventory as cohort
import codebase_ir_corpus_audit as audit
import codebase_ir_source_metadata as metadata

INPUT_SCHEMA = "codebase-ir-retained-join-capture-input@1"
REPORT_SCHEMA = "codebase-ir-retained-join-corpus@1"
CONTEXT_PATHS = ["root-training-context", "root-frozen-context", "child-training-context", "child-frozen-context"]
FINAL_MANIFEST = Path(__file__).parent / "examples" / "untouched_final_input.json"


@dataclass(frozen=True)
class CaptureLimits:
    max_primary_pins: int = 2048
    max_selected_files: int = 32
    max_selected_bytes: int = 32 * 1024 * 1024
    max_lineage_rows: int = 16

    def __post_init__(self):
        audit._require(all(type(value) is int and value > 0 for value in asdict(self).values()),
                       "positive exact retained join budgets required")


DEFAULT_LIMITS = CaptureLimits()


def _array_json(raw, limits):
    # Reuse strict duplicate-key, finite-value, depth/node checks for array exports.
    audit._require(len(raw) + 10 <= limits.max_json_bytes, "lineage JSON byte budget exceeded")
    value = audit._load_json(b'{"rows":' + raw + b'}', limits)["rows"]
    audit._require(type(value) is list, "lineage array required")
    return value


class _Capture:
    def __init__(self, spec_path, limits, audit_limits):
        self.limits, self.audit_limits = limits, audit_limits
        self.spec_raw = audit._read_bounded(spec_path, min(audit_limits.max_json_bytes, limits.max_selected_bytes))
        self.spec = audit._closed(audit._load_json(self.spec_raw, audit_limits),
                                  {"schema", "path_mapping", "result_sha256", "independent_audit_sha256",
                                   "artifact_pins_sha256", "context_paths"}, "retained join capture spec")
        audit._require(self.spec["schema"] == INPUT_SCHEMA and self.spec["context_paths"] == CONTEXT_PATHS,
                       "versioned complete four-context join profile required")
        mapping = audit._closed(self.spec["path_mapping"], {"declared_root", "retained_root"}, "explicit relocation mapping")
        for field in ("declared_root", "retained_root"):
            value = audit._text(mapping[field], "capture " + field, 2048)
            path = Path(value)
            audit._require(path.is_absolute() and path.as_posix() == value and ".." not in path.parts,
                           "canonical absolute relocation root required")
        self.root = Path(mapping["retained_root"])
        audit._require(self.root.is_dir() and self.root.resolve() == self.root
                       and not any(part.is_symlink() for part in (self.root, *self.root.parents)), "exact retained join root required")
        self.raws, self.pins, self.total = {}, {}, len(self.spec_raw)
        for field in ("result_sha256", "independent_audit_sha256", "artifact_pins_sha256"):
            audit._digest(self.spec[field], field)
        pins = self.document("artifact-pins.json", self.spec["artifact_pins_sha256"])
        audit._closed(pins, {"schema", "pins"}, "original primary artifact inventory")
        audit._require(pins["schema"] == "finite-reviewed-candidate-retained-artifact-pins@1", "versioned primary pins required")
        self.primary = {}
        for row in response._list(pins["pins"], limits.max_primary_pins, "primary artifact pin"):
            audit._closed(row, {"path", "bytes", "sha256"}, "primary artifact pin")
            path = audit._relative_path(row["path"], "primary artifact path")
            audit._require(path not in self.primary and type(row["bytes"]) is int and row["bytes"] >= 0,
                           "duplicate or malformed primary pin")
            audit._digest(row["sha256"], "primary artifact hash")
            self.primary[path] = row
        self.result = self.document("result.json", self.spec["result_sha256"])
        self.review = self.document("independent-audit.json", self.spec["independent_audit_sha256"])
        audit._require(self.result.get("schema") == "finite-repository-reviewed-candidate-qualification@1"
                       and self.result.get("status") == "completed" and self.result.get("output") == mapping["declared_root"],
                       "result declaration does not match explicit relocation origin")
        audit._require(self.review.get("schema") == "finite-reviewed-candidate-independent-retained-audit@1"
                       and self.review.get("status") == "qualified_snapshot_pass"
                       and self.review.get("output") == mapping["declared_root"]
                       and self.review.get("result_sha256") == self.spec["result_sha256"]
                       and self.review.get("artifact_manifest_sha256") == self.spec["artifact_pins_sha256"]
                       and type(self.review.get("artifact_pin_count")) is int
                       and self.review["artifact_pin_count"] == len(self.primary), "detached independent result/pin inventory binding")
        self._primary("result.json")
        self.contexts, self.versions = [], {}
        for path in CONTEXT_PATHS:
            self.context(path)
        expected_versions = {self.result["root_measurement"]["version_id"], self.result["child_measurement"]["version_id"]}
        audit._require(set(self.versions) == expected_versions and len(expected_versions) == 2,
                       "root/child measurement version population differs")
        root_version, child_version = self.result["root_measurement"]["version_id"], self.result["child_measurement"]["version_id"]
        parent, child = self.versions[root_version], self.versions[child_version]
        audit._require(parent["parent"] is None and child["parent"] == root_version
                       and parent["provenance"]["head"] == self.result["original_head"]
                       and child["provenance"]["head"] == self.result["successor_head"], "native parent/source head join drift")
        continuation = self.result["continuation"]
        audit._require(continuation.get("parent_version_id") == root_version
                       and continuation.get("child_version_id") == child_version, "recorded continuation join drift")
        audit._require(parent["checkpoint"]["contract"] == child["checkpoint"]["contract"]
                       and parent["checkpoint"]["feature_space"] == child["checkpoint"]["feature_space"],
                       "recorded frozen source feature basis changed")
        for _version, row in self.versions.items():
            audit._require(row["parent"] is None or row["parent"] in self.versions, "missing native model ancestor export")
            audit._require(all(x in self.versions for x in row["lineage_versions"]), "lineage contains uncaptured ancestor")
        final_capture = metadata._Captured(FINAL_MANIFEST, audit_limits)
        audit._require(not final_capture.manifest["native_records"] and not final_capture.manifest["ancestral_training"]
                       and all(unit.role == "final" for unit in final_capture.loader.units.values()),
                       "only independently authored existing final fixtures permitted")
        self.final_raw, self.final = final_capture.raw, final_capture.manifest
        audit._require(self.total + len(self.final_raw) <= limits.max_selected_bytes, "selected/final input byte budget exceeded")

    def read(self, relative, expected_sha=None, expected_size=None):
        primary = getattr(self, "primary", {}).get(relative)
        if primary is not None:
            audit._require(expected_size is None or expected_size == primary["bytes"], "context/primary artifact size disagreement")
            audit._require(expected_sha is None or expected_sha == primary["sha256"], "context/primary artifact digest disagreement")
            expected_size = primary["bytes"]
        elif hasattr(self, "primary") and relative not in {"artifact-pins.json", "independent-audit.json"}:
            raise audit.AuditInputError("selected source artifact missing original primary pin")
        if expected_size is not None:
            audit._require(type(expected_size) is int and 0 <= expected_size <= self.audit_limits.max_json_bytes,
                           "exact bounded selected artifact size required")
        if relative in self.raws:
            raw = self.raws[relative]
            audit._require(expected_sha is None or audit._sha(raw) == expected_sha, "conflicting selected artifact pin")
            audit._require(expected_size is None or len(raw) == expected_size, "conflicting selected artifact size")
            return raw
        audit._require(len(self.raws) < self.limits.max_selected_files, "selected artifact file budget exceeded")
        remaining = self.limits.max_selected_bytes - self.total
        audit._require(remaining > 0, "selected artifact byte budget exhausted")
        audit._require(expected_size is None or expected_size <= remaining, "selected artifact byte budget exceeded")
        cap = min(self.audit_limits.max_json_bytes, remaining, expected_size if expected_size is not None else remaining)
        raw = audit._read_bounded(audit._input_file(self.root, relative), cap)
        audit._require(expected_sha is None or audit._sha(raw) == expected_sha, "selected artifact byte binding drift")
        audit._require(expected_size is None or len(raw) == expected_size, "selected artifact size binding drift")
        self.total += len(raw)
        self.raws[relative] = raw
        self.pins[relative] = {"sha256": audit._sha(raw), "size_bytes": len(raw)}
        if primary is not None:
            self._primary(relative)
        return raw

    def _primary(self, path):
        audit._require(path in self.primary and path in self.raws, "selected source artifact missing original primary pin")
        row, raw = self.primary[path], self.raws[path]
        audit._require(row["sha256"] == audit._sha(raw) and row["bytes"] == len(raw), "original selected primary pin drift")

    def document(self, relative, sha=None):
        return audit._load_json(self.read(relative, sha), self.audit_limits)

    def context(self, path):
        value = self.document(path + "/context.json")
        audit._require(value.get("schema") == "supervisor-codebase-feature-context@1"
                       and value.get("profile") == "codebase_ir/source_bound_feature_v1"
                       and value.get("mode") == ("frozen" if "frozen" in path else "train"), "native context profile/mode drift")
        authority = value.get("authority")
        audit._require(type(authority) is dict and authority and all(flag is False for flag in authority.values()),
                       "native advisory context acquired authority")
        for field in ("state_sha256", "contract_sha256", "feature_space_sha256"):
            audit._digest(value.get(field), "recorded context " + field)
        checkpoint_raw = lineage_raw = record_raw = None
        for name in ("checkpoint", "lineage", "record"):
            descriptor = value["artifacts"][name]
            audit._closed(descriptor, {"schema", "role", "relative_path", "sha256", "size_bytes", "blob_cid"}, "native context artifact")
            audit._require(descriptor["schema"] == "supervisor-codebase-feature-blob@1" and descriptor["role"] == name
                           and descriptor["relative_path"] == name + ".json" and type(descriptor["size_bytes"]) is int
                           and 0 < descriptor["size_bytes"] <= self.audit_limits.max_json_bytes, "native artifact descriptor drift")
            raw = self.read(path + "/" + descriptor["relative_path"], audit._digest(descriptor["sha256"], "context artifact"),
                            descriptor["size_bytes"])
            audit._require(len(raw) == descriptor["size_bytes"], "native artifact size binding drift")
            if name == "checkpoint":
                checkpoint_raw = raw
            elif name == "lineage":
                lineage_raw = raw
            else:
                record_raw = raw
        checkpoint = audit._load_json(checkpoint_raw, self.audit_limits)
        provenance = checkpoint["report"]["codebase_provenance"]
        version = audit._text(value["version_id"], "native version", 128)
        audit._require(value["parent_version_id"] == provenance["parent_version_id"] and value["head"] == provenance["head"]
                       and value["candidate_checkpoint_raw_cid"] == audit._raw_source_cid(checkpoint_raw), "native context/checkpoint source binding drift")
        for field in ("contract_sha256", "feature_space_sha256"):
            audit._digest(value[field], field)
            audit._require(value[field] == provenance[field] == checkpoint["report"][field], "native context basis identity drift")
        audit._require(audit._sha(audit._canonical(checkpoint["feature_space"])) == value["feature_space_sha256"],
                       "native feature-space bytes drift")
        record = audit._load_json(record_raw, self.audit_limits)
        audit._require(record.get("schema") == "codebase-source-feature-training@1" and record.get("version_id") == version
                       and record.get("parent_version_id") == value["parent_version_id"] and record.get("head") == value["head"]
                       and record.get("registry_artifact") == {"sha256": audit._sha(checkpoint_raw), "bytes": len(checkpoint_raw)}
                       and record.get("checkpoint_raw_cid") == value["candidate_checkpoint_raw_cid"]
                       and record.get("training_performed_during_load") is False
                       and record.get("model_head_selected") is False, "retained model record/checkpoint drift")
        record_authority = record.get("authority")
        audit._require(type(record_authority) is dict and record_authority
                       and all(flag is False for flag in record_authority.values()), "native model record acquired authority")
        audit._require(type(record.get("report_json")) is str
                       and audit._load_json(record["report_json"].encode(), self.audit_limits) == checkpoint["report"],
                       "retained model report detached from checkpoint")
        lineage = response._list(_array_json(lineage_raw, self.audit_limits), self.limits.max_lineage_rows, "lineage")
        audit._require(bool(lineage), "complete lineage cannot be empty")
        seen, previous, line_versions = set(), version, []
        for row in lineage:
            audit._closed(row, {"checkpoint", "version"}, "native lineage row")
            identity = row["version"]
            audit._closed(identity, {"version_id", "parent_version_id", "artifact", "metadata", "variant_id"}, "native lineage version")
            audit._require(identity["version_id"] == previous and previous not in seen, "missing, reordered or cyclic native lineage")
            cp_raw = audit._canonical(row["checkpoint"])
            audit._require(identity["artifact"] == {"sha256": audit._sha(cp_raw), "bytes": len(cp_raw)}, "lineage checkpoint raw identity drift")
            prov = row["checkpoint"]["report"]["codebase_provenance"]
            audit._require(prov["parent_version_id"] == identity["parent_version_id"], "lineage model parent disagreement")
            if not seen:
                audit._require(cp_raw == checkpoint_raw, "lineage selected checkpoint drift")
            known = self.versions.get(previous)
            if known is not None:
                audit._require(cp_raw == known["raw"], "lineage ancestor checkpoint drift")
            seen.add(previous)
            line_versions.append(previous)
            previous = identity["parent_version_id"]
        audit._require(previous is None, "lineage missing terminal ancestor")
        row = {"raw": checkpoint_raw, "checkpoint": checkpoint, "provenance": provenance,
               "parent": value["parent_version_id"], "lineage_versions": line_versions}
        if version in self.versions:
            audit._require(self.versions[version]["raw"] == checkpoint_raw
                           and self.versions[version]["lineage_versions"] == line_versions, "frozen/train version identity drift")
        else:
            self.versions[version] = row
        self.contexts.append({"path": path, "version_id": version, "parent_version_id": value["parent_version_id"],
                              "mode": value["mode"], "head": value["head"], "context_cid_claim": value["context_cid"],
                              "context_sha256": self.pins[path + "/context.json"]["sha256"],
                              "checkpoint_sha256": audit._sha(checkpoint_raw), "lineage_version_ids": line_versions,
                              "continuation_claim": provenance["continuation"], "fork_status": "not_declared_by_captured_profile",
                              "contract_sha256_claim": value["contract_sha256"], "feature_space_sha256": value["feature_space_sha256"],
                              "state_sha256_claim": value["state_sha256"], "numerical_state_replayed": False})


def capture_join(spec_path, output, *, limits=DEFAULT_LIMITS, audit_limits=audit.DEFAULT_LIMITS):
    captured = _Capture(Path(spec_path), limits, audit_limits)
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    metadata._write_bytes(output / "capture_spec.json", captured.spec_raw)
    for name, raw in sorted(captured.raws.items()):
        path = output / "retained" / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        metadata._write_bytes(path, raw)
    manifest = copy.deepcopy(captured.final)
    manifest["native_records"] = []
    (output / "native_exports").mkdir(mode=0o700)
    for version, row in sorted(captured.versions.items()):
        digest = audit._sha(row["raw"])
        name = "native_exports/" + digest + ".json"
        metadata._write_bytes(output / name, row["raw"])
        manifest["native_records"].append({"version_id": version, "file": name, "sha256": digest, "unit_metadata": {}})
    audit.write_private_report(output / "audit_input.json", manifest)
    baseline = audit.audit_manifest(output / "audit_input.json", audit_limits)
    audit.write_private_report(output / "baseline_audit_report.json", baseline)
    reconstructed = metadata.export_metadata(output / "audit_input.json", output / "source-metadata", accept_supplied_scope=False, limits=audit_limits)
    requests = closure.create_closure_requests(output / "source-metadata/candidate_manifest.json", output / "closure-requests", audit_limits=audit_limits)
    review = response.review_response(output / "closure-requests/closure_requests.json", output / "response-template", audit_limits=audit_limits)
    groups = cohort.create_inventory(output / "response-template/response_review_report.json", output / "cohort-inventory", audit_limits=audit_limits)
    selected_paths = sorted({unit["path"] for unit in baseline["units"] if unit["id"].startswith("native/")})
    inventory = response._ids(captured.result["inventory_paths"], 256, "recorded source inventory")
    report = {"schema": REPORT_SCHEMA, "disposition": "captured_subset_produced", "capture_spec_sha256": audit._sha(captured.spec_raw),
              "result_sha256": captured.spec["result_sha256"], "independent_audit_sha256": captured.spec["independent_audit_sha256"],
              "artifact_pins_sha256": captured.spec["artifact_pins_sha256"], "path_mapping": captured.spec["path_mapping"],
              "primary_pin_inventory_count": len(captured.primary), "selected_artifact_count": len(captured.raws),
              "selected_artifact_bytes": sum(len(raw) for raw in captured.raws.values()), "selected_artifact_pins": captured.pins,
              "all_primary_artifacts_reverified": False, "independent_audit_executed": False,
              "contexts": captured.contexts, "native_version_count": len(captured.versions), "native_target_membership_count": groups["native_target_membership_count"],
              "ancestral_training_exposure_count": groups["ancestral_training_exposure_count"], "selected_native_paths": selected_paths,
              "recorded_metadata_only_paths": sorted(set(inventory) - set(selected_paths)),
              "final_fixture_manifest_sha256": audit._sha(captured.final_raw), "final_unit_ids": sorted(unit["id"] for unit in manifest["units"]),
              "baseline_audit_status": baseline["status"], "baseline_issue_count": len(baseline["issues"]), "baseline_leakage_count": len(baseline["leaks"]),
              "reconstructed_audit_status": reconstructed["candidate_audit_status"], "reconstructed_issue_count": len(reconstructed["candidate_issues"]),
              "closure_request_count": requests["closure_request_count"], "group_count": groups["group_count"],
              "cross_role_group_count": groups["cross_role_group_count"], "final_connected_group_count": groups["final_connected_group_count"],
              "template_disposition": review["disposition"], "limits": asdict(limits),
              "numerical_state_replayed": False, "registry_opened": False, "training_executed": False,
              "producer_authentication_verified": False, "native_closure_certification_verified": False, "independence_verified": False,
              "whole_repository_coverage": False, "closure_claims_applied": 0, "proof_authority": False, "promotion_decisions_made": False,
              "scope": "byte-bound selected native cohort/context/lineage subset; recorded resume/basis claims retained without numerical or producer verification"}
    audit.write_private_report(output / "retained_join_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = capture_join(args.manifest, args.output)
    except (audit.AuditInputError, OSError, UnicodeError, KeyError, TypeError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 3
    print(f"retained join subset: {report['reconstructed_audit_status']}; {report['group_count']} groups; "
          f"{report['cross_role_group_count']} cross-role; {report['reconstructed_issue_count']} unresolved issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
