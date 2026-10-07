#!/usr/bin/env python3
"""Explicit preflight or same-budget E384 two-bank authored replay.

Both authentic180 banks retain their validators/caches. One170-update fit
alternates six-clause banks using85 independent local ordinals each. Original
selection and all nine panels remain unchanged. No semantic or Lake admission.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

E_RUNNER_SHA = "e9231f6fa2bccc329539da089568254181756245333d1418249a6dbfe1c6507e"
E_ADAPTER_SHA = "48b7a3b2a0e5b69ae292f2c02dc0e87d92de4ffb4443bfba5ae52695b9a4320a"
PARENT_TENSOR_SHA = "0b3c7c3b1a5581cd393d9bb8db1d24b87fe2cb9dff0be268aa2b5ed1f88b6594"
PREFIX = "ipfs_datasets_py.logic.formalization.autoencoder."
OBSERVER = "ipfs_datasets_py/logic/formalization/autoencoder/generated_scalar_observation.py"
OBSERVER_SHA = "1f1d35f7fd90df0396f3222676f2ffd11f17e2b1b2c79c0a79f1600488eb08d8"
PROTOCOL_SCHEMA = "dual-bank-replay-comparison-protocol/v1"
PROTOCOL_SHA = "75d4d01893578265c2be3bcc53ed96ca661fdb03781704a074b9df56e6bf30d2"
COMMON = dict(dimension=384,
    parent_tensor_sha256=PARENT_TENSOR_SHA, seed=1729, source_bank_rows=180,
    source_bank_roles=["control", "balanced"], native_context_tokens=512, output_tokens=512,
    temperature=0, batch_size=8, source_auxiliary_weight=.05, paired_draws=170, first_bank="control",
    bank_local_ordinal_policy="floor(global_committed_step/2)",
    source_updates_per_bank=85, source_presentations_per_bank=510,
    max_seconds_per_generation=60, max_trace_memory_bytes=268435456,
    encoder_executed=False, downloads_performed=False, qualified=False, admitted=False,
    proof_authority=False, source_semantics_verified=False, formalized=False,
    bridge_names=[], metric_disk_cache_used=False,
    original_decoder_rows_unchanged=True, preprocessing_refitted=False,
    architecture_changed=False, selection_unchanged=True,
    fresh_optimizer=True, fresh_scheduler=True, exact_optimizer_resume=False,
    initial_learning_rate=.0001, non_action_learning_rate_multiplier=10.,
    cardinality_weight=.25, source_value_weight=.25, action_contrastive_weight=.05,
    generated_boundary_weight=.05, generated_boundary_site_policy="first_last",
    original_used113_auxiliary_weight=.05, alpha=0., full_vocabulary_size=32,
    reference_rows_unavailable_to_selection=["balanced48", "sealed60", "exposed-v3"],
    original_panel_names=["training", "validation", "zero-condition", "source-shuffle",
        "context-only-shuffle", "cross-length-shuffle", "context-reverse", "context-rotate",
        "recurrent-residual-off"])
PREFLIGHT = dict(COMMON, phase="preflight", max_seconds_total=800,
    training_executed=False, optimizer_steps=0, checkpoint_selected=False,
    fits=0, storage_bytes=100000000, memory_mb=1536, cpu_slots=1)
TRAINING = dict(COMMON, phase="training", max_seconds_total=900,
    training_executed=True, optimizer_steps_per_fit=170, fits=1,
    row_presentations_per_fit=1220, target_token_presentations_per_fit=112920,
    source_value_presentations_per_fit=12800, count_presentations_per_fit=1220,
    original_used113_presentations_per_fit=1020, new_auxiliary_presentations_per_fit=1020,
    max_seconds_per_fit=180, max_seconds_per_original_panel=30,
    max_fit_memory_bytes=1073741824, storage_bytes=400000000, memory_mb=1536, cpu_slots=1)


def validate_plan(plan, manifest, phase):
    require(phase in ("preflight", "training"), "explicit supported phase required")
    require(type(plan) is dict and plan.get("schema") == "dual-bank-replay-plan/v1"
        and plan.get("input_sha256") == manifest["inputs"], "closed continuation plan required")
    for name, profile in (("preflight_profile", PREFLIGHT), ("training_profile", TRAINING)):
        require(type(plan.get(name)) is dict and set(plan[name]) == set(profile)
            and all(type(plan[name][k]) is type(v) and plan[name][k] == v for k, v in profile.items()),
            "fixed " + name + " differs")
    return PREFLIGHT if phase == "preflight" else TRAINING


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load(path, wanted, name):
    require(sha(path) == wanted, "frozen private source differs: " + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    return owner


def resident(ctx, leaf, initialization_root):
    """Reuse the real frozen owner, rather than a previously configured view."""
    owner = sys.modules.get(PREFIX + leaf)
    require(owner is not None and getattr(owner, "__file__", None), "frozen resident owner required: " + leaf)
    path = str(Path(owner.__file__).resolve())
    allowed = dict(ctx["paraphrase_manifest"]["producer_pins"])
    allowed.update({str((initialization_root / rel).resolve()): wanted
        for rel, wanted in ctx["paraphrase_manifest"]["extensions"].items()})
    require(allowed.get(path) == sha(path), "unbound resident source owner: " + path)
    return owner


def scalar_observer(ctx, manifest):
    path = Path(manifest["scalar_observer_source"]).resolve()
    require(manifest["inputs"].get(str(path)) == OBSERVER_SHA == sha(path)
        and ctx["paraphrase_manifest"]["producer_pins"].get(str(path)) == OBSERVER_SHA,
        "scalar observer absent from immutable E closure")
    owner = sys.modules.get(PREFIX + "generated_scalar_observation")
    if owner is None:
        owner = ctx["helpers"].extension(path.parents[4], OBSERVER,
            PREFIX + "generated_scalar_observation", {OBSERVER: OBSERVER_SHA})
    require(Path(owner.__file__).resolve() == path and sha(path) == OBSERVER_SHA
        and owner.boundary is ctx["owners"]["contextual_generated_boundary_training"]
        and owner.fields is ctx["owners"]["generated_field_training"]
        and owner.core is ctx["core"], "scalar observer changed numerical owner identities")
    return owner


def declared_schedule(adapter, pairing, bank, role):
    adapter.validate_pairing(pairing, bank, role=role)
    draws = []
    for draw in pairing["draws"]:
        indices = draw["indices"][role]
        rows = [bank["rows"][i] for i in indices]
        draws.append(dict(step=draw["step"], indices=indices, row_ids=[r["id"] for r in rows],
            source_sha256=[r["source_sha256"] for r in rows],
            strata=[[r["modality"], r["template"]] for r in rows],
            target_token_ids=[r["modality_token_id"] for r in rows]))
    return dict(bank_sha256=bank["bank_sha256"], orders=pairing["orders"][role], draws=draws)


def execute(args):
    require(args.phase in ("preflight", "training") and type(args.dimension) is int and args.dimension == 384,
            "explicit native384 preflight or training only")
    started = time.monotonic()
    manifest = json.loads(args.manifest.read_bytes())
    plan = json.loads(args.plan.read_bytes())
    require(manifest.get("schema") == "dual-bank-replay-manifest/v1",
            "explicit continuation manifest required")
    profile = validate_plan(plan, manifest, args.phase)
    deadline = started + profile["max_seconds_total"]
    require(sha(args.plan) == manifest["plan_sha256"], "continuation plan bytes differ")
    manifest_sha = sha(args.manifest)
    def recheck():
        require(time.monotonic() < deadline and sha(args.manifest) == manifest_sha
            and sha(args.plan) == manifest["plan_sha256"], "preflight seal/deadline changed")
        for p, wanted in manifest["inputs"].items():
            require(sha(p) == wanted, "changed preflight input: " + p)
        for relative, wanted in manifest["extensions"].items():
            require(sha(args.extension_root / relative) == wanted, "changed private extension")
    def bound(path):
        path = Path(path).resolve()
        require(manifest["inputs"].get(str(path)) == sha(path), "unbound preflight input")
        return json.loads(path.read_bytes())
    recheck()
    require(not args.output.exists(), "fresh preflight output required")
    protocol = bound(manifest["comparison_protocol"])
    require(sha(manifest["comparison_protocol"]) == PROTOCOL_SHA
        and protocol.get("schema") == PROTOCOL_SCHEMA, "predeclared same-budget replay protocol required")
    root = Path(manifest["initialization_extension_root"])
    old = load(root / "scripts/ops/autoencoder/benchmark_normative_wording_training.py",
        E_RUNNER_SHA, "_balanced_preflight_e_initializer")
    previous = SimpleNamespace(**vars(args))
    previous.phase = "preflight"
    previous.manifest = Path(manifest["initialization_manifest"])
    previous.plan = Path(manifest["initialization_plan"])
    previous.extension_root = root
    owner = old.load_training_owner()
    ctx = owner.load_context(previous, deadline)
    source_before = owner.source_inventory(previous, ctx)
    lane = ctx["mixture_owner"].prepare_lane(ctx, 384)
    lane["continuation_manifest"] = manifest
    parent = bound(manifest["parent_summary"])
    require(parent["dimension"] == 384 and parent["arm"] == "normative-wording-ce"
        and parent["budget_completed"] is True and parent["states"]["selected"]["tensor_sha256"] == PARENT_TENSOR_SHA,
        "exact completed E384 auxiliary parent required")
    bound(parent["states"]["selected"]["path"])
    adapter_path = args.extension_root / "balanced_wording_runtime_adapter.py"
    adapter = load(adapter_path, manifest["extensions"]["balanced_wording_runtime_adapter.py"], "_balanced_preflight_adapter")
    normative = load(root / "ipfs_datasets_py/logic/formalization/autoencoder/normative_wording_modality_auxiliary.py",
        E_ADAPTER_SHA, "_balanced_preflight_normative_profile")
    authored = {"control": resident(ctx, "normative_wording_training_sources", root)}
    cp = args.extension_root / manifest["candidate_builder_relative"]
    authored["balanced"] = load(cp, manifest["extensions"][manifest["candidate_builder_relative"]], "_balanced_preflight_renderer")
    inventories = {role: bound(manifest["source_inventories"][role]) for role in adapter.ROLES}
    raw_auxiliary = resident(ctx, "paraphrase_modality_auxiliary_training", root)
    raw_trainer = resident(ctx, "_paraphrase_modality_training_owner", root)
    original_rules = bound(manifest["original90_rules"])
    # First use the authentic source-bank validator for each explicit profile.
    # No paired cache exists yet; its manifest is constructed from validated banks.
    helpers, banks = {}, {}
    for role in adapter.ROLES:
        templates = tuple(authored[role].TEMPLATES)
        renderer = adapter.renderer_view(authored[role], ctx["mixture_helper"])
        renderer.REQUIRED_PRIOR_DATASETS = tuple(inventories[role]["prior_sources_by_dataset"])
        require((set(authored[role].REQUIRED_PRIOR_DATASETS) | {normative.FUTURE_SOURCE_INVENTORY})
            <= set(renderer.REQUIRED_PRIOR_DATASETS), "complete authored source exclusions required")
        require(len(renderer.REQUIRED_PRIOR_DATASETS) == (13 if role == "control" else 16),
            "distinct authentic control13/balanced16 source inventories required")
        if role == "balanced":
            original_build = authored[role].build
            def view(_build=original_build, **kwargs):
                built = _build(**kwargs)
                require(set(built) == {"source_rows", "references", "clause_references", "receipt", "pairing_census"},
                    "complete separately retained pairing census required")
                return {k: built[k] for k in ("source_rows", "references", "clause_references", "receipt")}
            renderer.build = view
        bank_profile = normative.private_module(normative, TEMPLATES=templates,
            STRATA=tuple((m, t) for m in adapter.MODALITIES for t in templates),
            SCHEMA="training-balanced-wording-modality-bank/v1")
        helper = bank_profile.configure(auxiliary_owner=raw_auxiliary,
            mixture_owner=ctx["mixture_helper"], authored_owner=renderer)
        banks[role] = helper.prepare_bank(lane["rows"]["train"], lane["rows"]["validation"],
            training_references=lane["references"]["train"], validation_references=lane["references"]["validation"],
            source_contexts=lane["source_contexts"], codec=lane["donor"]["codec"],
            validate_rule=lane["validate_rule"], source_inventory=inventories[role], deadline=deadline)
        helpers[role] = helper
    pairing = adapter.build_pairing(banks["control"], banks["balanced"], original_rules=original_rules,
        templates_by_role={role: tuple(authored[role].TEMPLATES) for role in adapter.ROLES})
    dual = load(args.extension_root / "dual_bank_runtime_adapter.py",
        manifest["extensions"]["dual_bank_runtime_adapter.py"], "_dual_bank_runtime_adapter")
    retention = load(args.extension_root / "dual_bank_retention.py",
        manifest["extensions"]["dual_bank_retention.py"], "_dual_bank_retention")
    dual_schedule = retention.build_schedule(pairing=pairing, banks_by_role=banks,
        original_rules=original_rules, first_bank="control")
    dual_helpers = {}
    for role in adapter.ROLES:
        dual_helpers[role], _ = adapter.configure_profile(normative,
            auxiliary_owner=raw_auxiliary, mixture_owner=ctx["mixture_helper"],
            authored_owner=authored[role], pairing=pairing, role=role,
            prior_dataset_names=tuple(inventories[role]["prior_sources_by_dataset"]))
    dual_helper = dual.configure(helpers_by_role=dual_helpers, expected_banks=banks,
        schedule=dual_schedule, retention_owner=retention)
    dual_inventory = dual.source_inventory_pair(inventories)
    args.output.mkdir(parents=True)
    save = ctx["helpers"].save
    save(args.output / "sealed-recipe.json", dict(plan=plan, manifest=manifest, **adapter.FALSE))
    pairing_ref = save(args.output / "paired-source-schedule.json", pairing)
    dual_schedule_ref = save(args.output / "dual-source-schedule.json", dual_schedule)
    dual_inventory_ref = save(args.output / "dual-source-inventory.json", dual_inventory)
    model = ctx["mixture_owner"].restore_endpoint(lane, parent, "selected")
    require(lane["core"].tensor_digest(model) == PARENT_TENSOR_SHA, "restored parent tensor differs")
    prepared_dual_bank = dual_helper.prepare_bank(lane["rows"]["train"], lane["rows"]["validation"],
        training_references=lane["references"]["train"], validation_references=lane["references"]["validation"],
        source_contexts=lane["source_contexts"], codec=lane["donor"]["codec"],
        validate_rule=lane["validate_rule"], source_inventory=dual_inventory, deadline=deadline)
    parent_dual_cache = dual_helper.prepare_tensor_cache(lane["core"]._torch(), model, prepared_dual_bank,
        codec=lane["donor"]["codec"], input_transform=lane["donor"]["input_transform"],
        seed=1729, deadline=deadline, max_optimizer_steps=170)
    dual_cache_ref = save(args.output / "parent-dual-cache-receipt.json", parent_dual_cache.receipt)
    zero_graph_refs = []
    for global_step in (0, 1):
        observed_loss = dual_helper.modality_loss(lane["core"]._torch(), model, parent_dual_cache,
            committed_step=global_step, deadline=deadline, requires_grad=False)
        require(observed_loss["loss"].requires_grad is False, "detached preflight loss required")
        zero_graph_refs.append(save(args.output / ("parent-dual-detached-loss-" + str(global_step) + ".json"),
            observed_loss["receipt"]))
    require(lane["core"].tensor_digest(model) == PARENT_TENSOR_SHA,
        "dual preparation or detached source checks changed parent")
    del observed_loss, parent_dual_cache, prepared_dual_bank
    parent_validation = ctx["paraphrase_parent"].bounded_evaluate(lane, model, "validation", "conditioned", deadline)
    old_validation = bound(parent["postfit"]["selected"]["validation"]["path"])
    require(parent_validation["predictions"] == old_validation["predictions"], "E parent validation parity differs")
    parity_ref = save(args.output / "parent-validation-parity.json", dict(predictions_equal=True,
        model_tensor_sha256=PARENT_TENSOR_SHA, rows=len(parent_validation["predictions"]), **adapter.FALSE))
    readouts, initial_bank_metrics = {}, {}
    for role in adapter.ROLES:
        helper = helpers[role]
        prepared = helper.prepare_tensor_cache(lane["core"]._torch(), model, banks[role],
            codec=lane["donor"]["codec"], input_transform=lane["donor"]["input_transform"],
            seed=1729, deadline=deadline, max_optimizer_steps=170)
        cache = adapter.adopt_paired_cache(helper, prepared, banks[role], pairing, role=role)
        report = adapter.source_bank_readout(helper, lane["core"]._torch(), model, cache,
            banks[role], lane["donor"]["codec"], helper.values.SOURCE_FIELDS, deadline=deadline)
        readouts[role] = save(args.output / (role + "-parent-source-readout.json"), report)
        initial_bank_metrics[role] = report["by_field"]
        save(args.output / (role + "-bank.json"), banks[role])
        save(args.output / (role + "-paired-cache-receipt.json"), cache.receipt)
    # Actual new48 generation uses source-only inputs. The existing scalar owner
    # observes all four fields in that same pass; references are joined later.
    data = bound(manifest["balanced_source_inputs"])
    require(data["dimension"] == 384 and data["complete"] is True and data["targets_attached"] is False
        and data["inputs_sha256"] == adapter.digest({k: v for k, v in data.items() if k != "inputs_sha256"})
        and len(data["rows"]) == 48 and all(set(r) == {"id", "source_text", "input"} for r in data["rows"]),
        "authenticated target-free balanced48 inputs required")
    require(data == inventories["balanced"]["source_inputs"], "greedy sources differ from validated native TRAIN bank")
    contexts = data["source_contexts"]
    context_owner = ctx["owners"]["clause_source_context"]
    require(context_owner.build_source_contexts([{k: r[k] for k in ("id", "source_text")}
        for r in data["rows"]], data["clause_cache"]) == contexts
        and context_owner.validate_contexts(data["rows"], contexts)["dimension"] == 384,
        "balanced source contexts rejected")
    scalar = scalar_observer(ctx, manifest)
    trace = scalar.collect_source_scalar_trace(model, data["rows"],
        source_contexts=contexts, input_transform=lane["donor"]["input_transform"],
        codec=lane["donor"]["codec"], deadline=min(deadline, time.monotonic() + 60),
        max_target_tokens=512, batch_size=8, max_memory_bytes=profile["max_trace_memory_bytes"])
    require(trace["complete"] is True and lane["core"].tensor_digest(model) == PARENT_TENSOR_SHA,
        "complete frozen-parent new48 greedy trace required")
    trace_ref = save(args.output / "balanced48-parent-greedy-trace.json", trace)
    predictions_ref = save(args.output / "balanced48-parent-actual-predictions.json", dict(
        predictions=trace["predictions"], complete=True, model_tensor_sha256=PARENT_TENSOR_SHA,
        same_pass_trace_sha256=trace["trace_sha256"], generation_reference_access=False,
        source_rows_sha256=trace["source_rows_sha256"], source_contexts_sha256=trace["source_contexts_sha256"],
        generation_temperature=0, greedy_passes_per_row=1, max_target_tokens=512, batch_size=8,
        **adapter.FALSE))
    # References already belong to the declared authored TRAIN fixture; they
    # are joined after durable target-free generation, never fit/selection.
    references = inventories["balanced"]["corpus"]["references"]
    by_id = {r["id"]: r for r in references}
    require(len(by_id) == 48 and set(by_id) == {r["id"] for r in data["rows"]},
        "complete balanced48 authored TRAIN references required")
    scored_rows = [dict(row, target_ids=by_id[row["id"]]["target_ids"]) for row in data["rows"]]
    scores = scalar.score_scalar_trace(trace, scored_rows, references, split="training",
        codec=lane["donor"]["codec"], input_transform=lane["donor"]["input_transform"],
        source_contexts=contexts, validate_rule=lane["validate_rule"], deadline=deadline)
    scores_ref = save(args.output / "balanced48-parent-posthoc-scalar-scores.json", scores)
    fidelity_owner = resident(ctx, "decoder_source_fidelity", root)
    fidelity = fidelity_owner.score_predictions(references, trace["predictions"],
        codec=lane["donor"]["codec"], validate_rule=lane["validate_rule"],
        output_limit=512, validator_id=lane["validator_id"])
    require(fidelity["complete_evaluation"] is True and len(fidelity["rows"]) == 48,
        "all48 actual generated formula evaluations required")
    fidelity_ref = save(args.output / "balanced48-parent-posthoc-formula-fidelity.json", fidelity)
    del model, trace, scores, prepared, cache
    runs = []
    if args.phase == "training":
        baseline = bound(parent["training_ref"]["path"])
        for arm_name in ("dual-bank-retention-ce",):
            model = ctx["mixture_owner"].restore_endpoint(lane, parent, "selected")
            require(lane["core"].tensor_digest(model) == PARENT_TENSOR_SHA, "matched E parent differs")
            configure_trainer = normative.configure_trainer
            fit_lane = dict(lane, owners=dict(lane["owners"]))
            fit_lane["owners"]["long_span_source_value_training"] = configure_trainer(raw_trainer, dual_helper)
            arm = dict(name=arm_name, weight=.05)
            folder = args.output / arm["name"]
            states = {"initial": lane["native_runner"].save_state(lane, model, arm,
                "initial", False, folder / "initial-state.json")}
            fit_started = time.monotonic()
            try:
                value = owner.train_candidate(fit_lane, model,
                    dict(source_inventory=dual_inventory, weight=.05), deadline)
            except BaseException as error:
                save(folder / "training-failure.json", dict(error_type=type(error).__name__,
                    caller_tensor_sha256=lane["core"].tensor_digest(model), complete=False,
                    initial_state=states["initial"], partial_internal_state_available=False, **adapter.FALSE))
                raise
            fit_seconds = time.monotonic() - fit_started
            inherited_report = value["report"]
            inherited_report_ref = save(folder / "training-inherited.json", inherited_report)
            owner.validate_original_streams(lane, inherited_report, baseline, PARENT_TENSOR_SHA)
            report = dual.reconcile_report(inherited_report, dual_schedule, retention)
            report_ref = save(folder / "training.json", report)
            panels, endpoint_readouts = {}, {}
            for state_role, state, predicted in (("selected", value["state_dict"], value["predictions"]),
                ("last-attempt", value["last_complete_attempt_state_dict"], value["last_complete_attempt_predictions"])):
                require(state is not None, "both complete endpoints required")
                lane["native_runner"].validate_wrapper_state(lane, state)
                model.load_state_dict(state, strict=True)
                expected = report["selected_weights_sha256" if state_role == "selected"
                    else "last_complete_attempt_weights_sha256"]
                require(lane["core"].tensor_digest(model) == expected, "retained endpoint tensor differs")
                states[state_role] = lane["native_runner"].save_state(lane, model, arm, state_role,
                    state_role == "selected" or report["last_complete_attempt_is_selected"],
                    folder / (state_role + "-state.json"))
                compact = ctx["paraphrase_parent"].original_panels(lane, model, predicted,
                    folder / state_role, deadline)
                require(set(compact) == set(COMMON["original_panel_names"]), "all nine original panels required")
                panels[state_role] = {label: dict(path=str(folder / state_role / ("evaluation-" + label + ".json")),
                    sha256=sha(folder / state_role / ("evaluation-" + label + ".json")),
                    numerical=p["numerical"], fidelity=p["source_fidelity"]) for label, p in compact.items()}
                endpoint_readouts[state_role] = {}
                for bank_role in adapter.ROLES:
                    cache = helpers[bank_role].prepare_tensor_cache(lane["core"]._torch(), model, banks[bank_role],
                        codec=lane["donor"]["codec"], input_transform=lane["donor"]["input_transform"],
                        seed=1729, deadline=deadline, max_optimizer_steps=170)
                    paired = adapter.adopt_paired_cache(helpers[bank_role], cache, banks[bank_role], pairing, role=bank_role)
                    observed = adapter.source_bank_readout(helpers[bank_role], lane["core"]._torch(), model,
                        paired, banks[bank_role], lane["donor"]["codec"], helpers[bank_role].values.SOURCE_FIELDS,
                        deadline=deadline)
                    endpoint_readouts[state_role][bank_role] = save(folder / state_role /
                        (bank_role + "-source-bank-readout.json"), observed)
                    del cache, paired, observed
            record = dict(arm=arm["name"], dimension=384, seed=1729, recipe=arm,
                parent_state=parent["states"]["selected"], states=states, training_ref=report_ref,
                postfit=panels, full180_postfit_readouts=endpoint_readouts, budget_completed=True,
                initial_tensor_sha256=PARENT_TENSOR_SHA, pairing=pairing_ref, initial_parity=parity_ref,
                fresh_optimizer=True, fresh_scheduler=True, exact_optimizer_resume=False,
                zero_arm_archived_replay_verified=False, source_inventory_sha256=dual_inventory["payload_sha256"],
                source_inventory_sha256_by_role={r: inventories[r]["payload_sha256"] for r in adapter.ROLES},
                dual_source_schedule=dual_schedule_ref, inherited_training_ref=inherited_report_ref,
                actual_dual_receipt_counts_validated=True, inherited_template_counts_applicable=False,
                training_call_elapsed_seconds=fit_seconds, training_rows_per_second=1220 / fit_seconds,
                selected_last_tensor_alias=states["selected"]["tensor_sha256"] == states["last-attempt"]["tensor_sha256"],
                original_panels_physically_evaluated_for_both_roles=True, **adapter.FALSE)
            runs.append(save(folder / "summary.json", record))
            del model, value, report, inherited_report, state, compact
    after = owner.source_inventory(previous, ctx)
    require(all(after.get(p) == wanted for p, wanted in source_before.items()), "resident source changed")
    recheck()
    result = dict(profile, schema="dual-bank-replay-result/v1", complete=True,
        pairing=pairing_ref, dual_source_schedule=dual_schedule_ref, dual_source_inventory=dual_inventory_ref,
        parent_dual_cache_receipt=dual_cache_ref, parent_dual_detached_losses=zero_graph_refs,
        initial_parity=parity_ref, runs=runs, source_dependencies=after,
        source_bank_readouts=readouts, balanced48_actual_greedy_trace=trace_ref,
        initial_bank_source_scalar_metrics=initial_bank_metrics,
        initial_balanced_bank_all_four_scalars_correct=all(v["correct"] == v["total"]
            for v in initial_bank_metrics["balanced"].values()),
        interpretation_if_initial_bank_perfect="confidence/coverage comparison; no classification-repair claim",
        balanced48_actual_predictions=predictions_ref, balanced48_posthoc_scalar_scores=scores_ref,
        balanced48_posthoc_formula_fidelity=fidelity_ref,
        inherited_TRAIN_validation_metadata_loaded=True, labels_or_counts_supplied_to_generation=False,
        qualification_granted=False, model_executed=True,
        elapsed_seconds=time.monotonic() - started)
    save(args.output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dependency-root", "extension-root", "manifest", "plan", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", choices=("preflight", "training"), required=True)
    parser.add_argument("--dimension", type=int, choices=(384,), required=True)
    execute(parser.parse_args())


if __name__ == "__main__":
    main()
