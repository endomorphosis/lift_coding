"""Pure/interface tests with synthetic detached handles; no neural model runs."""
import ast
import importlib.util
import math
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    return owner


subject = load("dual_private_runtime_test", ROOT / "experiment-source/dual_bank_runtime_adapter.py")
retention = load("dual_private_retention_test", ROOT / "experiment-source/dual_bank_retention.py")
driver = load("dual_private_driver_test", ROOT / "experiment-source/scripts/ops/autoencoder/benchmark_dual_bank_replay.py")


def seal(value, key):
    value[key] = subject.digest({k: v for k, v in value.items() if k != key})
    return value


def fixture():
    rules = [dict(actor="actor" + str(i), action="deliver", object="notice", modality=m,
        conditions=[], exceptions=[], temporal=[]) for m in retention.MODALITIES for i in range(30)]
    banks, census, declarations = {}, {}, {}
    for role in subject.ROLES:
        templates = [role + "-template0", role + "-template1"]
        rows = []
        for slot in (0, 1):
            for rule in rules:
                text = role + " " + str(slot) + " " + retention.rule_sha(rule)
                sha = retention.text_sha(text)
                rows.append(dict(id="clause:" + sha, source_text=text, source_sha256=sha,
                    target=deepcopy(rule), modality=rule["modality"], template=templates[slot],
                    modality_token_id={"O": 3, "P": 4, "F": 5}[rule["modality"]]))
        rows.sort(key=lambda r: r["id"])
        banks[role] = seal(dict(dimension=384, rows=rows, qualified=False, admitted=False,
            proof_authority=False), "bank_sha256")
        census[role] = [dict(index=i, row_id=r["id"], source_sha256=r["source_sha256"],
            original_rule_sha256=retention.rule_sha(r["target"]), template=r["template"],
            modality=r["modality"], template_slot=templates.index(r["template"])) for i, r in enumerate(rows)]
        declarations[role] = dict(bank_sha256=banks[role]["bank_sha256"], templates=templates)
    orders = {role: [[r["index"] for r in sorted((item for item in census[role]
        if item["modality"] == m and item["template_slot"] == slot),
        key=lambda r: subject.digest([1729, m, slot, r["original_rule_sha256"]]))]
        for m in retention.MODALITIES for slot in (0, 1)] for role in subject.ROLES}
    draws = [dict(step=t, indices={r: [order[t % 30] for order in orders[r]] for r in subject.ROLES},
        original_rule_sha256=[retention.rule_sha(banks["control"]["rows"][order[t % 30]]["target"])
            for order in orders["control"]]) for t in range(170)]
    pairing = seal(dict(schema="balanced-wording-paired-draws/v1", seed=1729, steps=170,
        original_rules_sha256=subject.digest(rules), banks=declarations, census=census, orders=orders,
        draws=draws, qualified=False, admitted=False, proof_authority=False, train_eligible=False), "pairing_sha256")
    schedule = retention.build_schedule(pairing=pairing, banks_by_role=banks, original_rules=rules)
    inventories = {r: seal(dict(prior_sources_by_dataset={str(i): [] for i in range(
        13 if r == "control" else 16)}), "payload_sha256") for r in subject.ROLES}
    return banks, orders, schedule, inventories


class DetachedHandle:
    def __init__(self):
        self._version = 0
        self.requires_grad = False


class AuthenticCache:
    def __init__(self, model, bank, orders):
        self._model = model
        self._max_steps = 170
        self.bank = bank
        self.orders = orders
        self.tensor = DetachedHandle()
        self.receipt = dict(bank_sha256=bank["bank_sha256"], cached_tensor_bytes=100,
            orders=deepcopy(orders))


def fake_helpers(banks, orders):
    """Test doubles expose validators, detached ownership and local loss calls."""
    result = {}
    calls = []
    for role in subject.ROLES:
        helper = ModuleType("authentic_interface_fixture_" + role)
        helper.TensorCache = AuthenticCache
        helper.mixture = SimpleNamespace(authored=SimpleNamespace(TEMPLATES=(role + "-template0", role + "-template1")))
        def prepare_bank(train, validation, _role=role, **kwargs):
            calls.append(("bank", _role, train, validation, kwargs))
            return deepcopy(banks[_role])
        def estimate(bank, max_optimizer_steps):
            return 200
        def prepare_cache(torch, model, bank, _role=role, **kwargs):
            result = AuthenticCache(model, bank, orders[_role])
            calls.append(("cache", _role, model, kwargs, result))
            return result
        def select(cache, step):
            return tuple(order[step % 30] for order in cache.orders)
        def loss(torch, model, cache, *, committed_step, deadline, requires_grad, _role=role):
            calls.append(("loss", _role, committed_step, requires_grad, model))
            if model is not cache._model or cache.tensor._version != 0 or cache.tensor.requires_grad:
                raise ValueError("authentic detached handles changed")
            indices = tuple(order[committed_step % 30] for order in cache.orders)
            rows = [cache.bank["rows"][i] for i in indices]
            targets = [r["modality_token_id"] for r in rows]
            logits = [[3. if i == target else -2. for i in range(32)] for target in targets]
            ce = math.log(1 + 31 * math.exp(-5))
            receipt = dict(schema="authentic-fixture-loss/v1", committed_step=committed_step,
                bank_sha256=cache.bank["bank_sha256"], indices=list(indices),
                row_ids=[r["id"] for r in rows], source_sha256=[r["source_sha256"] for r in rows],
                strata=[dict(modality=r["modality"], template=r["template"]) for r in rows],
                target_token_ids=targets, full_vocabulary_logits=logits, per_row_cross_entropy=[ce]*6,
                mean_cross_entropy=ce, correct=6, full_vocabulary_size=32, batch_size=6,
                source_head_forward_calls=1, recurrent_forward_calls=0, count_forward_calls=0,
                loss_field="modality", source_slot=0, gradient_enabled=requires_grad,
                labels_passed_to_model=False, model_copied=False, sampler_state_advanced=False,
                qualified=False, admitted=False, proof_authority=False)
            return dict(loss=SimpleNamespace(requires_grad=requires_grad, synthetic_loss=ce), receipt=receipt)
        helper.prepare_bank = prepare_bank
        helper.estimate_training_work_bytes = estimate
        helper.prepare_tensor_cache = prepare_cache
        helper.select_indices = select
        helper.modality_loss = loss
        result[role] = helper
    return result, calls


class DualInterfaceContracts(unittest.TestCase):
    def setUp(self):
        self.banks, self.orders, self.schedule, inventories = fixture()
        self.envelope = subject.source_inventory_pair(inventories)
        self.helpers, self.calls = fake_helpers(self.banks, self.orders)
        self.dual = subject.configure(helpers_by_role=self.helpers, expected_banks=self.banks,
            schedule=self.schedule, retention_owner=retention)
        self.kw = dict(training_references=[], validation_references=[], source_contexts={}, codec={},
            validate_rule=lambda _: None, source_inventory=self.envelope, deadline=100.)
        self.descriptor = self.dual.prepare_bank(["train"], ["validation"], **self.kw)
        self.model = object()
        self.cache = self.dual.prepare_tensor_cache(None, self.model, self.descriptor, codec={},
            input_transform={}, seed=1729, deadline=100., max_optimizer_steps=170)

    def run_loss(self, step, grad=True):
        return self.dual.modality_loss(None, self.model, self.cache,
            committed_step=step, deadline=100., requires_grad=grad)

    def make_report(self):
        updates = []
        for t in range(170):
            result = self.run_loss(t)
            updates.append(dict(decoder_row_ids=["original"], count_row_ids=["original"],
                objective=1., paraphrase_modality_auxiliary=dict(zero_based_committed_step=t, weight=.05,
                    base_objective=1., weighted_loss=.05*result["loss"].synthetic_loss, receipt=result["receipt"])))
        return dict(committed_updates=updates, selected_weights_sha256="a"*64,
            paraphrase_modality_auxiliary=dict(weight=.05, bank_receipt={k: v for k, v in self.descriptor.items() if k != "rows"},
                cache_receipt=self.cache.receipt, used_for_selection=False, decoder_rows_replaced=False,
                normalization_refitted=False, zero_weight_graph_attached=False, committed_updates=170,
                committed_clause_presentations=1020, positively_supervised_clause_presentations=1020,
                committed_presentations_per_template={t: 510 for t in self.dual.mixture.authored.TEMPLATES}))

    def test_both_authentic_bank_validators_receive_distinct_envelopes(self):
        bank_calls = [c for c in self.calls if c[0] == "bank"]
        self.assertEqual([c[1] for c in bank_calls], list(subject.ROLES))
        self.assertEqual([len(c[4]["source_inventory"]["prior_sources_by_dataset"]) for c in bank_calls], [13, 16])
        self.assertEqual(self.descriptor["bank_count"], 2)
        self.assertFalse(self.descriptor["fake_360_row_bank"])
        self.assertEqual(len(self.descriptor["rows"]["control"]["rows"]), 180)

    def test_one_model_and_exact_authentic_detached_cache_handles_are_retained(self):
        self.assertTrue(all(c._model is self.model for c in self.cache._caches))
        self.assertEqual(len(self.cache._caches), 2)
        self.assertTrue(all(c[2] is self.model for c in self.calls if c[0] == "cache"))
        self.assertEqual(self.cache.receipt["cached_tensor_bytes"], 200)
        produced = [c[4] for c in self.calls if c[0] == "cache"]
        self.assertTrue(all(owned is produced_cache for owned, produced_cache
            in zip(self.cache._caches, produced, strict=True)))
        with self.assertRaises(AttributeError):
            self.cache._max_steps = 85
        receipt = self.cache.receipt
        receipt["bank_count"] = 9
        self.assertEqual(self.cache.receipt["bank_count"], 2)

    def test_all170_dispatches_cover180_per_bank_and85_local_steps(self):
        seen = {r: Counter() for r in subject.ROLES}
        for t in range(170):
            receipt = self.run_loss(t)["receipt"]
            self.assertEqual(receipt["bank_local_committed_step"], t//2)
            self.assertEqual(receipt["authentic_receipt"]["committed_step"], t//2)
            seen[receipt["bank_role"]].update(receipt["authentic_receipt"]["row_ids"])
        self.assertEqual({r: len(c) for r, c in seen.items()}, {r: 180 for r in subject.ROLES})
        self.assertEqual({r: sum(c.values()) for r, c in seen.items()}, {r: 510 for r in subject.ROLES})
        loss_calls = [c for c in self.calls if c[0] == "loss"]
        self.assertEqual(Counter(c[1] for c in loss_calls), {r: 85 for r in subject.ROLES})
        self.assertTrue(all(c[4] is self.model for c in loss_calls))

    def test_retry_does_not_advance_and_positive_zero_graph_flags_are_explicit(self):
        a = self.run_loss(0, False)
        b = self.run_loss(0, False)
        c = self.run_loss(1, True)
        self.assertEqual(a["receipt"], b["receipt"])
        self.assertFalse(a["loss"].requires_grad)
        self.assertTrue(c["loss"].requires_grad)
        self.assertEqual(c["receipt"]["authentic_receipt"]["committed_step"], 0)
        self.assertFalse(c["receipt"]["sampler_state_advanced"])

    def test_aborted_authentic_forward_does_not_mutate_pair_or_next_local_index(self):
        self.cache._caches[1].tensor._version = 1
        with self.assertRaisesRegex(ValueError, "detached"):
            self.run_loss(1)
        self.cache._caches[1].tensor._version = 0
        result = self.run_loss(1)
        self.assertEqual(result["receipt"]["bank_local_committed_step"], 0)

    def test_boolean_global_step_and_foreign_model_are_refused(self):
        for t in (False, -1, 170):
            with self.assertRaises(ValueError):
                self.run_loss(t)
        with self.assertRaises(ValueError):
            self.dual.modality_loss(None, object(), self.cache, committed_step=0, deadline=100., requires_grad=True)

    def test_payload_and_exclusion_envelope_resealing_cannot_hide_wrong_profiles(self):
        bad = deepcopy(self.envelope)
        del bad["inventories_by_role"]["balanced"]["prior_sources_by_dataset"]["0"]
        seal(bad["inventories_by_role"]["balanced"], "payload_sha256")
        seal(bad, "payload_sha256")
        with self.assertRaisesRegex(ValueError, "exclusion"):
            subject.validate_inventory_pair(bad)
        bad = deepcopy(self.descriptor)
        bad["rows"]["balanced"]["rows"][0]["source_text"] += " changed"
        seal(bad, "bank_sha256")
        with self.assertRaisesRegex(ValueError, "payload"):
            self.dual.estimate_training_work_bytes(bad, max_optimizer_steps=170)

    def test_resealed_descriptor_authority_dimension_bank_count_and_shape_are_refused(self):
        cases = [(key, True) for key in subject.FALSE]
        cases += [("dimension", 768), ("dimension", True), ("bank_count", 3),
            ("bank_count", True), ("fake_360_row_bank", True), ("total_unique_sources", 180),
            ("source_inventory_sha256", "not-a-sha"), ("shortcut_field", True)]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                bad = deepcopy(self.descriptor)
                bad[key] = value
                seal(bad, "bank_sha256")
                with self.assertRaisesRegex(ValueError, "two-bank descriptor"):
                    self.dual.estimate_training_work_bytes(bad, max_optimizer_steps=170)

    def test_resealed_mismatching_authentic_bank_receipt_is_refused(self):
        for value in (True, 0):
            bad = deepcopy(self.descriptor)
            bad["bank_receipts"]["balanced"]["qualified"] = value
            seal(bad, "bank_sha256")
            with self.assertRaisesRegex(ValueError, "two-bank descriptor"):
                self.dual.prepare_tensor_cache(None, self.model, bad, codec={}, input_transform={},
                    seed=1729, deadline=100., max_optimizer_steps=170)

    def test_actual_full32_logits_loss_arithmetic_is_checked(self):
        result = self.run_loss(0)
        bad = deepcopy(result["receipt"]["authentic_receipt"])
        bad["full_vocabulary_logits"][0][31] = 100
        with self.assertRaisesRegex(ValueError, "arithmetic"):
            subject._validate_nested(bad, self.schedule["draws"][0], requires_grad=True)

    def test_external_schedule_mutation_cannot_rebind_immutable_cache_draws(self):
        self.schedule["draws"][1]["bank_local_committed_step"] = 50
        receipt = self.run_loss(1)["receipt"]
        self.assertEqual(receipt["bank_local_committed_step"], 0)
        self.assertEqual(receipt["authentic_receipt"]["committed_step"], 0)

    def test_authentic_private_import_interception_preserves_original_trainer_namespace(self):
        path = Path("external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-r2-20261006/"
            "experiment-source/ipfs_datasets_py/logic/formalization/autoencoder/"
            "normative_wording_modality_auxiliary.py").resolve()
        normative = load("normative_private_interface_test", path)
        raw = ModuleType("fixture.autoencoder.long_span_source_value_training")
        raw.__package__ = "fixture.autoencoder"
        exec("def train():\n from . import paraphrase_modality_auxiliary_training\n"
            " return paraphrase_modality_auxiliary_training\n", raw.__dict__)
        configured = normative.configure_trainer(raw, self.dual)
        self.assertIs(configured.train(), self.dual)
        self.assertIs(raw.train.__globals__, raw.__dict__)
        self.assertIsNot(configured.train.__globals__, raw.__dict__)
        self.assertNotIn("paraphrase_modality_auxiliary_training", raw.__dict__)
        self.assertIs(raw.train.__code__, configured.train.__code__)

    def test_reconcile_preserves_original_report_and_replaces_wrong_legacy_four_template_counts(self):
        original = self.make_report()
        before = deepcopy(original)
        result = subject.reconcile_report(original, self.schedule, retention)
        self.assertEqual(original, before)
        self.assertEqual(result["committed_updates"], before["committed_updates"])
        self.assertEqual(result["selected_weights_sha256"], before["selected_weights_sha256"])
        summary = result["paraphrase_modality_auxiliary"]
        self.assertEqual(summary["committed_updates_per_bank"], {r: 85 for r in subject.ROLES})
        self.assertEqual(set(summary["committed_presentations_per_template"].values()), {255})
        self.assertEqual(set(summary["inherited_single_bank_template_counters"].values()), {510})
        self.assertFalse(summary["inherited_single_bank_template_counters_applicable"])
        self.assertTrue(summary["actual_counts_replayed_from_committed_receipts"])

    def test_corrupt_nested_local_step_or_gradient_receipt_is_refused(self):
        for field, value in (("committed_step", 99), ("gradient_enabled", False)):
            report = self.make_report()
            wrapper = report["committed_updates"][1]["paraphrase_modality_auxiliary"]["receipt"]
            wrapper["authentic_receipt"][field] = value
            wrapper["authentic_receipt_sha256"] = subject.digest(wrapper["authentic_receipt"])
            with self.assertRaises(ValueError):
                subject.reconcile_report(report, self.schedule, retention)


class DriverContracts(unittest.TestCase):
    def test_closed_one_fit_profiles_and_fixed_budgets(self):
        self.assertEqual(driver.TRAINING["fits"], 1)
        self.assertEqual(driver.TRAINING["optimizer_steps_per_fit"], 170)
        self.assertEqual(driver.TRAINING["new_auxiliary_presentations_per_fit"], 1020)
        self.assertEqual(driver.TRAINING["row_presentations_per_fit"], 1220)
        self.assertEqual(driver.TRAINING["target_token_presentations_per_fit"], 112920)
        self.assertEqual(driver.TRAINING["source_value_presentations_per_fit"], 12800)
        self.assertEqual(driver.COMMON["source_updates_per_bank"], 85)
        self.assertEqual(driver.COMMON["source_presentations_per_bank"], 510)
        self.assertEqual(driver.COMMON["temperature"], 0)
        self.assertEqual(driver.COMMON["native_context_tokens"], 512)
        self.assertEqual(len(driver.COMMON["original_panel_names"]), 9)
        self.assertFalse(driver.COMMON["admitted"])

    def test_plan_rejects_type_substitution_extra_profile_keys_or_budget_change(self):
        manifest = {"inputs": {"source": "a"*64}}
        plan = dict(schema="dual-bank-replay-plan/v1", input_sha256=manifest["inputs"],
            preflight_profile=deepcopy(driver.PREFLIGHT), training_profile=deepcopy(driver.TRAINING))
        driver.validate_plan(plan, manifest, "training")
        for field, value in (("fits", True), ("new_auxiliary_presentations_per_fit", 2040), ("hidden_extra", 1)):
            bad = deepcopy(plan)
            bad["training_profile"][field] = value
            with self.assertRaises(ValueError):
                driver.validate_plan(bad, manifest, "training")

    def test_driver_saves_inherited_report_before_reconciliation_and_preserves_original_validator(self):
        tree = ast.parse(Path(driver.__file__).read_text())
        calls = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertTrue(any("training-inherited.json" in c and c.startswith("save(") for c in calls))
        text = Path(driver.__file__).read_text()
        start = text.index('inherited_report = value["report"]')
        saved = text.index('save(folder / "training-inherited.json"', start)
        verified = text.index("owner.validate_original_streams(lane, inherited_report", saved)
        reconciled = text.index("dual.reconcile_report(inherited_report", verified)
        self.assertLess(saved, verified)
        self.assertLess(verified, reconciled)
        self.assertNotIn("owner.validate_auxiliary_report(report", text)
        self.assertIn('for arm_name in ("dual-bank-retention-ce",):', text)


if __name__ == "__main__":
    unittest.main()
