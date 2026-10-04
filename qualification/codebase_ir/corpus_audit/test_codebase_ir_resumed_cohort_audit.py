"""Independent synthetic source/scan/exposure controls; no owner fixtures."""

from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest import mock

import codebase_ir_corpus_audit as audit
import codebase_ir_resumed_cohort_audit as cohort


def _span(node, raw):
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return {
        "start_byte": offsets[node.lineno - 1] + node.col_offset,
        "end_byte": offsets[node.end_lineno - 1] + node.end_col_offset,
        "start_line": node.lineno,
        "end_line": node.end_lineno,
        "start_column": node.col_offset,
        "end_column": node.end_col_offset,
    }


def _captured(path, raw, source, head, failed=False):
    module_span = {
        "start_byte": 0,
        "end_byte": len(raw),
        "start_line": 1,
        "end_line": len(raw.splitlines()) + 1,
        "start_column": 0,
        "end_column": 0,
    }
    value = dict.fromkeys(cohort.AST_FIELDS)
    value.update(
        {
            "schema": "ipfs-datasets.software-contracts.ast-ir@1.0.0",
            "calls": [],
            "diagnostics": [],
            "effects": [],
            "frontend": {},
            "imports": [],
            "references": [],
            "scopes": [],
            "symbols": [],
            "unsupported": [],
            "module": {"module_id": "module:" + source, "span": module_span},
            "provenance": {
                "path": path,
                "source_cid": source,
                "repository_id": head["repository_id"],
                "repository_tree_cid": head["snapshot_cid"],
                "revision": "snapshot:" + head["snapshot_cid"],
            },
        }
    )
    if failed:
        value["diagnostics"] = [{"reason": "authored parse error"}]
        value["unsupported"] = [{"reason": "authored parse error"}]
        return value
    nodes = list(ast.walk(ast.parse(raw)))
    value["references"] = [
        {"name": n.id, "span": _span(n, raw)} for n in nodes if isinstance(n, ast.Name)
    ]
    value["references"] += [
        {"name": n.func.id, "span": _span(n.func, raw)}
        for n in nodes
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    ]
    value["symbols"] = [
        {"kind": "function", "name": n.name, "span": _span(n, raw)}
        for n in nodes
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    value["symbols"] += [
        {"kind": "parameter", "name": n.arg, "span": _span(n, raw)}
        for n in nodes
        if isinstance(n, ast.arg)
    ]
    return value


def packets():
    """Eight authored members, all static dispositions, two explicit lineages."""
    raw_bodies, records = {}, []

    def add(raw, kind, role="captured_source_artifact"):
        cid = cohort._cid(raw, kind)
        if cid not in raw_bodies:
            raw_bodies[cid] = raw
            records.append(
                {
                    "cid": cid,
                    "kind": kind,
                    "sha256": audit._sha(raw),
                    "size_bytes": len(raw),
                    "path": f"private/source-artifacts/{kind}/{cid[:4]}/{cid}",
                    "role": role,
                }
            )
        return cid

    def obj(value, role="captured_source_artifact"):
        return add(audit._canonical(value), "structured", role)

    head = {
        "schema": "codebase-head@1",
        "repository_id": "authored:cohort",
        "snapshot_cid": cohort._cid(b"authored snapshot", "structured"),
        "ast_revision_id": "revision:authored",
        "generation": 1,
    }
    samples = {
        "README.md": b"Authored corpus fixture.\n",
        "calc.py": b"def increment(n: int) -> int:\n    return n + 1\n",
        "canary.py": b"def increment(n: int) -> int:\n    return n + 5\n",
        "check.py": b"from calc import increment\nassert increment(1) == 2\n",
        "copy.py": b"def increment(n: int) -> int:\n    return n + 1\n",
        "malformed.py": b"def malformed(:\n",
        "non_utf8.py": None,
        "oversized.dat": None,
        "tune.py": b"def increment(n: int) -> int:\n    return n + 3\n",
    }
    members, units, entries = [], [], []
    for path, raw in samples.items():
        status = (
            "unindexed"
            if path == "README.md"
            else "failed"
            if path == "malformed.py"
            else "opaque"
            if raw is None
            else "ok"
        )
        source = (
            add(raw, "source")
            if raw is not None
            else None
            if path == "oversized.dat"
            else cohort._cid(b"\xff", "source")
        )
        captured = (
            obj(_captured(path, raw, source, head, status == "failed"))
            if status in {"ok", "failed"}
            else None
        )
        entry_cid = cohort._cid(("entry:" + path).encode(), "structured")
        member = {
            "path": path,
            "raw_path_hex": path.encode().hex(),
            "source_key": "raw:" + path.encode().hex(),
            "source_cid": source,
            "source_size_bytes": len(raw)
            if raw is not None
            else 65537
            if path == "oversized.dat"
            else 1,
            "ast_cid": captured,
            "entry_cid": entry_cid,
            "parse_status": status,
            "opaque_reason": "oversized"
            if path == "oversized.dat"
            else "undecodable"
            if raw is None
            else None,
        }
        members.append(member)
        units.append({k: member[k] for k in ("source_key", "ast_cid", "entry_cid", "parse_status")})
        entries.append(
            {
                **{
                    k: member[k]
                    for k in ("path", "raw_path_hex", "source_cid", "opaque_reason", "entry_cid")
                },
                "size_bytes": member["source_size_bytes"],
            }
        )
    head["manifest_cid"] = obj(
        {
            "schema": "codebase-ir-structural-manifest@1",
            "authority": "structural_only",
            "ast_revision_id": head["ast_revision_id"],
            "snapshot": {"snapshot_cid": head["snapshot_cid"], "entries": entries},
            "units": units,
        }
    )
    version_ids = {role: "sha256:" + audit._sha(role.encode()) for role in ("root", "child")}
    for role in ("root", "child"):
        provenance = dict.fromkeys(audit.NATIVE_PROVENANCE_FIELDS, False)
        selections = [
            {"path": path, "role": r, "contracts": []}
            for path, r in (("calc.py", "train"), ("canary.py", "canary"), ("tune.py", "tune"))
        ]
        provenance.update(
            {
                "head": head,
                "parent_version_id": version_ids["root"] if role == "child" else None,
                "selections": selections,
            }
        )

        def target(path):
            member = next(m for m in members if m["path"] == path)
            return {
                "source_digest": audit._sha(("authored target:" + path).encode()),
                "validation": [
                    {
                        "details": {
                            "source_bytes_hex": samples[path].hex(),
                            "source_binding": {
                                "path": path,
                                "head": head,
                                "content_sha256": audit._sha(samples[path]),
                                **{k: member[k] for k in ("source_cid", "ast_cid", "source_key")},
                            },
                        }
                    }
                ],
            }

        for batch, path in (
            ("training_targets", "calc.py"),
            ("tuning_targets", "tune.py"),
            ("canary_targets", "canary.py"),
        ):
            provenance[batch] = [target(path)]
        provenance["replay_targets"] = [target("calc.py")] if role == "child" else []
        provenance["ancestral_training"] = (
            [
                {
                    "path": "calc.py",
                    "repository_id": head["repository_id"],
                    "source_digest": audit._sha(samples["calc.py"]),
                }
            ]
            if role == "child"
            else []
        )
        obj(
            {
                "schema": "codebase-source-feature-training@1",
                "version_id": version_ids[role],
                "parent_version_id": provenance["parent_version_id"],
                "head": head,
                "state_sha256": audit._sha(b"authored state claim"),
                "training_performed_during_load": False,
                "authority": {"proof_authority": False},
                "report_json": json.dumps({"codebase_provenance": provenance}),
            }
        )
    root = {
        "schema": "codebase-inventory-resume-root@1",
        "authority": {"proof_authority": False},
        "head": head,
        "head_cid": cohort._cid(audit._canonical(head), "structured"),
        "membership_cid": cohort._cid(b"authored members", "structured"),
        "members": members,
        "model": {
            "version_id": version_ids["child"],
            "state_sha256": audit._sha(b"authored state claim"),
            "artifact_cid": cohort._cid(b"unread authored model", "source"),
            "ancestry": [{"version_id": version_ids["child"]}, {"version_id": version_ids["root"]}],
        },
        "limits": {"page_entries": 5},
    }
    root_cid = obj(root, "root")
    obj({"authored": "reference root"}, "optout-root")
    add(audit._canonical({"authored": "reference page"}), "source", "optout-reference-page")
    previous, pages, full_counts, inferred = None, [], Counter(), 0
    for offset in range(0, len(members), 5):
        page_entries, rows, counts = [], [], Counter()
        for index, member in enumerate(members[offset : offset + 5], start=offset):
            disposition = {
                "opaque": "opaque",
                "failed": "parse_failed",
                "unindexed": "unindexed",
            }.get(
                member["parse_status"],
                "unsupported_target"
                if member["path"] == "check.py"
                else "deferred_budget"
                if member["path"] == "copy.py"
                else "inferred",
            )
            counts[disposition] += 1
            digest = (
                audit._sha(("authored target:" + member["path"]).encode())
                if disposition == "inferred"
                else None
            )
            page_entries.append(
                {
                    "member_index": index,
                    "source_key": member["source_key"],
                    "entry_cid": member["entry_cid"],
                    "disposition": disposition,
                    "reason": None,
                    "target_sha256": digest,
                    "source_digest": digest,
                    "inference_index": len(rows) if disposition == "inferred" else None,
                }
            )
            if disposition == "inferred":
                rows.append({"source_digest": digest})
        page = {
            "schema": "codebase-inventory-resume-page@1",
            "authority": {"proof_authority": False},
            "root_cid": root_cid,
            "previous_page_cid": previous,
            "head_cid": root["head_cid"],
            "membership_cid": root["membership_cid"],
            "model_artifact_cid": root["model"]["artifact_cid"],
            "page_membership_cid": cohort._cid(str(offset).encode(), "structured"),
            "start": offset,
            "end": offset + len(page_entries),
            "total_entries": len(members),
            "entries": page_entries,
            "inference": {"rows": rows},
            "coverage": {
                "dispositions": dict(counts),
                "inferred_rows": len(rows),
                "inventory_entries": len(page_entries),
            },
        }
        cid = add(audit._canonical(page), "source", f"page-{len(pages) + 1:02d}")
        pages.append(
            {
                "page_cid": cid,
                "start": offset,
                "end": page["end"],
                "membership_cid": page["page_membership_cid"],
                "dispositions": dict(counts),
                "inferred_rows": len(rows),
            }
        )
        previous = cid
        full_counts.update(counts)
        inferred += len(rows)
    coverage = {
        "inventory_entries": len(members),
        "inferred_rows": inferred,
        "dispositions": dict(full_counts),
        "pages": len(pages),
    }
    completion = obj(
        {
            "schema": "codebase-inventory-resume-completion@1",
            "authority": {"proof_authority": False},
            "root_cid": root_cid,
            "coverage": coverage,
            "pages": pages,
            "head_cid": root["head_cid"],
            "membership_cid": root["membership_cid"],
            "model_artifact_cid": root["model"]["artifact_cid"],
        },
        "completion",
    )
    result = {
        "schema": "codebase-inventory-resume-native-qualification@1",
        "head": head,
        "selected_version_id": version_ids["child"],
        "scan_root_cid": root_cid,
        "completed_scan_cid": completion,
        "scan_coverage": coverage,
        "inherited_actual_setup_epochs": 2,
        "new_scan_pages_created": 0,
        "scan_reuse": {"new_fitting_epochs": 0},
    }
    sync_selection(result, records)
    return result, records, raw_bodies


def sync_selection(result, records):
    result["setup_reuse"] = {
        "copied_members": [
            {"path": r["path"], "sha256": r["sha256"], "bytes": r["size_bytes"], "mode": 384}
            for r in records
            if r["role"] == "captured_source_artifact"
        ]
    }
    result["source_scan_seed"] = {
        "copied_members": [
            {
                "path": r["path"].replace("private/source-artifacts/", "cas/"),
                "sha256": r["sha256"],
                "bytes": r["size_bytes"],
                "mode": 384,
                "kind": "cas",
                "cid": r["cid"],
                "codec": "raw" if r["kind"] == "source" else "dag-json",
                "role": r["role"],
            }
            for r in records
            if r["role"] != "captured_source_artifact"
        ]
    }


def changed(packet, cid, mutate):
    """Repair raw SHA descriptors and outer receipt after changing inert JSON."""
    result, records, bodies = packet
    value = json.loads(bodies[cid])
    mutate(value)
    bodies[cid] = audit._canonical(value)
    row = next(r for r in records if r["cid"] == cid)
    row.update(sha256=audit._sha(bodies[cid]), size_bytes=len(bodies[cid]))
    sync_selection(result, records)


def repair_cas(packet):
    """Repair all raw CIDs, source/scan links, nested and outer declarations."""
    result, records, bodies = packet

    def rebind(value, replacements):
        if type(value) is dict:
            updated = {}
            for key, item in value.items():
                if key == "report_json" and type(item) is str:
                    updated[key] = audit._canonical(rebind(json.loads(item), replacements)).decode()
                else:
                    updated[key] = rebind(item, replacements)
            return updated
        if type(value) is list:
            return [rebind(item, replacements) for item in value]
        if type(value) is str:
            return replacements.get(value, value)
        return value

    for _ in range(32):
        replacements = {
            row["cid"]: cohort._cid(bodies[row["cid"]], row["kind"])
            for row in records
            if cohort._cid(bodies[row["cid"]], row["kind"]) != row["cid"]
        }
        if not replacements:
            sync_selection(result, records)
            return
        rewritten = {}
        for row in records:
            old = row["cid"]
            raw = bodies[old]
            if row["kind"] == "structured" or row["role"] != "captured_source_artifact":
                raw = audit._canonical(rebind(json.loads(raw), replacements))
            row["cid"] = replacements.get(old, old)
            row["path"] = f"private/source-artifacts/{row['kind']}/{row['cid'][:4]}/{row['cid']}"
            row.update(sha256=audit._sha(raw), size_bytes=len(raw))
            rewritten[row["cid"]] = raw
        bodies.clear()
        bodies.update(rewritten)
        rebound = rebind(result, replacements)
        result.clear()
        result.update(rebound)
    raise AssertionError("authored CAS repair graph did not converge")


def write_fixture(directory, packet):
    result, records, bodies = packet
    directory = directory / "inputs"
    directory.mkdir()
    native = directory / "native"
    native.mkdir()
    for row in records:
        p = native / row["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(bodies[row["cid"]])
    result_path = native / "result.json"
    result_path.write_bytes(audit._canonical(result))
    review = directory / "review.json"
    review.write_bytes(
        audit._canonical(
            {
                "native_result": {
                    "path": "native/result.json",
                    "sha256": audit._sha(result_path.read_bytes()),
                    "bytes": result_path.stat().st_size,
                }
            }
        )
    )
    manifest = directory / "input.json"
    spec = {
        "schema": cohort.INPUT_SCHEMA,
        **{
            role: {
                "path": str(path),
                "sha256": audit._sha(path.read_bytes()),
                "size_bytes": path.stat().st_size,
            }
            for role, path in (("native_result", result_path), ("qualification_review", review))
        },
    }
    manifest.write_bytes(audit._canonical(spec))
    pins = {role: (spec[role]["sha256"], spec[role]["size_bytes"]) for role in cohort.INPUT_ROLES}
    return manifest, pins


class CohortControls(unittest.TestCase):
    def setUp(self):
        self.packet = packets()

    def analyse(self, limits=cohort.DEFAULT_LIMITS):
        return cohort._analyse(*self.packet, limits)

    def root(self):
        result, _, bodies = self.packet
        return json.loads(bodies[result["scan_root_cid"]])

    def page_cid(self):
        return next(r["cid"] for r in self.packet[1] if r["role"] == "page-01")

    def lineage_cid(self):
        return next(
            cid
            for cid, raw in self.packet[2].items()
            if b'"report_json"' in raw and json.loads(raw)["parent_version_id"] is not None
        )

    def refusal(self):
        with self.assertRaises((audit.AuditInputError, KeyError, UnicodeError)):
            self.analyse()

    def test_independent_golden_population_exposure_and_clones(self):
        r = self.analyse()
        self.assertEqual(r["inventory_member_count"], 9)
        self.assertEqual(
            r["disposition_counts"],
            {
                "unindexed": 1,
                "inferred": 3,
                "unsupported_target": 1,
                "deferred_budget": 1,
                "parse_failed": 1,
                "opaque": 2,
            },
        )
        self.assertEqual(r["declared_training_paths"], ["calc.py"])
        self.assertEqual(r["declared_tuning_paths"], ["tune.py"])
        self.assertEqual(r["declared_canary_paths"], ["canary.py"])
        self.assertEqual(r["clone_group_count"], 1)
        self.assertEqual(
            r["clone_groups_with_declared_exposure"][0]["paths"], ["calc.py", "copy.py"]
        )
        self.assertEqual(len(r["source_missing_members"]), 2)
        self.assertEqual(
            r["dependency_edges"],
            [{"path": "check.py", "dependency_path": "calc.py", "in_cohort": True}],
        )

    def test_duplicate_member_with_repaired_snapshot(self):
        changed(
            self.packet,
            self.packet[0]["scan_root_cid"],
            lambda x: x["members"].append(copy.deepcopy(x["members"][0])),
        )
        self.refusal()

    def test_page_entry_repaired_source_key(self):
        changed(
            self.packet,
            self.page_cid(),
            lambda x: x["entries"][1].update(source_key=x["entries"][2]["source_key"]),
        )
        self.refusal()

    def test_page_inference_row_digest_repaired(self):
        changed(
            self.packet,
            self.page_cid(),
            lambda x: x["inference"]["rows"][0].update(source_digest="1" * 64),
        )
        self.refusal()

    def test_noninferred_cannot_gain_numerical_row(self):
        changed(self.packet, self.page_cid(), lambda x: x["entries"][0].update(inference_index=0))
        self.refusal()

    def test_wrong_disposition_repaired_counts(self):
        changed(
            self.packet, self.page_cid(), lambda x: x["entries"][0].update(disposition="inferred")
        )
        self.refusal()

    def test_boolean_index_refused(self):
        changed(self.packet, self.page_cid(), lambda x: x["entries"][1].update(member_index=True))
        self.refusal()

    def test_repaired_page_coverage_refused(self):
        changed(self.packet, self.page_cid(), lambda x: x["coverage"].update(inferred_rows=4))
        self.refusal()

    def test_stale_page_cursor(self):
        changed(self.packet, self.page_cid(), lambda x: x.update(previous_page_cid="b" + "x" * 58))
        self.refusal()

    def test_truncated_page_population(self):
        self.packet[1][:] = [r for r in self.packet[1] if r["role"] != "page-02"]
        self.refusal()

    def test_wrong_completion_population(self):
        changed(self.packet, self.packet[0]["completed_scan_cid"], lambda x: x["pages"].pop())
        self.refusal()

    def test_completed_prefix_never_complete_inventory(self):
        changed(
            self.packet,
            self.packet[0]["completed_scan_cid"],
            lambda x: x["coverage"].update(inventory_entries=5),
        )
        self.refusal()

    def test_source_span_rehash_cannot_authenticate_wrong_bytes(self):
        cid = next(m["ast_cid"] for m in self.root()["members"] if m["path"] == "calc.py")
        changed(self.packet, cid, lambda x: x["references"][0]["span"].update(start_byte=0))
        self.refusal()

    def test_coherent_reference_name_forgery(self):
        cid = next(m["ast_cid"] for m in self.root()["members"] if m["path"] == "calc.py")
        changed(self.packet, cid, lambda x: x["references"][0].update(name="bool"))
        self.refusal()

    def test_missing_reference_population(self):
        cid = next(m["ast_cid"] for m in self.root()["members"] if m["path"] == "calc.py")
        changed(self.packet, cid, lambda x: x["references"].pop())
        self.refusal()

    def test_wrong_symbol_population(self):
        cid = next(m["ast_cid"] for m in self.root()["members"] if m["path"] == "calc.py")
        changed(self.packet, cid, lambda x: x["symbols"][0].update(name="different"))
        self.refusal()

    def test_wrong_ast_revision(self):
        cid = next(m["ast_cid"] for m in self.root()["members"] if m["path"] == "calc.py")
        changed(self.packet, cid, lambda x: x["provenance"].update(revision="different"))
        self.refusal()

    def test_wrong_source_binding_after_lineage_rehash(self):
        def change(value):
            report = json.loads(value["report_json"])
            report["codebase_provenance"]["training_targets"][0]["validation"][0]["details"][
                "source_bytes_hex"
            ] = b"different".hex()
            value["report_json"] = json.dumps(report)

        changed(self.packet, self.lineage_cid(), change)
        self.refusal()

    def test_selection_role_swap_preserving_population(self):
        def change(value):
            report = json.loads(value["report_json"])
            selections = report["codebase_provenance"]["selections"]
            selections[0]["role"], selections[1]["role"] = (
                selections[1]["role"],
                selections[0]["role"],
            )
            value["report_json"] = json.dumps(report)

        changed(self.packet, self.lineage_cid(), change)
        self.refusal()

    def test_target_batch_swap_with_repaired_report(self):
        def change(value):
            report = json.loads(value["report_json"])
            p = report["codebase_provenance"]
            p["training_targets"], p["tuning_targets"] = p["tuning_targets"], p["training_targets"]
            value["report_json"] = json.dumps(report)

        changed(self.packet, self.lineage_cid(), change)
        self.refusal()

    def test_missing_lineage_selection_target(self):
        def change(value):
            report = json.loads(value["report_json"])
            report["codebase_provenance"]["training_targets"] = []
            value["report_json"] = json.dumps(report)

        changed(self.packet, self.lineage_cid(), change)
        self.refusal()

    def test_parent_child_identity_confusion(self):
        changed(
            self.packet, self.lineage_cid(), lambda x: x.update(parent_version_id=x["version_id"])
        )
        self.refusal()

    def test_unseen_training_ancestry_never_independent(self):
        def change(value):
            report = json.loads(value["report_json"])
            report["codebase_provenance"]["ancestral_training"][0]["source_digest"] = "2" * 64
            value["report_json"] = json.dumps(report)

        changed(self.packet, self.lineage_cid(), change)
        self.refusal()

    def test_authority_escalation(self):
        changed(
            self.packet,
            self.packet[0]["scan_root_cid"],
            lambda x: x["authority"].update(proof_authority=True),
        )
        self.refusal()

    def test_boolean_effort_accounting_refused(self):
        self.packet[0]["inherited_actual_setup_epochs"] = True
        self.refusal()

    def test_missing_source_stays_explicit(self):
        cid = next(m["source_cid"] for m in self.root()["members"] if m["path"] == "tune.py")
        del self.packet[2][cid]
        self.refusal()

    def test_literal_changes_separate_normalized_groups(self):
        r = self.analyse()
        rows = {x["path"]: x for x in r["members"]}
        self.assertNotEqual(
            rows["calc.py"]["normalized_ast_sha256"], rows["canary.py"]["normalized_ast_sha256"]
        )
        self.assertEqual(
            rows["calc.py"]["template_ast_sha256"], rows["canary.py"]["template_ast_sha256"]
        )

    def test_budget_checked_before_allocation(self):
        with self.assertRaisesRegex(audit.AuditInputError, "before allocation"):
            cohort._selection(self.packet[0], replace(cohort.DEFAULT_LIMITS, max_total_bytes=128))
        with self.assertRaises(audit.AuditInputError):
            cohort._selection(
                self.packet[0], replace(cohort.DEFAULT_LIMITS, max_source_artifacts=1)
            )
        with self.assertRaises(audit.AuditInputError):
            self.analyse(replace(cohort.DEFAULT_LIMITS, max_members=1))

    def test_forbidden_paths_never_selected(self):
        self.packet[0]["setup_reuse"]["copied_members"] += [
            {"path": "private/model.duckdb"},
            {"path": "repository/.git/objects/unread"},
            {"path": "private/keys/unread"},
        ]
        self.assertEqual(cohort._selection(self.packet[0], cohort.DEFAULT_LIMITS), self.packet[1])

    def test_traversal_selector_refused(self):
        self.packet[0]["setup_reuse"]["copied_members"][0]["path"] = (
            "private/source-artifacts/source/../outside"
        )
        with self.assertRaises(audit.AuditInputError):
            cohort._selection(self.packet[0], cohort.DEFAULT_LIMITS)

    def test_copied_snapshot_cli_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, pins = write_fixture(root, self.packet)
            with mock.patch.object(cohort, "FROZEN_PINS", pins):
                r = cohort.evaluate(manifest, root / "output")
            self.assertTrue(all(r[f] is True for f in cohort.TRUE_FLAGS))
            self.assertTrue(all(r[f] is False for f in cohort.FALSE_FLAGS))
            self.assertEqual(r["additional_attempted_training_epochs"], 0)
            self.assertEqual(
                len(list((root / "output").iterdir())), r["captured_input_file_count"] + 1
            )

    def test_raw_pin_repair_cannot_replace_fixed_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, _ = write_fixture(root, self.packet)
            with self.assertRaisesRegex(audit.AuditInputError, "frozen native"):
                cohort.evaluate(manifest, root / "output")

    def test_coherent_inner_and_outer_rehash_retains_cid_guard(self):
        changed(self.packet, self.page_cid(), lambda x: x["entries"][0].update(reason="repaired"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, pins = write_fixture(root, self.packet)
            with (
                mock.patch.object(cohort, "FROZEN_PINS", pins),
                self.assertRaisesRegex(audit.AuditInputError, "CAS identity"),
            ):
                cohort.evaluate(manifest, root / "output")

    def test_fully_repaired_cas_reference_forgery_reaches_source_check(self):
        cid = next(m["ast_cid"] for m in self.root()["members"] if m["path"] == "calc.py")
        changed(self.packet, cid, lambda value: value["references"][0].update(name="bool"))
        repair_cas(self.packet)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, pins = write_fixture(root, self.packet)
            with (
                mock.patch.object(cohort, "FROZEN_PINS", pins),
                self.assertRaisesRegex(audit.AuditInputError, "reference population"),
            ):
                cohort.evaluate(manifest, root / "output")

    def test_fully_repaired_cas_selection_forgery_reaches_role_check(self):
        def change(value):
            report = json.loads(value["report_json"])
            p = report["codebase_provenance"]
            p["training_targets"], p["tuning_targets"] = p["tuning_targets"], p["training_targets"]
            value["report_json"] = json.dumps(report)

        changed(self.packet, self.lineage_cid(), change)
        repair_cas(self.packet)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, pins = write_fixture(root, self.packet)
            with (
                mock.patch.object(cohort, "FROZEN_PINS", pins),
                self.assertRaisesRegex(audit.AuditInputError, "selection role"),
            ):
                cohort.evaluate(manifest, root / "output")

    def test_fully_repaired_cas_cursor_forgery_reaches_page_check(self):
        changed(
            self.packet,
            self.page_cid(),
            lambda value: value.update(previous_page_cid="b" + "z" * 58),
        )
        repair_cas(self.packet)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, pins = write_fixture(root, self.packet)
            with (
                mock.patch.object(cohort, "FROZEN_PINS", pins),
                self.assertRaisesRegex(audit.AuditInputError, "page continuity"),
            ):
                cohort.evaluate(manifest, root / "output")

    def test_bounded_source_ast_node_allocation(self):
        with self.assertRaisesRegex(audit.AuditInputError, "budget"):
            self.analyse(replace(cohort.DEFAULT_LIMITS, max_ast_nodes=1))

    def test_late_extra_file_and_root_alias_reachable(self):
        for alias in (False, True):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, pins = write_fixture(root, self.packet)
                output = root / "output"
                original = cohort._output_population

                def inject(path, retained, limits, alias=alias, root=root, original=original):
                    if alias:
                        path.rename(root / "moved")
                        path.symlink_to(root / "moved", target_is_directory=True)
                    else:
                        (path / "late-extra").write_text("unexpected")
                    return original(path, retained, limits)

                with (
                    mock.patch.object(cohort, "FROZEN_PINS", pins),
                    mock.patch.object(cohort, "_output_population", side_effect=inject),
                    self.assertRaises(audit.AuditInputError),
                ):
                    cohort.evaluate(manifest, output)
                self.assertFalse((output / "resumed_cohort_audit.json").exists())

    def test_late_original_and_copy_drift_reachable(self):
        for copied in (False, True):
            with self.subTest(copied=copied), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, pins = write_fixture(root, self.packet)
                output = root / "output"
                original = cohort._output_population

                def inject(path, retained, limits, copied=copied, original=original):
                    target = Path(retained[-1]["retained_path"] if copied else retained[-1]["path"])
                    raw = target.read_bytes()
                    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                    return original(path, retained, limits)

                with (
                    mock.patch.object(cohort, "FROZEN_PINS", pins),
                    mock.patch.object(cohort, "_output_population", side_effect=inject),
                ):
                    if copied:
                        with self.assertRaises(audit.AuditInputError):
                            cohort.evaluate(manifest, output)
                    else:
                        # An original changing after the final original read must
                        # also be checked by the publication fence.
                        with self.assertRaises(audit.AuditInputError):
                            cohort.evaluate(manifest, output)

    def test_cli_clean_refusal_keeps_unknown_exposure(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.redirect_stderr(io.StringIO()) as error,
        ):
            status = cohort.main(
                [
                    "--manifest",
                    str(Path(directory) / "missing.json"),
                    "--output",
                    str(Path(directory) / "output"),
                ]
            )
            self.assertEqual(status, 3)
            self.assertTrue(json.loads(error.getvalue())["unknown_pretraining_exposure"])


if __name__ == "__main__":
    unittest.main()
