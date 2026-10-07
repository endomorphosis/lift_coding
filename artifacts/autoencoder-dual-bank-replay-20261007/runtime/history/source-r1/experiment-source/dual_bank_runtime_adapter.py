"""Private same-budget replay; importing performs no tensor or model work.

Both authentic validators and caches retain ownership of their own 180 sources.
The existing trainer computes its unchanged objective and selection; only its
relative auxiliary owner and an explicitly reconciled metadata receipt differ.
This authored fixture diagnostic provides no semantic or Lean admission.
"""
import hashlib
import json
import math
from collections import Counter
from copy import deepcopy
from types import ModuleType, SimpleNamespace

ROLES = ("control", "balanced")
SCHEMA = "dual-authored-wording-modality-bank/v1"
CACHE_SCHEMA = "dual-authored-wording-modality-cache/v1"
LOSS_SCHEMA = "dual-authored-wording-modality-loss/v1"
FALSE = dict(qualified=False, admitted=False, proof_authority=False,
    source_semantics_verified=False, formalized=False, checkpoint_promoted=False,
    lake_executed=False, roundtrip_ok=False, encoder_executed=False,
    historical_linguistic_teacher_modified=False, selection_performed=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def source_inventory_pair(inventories):
    require(type(inventories) is dict and set(inventories) == set(ROLES),
        "two separately authenticated source inventories required")
    for role in ROLES:
        value = inventories[role]
        require(type(value) is dict and value.get("payload_sha256") == digest(
            {k: v for k, v in value.items() if k != "payload_sha256"}),
            "source inventory payload differs: " + role)
        require(len(value["prior_sources_by_dataset"]) == (13 if role == "control" else 16),
            "distinct authentic source exclusion envelopes required")
    result = dict(schema="dual-authored-wording-source-inventories/v1",
        inventories_by_role=deepcopy(inventories), **FALSE)
    result["payload_sha256"] = digest(result)
    return result


def validate_inventory_pair(value):
    require(type(value) is dict and value.get("schema") == "dual-authored-wording-source-inventories/v1"
        and value.get("payload_sha256") == digest({k: v for k, v in value.items() if k != "payload_sha256"})
        and all(value.get(k) is False for k in FALSE), "closed unqualified dual source envelope required")
    expected = source_inventory_pair(value["inventories_by_role"])
    require(value == expected, "dual source envelope changed")
    return value["inventories_by_role"]


class TensorCache:
    __slots__ = ("_model", "_caches", "_losses", "_draws", "_receipt", "_max_steps")

    def __setattr__(self, name, value):
        raise AttributeError("dual cache pair is immutable")

    @property
    def receipt(self):
        return deepcopy(self._receipt)


def _validate_nested(receipt, draw, *, requires_grad):
    """Validate untouched local receipt, including genuine full32 CE values."""
    require(type(receipt) is dict and type(requires_grad) is bool
        and type(receipt["committed_step"]) is int
        and receipt["committed_step"] == draw["bank_local_committed_step"]
        and receipt["bank_sha256"] == draw["selected_bank_sha256"]
        and receipt["gradient_enabled"] is requires_grad,
        "authentic local step, bank or gradient receipt differs")
    for key in ("indices", "row_ids", "source_sha256", "target_token_ids"):
        require(receipt[key] == draw[key], "authentic scheduled stream differs: " + key)
    require(receipt["strata"] == [dict(modality=m, template=t)
        for m, t in zip(draw["modalities"], draw["templates"], strict=True)], "actual source strata differ")
    require(receipt["full_vocabulary_size"] == 32 and receipt["batch_size"] == 6
        and receipt["source_head_forward_calls"] == 1 and receipt["recurrent_forward_calls"] == 0
        and receipt["count_forward_calls"] == 0 and receipt["loss_field"] == "modality"
        and receipt["source_slot"] == 0
        and all(receipt.get(k) is False for k in ("labels_passed_to_model", "model_copied",
            "sampler_state_advanced", "qualified", "admitted", "proof_authority")),
        "unchanged one-forward full32 authored loss required")
    logits = receipt["full_vocabulary_logits"]
    targets = receipt["target_token_ids"]
    losses = receipt["per_row_cross_entropy"]
    require(type(logits) is list and len(logits) == len(targets) == len(losses) == 6,
        "all six full32 logits/targets/losses required")
    derived = []
    for vector, target, loss in zip(logits, targets, losses, strict=True):
        require(type(vector) is list and len(vector) == 32
            and all(type(v) in (int, float) and math.isfinite(v) for v in vector)
            and type(target) is int and 0 <= target < 32 and type(loss) in (int, float)
            and math.isfinite(loss) and loss >= 0, "finite full32 CE arrays required")
        maximum = max(vector)
        ce = maximum + math.log(sum(math.exp(v - maximum) for v in vector)) - vector[target]
        require(math.isclose(ce, loss, rel_tol=1e-5, abs_tol=2e-6), "full32 loss arithmetic differs")
        derived.append(loss)
    mean = sum(derived) / 6
    require(type(receipt["mean_cross_entropy"]) in (int, float)
        and math.isclose(mean, receipt["mean_cross_entropy"], rel_tol=1e-5, abs_tol=2e-6)
        and receipt["correct"] == sum(max(range(32), key=vector.__getitem__) == target
            for vector, target in zip(logits, targets, strict=True)), "full32 mean/argmax arithmetic differs")
    return receipt


def configure(*, helpers_by_role, expected_banks, schedule, retention_owner):
    """Expose the inherited owner's exact auxiliary interface with two banks.

    `prepare_bank` still calls each genuine profile, rather than trusting its
    prior snapshot. `prepare_tensor_cache` creates exactly two authentic caches
    for the trainer's one working model. No model, tensor or old cache is copied.
    """
    require(type(helpers_by_role) is dict and set(helpers_by_role) == set(ROLES)
        and all(type(helpers_by_role[r]) is ModuleType for r in ROLES)
        and type(expected_banks) is dict and set(expected_banks) == set(ROLES),
        "two loaded authentic helper owners and complete banks required")
    retention_owner.validate_schedule(schedule)
    schedule_json = json.dumps(schedule, sort_keys=True, separators=(",", ":"), allow_nan=False)
    schedule = json.loads(schedule_json)
    helpers_by_role = {r: helpers_by_role[r] for r in ROLES}
    expected_json = {r: json.dumps(expected_banks[r], sort_keys=True,
        separators=(",", ":"), allow_nan=False) for r in ROLES}
    templates = tuple(t for r in ROLES for t in helpers_by_role[r].mixture.authored.TEMPLATES)
    require(len(templates) == len(set(templates)) == 4 and all(
        expected_banks[r]["bank_sha256"] == schedule["bank_sha256"][r] for r in ROLES),
        "four distinct actual template families and scheduled source banks required")
    helper = ModuleType("_private_dual_bank_auxiliary")
    helper.mixture = SimpleNamespace(authored=SimpleNamespace(TEMPLATES=templates))
    helper.TensorCache = TensorCache
    helper.schedule_sha256 = schedule["schedule_sha256"]

    def prepare_bank(training_rows, validation_rows, **kwargs):
        require(set(kwargs) == {"training_references", "validation_references", "source_contexts",
            "codec", "validate_rule", "source_inventory", "deadline"}, "exact inherited bank interface required")
        inventories = validate_inventory_pair(kwargs["source_inventory"])
        banks = {}
        for role in ROLES:
            banks[role] = helpers_by_role[role].prepare_bank(training_rows, validation_rows,
                **dict(kwargs, source_inventory=inventories[role]))
            require(json.dumps(banks[role], sort_keys=True, separators=(",", ":"), allow_nan=False)
                == expected_json[role], "authentic validated bank changed: " + role)
        result = dict(schema=SCHEMA, dimension=384, bank_count=2,
            rows=banks, bank_receipts={r: {k: deepcopy(v) for k, v in banks[r].items() if k != "rows"}
                for r in ROLES}, schedule_sha256=schedule["schedule_sha256"],
            source_inventory_sha256=kwargs["source_inventory"]["payload_sha256"],
            total_unique_sources=360, fake_360_row_bank=False, **FALSE)
        result["bank_sha256"] = digest(result)
        return result

    def check_bank(bank):
        require(type(bank) is dict and bank.get("schema") == SCHEMA
            and bank.get("bank_sha256") == digest({k: v for k, v in bank.items() if k != "bank_sha256"})
            and bank.get("schedule_sha256") == schedule["schedule_sha256"]
            and set(bank["rows"]) == set(ROLES), "sealed explicit two-bank descriptor required")
        require(all(json.dumps(bank["rows"][r], sort_keys=True, separators=(",", ":"), allow_nan=False)
            == expected_json[r] for r in ROLES), "descriptor bank payload differs")

    def estimate_training_work_bytes(bank, *, max_optimizer_steps):
        check_bank(bank)
        require(type(max_optimizer_steps) is int and max_optimizer_steps == 170,
            "unchanged full170 original step capacity required")
        return sum(helpers_by_role[r].estimate_training_work_bytes(bank["rows"][r],
            max_optimizer_steps=max_optimizer_steps) for r in ROLES) + len(schedule_json.encode()) * 4

    def prepare_tensor_cache(torch, model, bank, **kwargs):
        check_bank(bank)
        require(set(kwargs) == {"codec", "input_transform", "seed", "deadline", "max_optimizer_steps"}
            and type(kwargs["seed"]) is int and kwargs["seed"] == 1729
            and type(kwargs["max_optimizer_steps"]) is int and kwargs["max_optimizer_steps"] == 170,
            "exact unchanged authenticated cache interface required")
        caches = tuple(helpers_by_role[r].prepare_tensor_cache(torch, model, bank["rows"][r], **kwargs)
            for r in ROLES)
        for role, cache in zip(ROLES, caches, strict=True):
            require(type(cache) is helpers_by_role[role].TensorCache and cache._model is model
                and cache._max_steps == 170 and cache.receipt["bank_sha256"] == schedule["bank_sha256"][role],
                "each authentic cache must share the one working model")
            for draw in schedule["draws"]:
                if draw["bank_role"] == role:
                    require(list(helpers_by_role[role].select_indices(cache,
                        draw["bank_local_committed_step"])) == draw["indices"],
                        "authentic local sampler differs from exhaustive schedule")
        receipt = dict(schema=CACHE_SCHEMA, schedule_sha256=schedule["schedule_sha256"],
            bank_sha256=bank["bank_sha256"], bank_count=2, authentic_caches_by_role={
                r: cache.receipt for r, cache in zip(ROLES, caches, strict=True)}, max_optimizer_steps=170,
            max_local_uses_per_bank=85, cached_tensor_bytes=sum(c.receipt["cached_tensor_bytes"] for c in caches),
            authentic_cache_handles_retained=True, model_copied=False, tensors_copied=False,
            prepared_caches_mutated=False, **FALSE)
        result = TensorCache()
        for key, value in dict(_model=model, _caches=caches,
            _losses=tuple(helpers_by_role[r].modality_loss for r in ROLES),
            _draws=tuple(json.dumps(d, sort_keys=True, separators=(",", ":")) for d in schedule["draws"]),
            _receipt=receipt, _max_steps=170).items():
            object.__setattr__(result, key, value)
        return result

    def modality_loss(torch, model, cache, *, committed_step, deadline, requires_grad):
        require(type(cache) is TensorCache and cache._model is model
            and type(committed_step) is int and 0 <= committed_step < cache._max_steps
            and type(requires_grad) is bool, "explicit bounded global step and matching working model required")
        draw = json.loads(cache._draws[committed_step])
        index = ROLES.index(draw["bank_role"])
        result = cache._losses[index](torch, model, cache._caches[index],
            committed_step=draw["bank_local_committed_step"], deadline=deadline, requires_grad=requires_grad)
        require(type(result) is dict and set(result) == {"loss", "receipt"}, "authentic loss result required")
        nested = _validate_nested(result["receipt"], draw, requires_grad=requires_grad)
        receipt = dict(schema=LOSS_SCHEMA, global_committed_step=committed_step,
            bank_role=draw["bank_role"], bank_local_committed_step=draw["bank_local_committed_step"],
            selected_bank_sha256=draw["selected_bank_sha256"], schedule_sha256=schedule["schedule_sha256"],
            authentic_receipt=deepcopy(nested), authentic_receipt_sha256=digest(nested),
            local_receipt_relabelled=False, source_head_forward_calls=1,
            sampler_state_advanced=False, **FALSE)
        return dict(loss=result["loss"], receipt=receipt)

    helper.prepare_bank = prepare_bank
    helper.estimate_training_work_bytes = estimate_training_work_bytes
    helper.prepare_tensor_cache = prepare_tensor_cache
    helper.modality_loss = modality_loss
    return helper


def reconcile_report(report, schedule, retention_owner):
    """Derive actual counts from commits; caller must save inherited report first.

    The numerical report is returned unchanged apart from its auxiliary metadata
    and an explicit reconciliation record. Original update receipts and tensor
    choices remain byte-for-byte values. Legacy four-template counters are
    preserved as inapplicable; they never become actual exposure evidence.
    """
    retention_owner.validate_schedule(schedule)
    require(type(report) is dict and "source_training_mixture" not in report,
        "unaltered original decoder/selection stream report required")
    result = deepcopy(report)
    summary = result["paraphrase_modality_auxiliary"]
    require(summary["weight"] == .05 and summary["used_for_selection"] is False
        and summary["decoder_rows_replaced"] is False and summary["normalization_refitted"] is False
        and summary["zero_weight_graph_attached"] is False
        and summary["bank_receipt"]["schema"] == SCHEMA
        and summary["bank_receipt"]["schedule_sha256"] == schedule["schedule_sha256"],
        "explicit same-budget two-bank metadata required")
    updates = result["committed_updates"]
    require(len(updates) == 170 and summary["committed_updates"] == 170
        and summary["committed_clause_presentations"] == 1020
        and summary["positively_supervised_clause_presentations"] == 1020,
        "completed170/1020 positive replay required")
    banks = Counter()
    templates = Counter()
    modalities = Counter()
    source_counts = {r: Counter() for r in ROLES}
    for t, (update, draw) in enumerate(zip(updates, schedule["draws"], strict=True)):
        item = update["paraphrase_modality_auxiliary"]
        receipt = item["receipt"]
        require(item["zero_based_committed_step"] == t and item["weight"] == .05
            and receipt["schema"] == LOSS_SCHEMA and receipt["global_committed_step"] == t
            and receipt["bank_role"] == draw["bank_role"]
            and receipt["bank_local_committed_step"] == draw["bank_local_committed_step"]
            and receipt["selected_bank_sha256"] == draw["selected_bank_sha256"]
            and receipt["schedule_sha256"] == schedule["schedule_sha256"]
            and receipt["local_receipt_relabelled"] is False,
            "explicit dual committed wrapper differs")
        nested = receipt["authentic_receipt"]
        require(receipt["authentic_receipt_sha256"] == digest(nested), "nested authentic receipt changed")
        _validate_nested(nested, draw, requires_grad=True)
        require(math.isclose(item["weighted_loss"], .05 * nested["mean_cross_entropy"],
            rel_tol=1e-5, abs_tol=2e-6), "actual .05 full32 objective term differs")
        banks[draw["bank_role"]] += 1
        templates.update(draw["templates"])
        modalities.update(draw["modalities"])
        source_counts[draw["bank_role"]].update(draw["row_ids"])
    require(dict(banks) == schedule["updates_per_bank"]
        and dict(templates) == schedule["presentations_per_actual_template"]
        and dict(modalities) == schedule["presentations_per_modality"]
        and {r: dict(c) for r, c in source_counts.items()} == schedule["per_source_exposures"],
        "actual committed bank/template/member budgets differ")
    legacy = deepcopy(summary["committed_presentations_per_template"])
    summary.update(schema="dual-authored-wording-training-summary/v1",
        committed_presentations_per_template=dict(templates),
        committed_updates_per_bank=dict(banks), committed_presentations_per_bank={r: 6*n for r, n in banks.items()},
        committed_per_source_exposures={r: dict(c) for r, c in source_counts.items()},
        committed_presentations_per_modality=dict(modalities), schedule_sha256=schedule["schedule_sha256"],
        inherited_single_bank_template_counters=legacy,
        inherited_single_bank_template_counters_applicable=False,
        actual_counts_replayed_from_committed_receipts=True,
        numerical_loss_or_updates_changed=False, **FALSE)
    result["dual_bank_receipt_reconciliation"] = dict(schema="dual-authored-wording-report-reconciliation/v1",
        inherited_report_canonical_sha256=digest(report),
        inherited_report_must_be_saved_separately=True,
        numerical_report_fields_unchanged=True, original_checkpoint_selection_unchanged=True,
        actual_counts_validated=True, **FALSE)
    return result
