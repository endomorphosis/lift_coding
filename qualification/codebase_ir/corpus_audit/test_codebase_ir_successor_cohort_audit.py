"""Embedded source-only successor fixtures; no owner artifacts or execution."""
from __future__ import annotations

import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import codebase_ir_successor_cohort_audit as audit


def location(raw, start, end):
    def coordinate(position):
        prefix = raw[:position]
        return prefix.count(b"\n") + 1, len(prefix.rsplit(b"\n", 1)[-1])
    a, b = coordinate(start), coordinate(end)
    return dict(start_byte=start, end_byte=end, start_line=a[0], end_line=b[0], start_column=a[1], end_column=b[1])


def captured(raw, path, source_head, identity):
    value = dict(schema="ipfs-datasets.software-contracts.ast-ir@1.0.0", calls=[], diagnostics=[], effects=[], frontend={}, imports=[],
                 module={"module_id": "module:" + identity, "span": location(raw, 0, len(raw))},
                 provenance=dict(repository_id=source_head["repository_id"], repository_tree_cid=source_head["snapshot_cid"],
                                 revision="snapshot:" + source_head["snapshot_cid"], path=path, source_cid=identity),
                 references=[], scopes=[{"scope_id": "scope:module"}], symbols=[], unsupported=[])
    try:
        tree = ast.parse(raw.decode(), type_comments=True)
    except (SyntaxError, UnicodeDecodeError):
        value["diagnostics"], value["unsupported"] = ["authored parse failure"], ["syntax"]
        return value
    offsets, total = [], 0
    for line in raw.split(b"\n"):
        offsets.append(total)
        total += len(line) + 1
    def extent(node):
        return location(raw, offsets[node.lineno - 1] + node.col_offset, offsets[node.end_lineno - 1] + node.end_col_offset)
    annotations = set()
    for node in ast.walk(tree):
        a = node.annotation if isinstance(node, ast.arg | ast.AnnAssign) else node.returns if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else None
        if a is not None:
            annotations.update(id(x) for x in ast.walk(a) if isinstance(x, ast.Name))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            context = "type" if id(node) in annotations else "write" if isinstance(node.ctx, ast.Store) else "read"
            value["references"].append(dict(name=node.id, context=context, span=extent(node), scope_id="scope:module"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            value["references"].append(dict(name=node.func.id, context="call", span=extent(node.func), scope_id="scope:module"))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.arg):
            function = isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            symbol = dict(kind="function" if function else "parameter", name=node.name if function else node.arg,
                          span=extent(node), scope_id="scope:module", symbol_id="symbol:" + str(len(value["symbols"])))
            if function:
                symbol["signature"] = dict(parameters=[dict(name=a.arg, annotation=ast.unparse(a.annotation) if a.annotation is not None else None,
                                                           position=i, kind="positional_or_named", default_kind="none") for i, a in enumerate(node.args.args)],
                                           return_annotation=ast.unparse(node.returns) if node.returns is not None else None)
            value["symbols"].append(symbol)
    return value


def packets(role_literals=(2, 101, 103), prefix_literals=None):
    source_head = dict(schema="codebase-head@1", repository_id="authored:successor", generation=2,
                       snapshot_cid=audit.object_cid({"authored": "current_snapshot"}),
                       manifest_cid=audit.object_cid({"authored": "excluded_manifest"}),
                       receipt_cid=audit.object_cid({"authored": "current_receipt"}))
    source_head["ast_revision_id"] = "rev:authored:successor:snapshot:" + source_head["snapshot_cid"]
    previous = dict(source_head, generation=1, snapshot_cid=audit.object_cid({"authored": "previous_snapshot"}))
    previous["ast_revision_id"] = "rev:authored:successor:snapshot:" + previous["snapshot_cid"]
    raw_by_path = {"README.md": b"authored inert documentation\n", "added.py": b"def added(n: int) -> int:\n    return n + 700\n"}
    prefix_literals = prefix_literals if prefix_literals is not None else list(range(3, 33))
    for i, literal in enumerate(prefix_literals, 2):
        raw_by_path[f"bulk{i:03d}.py"] = f"def increment(n: int) -> int:\n    return n + {literal}\n".encode()
    for path, literal in zip(("calc.py", "tune.py", "canary.py"), role_literals, strict=True):
        raw_by_path[path] = f"def increment(n: int) -> int:\n    return n + {literal}\n".encode()
    sources, asts, members = {}, {}, []
    for path, raw in sorted(raw_by_path.items()):
        identity = audit.cid(raw)
        sources[identity] = raw
        captured_ast = captured(raw, path, source_head, identity) if path.endswith(".py") else None
        ast_cid = audit.object_cid(captured_ast) if captured_ast is not None else None
        if captured_ast is not None:
            asts[ast_cid] = captured_ast
        members.append(dict(path=path, raw_path_hex=path.encode().hex(), source_key="raw:" + path.encode().hex(),
                            source_cid=identity, source_size_bytes=len(raw), ast_cid=ast_cid,
                            parse_status="ok" if captured_ast is not None else "unindexed", opaque_reason=None,
                            entry_cid=audit.object_cid({"authored_entry": path, "source": identity})))
    for i in range(265):
        path = f"z{i:03d}.dat"
        members.append(dict(path=path, raw_path_hex=path.encode().hex(), source_key="raw:" + path.encode().hex(),
                            source_cid=None, source_size_bytes=65537, ast_cid=None, parse_status="opaque", opaque_reason="authored excluded source",
                            entry_cid=audit.object_cid({"authored_entry": path})))
    parent = dict(artifact={"bytes": 999, "sha256": "d" * 64}, artifact_cid="uninspected-parent",
                  contract_sha256="a" * 64, feature_space_sha256="f" * 64, state_sha256="b" * 64,
                  feature_columns=53, latent_width=8, projection_ids=["codebase_ir.contracts@1", "codebase_ir.program@1"],
                  projection_widths={"codebase_ir.contracts@1": 2, "codebase_ir.program@1": 51},
                  variant_id="modality-" + "a" * 64, version_id="sha256:" + "1" * 64)
    parent["ancestry"] = [{"version_id": parent["version_id"], "artifact": parent["artifact"]}]
    child = dict(parent, artifact={"bytes": 1000, "sha256": "e" * 64}, artifact_cid="uninspected-child",
                 state_sha256="c" * 64, version_id="sha256:" + "2" * 64)
    child["ancestry"] = [{"version_id": child["version_id"], "artifact": child["artifact"]}, parent["ancestry"][0]]
    request = dict(schema="codebase-source-feature-training@1", head=source_head, parent_version_id=parent["version_id"],
                   selections=[{"path": p, "role": r, "contracts": []} for p, r in (("calc.py", "train"), ("canary.py", "canary"), ("tune.py", "tune"))],
                   configuration={"epochs": 1, "learning_rate": 0.002, "seed": 1729}, contract_sha256=child["contract_sha256"],
                   implementation=[], training_targets_sha256="3" * 64, tuning_targets_sha256="4" * 64, canary_targets_sha256="5" * 64)
    result = dict(admitted=False, formalized=False, promotion_performed=False, qualified=False, training_purpose="feature_pretraining",
                  **{k: child[k] for k in ("contract_sha256", "state_sha256", "feature_space_sha256")})
    registry = {k: [] for k in ("events", "heads", "meta", "operations", "outbox", "runs", "variants", "versions")}
    registry["versions"] = [[parent["version_id"], parent["variant_id"], None, audit.wire(parent["artifact"]).decode(), "{}"],
                            [child["version_id"], child["variant_id"], parent["version_id"], audit.wire(child["artifact"]).decode(), "{}"]]
    registry["runs"] = [["authored-child", child["variant_id"], parent["version_id"], audit.wire(request).decode(), "completed", 1, 1, "{}", audit.wire(result).decode()]]
    metadata = {"owners_before": {"model_artifacts": [], "registry": registry, "source": {"current_head": source_head, "tables": {}}}}
    for route in ("optimized", "reference"):
        root = dict(schema="codebase-inventory-resume-root@1", authority=dict.fromkeys(audit.AUTHORITY_FIELDS, False),
                    head=source_head, head_cid=audit.object_cid(source_head), implementation=[], limits={"page_entries": 32},
                    members=members, membership_cid=audit.object_cid(members), model=child, optimized=route == "optimized")
        metadata[route + "_root"] = {"artifact_cid": audit.object_cid(root), "value": root}
        s = dict(schema="codebase-inventory-successor-scan@1", authority=dict.fromkeys(audit.AUTHORITY_FIELDS, False),
                 previous_head=previous, current_head=source_head, previous_membership_cid="uninspected-old-membership",
                 current_membership_cid=root["membership_cid"], implementation=[], model=child, previous_model=parent,
                 previous_training_record_cid="uninspected-root-training", training_record_cid="uninspected-child-training",
                 root_cid=metadata[route + "_root"]["artifact_cid"], source_delta_cid="uninspected-source-delta", scan_limits=root["limits"],
                 optimized=route == "optimized", inference_performed_here=False, training_performed_here=False, model_head_promoted=False, numerical_reuse=False)
        metadata[route + "_selection"] = {"artifact_cid": audit.object_cid(s), "value": s}
        entries, rows, coverage = [], [], []
        for index, m in enumerate(members[:32]):
            d = "unindexed" if index == 0 else "inferred" if index <= 22 else "deferred_budget"
            source_digest, target_hash = (None, None) if index == 0 else (audit.sha((m["path"] + "source").encode()), audit.sha((m["path"] + "target").encode()))
            c = [] if index == 0 else [{"projection_id": k, "known_atoms": width - (1 if width == 51 else 0), "unknown_atoms": 1 if width == 51 else 0} for k, width in child["projection_widths"].items()]
            entries.append(dict(coverage=c, disposition=d, entry_cid=m["entry_cid"], source_key=m["source_key"], member_index=index,
                                inference_index=len(rows) if d == "inferred" else None, reason=None if d == "inferred" else "captured_source_has_no_ast_projection" if index == 0 else "authored budget",
                                source_digest=source_digest, target_sha256=target_hash))
            if d == "inferred":
                rows.append({"source_digest": source_digest, "latent": [0.1] * 8,
                             "reconstructed_projection_features": {k: [0.2] * w for k, w in child["projection_widths"].items()}})
                coverage.extend(c)
        inference = dict(schema="native-projection-feature-inference/v1", admitted=False, formalized=False, promotion_performed=False,
                         qualified=False, decoded_formulas_generated=False, training_executed=False, representation="native_compiler_structural_features_not_semantic_text_embeddings",
                         rows=rows, coverage=coverage, **{k: child[k] for k in ("contract_sha256", "state_sha256", "feature_space_sha256")})
        p = dict(schema="codebase-inventory-resume-page@1", authority=dict.fromkeys(audit.AUTHORITY_FIELDS, False), coverage={"dispositions": {"inferred": 22, "deferred_budget": 9, "unindexed": 1}, "inferred_rows": 22, "inventory_entries": 32},
                 start=0, end=32, total_entries=300, entries=entries, head_cid=root["head_cid"], inference=inference,
                 membership_cid=root["membership_cid"], model_artifact_cid=child["artifact_cid"], page_membership_cid=audit.object_cid(members[:32]),
                 previous_page_cid=None, root_cid=s["root_cid"], worker_receipt={"scope": "authored recorded claim"})
        metadata[route + "_prefix"] = {"artifact_cid": audit.cid(audit.wire(p)), "value": p}
    native = dict(schema="codebase-source-successor-native-qualification@1", qualified=True, parent_version_id=parent["version_id"], child_version_id=child["version_id"],
                  current_head=source_head, previous_head=previous, training_attempts_after_setup=0, inference_attempts_during_selection_or_cold_receiving=0,
                  new_fitting_epochs=2, recorded_seconds=809.9, root_cid=metadata["optimized_root"]["artifact_cid"], prefix_page_cid=metadata["optimized_prefix"]["artifact_cid"],
                  successor_selection_cid=metadata["optimized_selection"]["artifact_cid"], setup_training_attempts=[dict(name=n, requested_epochs=1, actual_completed_epochs=1, unknown_actual_epochs_on_failure=False) for n in ("root", "child")])
    failed = dict(native, qualified=False, error_type="LeaseTimeoutError", recorded_seconds=394.9)
    return {"metadata": metadata, "sources": sources, "asts": asts, "native": native, "failed": failed}


def rehash(p):
    for key, envelope in p["metadata"].items():
        if key != "owners_before":
            envelope["artifact_cid"] = audit.cid(audit.wire(envelope["value"]), not key.endswith("_prefix"))


def rejoin(p):
    for route in ("optimized", "reference"):
        root = p["metadata"][route + "_root"]["value"]
        root["membership_cid"] = audit.object_cid(root["members"])
        root_cid = audit.object_cid(root)
        p["metadata"][route + "_root"]["artifact_cid"] = root_cid
        s = p["metadata"][route + "_selection"]["value"]
        s["root_cid"], s["current_membership_cid"] = root_cid, root["membership_cid"]
        p["metadata"][route + "_selection"]["artifact_cid"] = audit.object_cid(s)
        page = p["metadata"][route + "_prefix"]["value"]
        page.update(root_cid=root_cid, membership_cid=root["membership_cid"], page_membership_cid=audit.object_cid(root["members"][:32]))
        p["metadata"][route + "_prefix"]["artifact_cid"] = audit.cid(audit.wire(page))
    p["native"].update(root_cid=p["metadata"]["optimized_root"]["artifact_cid"],
                       successor_selection_cid=p["metadata"]["optimized_selection"]["artifact_cid"],
                       prefix_page_cid=p["metadata"]["optimized_prefix"]["artifact_cid"])


def derive(p):
    return audit.derive(p["metadata"], p["sources"], p["asts"], p["native"], p["failed"])


class Fixture:
    def __init__(self, base):
        self.base = base
        self.input = base / "input"
        self.output = base / "output"
        self.input.mkdir()
        self.packets = packets()
        self.manifest = {"schema": audit.INPUT_SCHEMA, "metadata": {}, "source_artifacts": []}
        self.raw = {}
        archive = []

        def emit(label, raw):
            path = self.input / (label + ".body")
            path.write_bytes(raw)
            self.raw[label] = raw
            return {"path": str(path), "sha256": audit.sha(raw), "size_bytes": len(raw)}

        for role, selector in audit.METADATA.items():
            raw = audit.wire(self.packets["metadata"][role])
            self.manifest["metadata"][role] = emit(role, raw)
            archive.append({"path": selector, "kind": "file", "bytes": len(raw), "sha256": audit.sha(raw)})
        for kind, values in (("source", self.packets["sources"]), ("structured", self.packets["asts"])):
            for index, (identity, value) in enumerate(sorted(values.items())):
                raw = value if kind == "source" else audit.wire(value)
                selector = f"private/source-artifacts/{kind}/{identity[:4]}/{identity}"
                desc = emit(kind + str(index), raw)
                self.manifest["source_artifacts"].append(dict(desc, selector=selector))
                archive.append({"path": selector, "kind": "file", "bytes": len(raw), "sha256": audit.sha(raw)})
        for role, key in (("native_result", "native"), ("failed_result", "failed")):
            self.manifest[role] = emit(role, audit.wire(self.packets[key]))
        native_cids = {k: self.packets["metadata"][role]["artifact_cid"] for k, role in (("default_root", "optimized_root"), ("reference_root", "reference_root"),
                      ("default_prefix_page", "optimized_prefix"), ("reference_prefix_page", "reference_prefix"), ("default_selection", "optimized_selection"), ("reference_selection", "reference_selection"))}
        independent = {"schema": "codebase-source-successor-independent-audit@1", "archive": {"files": archive}, "native_artifact_cids": native_cids,
                       "audited_result": {"sha256": self.manifest["native_result"]["sha256"], "bytes": self.manifest["native_result"]["size_bytes"]}}
        self.manifest["independent_audit"] = emit("independent_audit", audit.wire(independent))
        review = {"schema": "repository-proof-index-source-successor-review@1"}
        for field, role in (("native_result", "native_result"), ("independent_closed_audit", "independent_audit"), ("failed_native_attempt", "failed_result")):
            pin = {"sha256": self.manifest[role]["sha256"], "bytes": self.manifest[role]["size_bytes"]}
            review[field] = {"result": pin} if role == "failed_result" else pin
        self.manifest["review"] = emit("review", audit.wire(review))
        self.anchors = {role: self.manifest[role]["sha256"] for role in audit.ROLES}
        self.path = self.input / "manifest.json"
        self.save()

    def save(self):
        self.path.write_bytes(audit.wire(self.manifest))

    def evaluate(self):
        self.save()
        with patch.dict(audit.ANCHORS, self.anchors, clear=True):
            return audit.evaluate(self.path, self.output)


class SuccessorCohortTests(unittest.TestCase):
    def refused(self, p, reason=None):
        with self.assertRaises(audit.Refused) as caught:
            derive(p)
        if reason:
            self.assertIn(reason, str(caught.exception))

    def test_complete_independent_population_and_unknowns(self):
        r = derive(packets())
        self.assertEqual((r["complete_member_count"], r["unique_prefix_member_count"], r["outside_prefix_member_count"]), (300, 32, 268))
        self.assertEqual((r["selected_path_count"], r["source_body_count"], r["ast_body_count"]), (35, 35, 34))
        self.assertEqual(r["prefix_dispositions"], {"inferred": 22, "deferred_budget": 9, "unindexed": 1})
        self.assertEqual(r["exact_source_role_overlap_count"], 0)
        self.assertEqual(r["normalized_clone_role_overlap_count"], 0)
        self.assertEqual(r["template_role_overlap_count"], 90)
        self.assertEqual(r["claimed_total_native_setup_epochs"], 4)
        self.assertTrue(r["root_exposure_disposition"].startswith("unknown"))

    def test_exact_clone_overlaps_preserve_role(self):
        p = packets(role_literals=(3, 101, 103))
        r = derive(p)
        self.assertEqual(r["exact_source_role_overlap_count"], 1)
        self.assertEqual(r["normalized_clone_role_overlap_count"], 1)
        self.assertEqual(r["declared_role_overlaps"][0]["declared_child_role"], "train")

    def test_refuses_fresh_root_population_drift_after_rehash(self):
        p = packets()
        p["metadata"]["reference_root"]["value"]["members"] = copy.deepcopy(p["metadata"]["reference_root"]["value"]["members"])
        p["metadata"]["reference_root"]["value"]["members"][-1]["path"] = "other.dat"
        rehash(p)
        self.refused(p)

    def test_refuses_bool_generation_and_feature_width(self):
        for role, field in (("optimized_selection", "current_head"), ("optimized_root", "model")):
            p = packets()
            value = p["metadata"][role]["value"][field]
            value["generation" if field == "current_head" else "feature_columns"] = True
            rehash(p)
            self.refused(p)

    def test_comment_clone_keeps_exact_and_normalized_relations_distinct(self):
        raw = b"def increment(n: int) -> int:\n    return n + 3 # commentary\n"
        p = packets(role_literals=(3, 101, 103))
        roots = p["metadata"]["optimized_root"]["value"]
        m = next(m for m in roots["members"] if m["path"] == "calc.py")
        old_source, old_ast = m["source_cid"], m["ast_cid"]
        m["source_cid"], m["source_size_bytes"] = audit.cid(raw), len(raw)
        value = captured(raw, m["path"], roots["head"], m["source_cid"])
        m["ast_cid"] = audit.object_cid(value)
        p["sources"][m["source_cid"]] = raw
        p["asts"].pop(old_ast)
        p["asts"][m["ast_cid"]] = value
        if not any(x["source_cid"] == old_source for x in roots["members"][:35]):
            p["sources"].pop(old_source)
        rejoin(p)
        r = derive(p)
        self.assertEqual(r["exact_source_role_overlap_count"], 0)
        self.assertEqual(r["normalized_clone_role_overlap_count"], 1)

    def test_source_only_unsupported_and_unicode_spans_are_explicit(self):
        for raw, supported in (("def αύξηση(ν: int) -> int:\n    return ν + 3\n".encode(), True),
                               (b"def increment(n: int) -> int:\n    print(n)\n    return n + 3\n", False)):
            p = packets()
            h = p["metadata"]["optimized_root"]["value"]["head"]
            identity = audit.cid(raw)
            m = dict(path="unicode.py", source_cid=identity, source_size_bytes=len(raw), parse_status="ok")
            value = captured(raw, m["path"], h, identity)
            result = audit.syntax(m, raw, value, h)
            self.assertEqual(result["syntax_disposition"], "parsed")
            self.assertEqual(result["label"] is not None, supported)

    def test_syntactic_walk_and_typed_parameter_allocation_bounds(self):
        p = packets()
        root = p["metadata"]["optimized_root"]["value"]
        m = next(m for m in root["members"] if m["path"] == "added.py")
        raw = p["sources"][m["source_cid"]]
        value = copy.deepcopy(p["asts"][m["ast_cid"]])
        value["module"]["extra"] = [0] * 16384
        with self.assertRaisesRegex(audit.Refused, "AST walk budget"):
            audit.syntax(m, raw, value, root["head"])

    def test_refuses_bool_member_index_with_repaired_page(self):
        p = packets()
        p["metadata"]["optimized_prefix"]["value"]["entries"][1]["member_index"] = True
        rehash(p)
        self.refused(p, "typed exact member index")

    def test_refuses_shifted_prefix_and_stale_root(self):
        for field, value in (("start", 1), ("previous_page_cid", "old-page"), ("root_cid", "old-root")):
            p = packets()
            p["metadata"]["optimized_prefix"]["value"][field] = value
            rehash(p)
            self.refused(p)

    def test_refuses_missing_duplicate_and_wrong_source_entries(self):
        for mutation in ("missing", "duplicate", "wrong"):
            p = packets()
            entries = p["metadata"]["optimized_prefix"]["value"]["entries"]
            if mutation == "missing":
                entries.pop()
            elif mutation == "duplicate":
                entries[2] = copy.deepcopy(entries[1])
            else:
                entries[2]["source_key"] = entries[3]["source_key"]
            rehash(p)
            self.refused(p)

    def test_refuses_deferred_fake_row_and_unknown_disposition(self):
        for field, value in (("inference_index", 22), ("disposition", "complete")):
            p = packets()
            p["metadata"]["optimized_prefix"]["value"]["entries"][-1][field] = value
            rehash(p)
            self.refused(p)

    def test_refuses_repaired_coverage_and_inference_populations(self):
        for field in ("coverage", "rows"):
            p = packets()
            p["metadata"]["optimized_prefix"]["value"]["inference"][field].pop()
            rehash(p)
            self.refused(p)

    def test_refuses_bool_numerics_and_wrong_latent_width(self):
        for value in ([True] * 8, [0.1] * 7):
            p = packets()
            p["metadata"]["optimized_prefix"]["value"]["inference"]["rows"][0]["latent"] = value
            rehash(p)
            self.refused(p)

    def test_refuses_selection_native_authority_and_fit_escalation(self):
        for field in ("training_performed_here", "inference_performed_here", "model_head_promoted", "numerical_reuse"):
            p = packets()
            p["metadata"]["optimized_selection"]["value"][field] = True
            rehash(p)
            self.refused(p)

    def test_refuses_parent_pointer_and_basis_drift(self):
        p = packets()
        p["metadata"]["owners_before"]["registry"]["versions"][1][2] = "different-parent"
        self.refused(p)
        p = packets()
        p["metadata"]["optimized_selection"]["value"]["model"]["feature_space_sha256"] = "0" * 64
        rehash(p)
        self.refused(p)

    def test_refuses_child_role_population_and_head_drift(self):
        for mutate in ("role", "head", "epoch"):
            p = packets()
            row = p["metadata"]["owners_before"]["registry"]["runs"][0]
            request = audit.document(row[3].encode())
            if mutate == "role":
                request["selections"][0]["role"] = "canary"
            elif mutate == "head":
                request["head"]["generation"] = True
            else:
                request["configuration"]["epochs"] = True
            row[3] = audit.wire(request).decode()
            self.refused(p)

    def test_refuses_source_bytes_and_missing_ast(self):
        p = packets()
        key = next(iter(p["sources"]))
        p["sources"][key] += b" "
        self.refused(p)
        p = packets()
        p["asts"].pop(next(iter(p["asts"])))
        self.refused(p)

    def test_refuses_ast_span_symbol_reference_and_schema(self):
        for mutate in ("span", "reference", "symbol", "schema", "signature"):
            p = packets()
            key = next(iter(p["asts"]))
            value = p["asts"].pop(key)
            if mutate == "span":
                value["references"][0]["span"]["start_byte"] = True
            elif mutate == "reference":
                value["references"][0]["name"] = "forged"
            elif mutate == "symbol":
                value["symbols"][0]["name"] = "forged"
            elif mutate == "schema":
                value["schema"] = "future-ast@2"
            else:
                value["symbols"][0]["signature"]["parameters"][0]["position"] = False
            new_key = audit.object_cid(value)
            p["asts"][new_key] = value
            for route in ("optimized", "reference"):
                for m in p["metadata"][route + "_root"]["value"]["members"]:
                    if m["ast_cid"] == key:
                        m["ast_cid"] = new_key
                root = p["metadata"][route + "_root"]["value"]
                root["membership_cid"] = audit.object_cid(root["members"])
                p["metadata"][route + "_selection"]["value"]["current_membership_cid"] = root["membership_cid"]
            self.assertNotEqual(new_key, key)
            rejoin(p)
            expected = {"span": "typed span offsets", "reference": "reference population", "symbol": "symbol population",
                        "schema": "unsupported captured AST schema", "signature": "signature annotations"}[mutate]
            self.refused(p, expected)

    def test_native_target_digest_remains_opaque(self):
        r = derive(packets())
        self.assertIn("opaque", r["native_target_digest_disposition"])
        self.assertIn("unavailable", r["snapshot_schema_disposition"])

    def test_refuses_lost_failed_attempt_and_bool_epochs(self):
        for field, value in (("qualified", True), ("new_fitting_epochs", True), ("training_attempts_after_setup", False)):
            p = packets()
            p["failed"][field] = value
            self.refused(p)

    def test_pipeline_exact_population_flags_and_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Fixture(Path(tmp))
            r = f.evaluate()
            self.assertEqual(r["selected_original_count"], 80)
            self.assertTrue(all(r[k] is True for k in audit.TRUE_FLAGS))
            self.assertTrue(all(r[k] is False for k in audit.FALSE_FLAGS))
            self.assertEqual((r["runtime_fact_count"], r["additional_attempted_training_epochs"]), (0, 0))
            self.assertEqual(len(list(f.output.rglob("*.body"))), 80)

    def test_refuses_metadata_counterparty_repin(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Fixture(Path(tmp))
            d = f.manifest["metadata"]["owners_before"]
            value = audit.document(Path(d["path"]).read_bytes())
            row = value["registry"]["runs"][0]
            request = audit.document(row[3].encode())
            request["selections"][0]["role"], request["selections"][1]["role"] = request["selections"][1]["role"], request["selections"][0]["role"]
            row[3] = audit.wire(request).decode()
            raw = audit.wire(value)
            Path(d["path"]).write_bytes(raw)
            d.update(sha256=audit.sha(raw), size_bytes=len(raw))
            with self.assertRaisesRegex(audit.Refused, "audit-declared child raw pin"):
                f.evaluate()

    def test_refuses_wrong_outer_anchor_and_descriptor_alias(self):
        for mode in ("anchor", "alias", "size", "bool"):
            with tempfile.TemporaryDirectory() as tmp:
                f = Fixture(Path(tmp))
                if mode == "anchor":
                    f.manifest["review"]["sha256"] = "0" * 64
                elif mode == "alias":
                    f.manifest["metadata"]["owners_before"] = dict(f.manifest["native_result"])
                elif mode == "size":
                    f.manifest["source_artifacts"][0]["size_bytes"] = audit.MiB + 1
                else:
                    f.manifest["native_result"]["size_bytes"] = True
                with self.assertRaises((audit.Refused, OSError)):
                    f.evaluate()

    def test_refuses_duplicate_or_forbidden_source_selector(self):
        for mode in ("duplicate", "forbidden", "extra"):
            with tempfile.TemporaryDirectory() as tmp:
                f = Fixture(Path(tmp))
                if mode == "duplicate":
                    f.manifest["source_artifacts"][0]["selector"] = f.manifest["source_artifacts"][1]["selector"]
                elif mode == "forbidden":
                    f.manifest["source_artifacts"][0]["selector"] = "private/model-artifacts/no-follow"
                else:
                    f.manifest["source_artifacts"].append(f.manifest["source_artifacts"][0])
                with self.assertRaises(audit.Refused):
                    f.evaluate()

    def test_strict_json_duplicate_huge_integer_depth_and_surrogate(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":999999999999999999999999}', b'{"a":NaN}', b'{"a":"\\ud800"}', b'{"a":' + b'[' * 65 + b'0' + b']' * 65 + b'}'):
            with self.assertRaises((audit.Refused, UnicodeError)):
                audit.document(raw)

    def test_bounded_reads_no_symlink_or_fifo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw = base / "raw"
            raw.write_bytes(b"123")
            link = base / "link"
            link.symlink_to(raw)
            with self.assertRaises(audit.Refused):
                audit.Reads.bounded(link, 3)
            with self.assertRaises(audit.Refused):
                audit.Reads.bounded(raw, 2)

    def test_late_original_and_copy_and_report_drift(self):
        for mode in ("original", "copy", "report"):
            with tempfile.TemporaryDirectory() as tmp:
                f = Fixture(Path(tmp))
                reached = []
                def inject(stage, output, mode=mode, f=f, reached=reached):
                    if stage == "after_publish":
                        reached.append(stage)
                        p = Path(f.manifest["native_result"]["path"]) if mode == "original" else output / "inputs/000-review.body" if mode == "copy" else output / "successor_cohort_audit.json"
                        raw = p.read_bytes()
                        p.write_bytes(b" " + raw[1:])
                with patch.object(audit, "checkpoint", side_effect=inject), self.assertRaises(audit.Refused):
                    f.evaluate()
                self.assertEqual(reached, ["after_publish"])
                self.assertFalse((f.output / "successor_cohort_audit.json").exists())

    def test_late_output_extra_root_alias_and_member_symlink(self):
        for mode in ("extra", "alias", "symlink", "directory"):
            with tempfile.TemporaryDirectory() as tmp:
                f = Fixture(Path(tmp))
                reached = []
                def inject(stage, output, mode=mode, f=f, reached=reached):
                    if stage == "after_final_copies":
                        reached.append(stage)
                        if mode == "extra":
                            (output / "unexpected").write_bytes(b"x")
                        elif mode == "directory":
                            (output / "unexpected").mkdir()
                        elif mode == "alias":
                            moved = output.with_name("moved")
                            output.rename(moved)
                            output.symlink_to(moved, target_is_directory=True)
                        else:
                            p = output / "inputs/000-review.body"
                            p.unlink()
                            p.symlink_to(Path(f.manifest["review"]["path"]))
                with patch.object(audit, "checkpoint", side_effect=inject), self.assertRaises(audit.Refused):
                    f.evaluate()
                self.assertEqual(reached, ["after_final_copies"])

    def test_allocation_reserves_before_read_and_protects_input_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Fixture(Path(tmp))
            with patch.object(audit, "MAX_BYTES", 10), self.assertRaises(audit.Refused):
                f.evaluate()
            f.output = f.input / "forbidden-output"
            with self.assertRaisesRegex(audit.Refused, "protected"):
                f.evaluate()

    def test_cli_typed_refusal_is_not_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_bytes(b'{"schema":"unknown"}')
            with patch("builtins.print") as printed:
                self.assertEqual(audit.main(["--manifest", str(path), "--output", str(Path(tmp) / "out")]), 2)
            r = json.loads(printed.call_args.args[0])
            self.assertTrue(r["unknown_pretraining_exposure"])
            self.assertTrue(all(r[k] is False for k in audit.FALSE_FLAGS))


if __name__ == "__main__":
    unittest.main()
