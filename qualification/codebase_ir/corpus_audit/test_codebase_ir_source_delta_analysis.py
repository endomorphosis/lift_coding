"""Authored inert successors; no workspace owner fixtures or source execution."""
from __future__ import annotations

import ast
import copy
import json
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import codebase_ir_source_delta_analysis as audit

OLD = b"def increment(n: int) -> int:\n    return n + 1\n"
NEW = b"def increment(n: int) -> int:\n    return n + 2\n"


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


def packets(previous=None, current=None, ast_mutator=None, snapshot_schema="ipfs-datasets.software-contracts.semantic-repository-snapshot@4", entry_schema="ipfs-datasets.software-contracts.semantic-snapshot-entry@3"):
    previous = previous if previous is not None else {"calc.py": OLD, "gone.py": NEW, "consumer.py": b"import calc\n"}
    current = current if current is not None else {"calc.py": NEW, "renamed.py": NEW, "consumer.py": b"import calc\n"}
    policy = dict(mode="authored", max_entries=512, max_file_bytes=65536)
    sources, asts, manifests, heads, receipts, memberships = {}, {}, {}, {}, {}, {}
    for side, bodies in (("previous", previous), ("current", current)):
        entries = []
        for path, raw in sorted(bodies.items(), key=lambda x: x[0].encode()):
            identity = audit.cid(raw) if raw is not None else None
            if raw is not None:
                sources[identity] = raw
            entry = dict(acquisition="authored", disposition="captured", git_blob_oid=None, head_blob_oid=None, index_blob_oids=[],
                         kind="file", opaque_reason="authored unavailable" if raw is None else None, path=path, raw_path_hex=path.encode().hex(),
                         schema=entry_schema, size_bytes=len(raw) if raw is not None else 1, source_cid=identity)
            entry["entry_cid"] = audit.object_cid(entry)
            entries.append(entry)
        snapshot = dict(entries=entries, exclusions=[], git_commit=None, git_tree=None, repository_id="authored:source-delta",
                        schema=snapshot_schema, **policy)
        snapshot["snapshot_cid"] = audit.object_cid(snapshot)
        h = dict(schema="codebase-head@1", repository_id=snapshot["repository_id"], generation=1 if side == "previous" else 2,
                 ast_revision_id="rev:" + snapshot["repository_id"] + ":snapshot:" + snapshot["snapshot_cid"], snapshot_cid=snapshot["snapshot_cid"])
        units, members = [], []
        for entry in entries:
            raw = bodies[entry["path"]]
            parsed, identity = "opaque", None
            if raw is not None and entry["path"].endswith(".py"):
                a = captured(raw, entry["path"], h, entry["source_cid"])
                parsed = "failed" if a["diagnostics"] else "ok"
                if ast_mutator is not None:
                    ast_mutator(side, entry["path"], a)
                identity = audit.object_cid(a)
                asts[identity] = a
            elif raw is not None:
                parsed = "unindexed"
            unit = dict(schema="codebase-ir-structural-unit@1", source_key="raw:" + entry["raw_path_hex"], entry_cid=entry["entry_cid"], ast_cid=identity, parse_status=parsed)
            units.append(unit)
            members.append(dict(ast_cid=identity, entry_cid=entry["entry_cid"], opaque_reason=entry["opaque_reason"], parse_status=parsed,
                                path=entry["path"], raw_path_hex=entry["raw_path_hex"], source_cid=entry["source_cid"], source_key=unit["source_key"], source_size_bytes=entry["size_bytes"]))
        manifest = dict(schema="codebase-ir-structural-manifest@1", ast_revision_id=h["ast_revision_id"], authority="structural_only", coverage={},
                        semantic_state="unknown", snapshot=snapshot, units=units)
        h["manifest_cid"] = audit.object_cid(manifest)
        receipt = {k: h[k] for k in ("repository_id", "generation", "ast_revision_id", "snapshot_cid", "manifest_cid")}
        if side == "current":
            receipt["previous_head"] = heads["previous"]
        h["receipt_cid"] = audit.object_cid(receipt)
        manifests[side], heads[side], receipts[side] = manifest, h, receipt
        memberships[side] = {m["source_key"]: {"entry": e, "member": m} for e, m in zip(entries, members, strict=True)}
    rows = []
    for key in sorted(set(memberships["previous"]) | set(memberships["current"])):
        a, b = memberships["previous"].get(key), memberships["current"].get(key)
        state = "added" if a is None else "removed" if b is None else "retained" if a["entry"] == b["entry"] else "changed"
        source, syntax = "unavailable", "unavailable"
        if a is not None and b is not None:
            x, y = a["member"], b["member"]
            if x["source_cid"] in sources and y["source_cid"] in sources:
                source = "equal" if sources[x["source_cid"]] == sources[y["source_cid"]] else "different"
            if x["ast_cid"] is not None and y["ast_cid"] is not None:
                syntax = "equal" if x["ast_cid"] == y["ast_cid"] else "different"
        rows.append(dict(source_key=key, classification=state, previous=a, current=b, source_bytes_comparison=source, ast_identity_comparison=syntax))
    counts = {field: Counter(row[field] for row in rows) for field in ("classification", "source_bytes_comparison", "ast_identity_comparison")}
    coverage = dict(previous_entries=len(previous), current_entries=len(current), union_entries=len(rows),
                    classifications={k: counts["classification"][k] for k in ("retained", "changed", "added", "removed")},
                    source_bytes_comparisons={k: counts["source_bytes_comparison"][k] for k in ("equal", "different", "unavailable")},
                    ast_identity_comparisons={k: counts["ast_identity_comparison"][k] for k in ("equal", "different", "unavailable")})
    value = dict(schema="codebase-inventory-source-delta@1", authority=dict.fromkeys(audit.AUTHORITY_FIELDS, False), capture_policy=policy,
                 coverage=coverage, current_head=heads["current"], previous_head=heads["previous"],
                 current_membership_cid=audit.object_cid([x["member"] for x in memberships["current"].values()]),
                 previous_membership_cid=audit.object_cid([x["member"] for x in memberships["previous"].values()]),
                 current_publication_receipt=receipts["current"], previous_publication_receipt=receipts["previous"], implementation="authored",
                 ledger=rows, limits={}, model_advanced=False, numerical_reuse=False, optimized=True, physical_absence_verified=False, removal_scope="captured entries")
    return dict(envelope=dict(artifact_cid=audit.object_cid(value), value=value), manifests=manifests, sources=sources, asts=asts)


def rehash(p):
    p["envelope"]["artifact_cid"] = audit.object_cid(p["envelope"]["value"])


def derive(p):
    return audit.derive_delta(p["envelope"], p["manifests"]["previous"], p["manifests"]["current"], p["sources"], p["asts"])


class Fixture:
    def __init__(self, base):
        self.base, self.pins, self.values = base, {}, {}
        self.main, self.ignored = base / "native-main", base / "native-ignore"
        self.main.mkdir()
        self.ignored.mkdir()
        self.packet, self.ignore_packet = packets(), packets({"keep.py": OLD, "ignored.py": NEW}, {"keep.py": OLD})
        def retain(root, p, reference):
            pins = {}
            bodies = {side + "-manifest.json": p["manifests"][side] for side in ("previous", "current")}
            bodies.update({side + "-publication-receipt.json": p["envelope"]["value"][side + "_publication_receipt"] for side in ("previous", "current")})
            bodies["optimized-source-delta.json"] = p["envelope"]
            if reference:
                ref = copy.deepcopy(p["envelope"])
                ref["value"]["optimized"] = False
                ref["artifact_cid"] = audit.object_cid(ref["value"])
                bodies["reference-source-delta.json"] = ref
            for name, body in bodies.items():
                pins[name] = self.write(root / name, body)
            for kind in ("source", "structured"):
                for identity, value in p["sources" if kind == "source" else "asts"].items():
                    relative = "private/source-artifacts/" + kind + "/" + identity[:4] + "/" + identity
                    pins[relative] = self.write(root / relative, value, raw=kind == "source")
            return pins
        main_pins, ignored_pins = retain(self.main, self.packet, True), retain(self.ignored, self.ignore_packet, False)
        v, i = self.packet["envelope"]["value"], self.ignore_packet["envelope"]["value"]
        presence = dict(path="ignored.py", bytes=len(NEW), regular=True, sha256=audit.sha(NEW), source_cid=audit.cid(NEW))
        historical = dict(schema="codebase-ir-resumed-cohort-audit@1", status="passed", unknown_pretraining_exposure=True,
                          source_semantics_verified=False, heldout_independence_verified=False,
                          **dict.fromkeys(("candidate_model_qualified", "producer_authentication_verified", "numerical_provenance_verified", "model_selection_performed", "optimizer_state_replayed", "complete_pretraining_exposure_verified"), False),
                          captured_source_head={"repository_id": "authored:other", "generation": 7},
                          members=[dict(path="historical.py", source_sha256=audit.sha(OLD), source_body_available=True)],
                          retained_lineage_selection_ledger=[dict(version_id="historical-version", selections=[dict(path="historical.py", role="train")],
                                                                target_observations=[dict(path="historical.py", role=role, source_sha256=audit.sha(OLD)) for role in ("train", "replay")])])
        self.values = dict(source_result=dict(schema="codebase-source-delta-native-qualification@1", qualified=True, coverage=v["coverage"], previous_head=v["previous_head"], current_head=v["current_head"]),
                           source_audit=dict(schema="codebase-source-delta-independent-audit@1", qualified=True, errors=[], namespace=str(self.main), guarded_artifacts=main_pins,
                                             source_delta={"coverage": v["coverage"]}, ignored_control=dict(namespace=str(self.ignored), archive={"files": [dict(path=name, kind="file", **pin) for name, pin in ignored_pins.items()]}, source_delta={"coverage": i["coverage"]})),
                           ignored_result=dict(schema="codebase-source-delta-ignore-native-qualification@1", qualified=True, coverage=i["coverage"], physical_absence_verified=False, physical_bytes_unchanged=True, physical_presence_before=presence, physical_presence_after=presence),
                           failed_ignore_result=dict(schema="codebase-source-delta-ignore-native-qualification@1", qualified=False, error="original authored failure"),
                           historical_cohort_report=historical, checkpoint_result=dict(schema="codebase-ir-independent-lanes-run@1", tests_passed=True))
        self.paths = {role: base / "outer" / (role + ".json") for role in audit.ROLES}
        self.paths["source_result"], self.paths["ignored_result"] = self.main / "result.json", self.ignored / "result.json"
        self.input = base / "input" / "manifest.json"
        self.output = base / "out"
        self.refresh()

    @staticmethod
    def write(path, value, raw=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        body = value if raw else audit.wire(value)
        path.write_bytes(body)
        return dict(bytes=len(body), sha256=audit.sha(body))

    def refresh(self):
        pins = {role: self.write(self.paths[role], value) for role, value in self.values.items() if role not in {"review", "checkpoint_result"}}
        self.values["checkpoint_result"]["qualification_findings"] = {"resumed_cohort_audit": dict(status="passed", sha256=pins["historical_cohort_report"]["sha256"])}
        pins["checkpoint_result"] = self.write(self.paths["checkpoint_result"], self.values["checkpoint_result"])
        self.values["review"] = dict(schema="codebase-source-delta-current-runtime-review@1", source_native={"result": pins["source_result"]}, source_independent_audit={"report": pins["source_audit"]},
                                     ignored_file_native={"result": pins["ignored_result"]}, failed_ignore_attempt=dict(result=pins["failed_ignore_result"], qualified=False, error=self.values["failed_ignore_result"]["error"]))
        pins["review"] = self.write(self.paths["review"], self.values["review"])
        spec = dict(schema=audit.INPUT_SCHEMA, **{role: dict(path=str(self.paths[role]), sha256=pin["sha256"], size_bytes=pin["bytes"]) for role, pin in pins.items()})
        self.write(self.input, spec)
        self.anchors = {role: pin["sha256"] for role, pin in pins.items()}

    def run(self):
        with patch.dict(audit.ANCHORS, self.anchors, clear=True):
            return audit.evaluate(self.input, self.output)


class SourceDeltaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()

    def refuse_packet(self, transform, reason=None):
        p = packets()
        transform(p)
        rehash(p)
        with self.assertRaisesRegex(audit.Refused, reason or "."):
            derive(p)

    def test_independent_golden_successor_and_dependencies(self):
        result = derive(packets())
        self.assertEqual(result["coverage"]["classifications"], dict(retained=1, changed=1, added=1, removed=1))
        self.assertEqual(result["comparison_counts"]["syntax"], {"different": 1, "equal": 1, "unavailable": 2})
        self.assertEqual(result["comparison_counts"]["ast"], {"different": 2, "unavailable": 2})
        self.assertEqual({(x["previous_source_key"], x["current_source_key"]) for x in result["cross_path_content_pairs"]},
                         {("raw:" + b"gone.py".hex(), "raw:" + path.hex()) for path in (b"calc.py", b"renamed.py")})
        self.assertFalse(result["cross_path_content_pairs"][0]["rename_inferred"])
        self.assertIn("raw:" + b"consumer.py".hex(), result["potential_dependency_frontier"]["syntactic_reverse_closure_keys"])
        changed = next(x for x in result["rows"] if x["entry_transition"] == "changed")
        self.assertEqual(changed["structural_label_comparison"], "different")

    def test_comment_bytes_change_keeps_normalized_syntax(self):
        result = derive(packets({"a.py": OLD}, {"a.py": b"# harmless\n" + OLD}))
        self.assertEqual(result["rows"][0]["source_bytes_comparison"], "different")
        self.assertEqual(result["rows"][0]["source_syntax_comparison"], "equal")

    def test_explicit_opaque_failed_unindexed_and_unsupported(self):
        bodies = {"opaque.py": None, "README": b"authored", "bad.py": b"def broken(\n", "effect.py": b"print(1)\n"}
        result = derive(packets(bodies, bodies))
        dispositions = {r["current"]["syntax_disposition"] for r in result["rows"]}
        self.assertEqual(dispositions, {"unavailable", "unindexed", "parse_failed", "parsed"})
        self.assertTrue(all(r["current"]["label"] is None for r in result["rows"]))

    def test_utf8_spans_and_literal_template_clones(self):
        a = "def λ(n: int) -> int:\n    return n + 1\n".encode()
        b = "def λ(n: int) -> int:\n    return n + 2\n".encode()
        result = derive(packets({"a.py": a, "b.py": b}, {"a.py": a, "b.py": b}))
        self.assertEqual(len(result["previous_templates"]), 1)
        self.assertEqual(result["previous_clones"], [])

    def test_coherent_ledger_classification_forgery(self):
        self.refuse_packet(lambda p: p["envelope"]["value"]["ledger"][0].update(classification="retained"), "complete source ledger")

    def test_coherent_missing_ledger_member(self):
        self.refuse_packet(lambda p: p["envelope"]["value"]["ledger"].pop(), "complete source ledger")

    def test_coherent_duplicate_ledger_member(self):
        self.refuse_packet(lambda p: p["envelope"]["value"]["ledger"].append(copy.deepcopy(p["envelope"]["value"]["ledger"][0])), "complete source ledger")

    def test_coherent_coverage_and_boolean_alias(self):
        for field, value in (("union_entries", 9), ("previous_entries", True)):
            with self.subTest(field=field):
                self.refuse_packet(lambda p, field=field, value=value: p["envelope"]["value"]["coverage"].update({field: value}), "complete coverage")
        self.refuse_packet(lambda p: p["envelope"]["value"]["coverage"]["classifications"].update(changed=True), "complete coverage")

    def test_coherent_authority_escalation(self):
        self.refuse_packet(lambda p: p["envelope"]["value"]["authority"].update(training_executed=True), "authority ceiling")
        self.refuse_packet(lambda p: p["envelope"]["value"].update(numerical_reuse=True), "authority ceiling")

    def test_wrong_head_or_predecessor(self):
        self.refuse_packet(lambda p: p["envelope"]["value"]["current_head"].update(generation=True), "head identity")
        self.refuse_packet(lambda p: p["envelope"]["value"]["current_publication_receipt"]["previous_head"].update(generation=8), ".")

    def test_policy_budget_refused(self):
        self.refuse_packet(lambda p: p["envelope"]["value"]["capture_policy"].update(max_entries=513), "policy")

    def test_missing_raw_source_or_ast(self):
        for field in ("sources", "asts"):
            with self.subTest(field=field):
                self.refuse_packet(lambda p, field=field: p[field].clear(), "closure")

    def test_same_size_raw_source_tamper(self):
        self.refuse_packet(lambda p: p["sources"].update({audit.cid(OLD): OLD.replace(b"+", b"-")}), "source CID")

    def test_coherently_rehashed_ast_reference_forgery(self):
        def mutate(side, path, value):
            if side == "current" and path == "calc.py":
                value["references"][-1]["name"] = "counterparty"
        with self.assertRaisesRegex(audit.Refused, "reference population"):
            derive(packets(ast_mutator=mutate))

    def test_coherently_rehashed_ast_span_forgery(self):
        def mutate(side, path, value):
            if side == "current" and path == "calc.py":
                value["references"][-1]["span"] = location(NEW, 0, 1)
        with self.assertRaisesRegex(audit.Refused, "reference population"):
            derive(packets(ast_mutator=mutate))

    def test_coherently_rehashed_ast_signature_forgery(self):
        def mutate(side, path, value):
            if side == "current" and path == "calc.py":
                value["symbols"][0]["signature"]["parameters"][0]["annotation"] = "bool"
        with self.assertRaisesRegex(audit.Refused, "signature annotations"):
            derive(packets(ast_mutator=mutate))

    def test_coherently_rehashed_snapshot_and_entry_future_versions(self):
        for args, reason in (({"snapshot_schema": "ipfs-datasets.software-contracts.semantic-repository-snapshot@5"}, "snapshot schema"),
                             ({"entry_schema": "ipfs-datasets.software-contracts.semantic-snapshot-entry@4"}, "entry schema")):
            with self.subTest(args=args), self.assertRaisesRegex(audit.Refused, reason):
                derive(packets(**args))

    def test_coherently_rehashed_signature_boolean_position(self):
        def mutate(side, path, value):
            if side == "current" and path == "calc.py":
                value["symbols"][0]["signature"]["parameters"][0]["position"] = False
        with self.assertRaisesRegex(audit.Refused, "signature annotations"):
            derive(packets(ast_mutator=mutate))

    def test_coherently_rehashed_ast_scope_forgery(self):
        def mutate(side, path, value):
            if side == "current" and path == "calc.py":
                value["references"][0]["scope_id"] = "missing-scope"
        with self.assertRaisesRegex(audit.Refused, "scope closure"):
            derive(packets(ast_mutator=mutate))

    def test_coherently_rehashed_ast_provenance_forgery(self):
        def mutate(side, path, value):
            if side == "current" and path == "calc.py":
                value["provenance"]["repository_id"] = "other"
        with self.assertRaisesRegex(audit.Refused, "source provenance"):
            derive(packets(ast_mutator=mutate))

    def test_full_inert_reader_golden_roles_and_population(self):
        f = Fixture(self.base)
        report = f.run()
        self.assertEqual(report["union_member_count"], 4)
        self.assertEqual(report["historical_content_match_role_counts"], {"train": 1, "replay": 1})
        self.assertEqual(report["current_exposure_unknown_member_count"], 3)
        self.assertTrue(all(report[x] is True for x in audit.TRUE_FLAGS))
        self.assertTrue(all(report[x] is False for x in audit.FALSE_FLAGS))
        self.assertEqual(len(list(f.output.iterdir())), report["input_file_count"] + 1)
        self.assertFalse(report["physical_presence_live_replayed"])
        self.assertEqual(report["ignored_removed_count"], 1)
        self.assertEqual(report["original_failed_ignored_observation"]["error"], "original authored failure")

    def test_coherent_historical_role_mismatch(self):
        f = Fixture(self.base)
        f.values["historical_cohort_report"]["retained_lineage_selection_ledger"][0]["selections"][0]["role"] = "canary"
        f.refresh()
        with self.assertRaisesRegex(audit.Refused, "selection role binding"):
            f.run()

    def test_coherent_historical_source_mismatch(self):
        f = Fixture(self.base)
        f.values["historical_cohort_report"]["members"][0]["source_sha256"] = audit.sha(NEW)
        f.refresh()
        with self.assertRaisesRegex(audit.Refused, "target source binding"):
            f.run()

    def test_zero_historical_content_matches_still_unknown(self):
        f = Fixture(self.base)
        h = f.values["historical_cohort_report"]
        h["members"][0]["source_sha256"] = audit.sha(b"other exact body")
        for observation in h["retained_lineage_selection_ledger"][0]["target_observations"]:
            observation["source_sha256"] = h["members"][0]["source_sha256"]
        f.refresh()
        result = f.run()
        self.assertEqual(result["historical_content_match_member_count"], 0)
        self.assertTrue(result["current_exposure_unknown"])
        self.assertFalse(result["heldout_independence_verified"])

    def test_historical_quality_escalation_refused(self):
        f = Fixture(self.base)
        f.values["historical_cohort_report"]["candidate_model_qualified"] = True
        f.refresh()
        with self.assertRaisesRegex(audit.Refused, "authority ceiling"):
            f.run()

    def test_outer_repin_cannot_replace_fixed_original(self):
        f = Fixture(self.base)
        original = dict(f.anchors)
        f.values["source_result"]["qualified"] = False
        f.refresh()
        with patch.dict(audit.ANCHORS, original, clear=True), self.assertRaisesRegex(audit.Refused, "fixed original outer anchor"):
            audit.evaluate(f.input, f.output)

    def test_reference_disagreement_after_child_outer_repins(self):
        f = Fixture(self.base)
        path = f.main / "reference-source-delta.json"
        body = json.loads(path.read_bytes())
        body["value"]["removal_scope"] = "invented absence"
        body["artifact_cid"] = audit.object_cid(body["value"])
        f.values["source_audit"]["guarded_artifacts"][path.name] = f.write(path, body)
        f.refresh()
        with self.assertRaisesRegex(audit.Refused, "full value equivalence"):
            f.run()

    def test_physical_absence_and_failed_observation_escalation(self):
        f = Fixture(self.base)
        f.values["ignored_result"]["physical_absence_verified"] = True
        f.refresh()
        with self.assertRaisesRegex(audit.Refused, "ignored capture scope"):
            f.run()
        f.values["ignored_result"]["physical_absence_verified"] = False
        f.values["failed_ignore_result"]["qualified"] = True
        f.refresh()
        with self.assertRaisesRegex(audit.Refused, "original failed"):
            f.run()

    def test_closed_manifest_strict_json_and_typed_descriptor(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":999999999999999999999}', b'{"x":"\\ud800"}'):
            with self.subTest(raw=raw), self.assertRaises((audit.Refused, UnicodeError)):
                audit.document(raw)
        with self.assertRaises(audit.Refused):
            audit.descriptor(dict(path="/tmp/example", sha256="0" * 64, size_bytes=True))
        f = Fixture(self.base)
        doc = json.loads(f.input.read_bytes())
        doc["extra"] = True
        f.write(f.input, doc)
        with self.assertRaisesRegex(audit.Refused, "closed source delta analysis input"):
            f.run()

    def test_preallocation_and_report_serialization_bounds(self):
        f = Fixture(self.base)
        with patch.object(audit, "MAX_ORIGINALS", 2), self.assertRaisesRegex(audit.Refused, "reservation budget"):
            f.run()
        self.assertFalse(f.output.exists())
        with patch.object(audit, "MiB", 32), self.assertRaisesRegex(audit.Refused, "report allocation bound"):
            audit.report_bytes({"long": "a" * 200})

    def test_symlink_and_hardlink_input_alias_refusal(self):
        f = Fixture(self.base)
        path = f.paths["failed_ignore_result"]
        raw = path.read_bytes()
        other = self.base / "alias"
        other.write_bytes(raw)
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(audit.Refused, "canonical selected"):
            f.run()
        r = audit.Reads()
        pin = dict(sha256=audit.sha(raw), size_bytes=len(raw))
        r.reserve(other, pin, 65536)
        link = self.base / "hardlink"
        os.link(other, link)
        with self.assertRaisesRegex(audit.Refused, "hardlink"):
            r.reserve(link, pin, 65536)

    def test_fresh_output_and_input_scope_protection(self):
        f = Fixture(self.base)
        f.output = f.input.parent / "overlap"
        with self.assertRaisesRegex(audit.Refused, "overlaps"):
            f.run()
        f.output = self.base / "already"
        f.output.mkdir()
        with self.assertRaisesRegex(audit.Refused, "fresh canonical"):
            f.run()

    def test_reachable_late_original_drift(self):
        f = Fixture(self.base)
        original, count = audit.Reads.stable, [0]
        def drift(reads):
            count[0] += 1
            if count[0] == 2:
                p = f.paths["failed_ignore_result"]
                p.write_bytes(p.read_bytes().replace(b"failure", b"FAILURE"))
            original(reads)
        with patch.object(audit.Reads, "stable", drift), self.assertRaisesRegex(audit.Refused, "late original"):
            f.run()
        self.assertEqual(count[0], 2)
        self.assertFalse((f.output / "source_delta_analysis.json").exists())

    def test_reachable_late_copy_drift(self):
        f = Fixture(self.base)
        original, hit = audit.population, []
        def drift(root, expected):
            hit.append(True)
            p = root / sorted(expected)[0]
            body = p.read_bytes()
            p.write_bytes(bytes([body[0] ^ 1]) + body[1:])
            original(root, expected)
        with patch.object(audit, "population", drift), self.assertRaisesRegex(audit.Refused, "retained output body drift"):
            f.run()
        self.assertEqual(hit, [True])

    def test_reachable_late_extra_file_and_root_alias(self):
        for kind in ("extra", "alias"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                f = Fixture(Path(temporary).resolve())
                original, hit = audit.population, []
                def drift(root, expected, hit=hit, kind=kind, original=original):
                    hit.append(True)
                    if kind == "extra":
                        (root / "unexpected").write_bytes(b"extra")
                    else:
                        moved = root.with_name("moved")
                        root.rename(moved)
                        root.symlink_to(moved, target_is_directory=True)
                    original(root, expected)
                with patch.object(audit, "population", drift), self.assertRaises(audit.Refused):
                    f.run()
                self.assertEqual(hit, [True])

    def test_reachable_postpublication_report_drift(self):
        f = Fixture(self.base)
        original, count = audit.population, [0]
        def drift(root, expected):
            count[0] += 1
            if count[0] == 2:
                p = root / "source_delta_analysis.json"
                body = p.read_bytes()
                p.write_bytes(body.replace(b'"passed"', b'"failed"', 1))
            original(root, expected)
        with patch.object(audit, "population", drift), self.assertRaisesRegex(audit.Refused, "retained output body drift"):
            f.run()
        self.assertEqual(count[0], 2)

    def test_reachable_canonical_output_root_replacement(self):
        f = Fixture(self.base)
        original, hit = audit.population, []
        def replacement(root, expected):
            hit.append(True)
            root.rename(root.with_name("old-root"))
            root.mkdir()
            for name, raw in expected.items():
                (root / name).write_bytes(raw)
            original(root, expected)
        with patch.object(audit, "population", replacement), self.assertRaisesRegex(audit.Refused, "root identity drift"):
            f.run()
        self.assertEqual(hit, [True])
        self.assertFalse((f.output / "source_delta_analysis.json").exists())

    def test_cross_path_pair_budget_and_nonregular_input(self):
        bodies = {f"clone-{i:02}.py": OLD for i in range(66)}
        with self.assertRaisesRegex(audit.Refused, "cross-path content pair allocation budget"):
            derive(packets(bodies, bodies))
        fifo = self.base / "fifo"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(audit.Refused, "regular exact selected"):
            audit.Reads().reserve(fifo, dict(sha256="0" * 64, size_bytes=0), 65536)


if __name__ == "__main__":
    unittest.main()
