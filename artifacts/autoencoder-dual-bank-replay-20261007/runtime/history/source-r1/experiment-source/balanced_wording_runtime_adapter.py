"""Private, paired TRAIN-wording transport; importing performs no model work.

The inherited source-bank, native-input, detached-cache and full32 loss owners
retain their validators. A new immutable cache changes only declared draw order
and metadata; no prepared cache, tensor, model or canonical default is mutated.
This authored reconstruction diagnostic grants no source/proof qualification.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from types import ModuleType, SimpleNamespace

SCHEMA = "balanced-wording-paired-draws/v1"
SAMPLING = "original-rule-identity-template-slot-six-stratum-cycles/v1"
ROLES = ("control", "balanced")
MODALITIES = ("O", "P", "F")
FALSE = dict(qualified=False, admitted=False, proof_authority=False,
             source_semantics_verified=False, formalized=False,
             checkpoint_promoted=False, train_eligible=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _rule(rule):
    require(type(rule) is dict and set(rule) == {
        "modality", "actor", "action", "object", "conditions", "exceptions", "temporal"},
        "complete unchanged seven-facet rule required")
    require(type(rule["modality"]) is str and rule["modality"] in MODALITIES and all(rule[k] == [] for k in
        ("conditions", "exceptions", "temporal")), "only existing empty-qualifier TRAIN lane")
    return digest(rule)


def build_pairing(control_bank, balanced_bank, *, original_rules,
                  templates_by_role, seed=1729, steps=170):
    """Pair actual source rows using explicit original targets and template slots.

    These are supplied, authored TRAIN labels; the pairing neither infers legal
    meaning nor authenticates external semantic review. Both banks must contain
    every original90 rule exactly once in each of their two declared families.
    """
    require(type(original_rules) is list and len(original_rules) == 90,
            "complete original90 rule census required")
    originals = {_rule(rule): deepcopy(rule) for rule in original_rules}
    require(len(originals) == 90 and Counter(r["modality"] for r in originals.values())
        == Counter({m: 30 for m in MODALITIES}), "unique balanced original90 targets required")
    require(type(templates_by_role) is dict and set(templates_by_role) == set(ROLES),
            "explicit templates for both roles required")
    require(type(seed) is int and seed == 1729 and type(steps) is int and steps == 170,
            "unchanged seed1729 and full170 committed steps required")
    banks, mappings, census = {}, {}, {}
    for role, bank in zip(ROLES, (control_bank, balanced_bank)):
        templates = templates_by_role[role]
        require(type(templates) in (list, tuple) and len(templates) == 2
            and all(type(t) is str and t for t in templates) and len(set(templates)) == 2,
            "two explicit distinct template families required")
        require(type(bank) is dict and bank.get("dimension") == 384
            and bank.get("bank_sha256") == digest({k: v for k, v in bank.items() if k != "bank_sha256"})
            and type(bank.get("rows")) is list and len(bank["rows"]) == 180,
            "complete sealed native384 bank required")
        require([row["id"] for row in bank["rows"]] == sorted({row["id"] for row in bank["rows"]}),
                "authentic sorted unique clause IDs required")
        lookup, rows = {}, []
        for index, row in enumerate(bank["rows"]):
            identity = _rule(row["target"])
            require(identity in originals and row["target"] == originals[identity],
                    "new label outside exact original90 rules")
            require(row["template"] in templates and row["modality"] == row["target"]["modality"],
                    "declared modality/template differs")
            source_sha = hashlib.sha256(row["source_text"].encode()).hexdigest()
            require(row["id"] == "clause:" + source_sha and row["source_sha256"] == source_sha,
                    "source IDs/hashes must remain authentic")
            slot = templates.index(row["template"])
            require((identity, slot) not in lookup, "duplicate original-rule/template occurrence")
            lookup[identity, slot] = index
            rows.append(dict(index=index, row_id=row["id"], source_sha256=source_sha,
                original_rule_sha256=identity, template_slot=slot,
                template=row["template"], modality=row["modality"]))
        require(set(lookup) == {(identity, slot) for identity in originals for slot in (0, 1)},
                "missing original-rule/template occurrence")
        mappings[role], census[role] = lookup, rows
        banks[role] = dict(bank_sha256=bank["bank_sha256"], templates=list(templates))
    identities = tuple(tuple(sorted((identity for identity, rule in originals.items()
        if rule["modality"] == modality), key=lambda identity: digest([seed, modality, slot, identity])))
        for modality in MODALITIES for slot in (0, 1))
    orders = {role: [[mappings[role][identity, slot] for identity in order]
        for (_, slot), order in zip(((m, s) for m in MODALITIES for s in (0, 1)), identities)]
        for role in ROLES}
    draws = []
    for step in range(steps):
        draws.append(dict(step=step, original_rule_sha256=[order[step % 30] for order in identities],
            indices={role: [order[step % 30] for order in orders[role]] for role in ROLES}))
    result = dict(schema=SCHEMA, seed=seed, steps=steps, banks=banks, census=census,
        original_rules_sha256=digest(original_rules), orders=orders, draws=draws,
        rows_per_role=180, presentations_per_role=1020,
        presentations_per_modality={m: 340 for m in MODALITIES},
        source_hashes_relabelled=False, external_review_authenticated=False, **FALSE)
    result["pairing_sha256"] = digest(result)
    return result


def validate_pairing(pairing, bank, *, role):
    require(role in ROLES and type(pairing) is dict and pairing.get("schema") == SCHEMA
        and pairing.get("pairing_sha256") == digest({k: v for k, v in pairing.items() if k != "pairing_sha256"})
        and type(pairing.get("steps")) is int and pairing["steps"] == 170
        and type(pairing.get("seed")) is int and pairing["seed"] == 1729
        and all(pairing.get(k) is False for k in FALSE), "closed unqualified paired draw manifest required")
    require(pairing["banks"][role]["bank_sha256"] == bank["bank_sha256"],
            "pairing belongs to a different source bank")
    require(bank["bank_sha256"] == digest({k: v for k, v in bank.items() if k != "bank_sha256"}),
            "source bank changed after pairing")
    rows = bank["rows"]
    require(len(rows) == len(pairing["census"][role]) == 180, "complete paired row census required")
    for index, (row, item) in enumerate(zip(rows, pairing["census"][role])):
        require(type(item["index"]) is int and item["index"] == index
            and type(item["template_slot"]) is int and item["template_slot"] in (0, 1)
            and pairing["banks"][role]["templates"][item["template_slot"]] == row["template"],
            "paired census position/template slot differs")
        require((row["id"], row["source_sha256"], _rule(row["target"]), row["template"], row["modality"])
            == (item["row_id"], item["source_sha256"], item["original_rule_sha256"], item["template"], item["modality"]),
            "paired row identity changed")
    orders = pairing["orders"][role]
    require(len(orders) == 6 and all(type(order) is list and len(order) == len(set(order)) == 30
        and all(type(i) is int and 0 <= i < 180 for i in order) for order in orders)
        and sorted(i for order in orders for i in order) == list(range(180)),
        "six exhaustive nonoverlapping paired orders required")
    census = pairing["census"][role]
    require(Counter((item["modality"], item["template_slot"]) for item in census)
        == Counter({(m, slot): 30 for m in MODALITIES for slot in (0, 1)}),
        "six complete modality/template-slot strata required")
    canonical = [[item["index"] for item in sorted(
        (r for r in census if (r["modality"], r["template_slot"]) == (m, slot)),
        key=lambda r: digest([1729, m, slot, r["original_rule_sha256"]]))]
        for m in MODALITIES for slot in (0, 1)]
    require(orders == canonical, "canonical original-rule/template-slot ordering differs")
    require(len(pairing["draws"]) == 170, "complete170 draw census required")
    for step, draw in enumerate(pairing["draws"]):
        indices = [order[step % 30] for order in orders]
        require(type(draw["step"]) is int and draw["step"] == step and draw["indices"][role] == indices
            and [_rule(rows[i]["target"]) for i in indices] == draw["original_rule_sha256"],
            "paired schedule or original target exposure changed")
    return orders


def adopt_paired_cache(helper, prepared, bank, pairing, *, role):
    """Construct a fresh immutable cache, reusing exact validated tensor handles."""
    require(type(prepared) is helper.TensorCache, "authentic prepared cache type required")
    orders = validate_pairing(pairing, bank, role=role)
    require(prepared._receipt["bank_sha256"] == bank["bank_sha256"]
        and prepared._receipt["seed"] == 1729 and prepared._max_steps == 170,
        "original validated cache provenance differs")
    require(prepared._rows == tuple((r["id"], r["source_sha256"], r["modality"], r["template"])
        for r in bank["rows"]), "validated cache row/source census differs")
    slots = tuple(helper.TensorCache.__slots__)
    require(set(slots) == {"_model", "_data", "_vectors", "_mask", "_targets", "_orders",
        "_rows", "_fixed", "_versions", "_receipt", "_max_steps"},
        "unchanged authenticated detached-cache interface required")
    tensors = (prepared._data, prepared._vectors, prepared._mask, prepared._targets)
    require(tuple(t._version for t in tensors) == prepared._versions
        and all(not t.requires_grad for t in tensors), "detached tensor handle/version parity required")
    receipt = deepcopy(prepared._receipt)
    receipt.update(orders=deepcopy(orders), sampling=SAMPLING,
        pairing_sha256=pairing["pairing_sha256"], pairing_role=role,
        original_cache_receipt_sha256=digest(prepared._receipt),
        fresh_immutable_cache=True, prepared_cache_mutated=False,
        model_copied=False, tensors_copied=False, source_hashes_relabelled=False)
    result = helper.TensorCache()
    for slot in slots:
        value = receipt if slot == "_receipt" else tuple(tuple(o) for o in orders) if slot == "_orders" else getattr(prepared, slot)
        object.__setattr__(result, slot, value)
    require(all(getattr(result, key) is getattr(prepared, key) for key in slots
        if key not in {"_receipt", "_orders"}), "copied model/tensor handles forbidden")
    require(tuple(t._version for t in tensors) == prepared._versions,
            "tensor changed during immutable cache adoption")
    return result


def renderer_view(authored_owner, mixture_owner):
    """Bind the inherited source-only validators without rebinding the builder.

    The candidate builder retains its original globals and base helpers. Only
    the private mixture-facing view uses the complete authentic scalar source
    owner required by inherited exclusion, normalization and source hashing.
    """
    authentic = mixture_owner.authored.base
    require(type(authentic) is ModuleType and callable(getattr(authentic, "_source", None))
        and callable(getattr(authentic, "_normal", None)), "authentic frozen scalar source validators required")
    renderer = SimpleNamespace(**vars(authored_owner))
    require(callable(getattr(authentic, "text_sha", None)), "authentic frozen source hashing required")
    renderer.base = authentic
    return renderer


def configure_profile(normative_adapter, *, auxiliary_owner, mixture_owner,
                      authored_owner, pairing, role, prior_dataset_names):
    """Use the authentic E validators under explicit private renderer constants."""
    require(type(normative_adapter) is ModuleType and role in ROLES,
            "authenticated loaded E adapter and explicit role required")
    templates = tuple(authored_owner.TEMPLATES)
    require(list(templates) == pairing["banks"][role]["templates"],
            "explicit renderer profile differs from paired template slots")
    require(type(prior_dataset_names) in (list, tuple) and prior_dataset_names
        and all(type(name) is str and name for name in prior_dataset_names)
        and len(set(prior_dataset_names)) == len(prior_dataset_names)
        and (set(authored_owner.REQUIRED_PRIOR_DATASETS) |
             {normative_adapter.FUTURE_SOURCE_INVENTORY}) <= set(prior_dataset_names),
        "complete explicit source-exclusion dataset names required")
    profile = normative_adapter.private_module(normative_adapter, TEMPLATES=templates,
        STRATA=tuple((m, t) for m in MODALITIES for t in templates),
        SCHEMA="training-balanced-wording-modality-bank/v1")
    renderer = renderer_view(authored_owner, mixture_owner)
    # Retain separately declared, reviewed aliases as full census members. The
    # inherited exact-set equality now checks all declared banks; authentic
    # authored build() still validates its own mandatory/allowed inventories.
    renderer.REQUIRED_PRIOR_DATASETS = tuple(prior_dataset_names)
    original_build = authored_owner.build
    def build_view(**kwargs):
        built = original_build(**kwargs)
        legacy = {"source_rows", "references", "clause_references", "receipt"}
        require(type(built) is dict and set(built) == legacy | ({"pairing_census"} if role == "balanced" else set()),
                "closed authored builder output required")
        if role == "balanced":
            # Pairing metadata has its own separately sealed census. It is not a
            # qualifier/target/row and never replaces any legacy source member.
            census = built["pairing_census"]
            require(type(census) in (dict, list) and bool(census), "separately sealed pairing census required")
        return {key: built[key] for key in legacy}
    renderer.build = build_view
    helper = profile.configure(auxiliary_owner=auxiliary_owner,
        mixture_owner=mixture_owner, authored_owner=renderer)
    original_prepare = helper.prepare_tensor_cache
    def prepare(torch, model, bank, **kwargs):
        prepared = original_prepare(torch, model, bank, **kwargs)
        return adopt_paired_cache(helper, prepared, bank, pairing, role=role)
    helper.prepare_tensor_cache = prepare
    helper.pairing_role = role
    helper.pairing_sha256 = pairing["pairing_sha256"]
    return helper, profile.configure_trainer


def prepare_native384(producer, source_rows, *, expected_source_rows_sha256,
                      sealed_recipe_sha256, asset_config, source_artifact_directory,
                      max_seconds=600):
    """Guarded caller only: invoke the existing source-only TRAIN producer.

    This function does not acquire a lease or authorize execution. The reviewed
    preparation CLI/guardian must establish real resource admission first.
    Neither this API nor the inherited producer receives reference labels.
    """
    require(type(source_rows) is list and len(source_rows) == 48
        and all(type(row) is dict and set(row) == {"id", "source_text"} for row in source_rows),
        "closed48 source-only paragraph rows required")
    require(digest(source_rows) == expected_source_rows_sha256,
            "source rows differ from pre-model source seal")
    require(type(asset_config) is dict and set(asset_config) == {"snapshot_path"},
            "existing explicit local384 snapshot configuration required")
    plan = producer.source_plan(source_rows,
        expected_source_rows_sha256=expected_source_rows_sha256,
        sealed_recipe_sha256=sealed_recipe_sha256)
    require(plan["shape_plan"]["unique_sources"] == 216
        and plan["shape_plan"]["encoder_context_tokens"] == 512,
        "unchanged216 source/512-context producer shape required")
    report = producer.produce_width(plan, dimension=384, asset_config=deepcopy(asset_config),
        source_artifact_directory=source_artifact_directory, batch_size=4, max_seconds=max_seconds)
    require(producer.validate_report(plan, report) == 384,
            "authenticated native384 production validation failed")
    require(report["encoder_executed"] is True and report["downloads_performed"] is False
        and all(report[k] is False for k in ("qualified", "admitted", "proof_authority", "source_semantics_verified")),
        "numerical feature receipt cannot acquire source/proof authority")
    return plan, report


def source_bank_readout(helper, torch, model, cache, bank, codec, source_fields, *, deadline):
    """Observe every source field in the authentic180-row bank evaluation.

    The inherited evaluator owns the actual source forward and modality CE.
    A temporary instance observer copies its returned slot0/full32 values; it
    adds no source/model pass and never supplies targets to the forward call.
    Actor/action/object/modality reference joins occur after the numeric return.
    """
    require(tuple(source_fields) == tuple(helper.values.SOURCE_FIELDS)
        and set(source_fields) == {"actor", "action", "object", "modality"},
        "authentic four-field source ordering required")
    require(model is cache._model and type(cache) is helper.TensorCache,
        "authentic model/cache ownership required")
    before = helper.core.tensor_digest(model)
    previous_local = model.__dict__.get("source_value_logits")
    had_local = "source_value_logits" in model.__dict__
    original = model.source_value_logits
    captured = []
    def observer(*args, **kwargs):
        output = original(*args, **kwargs)
        require(tuple(output.shape[1:]) == (8, 4, 32), "authentic full32 source shape required")
        captured.extend(output[:, 0].detach().tolist())
        return output
    model.source_value_logits = observer
    try:
        inherited = helper.evaluate_bank(torch, model, cache, deadline=deadline)
    finally:
        if had_local:
            model.source_value_logits = previous_local
        else:
            delattr(model, "source_value_logits")
    require(len(captured) == len(bank["rows"]) == 180 and inherited["complete"] is True
        and helper.core.tensor_digest(model) == before, "complete unmodified180-row source pass required")
    vocabulary = codec["target_vocabulary"]
    rows = []
    for row, fields in zip(bank["rows"], captured):
        joined = {}
        for field, values in zip(source_fields, fields):
            require(len(values) == 32 and all(type(v) in (int, float) and math.isfinite(v) for v in values),
                "finite full32 source values required")
            target = vocabulary.index(json.dumps(row["target"][field], ensure_ascii=False, separators=(",", ":")))
            winner = max(range(32), key=values.__getitem__)
            high = max(values)
            ce = high + math.log(math.fsum(math.exp(v - high) for v in values)) - values[target]
            joined[field] = dict(target_token_id=target, argmax_token_id=winner,
                correct=winner == target, margin=values[target] - max(v for i, v in enumerate(values) if i != target),
                cross_entropy=ce, full32_logits=values)
        rows.append(dict(row_id=row["id"], source_sha256=row["source_sha256"],
            original_rule_sha256=_rule(row["target"]), template=row["template"], fields=joined))
    return dict(schema="balanced-wording-source-bank-readout/v1", complete=True,
        rows=rows, row_count=180, reference_fields=720,
        by_field={field: dict(correct=sum(r["fields"][field]["correct"] for r in rows),
            total=180, cross_entropy=math.fsum(r["fields"][field]["cross_entropy"] for r in rows) / 180,
            minimum_target_margin=min(r["fields"][field]["margin"] for r in rows)) for field in source_fields},
        inherited_modality_readout=inherited, model_tensor_sha256=before,
        source_forwards_owned_by_inherited_evaluator=True, extra_source_forwards=0,
        optimizer_steps=0, used_for_selection=False,
        source_targets_joined_after_numeric_return=True,
        interpretation="Known authored TRAIN reconstruction diagnostic; not semantic review or holdout.", **FALSE)
