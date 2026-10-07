"""Pure postfit source/denominator/barrier tests; no numerical owner imports."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "source/evaluate_dual_bank_replay.py"
spec = importlib.util.spec_from_file_location("balanced_postfit_pure_subject", SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


def fixture(prefix="original"):
    rule = dict(actor="actor", action="deliver", modality="O", object="notice",
        conditions=[], exceptions=[], temporal=[])
    documents = {n: dict(rules=[deepcopy(rule) for _ in range(n)]) for n in (1, 2, 4, 8)}
    vocabulary = ["<pad>", "<bos>", "<eos>"] + [json.dumps(doc, separators=(",", ":"))
        for doc in documents.values()] + [json.dumps("unused" + str(i)) for i in range(25)]
    sources = []; refs = []
    for count, token in zip((1, 2, 4, 8), range(3, 7)):
        for index in range(12):
            text = "\n\n".join(prefix + " source " + str(count) + " " + str(index) + " " + str(i)
                for i in range(count))
            row = dict(id=prefix + str(len(sources)), source_text=text, input=[1.] + [0.] * 383)
            sources.append(row)
            refs.append(dict(id=row["id"], source_text=text, target_ids=[1, token, 2],
                target=deepcopy(documents[count]), clause_count=count))
    return sources, refs, dict(target_vocabulary=vocabulary)


class ReferenceContracts(unittest.TestCase):
    def setUp(self):
        self.rows, self.refs, self.codec = fixture()

    def test_reference_order_join_keeps_48_rows_and180_full7facet_rules(self):
        refs = subject.bind_references(self.rows, list(reversed(self.refs)), self.codec)
        self.assertEqual([r["id"] for r in refs], [r["id"] for r in self.rows])
        self.assertEqual(sum(r["clause_count"] for r in refs), 180)
        self.assertTrue(all(set(rule) == set(subject.FACETS) for r in refs for rule in r["target"]["rules"]))

    def test_changed_source_target_count_or_nonempty_qualifier_refused(self):
        for kind in ("text", "token", "count", "qualifier", "duplicate", "missing"):
            refs = deepcopy(self.refs)
            if kind == "text":
                refs[0]["source_text"] += " changed"
            elif kind == "token":
                refs[0]["target_ids"] = [1, 4, 2]
            elif kind == "count":
                refs[0]["target"]["rules"] *= 2
            elif kind == "qualifier":
                refs[0]["target"]["rules"][0]["conditions"] = ["if"]
            elif kind == "duplicate":
                refs[-1] = deepcopy(refs[0])
            else:
                refs.pop()
            with self.assertRaises(ValueError):
                subject.bind_references(self.rows, refs, self.codec)

    def test_original_targets_are_only_decoded_by_explicit_posthoc_function(self):
        labelled = [dict(row, target_ids=ref["target_ids"]) for row, ref in zip(self.rows, self.refs)]
        derived = subject.original_train_references(labelled, self.codec)
        bound = subject.bind_references(self.rows, derived, self.codec)
        self.assertEqual([r["target"] for r in bound], [r["target"] for r in self.refs])


class JoinContracts(unittest.TestCase):
    def setUp(self):
        _, self.refs, _ = fixture()
        self.fidelity = dict(rows=[dict(id=r["id"], generated_ir=deepcopy(r["target"])) for r in self.refs])
        self.scalar = dict(complete=True, events=[], unscored_sites=[],
            unvisited_reference_sites=[dict(id=r["id"], slot=slot, field=field) for r in self.refs
                for slot in range(r["clause_count"]) for field in subject.FIELDS])

    def event(self, identity, slot, field):
        return dict(id=identity, slot=slot, field=field, target_token_id=3, actual_next_token_id=4,
            position=10, source=dict(argmax_token_id=3, target_margin=.1),
            recurrent=dict(argmax_token_id=4, target_margin=-.2), combined=dict(argmax_token_id=4, target_margin=-.1))

    def test_missing_generation_sites_keep_all720_denominators_and_no_false_correctness(self):
        value = subject.join_scalar_formula(self.scalar, self.fidelity, self.refs)
        self.assertEqual(len(value["rows"]), 180)
        for counts in value["per_field"].values():
            self.assertEqual(counts["reference_sites"], 180)
            self.assertEqual(counts["unvisited"], 180)
            self.assertEqual(counts["source_correct"], 0)
        self.assertTrue(all(value[k] is False for k in subject.FALSE))

    def test_source_correct_action_wrong_remains_explicit_and_unavailable_is_not_double_counted(self):
        identity = self.refs[0]["id"]
        self.scalar["events"] = [self.event(identity, 0, "action")]
        self.scalar["unvisited_reference_sites"] = [r for r in self.scalar["unvisited_reference_sites"]
            if not (r["id"] == identity and r["slot"] == 0 and r["field"] == "action")]
        self.scalar["unscored_sites"] = [dict(id=identity, slot=0, field="actor", reason="unavailable")]
        self.fidelity["rows"][0]["generated_ir"]["rules"][0]["action"] = "approve"
        value = subject.join_scalar_formula(self.scalar, self.fidelity, self.refs)
        self.assertEqual(value["per_field"]["action"]["source_correct_formula_wrong"], 1)
        self.assertEqual(value["per_field"]["actor"]["unavailable"], 1)
        self.assertEqual(value["per_field"]["actor"]["unvisited"], 179)
        self.assertLess(value["rows"][0]["fields"]["action"]["combined"]["target_margin"], 0.)

    def test_duplicate_or_foreign_event_and_dropped_denominator_refused(self):
        for kind in ("duplicate", "foreign", "dropped"):
            scalar = deepcopy(self.scalar)
            if kind == "dropped":
                scalar["unvisited_reference_sites"].pop()
            else:
                event = self.event("foreign" if kind == "foreign" else self.refs[0]["id"], 0, "actor")
                scalar["events"] = [event, deepcopy(event)] if kind == "duplicate" else [event]
            with self.assertRaises(ValueError):
                subject.join_scalar_formula(scalar, self.fidelity, self.refs)

    def test_malformed_emitted_rule_container_keeps_failure_denominators(self):
        for emitted in (None, {"rules": None}, {"rules": 1}, {"rules": [True]}):
            fidelity = deepcopy(self.fidelity)
            fidelity["rows"][0]["generated_ir"] = emitted
            value = subject.join_scalar_formula(self.scalar, fidelity, self.refs)
            self.assertEqual(len(value["rows"]), 180)
            self.assertTrue(all(r["reference_sites"] == 180 for r in value["per_field"].values()))
            self.assertTrue(all(r["formula_field_correct"] is False for r in value["rows"][0]["fields"].values()))


class BarrierContracts(unittest.TestCase):
    def records(self, root):
        records = []
        for arm in subject.ARMS:
            for role in subject.ROLES:
                for cohort in subject.COHORTS:
                    path = root / (arm + "-" + role + "-" + cohort + ".json")
                    path.write_text("{}\n")
                    ref = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    records.append(dict(arm=arm, role=role, cohort=cohort, prediction_fsynced=True,
                        physical_panel_computed=True, trace_ref=ref, predictions_ref=ref))
        return records

    def test_all8_durable_panels_required_before_reference_barrier(self):
        with tempfile.TemporaryDirectory() as directory:
            records = self.records(Path(directory))
            subject.verify_barrier(records)
            for kind in ("missing", "duplicate", "foreign", "not_fsynced", "alias_skipped"):
                changed = deepcopy(records)
                if kind == "missing":
                    changed.pop()
                elif kind == "duplicate":
                    changed[-1] = deepcopy(changed[0])
                elif kind == "foreign":
                    changed[0]["cohort"] = "implicit_cohort"
                elif kind == "not_fsynced":
                    changed[0]["prediction_fsynced"] = False
                else:
                    changed[0]["physical_panel_computed"] = False
                with self.assertRaises(ValueError):
                    subject.verify_barrier(changed)
            Path(records[0]["trace_ref"]["path"]).write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "changed panel"):
                subject.verify_barrier(records)

    def test_explicit_v3_reference_parse_follows_barrier_and_no_fit_call_exists(self):
        tree = ast.parse(SOURCE.read_text())
        execute = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute")
        barrier_line = next(n.lineno for n in ast.walk(execute) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "verify_barrier")
        parse_line = next(n.lineno for n in ast.walk(execute) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "bound"
            and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == "v3_path")
        self.assertGreater(parse_line, barrier_line)
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ("train", "train_candidate", "step", "produce_width")
            for n in ast.walk(execute)))


class TraceContracts(unittest.TestCase):
    def setUp(self):
        self.rows, _, self.codec = fixture()
        self.contexts = {r["id"]: dict(source_sha256=hashlib.sha256(r["source_text"].encode()).hexdigest()) for r in self.rows}
        self.state = dict(tensor_sha256="frozen")
        self.transform = dict(mode="none")
        trace = dict(complete=True, sample_count=48, dimension=384, model_tensor_sha256="frozen",
            source_rows_sha256=subject.digest(self.rows), source_contexts_sha256=subject.digest(self.contexts),
            codec_sha256=subject.digest(self.codec), input_transform_sha256=subject.digest(self.transform),
            vocabulary_size=32, generation_temperature=0, max_target_tokens=512, batch_size=8,
            predictions=[dict(id=r["id"], token_ids=[], eos_reached=False, generation_status="output_limit") for r in self.rows])
        trace.update({k: True for k in ("source_only", "full_vocabulary_retained", "decomposition_exact",
            "caller_state_preserved", "hooks_removed", "complete_rollout_before_reference_scoring")})
        trace.update({k: False for k in ("reference_count_access", "reference_prefix_access",
            "reference_documents_passed_to_model", "inventory_access", "source_context_target_access",
            "syntax_mask", "forced_closure", "model_copied", "qualified", "admitted", "proof_authority",
            "source_semantics_verified", "lake_executed", "native_family_validation_performed")})
        trace.update(extra_model_passes=0, source_head_extra_evaluations=0, optimizer_steps=0)
        trace["trace_sha256"] = subject.digest(trace)
        self.trace = trace

    def test_complete_mask_free_same_pass_trace_accepted(self):
        subject.verify_trace(self.trace, self.rows, self.contexts, self.state, self.codec, self.transform)

    def test_resealed_reference_access_mask_pass_count_or_state_change_refused(self):
        for key, value in (("syntax_mask", True), ("reference_prefix_access", True),
            ("source_head_extra_evaluations", 1), ("optimizer_steps", False),
            ("model_tensor_sha256", "another"), ("sample_count", 47), ("qualified", True)):
            trace = deepcopy(self.trace); trace[key] = value
            trace["trace_sha256"] = subject.digest({k: v for k, v in trace.items() if k != "trace_sha256"})
            with self.assertRaises(ValueError):
                subject.verify_trace(trace, self.rows, self.contexts, self.state, self.codec, self.transform)

    def test_changed_predictions_or_context_provenance_refused(self):
        trace = deepcopy(self.trace); trace["predictions"][0]["id"] = "foreign"
        trace["trace_sha256"] = subject.digest({k: v for k, v in trace.items() if k != "trace_sha256"})
        with self.assertRaises(ValueError):
            subject.verify_trace(trace, self.rows, self.contexts, self.state, self.codec, self.transform)


class SourceCohortContracts(unittest.TestCase):
    def setUp(self):
        def build(rows, cache):
            lookup = {r["source_text"]: r["input"] for r in cache}
            if len(lookup) != len(cache):
                raise ValueError("duplicate source cache")
            return {r["id"]: dict(source_sha256=hashlib.sha256(r["source_text"].encode()).hexdigest(),
                segments=[dict(source_text=t, vector=lookup[t]) for t in r["source_text"].split("\n\n")]) for r in rows}
        self.owner = SimpleNamespace(build_source_contexts=build,
            validate_contexts=lambda rows, contexts: dict(dimension=384))
        def packet(prefix):
            rows, refs, _ = fixture(prefix)
            sources = [{k: r[k] for k in ("id", "source_text")} for r in rows]
            texts = sorted({t for r in rows for t in r["source_text"].split("\n\n")})
            cache = [dict(id="clause:" + hashlib.sha256(t.encode()).hexdigest(), source_text=t,
                input=[1.] + [0.] * 383) for t in texts]
            data = dict(dimension=384, complete=True, targets_attached=False, rows=rows,
                source_contexts=build(sources, cache), clause_cache=cache)
            data["inputs_sha256"] = subject.digest(data)
            return sources, rows, refs, cache, data
        original = packet("original"); normative = packet("normative"); balanced = packet("balanced"); v3 = packet("v3")
        self.lane = dict(rows=dict(train=[dict(r, target_ids=ref["target_ids"]) for r, ref in zip(original[1], original[2])]),
            source_contexts=dict(train=original[4]["source_contexts"]))
        prior = dict(exposed_v3=v3[0], **{"p" + str(i): [] for i in range(12)})
        self.control = dict(prior_sources_by_dataset=prior, source_inputs=normative[4],
            evaluation_vectors_by_dataset=dict(exposed_v3=v3[1] + v3[3]))
        self.balanced = dict(prior_sources_by_dataset=dict(prior, current_normative_train=normative[0],
            exposed_v3_primary=v3[0], sealed60_development_primary=[]), source_inputs=balanced[4])

    def test_four_separate_source_only_cohorts_use_existing_vectors_without_fallback(self):
        value = subject.prepare_cohorts(self.lane, self.control, self.balanced, self.owner)
        self.assertEqual(set(value), set(subject.COHORTS))
        self.assertEqual(sum(len(c["rows"]) for c in value.values()), 192)
        self.assertTrue(all(set(r) == {"id", "source_text", "input"} for c in value.values() for r in c["rows"]))
        self.assertTrue(all(sum(len(r["source_text"].split("\n\n")) for r in c["rows"]) == 180 for c in value.values()))

    def test_missing_v3_vector_and_conflicting_duplicate_refused(self):
        changed = deepcopy(self.control)
        text = changed["prior_sources_by_dataset"]["exposed_v3"][12]["source_text"]
        changed["evaluation_vectors_by_dataset"]["exposed_v3"] = [r for r in
            changed["evaluation_vectors_by_dataset"]["exposed_v3"] if r["source_text"] != text]
        with self.assertRaisesRegex(ValueError, "complete exact-text"):
            subject.prepare_cohorts(self.lane, changed, self.balanced, self.owner)
        changed = deepcopy(self.control)
        row = deepcopy(changed["evaluation_vectors_by_dataset"]["exposed_v3"][0]); row["input"] = [0., 1.] + [0.] * 382
        changed["evaluation_vectors_by_dataset"]["exposed_v3"].append(row)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            subject.prepare_cohorts(self.lane, changed, self.balanced, self.owner)


class DualReplayContracts(unittest.TestCase):
    def test_one_arm_eight_complete_physical_panels_and_no_qualification(self):
        self.assertEqual(subject.ARMS, ("dual-bank-retention-ce",))
        self.assertEqual(subject.PROFILE["logical_panels"], 8)
        self.assertEqual(subject.PROFILE["physical_panels"], 8)
        self.assertTrue(all(subject.PROFILE[k] is False for k in subject.FALSE))
        manifest = dict(inputs={})
        plan = dict(subject.PROFILE, input_sha256={})
        subject.validate_plan(plan, manifest)
        for key, value in (("physical_panels", 4), ("logical_panels", 16), ("qualified", True)):
            changed = dict(plan, **{key: value})
            with self.assertRaises(ValueError):
                subject.validate_plan(changed, manifest)

    def test_two_authentic_bank_bindings_required_and_no_extra_selector_bank(self):
        envelopes = {role: dict(source=role) for role in ("control", "balanced")}
        for envelope in envelopes.values():
            envelope["payload_sha256"] = subject.digest(envelope)
        run = dict(source_inventory_sha256_by_role={r: e["payload_sha256"] for r, e in envelopes.items()}, initial_tensor_sha256="parent")
        subject.verify_source_inventories(run, envelopes, "parent")
        for kind in ("changed_source", "missing_bank", "extra_bank", "wrong_parent"):
            copied, altered = deepcopy(envelopes), deepcopy(run)
            if kind == "changed_source":
                copied["balanced"]["source"] = "different"
            elif kind == "missing_bank":
                altered["source_inventory_sha256_by_role"].pop("balanced")
            elif kind == "extra_bank":
                altered["source_inventory_sha256_by_role"]["exposed_v3"] = "another"
            else:
                altered["initial_tensor_sha256"] = "another"
            with self.assertRaises(ValueError):
                subject.verify_source_inventories(altered, copied, "parent")


if __name__ == "__main__":
    unittest.main()
