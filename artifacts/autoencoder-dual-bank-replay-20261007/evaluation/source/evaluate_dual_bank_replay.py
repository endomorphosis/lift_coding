#!/usr/bin/env python3
"""Postfit source-only native384 observation, keeping four cohorts separate.

Eight physical panels (one arm, two roles, four cohorts) are durably collected
before exposed-v3 references are parsed. TRAIN metadata was already known.
Original generation/scalar/fidelity owners remain unchanged; no fit, selection,
encoder, proof engine, syntax mask or forced closure is invoked by this writer.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

ARMS = ("dual-bank-retention-ce",)
ROLES = ("selected", "last-attempt")
COHORTS = ("original_train48", "normative_train48", "new_balanced_train48", "exposed_v3_48")
FIELDS = ("actor", "action", "modality", "object")
FACETS = (*FIELDS, "conditions", "exceptions", "temporal")
BENCHMARK = "scripts/ops/autoencoder/benchmark_dual_bank_replay.py"
FALSE = dict(qualified=False, admitted=False, proof_authority=False, formalized=False,
    source_semantics_verified=False, checkpoint_promoted=False, convergence_proven=False,
    encoder_executed=False, downloads_performed=False, training_executed=False,
    lake_executed=False, native_family_validation_performed=False, used_for_selection=False,
    fresh_holdout=False, independent_semantic_holdout=False, Constitution_formalized=False)
PROFILE = dict(schema="dual-bank-replay-postfit-evaluation-plan/v1", phase="evaluation",
    dimensions=[384], arms=list(ARMS), roles=list(ROLES), cohorts=list(COHORTS),
    logical_panels=8, physical_panels=8, samples_per_panel=48, rules_per_panel=180,
    scalar_reference_sites_per_panel=720, source_context_tokens=512, output_tokens=512,
    batch_size=8, temperature=0, full_vocabulary_size=32, cpu_slots=1, memory_mb=1536,
    storage_bytes=100000000, max_seconds_total=800, max_seconds_per_panel=60,
    max_trace_memory_bytes=268435456, predictions_fsynced_before_v3_reference_load=True,
    same_pass_scalar_observation=True, extra_source_head_passes=0,
    inherited_TRAIN_validation_metadata_loaded=True, bridge_names=[],
    legal_ir_evaluate_provers=False, metric_disk_cache_used=False,
    teacher_forced_loss_measured=False, reconstructed_input_mse_measured=False, **FALSE)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def validate_plan(plan, manifest):
    require(type(plan) is dict and all(type(plan.get(k)) is type(v) and plan[k] == v
        for k, v in PROFILE.items()) and plan.get("input_sha256") == manifest["inputs"],
        "fixed native384 four-cohort evaluation plan required")


def durable(save, path, value):
    ref = save(path, value)
    require(Path(ref["path"]).resolve() == Path(path).resolve() and sha(path) == ref["sha256"],
        "durable evaluation reference differs")
    with Path(path).open("rb") as stream:
        os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return ref


def prepare_cohorts(lane, control, balanced, context_owner):
    """Use authenticated cached inputs; the source-only v3 join uses exact text."""
    require(set(control["prior_sources_by_dataset"]) <= set(balanced["prior_sources_by_dataset"])
        and len(control["prior_sources_by_dataset"]) == 13
        and len(balanced["prior_sources_by_dataset"]) == 16,
        "preserved control13/balanced16 declarations required")
    cohorts = {"original_train48": dict(rows=[{k: r[k] for k in ("id", "source_text", "input")}
        for r in lane["rows"]["train"]], source_contexts=lane["source_contexts"]["train"])}
    for name, envelope in (("normative_train48", control), ("new_balanced_train48", balanced)):
        data = envelope["source_inputs"]
        require(data["dimension"] == 384 and data["complete"] is True
            and data["targets_attached"] is False and data["inputs_sha256"] ==
            digest({k: v for k, v in data.items() if k != "inputs_sha256"}), "closed native384 TRAIN cache required")
        rows = data["rows"]
        contexts = context_owner.build_source_contexts([{k: r[k] for k in ("id", "source_text")}
            for r in rows], data["clause_cache"])
        require(contexts == data["source_contexts"], "TRAIN source contexts differ from frozen owner")
        cohorts[name] = dict(rows=rows, source_contexts=contexts)
    prior = control["prior_sources_by_dataset"]["exposed_v3"]
    require(len(prior) == 48 and all(set(r) == {"id", "source_text"} for r in prior),
        "closed original48 v3 source declaration required")
    lookup = {}
    for row in control["evaluation_vectors_by_dataset"]["exposed_v3"]:
        require(set(row) == {"id", "source_text", "input"}, "source-only v3 vector inventory required")
        text = row["source_text"]
        require(text not in lookup or lookup[text] == row["input"], "inconsistent exact v3 source vectors")
        lookup[text] = row["input"]
    texts = {r["source_text"] for r in prior} | {piece for r in prior for piece in r["source_text"].split("\n\n")}
    require(texts <= set(lookup), "complete exact-text cached native384 v3 vectors required; no fallback")
    v3_rows = [dict(r, input=deepcopy(lookup[r["source_text"]])) for r in prior]
    clauses = sorted({piece for r in prior for piece in r["source_text"].split("\n\n")})
    cache = [dict(id="clause:" + hashlib.sha256(text.encode()).hexdigest(), source_text=text,
        input=deepcopy(lookup[text])) for text in clauses]
    cohorts["exposed_v3_48"] = dict(rows=v3_rows, source_contexts=context_owner.build_source_contexts(prior, cache))
    identities = set()
    for cohort in COHORTS:
        rows, contexts = cohorts[cohort]["rows"], cohorts[cohort]["source_contexts"]
        require(len(rows) == 48 and all(set(r) == {"id", "source_text", "input"} for r in rows)
            and sum(len(r["source_text"].split("\n\n")) for r in rows) == 180
            and context_owner.validate_contexts(rows, contexts)["dimension"] == 384,
            "complete48/180 native384 source-only cohort required")
        require(not identities & {r["id"] for r in rows}, "source cohort identities overlap")
        identities.update(r["id"] for r in rows)
    return cohorts


def verify_trace(trace, rows, contexts, state_ref, codec, transform):
    require(trace["trace_sha256"] == digest({k: v for k, v in trace.items() if k != "trace_sha256"})
        and trace["complete"] is True and trace["sample_count"] == 48 and trace["dimension"] == 384
        and trace["model_tensor_sha256"] == state_ref["tensor_sha256"]
        and trace["source_rows_sha256"] == digest(rows) and trace["source_contexts_sha256"] == digest(contexts)
        and trace["codec_sha256"] == digest(codec) and trace["input_transform_sha256"] == digest(transform)
        and trace["vocabulary_size"] == 32 and trace["generation_temperature"] == 0
        and trace["max_target_tokens"] == 512 and trace["batch_size"] == 8
        and len(trace["predictions"]) == 48 and [r["id"] for r in trace["predictions"]] == [r["id"] for r in rows]
        and all(trace.get(k) is True for k in ("source_only", "full_vocabulary_retained", "decomposition_exact",
            "caller_state_preserved", "hooks_removed", "complete_rollout_before_reference_scoring"))
        and all(trace.get(k) is False for k in ("reference_count_access", "reference_prefix_access",
            "reference_documents_passed_to_model", "inventory_access", "source_context_target_access",
            "syntax_mask", "forced_closure", "model_copied", "qualified", "admitted", "proof_authority",
            "source_semantics_verified", "lake_executed", "native_family_validation_performed"))
        and all(type(trace.get(k)) is int and trace[k] == 0 for k in
            ("extra_model_passes", "source_head_extra_evaluations", "optimizer_steps")),
        "same-pass complete source-only trace contract differs")


def bind_references(rows, references, codec):
    """Authored positional fixture labels; never infer law or add review status."""
    require(type(references) is list and len(references) == 48
        and len({r["id"] for r in references}) == 48, "complete48 reference cohort required")
    by_id = {r["id"]: r for r in references}
    require(set(by_id) == {r["id"] for r in rows}, "reference/source identities differ")
    result = []
    for row in rows:
        reference = deepcopy(by_id[row["id"]]); tokens = reference["target_ids"]
        require(reference["source_text"] == row["source_text"]
            and type(tokens) is list and 3 <= len(tokens) <= 512 and tokens[0] == 1 and tokens[-1] == 2
            and all(type(t) is int and 3 <= t < 32 for t in tokens[1:-1])
            and json.loads("".join(codec["target_vocabulary"][t] for t in tokens[1:-1])) == reference["target"]
            and set(reference["target"]) == {"rules"}
            and len(reference["target"]["rules"]) == len(row["source_text"].split("\n\n"))
            and all(set(rule) == set(FACETS) and all(rule[k] == [] for k in
                ("conditions", "exceptions", "temporal")) for rule in reference["target"]["rules"]),
            "complete fixed seven-facet authored source/target binding required")
        reference.update(source_sha256=hashlib.sha256(row["source_text"].encode()).hexdigest(),
            clause_count=len(reference["target"]["rules"]))
        result.append(reference)
    require(sum(r["clause_count"] for r in result) == 180, "fixed180 rule reference denominator required")
    return result


def original_train_references(rows, codec):
    """Decode the already exposed original TRAIN labels after source rollout."""
    refs = []
    for row in rows:
        ids = row["target_ids"]
        require(type(ids) is list and 3 <= len(ids) <= 512 and ids[0] == 1 and ids[-1] == 2
            and all(type(t) is int and 3 <= t < 32 for t in ids[1:-1]), "fixed original TRAIN token labels required")
        target = json.loads("".join(codec["target_vocabulary"][t] for t in ids[1:-1]))
        refs.append(dict(id=row["id"], source_text=row["source_text"], target_ids=deepcopy(ids),
            target=target, clause_count=len(target["rules"]), template="original_train", split="training"))
    return refs


def verify_source_inventories(run, envelopes, parent_tensor_sha256):
    require(set(envelopes) == {"control", "balanced"}
        and set(run["source_inventory_sha256_by_role"]) == set(envelopes),
        "both explicit source inventories required")
    for bank_role, envelope in envelopes.items():
        require(envelope["payload_sha256"] == digest({k: v for k, v in envelope.items() if k != "payload_sha256"})
            and run["source_inventory_sha256_by_role"][bank_role] == envelope["payload_sha256"]
            and run["initial_tensor_sha256"] == parent_tensor_sha256,
            "both postfit sources must remain those of the authentic replay fit")


def verify_barrier(records):
    expected = {(arm, role, cohort) for arm in ARMS for role in ROLES for cohort in COHORTS}
    require(type(records) is list and len(records) == 8 and
        {(r["arm"], r["role"], r["cohort"]) for r in records} == expected
        and all(r["prediction_fsynced"] is True and r["physical_panel_computed"] is True for r in records),
        "complete eight-panel durable reference barrier required")
    for record in records:
        for key in ("trace_ref", "predictions_ref"):
            ref = record[key]
            require(sha(ref["path"]) == ref["sha256"], "changed panel before v3 reference barrier")


def join_scalar_formula(scalar, fidelity, references):
    """Keep all180 positional rules and720 sites, including unvisited failures."""
    require(scalar["complete"] is True and len(references) == len(fidelity["rows"]) == 48
        and [r["id"] for r in references] == [r["id"] for r in fidelity["rows"]],
        "full48 aligned scalar/formula evidence required")
    wanted = {(r["id"], slot, field) for r in references for slot in range(r["clause_count"]) for field in FIELDS}
    require(len(wanted) == 720, "complete720 scalar denominator required")
    events = {}
    for event in scalar["events"]:
        key = (event["id"], event["slot"], event["field"])
        require(key in wanted and key not in events, "duplicate or foreign scalar event")
        events[key] = event
    unvisited = {(r["id"], r["slot"], r["field"]) for r in scalar["unvisited_reference_sites"]}
    unavailable = {(r["id"], r["slot"], r["field"]) for r in scalar["unscored_sites"]
        if (r["id"], r["slot"], r["field"]) in wanted}
    extras = [r for r in scalar["unscored_sites"] if (r["id"], r["slot"], r["field"]) not in wanted]
    require(len(unvisited) == len(scalar["unvisited_reference_sites"]) and unavailable <= unvisited
        and len(unavailable) + len(extras) == len(scalar["unscored_sites"]), "unvisited/unavailable accounting differs")
    unvisited -= unavailable
    require(not set(events) & (unvisited | unavailable) and not unvisited & unavailable
        and set(events) | unvisited | unavailable == wanted, "every reference site must retain one status")
    counts = {f: dict(reference_sites=180, visited=0, unvisited=0, unavailable=0,
        source_correct=0, source_incorrect=0, source_correct_formula_wrong=0,
        source_wrong_formula_correct=0) for f in FIELDS}
    joined = []
    for ref, formula in zip(references, fidelity["rows"]):
        emitted = formula.get("generated_ir")
        raw_rules = emitted.get("rules") if type(emitted) is dict else None
        produced = raw_rules if type(raw_rules) is list else []
        for slot, target in enumerate(ref["target"]["rules"]):
            rule = produced[slot] if slot < len(produced) else None
            fields = {}
            for field in FIELDS:
                key = (ref["id"], slot, field); event = events.get(key); bucket = counts[field]
                formula_correct = type(rule) is dict and rule.get(field) == target[field]
                if event is None:
                    status = "unvisited" if key in unvisited else "unavailable"
                    bucket[status] += 1
                    fields[field] = dict(status=status, source_correct=None, formula_field_correct=formula_correct)
                else:
                    correct = event["source"]["argmax_token_id"] == event["target_token_id"]
                    bucket["visited"] += 1; bucket["source_correct" if correct else "source_incorrect"] += 1
                    bucket["source_correct_formula_wrong"] += int(correct and not formula_correct)
                    bucket["source_wrong_formula_correct"] += int(not correct and formula_correct)
                    fields[field] = dict(status="visited", source_correct=correct,
                        formula_field_correct=formula_correct, **deepcopy(event))
            joined.append(dict(id=ref["id"], slot=slot, expected_rule=target, generated_rule=rule, fields=fields))
    require(len(joined) == 180 and all(v["visited"] + v["unvisited"] + v["unavailable"] == 180
        for v in counts.values()), "fixed180 per-field denominator differs")
    return dict(schema="balanced-wording-postfit-scalar-formula-join/v1", complete=True,
        rows=joined, per_field=counts, extra_generated_unavailable_sites=extras,
        formula_field_match_scope="literal position in raw parsed emitted rule; complete valid-formula metrics remain separate",
        unvisited_counted_correct=False, unavailable_counted_correct=False, **FALSE)


def execute(args):
    require(args.phase == "evaluation", "explicit evaluation phase required")
    started = time.monotonic(); deadline = started + PROFILE["max_seconds_total"]
    manifest = json.loads(args.manifest.read_bytes()); plan = json.loads(args.plan.read_bytes())
    require(manifest["schema"] == "dual-bank-replay-postfit-evaluation-manifest/v1", "explicit evaluation manifest required")
    validate_plan(plan, manifest); manifest_sha = sha(args.manifest)
    def recheck():
        require(time.monotonic() < deadline and sha(args.manifest) == manifest_sha
            and sha(args.plan) == manifest["plan_sha256"], "evaluation seal/deadline changed")
        for path, wanted in manifest["inputs"].items():
            require(sha(path) == wanted and time.monotonic() < deadline, "changed evaluation input")
        for relative, wanted in manifest["extensions"].items():
            require(sha(args.extension_root / relative) == wanted, "changed evaluation extension")
    def bound(path):
        path = Path(path).resolve()
        require(manifest["inputs"].get(str(path)) == sha(path), "unbound evaluation input")
        return json.loads(path.read_bytes())
    recheck(); require(not args.output.exists(), "fresh evaluation output required")
    spec = importlib.util.spec_from_file_location("_balanced_postfit_frozen_benchmark", args.extension_root / BENCHMARK)
    benchmark = importlib.util.module_from_spec(spec); spec.loader.exec_module(benchmark)
    require(manifest["inputs"].get(str(Path(manifest["comparison_protocol"]).resolve())) == benchmark.PROTOCOL_SHA,
        "unchanged predeclared comparison required")
    bound(manifest["comparison_protocol"])
    terminal = manifest["training_terminal"]
    require(bound(terminal["child_exit"])["returncode"] == 0
        and bound(terminal["resources_final"])["status"] == "released", "completed released training required")
    summary = bound(manifest["training_summary"])
    require(summary["complete"] is True and summary["phase"] == "training"
        and summary["dimension"] == 384 and len(summary["runs"]) == 1, "one complete native384 replay fit required")
    runs = {}
    for ref in summary["runs"]:
        run = bound(ref["path"])
        require(sha(ref["path"]) == ref["sha256"] and run["arm"] in ARMS and run["arm"] not in runs
            and run["dimension"] == 384 and run["budget_completed"] is True
            and run["fresh_optimizer"] is True and run["exact_optimizer_resume"] is False
            and all(run[k] is False for k in ("qualified", "admitted", "proof_authority", "checkpoint_promoted")),
            "authentic replay fit summary required")
        require(all(set(run["postfit"][role]) == set(benchmark.COMMON["original_panel_names"]) for role in ROLES),
            "all nine original panels and both endpoint roles must remain available")
        for role in ROLES:
            state = run["states"][role]
            require(manifest["inputs"].get(str(Path(state["path"]).resolve())) == state["sha256"],
                "exact endpoint files must be bound")
        runs[run["arm"]] = run
    require(set(runs) == set(ARMS), "one dual replay arm with both endpoints required")
    root = Path(manifest["initialization_extension_root"])
    old = benchmark.load(root / "scripts/ops/autoencoder/benchmark_normative_wording_training.py",
        benchmark.E_RUNNER_SHA, "_balanced_postfit_e_initializer")
    owner = old.load_training_owner()
    previous = SimpleNamespace(**vars(args)); previous.dimension = 384; previous.phase = "preflight"
    previous.manifest = Path(manifest["initialization_manifest"])
    previous.plan = Path(manifest["initialization_plan"]); previous.extension_root = root
    ctx = owner.load_context(previous, deadline); before = owner.source_inventory(previous, ctx)
    lane = ctx["mixture_owner"].prepare_lane(ctx, 384); lane["continuation_manifest"] = manifest
    scalar_owner = benchmark.scalar_observer(ctx, manifest)
    fidelity_owner = benchmark.resident(ctx, "decoder_source_fidelity", root)
    control = bound(manifest["source_inventories"]["control"])
    balanced = bound(manifest["source_inventories"]["balanced"])
    verify_source_inventories(runs[ARMS[0]], {"control": control, "balanced": balanced}, benchmark.PARENT_TENSOR_SHA)
    cohorts = prepare_cohorts(lane, control, balanced, ctx["owners"]["clause_source_context"])
    v3_path = Path(manifest["v3_references"]).resolve()
    require(v3_path not in {Path(p).resolve() for p in manifest["source_inventories"].values()},
        "v3 references must remain a separate posthoc file")
    args.output.mkdir(parents=True); save = ctx["helpers"].save
    durable(save, args.output / "sealed-recipe.json", dict(plan=plan, manifest=manifest, **FALSE))
    records = []
    for arm in ARMS:
        run = runs[arm]
        alias = run["states"]["selected"]["tensor_sha256"] == run["states"]["last-attempt"]["tensor_sha256"]
        for role in ROLES:
            require(time.monotonic() < deadline, "evaluation deadline")
            model = ctx["mixture_owner"].restore_endpoint(lane, run, role)
            require(lane["core"].tensor_digest(model) == run["states"][role]["tensor_sha256"], "exact endpoint tensor differs")
            for cohort in COHORTS:
                sources = cohorts[cohort]; rows = sources["rows"]; contexts = sources["source_contexts"]
                trace = scalar_owner.collect_source_scalar_trace(model, rows, codec=lane["donor"]["codec"],
                    input_transform=lane["donor"]["input_transform"], source_contexts=contexts,
                    max_target_tokens=512, batch_size=8, deadline=min(deadline, time.monotonic() + 60.),
                    max_memory_bytes=PROFILE["max_trace_memory_bytes"])
                verify_trace(trace, rows, contexts, run["states"][role], lane["donor"]["codec"], lane["donor"]["input_transform"])
                require(lane["core"].tensor_digest(model) == run["states"][role]["tensor_sha256"], "observer mutated endpoint")
                folder = args.output / arm / role / cohort
                trace_ref = durable(save, folder / "source-head-trace.json", trace)
                predictions_ref = durable(save, folder / "actual-predictions.json", dict(
                    predictions=trace["predictions"], complete=True, model_tensor_sha256=trace["model_tensor_sha256"],
                    same_pass_scalar_trace_sha256=trace["trace_sha256"], generation_reference_access=False,
                    generation_temperature=0, greedy_passes_per_row=1, **FALSE))
                records.append(dict(arm=arm, role=role, cohort=cohort, state_ref=run["states"][role],
                    trace_ref=trace_ref, predictions_ref=predictions_ref, prediction_fsynced=True,
                    generation_seconds=trace["elapsed_seconds"], selected_last_tensor_alias=alias,
                    physical_panel_computed=True))
                del trace
            del model
    verify_barrier(records)
    durable(save, args.output / "predictions-complete.json", dict(complete=True, records=records,
        v3_reference_json_loaded=False, inherited_TRAIN_validation_metadata_already_loaded=True,
        all_predictions_fsynced=True, logical_panels=8, physical_panels=8, **FALSE))
    # Only now parse the separately bound exposed-v3 references. Historical
    # TRAIN/validation targets were already loaded by the frozen initializer.
    reference_sets = dict(original_train48=original_train_references(lane["rows"]["train"], lane["donor"]["codec"]),
        normative_train48=control["corpus"]["references"],
        new_balanced_train48=balanced["corpus"]["references"], exposed_v3_48=bound(v3_path))
    refs = {name: bind_references(cohorts[name]["rows"], reference_sets[name], lane["donor"]["codec"])
        for name in COHORTS}
    results = []
    for record in records:
        name = record["cohort"]; sources = cohorts[name]; references = refs[name]
        trace = bound_output(record["trace_ref"])
        predictions = bound_output(record["predictions_ref"])
        verify_trace(trace, sources["rows"], sources["source_contexts"], record["state_ref"],
            lane["donor"]["codec"], lane["donor"]["input_transform"])
        require(predictions["predictions"] == trace["predictions"], "durable prediction/trace differs")
        scored_rows = [dict(r, target_ids=reference["target_ids"]) for r, reference in zip(sources["rows"], references)]
        score_deadline = min(deadline, time.monotonic() + max(0., 60. - record["generation_seconds"]))
        started_score = time.monotonic()
        scalar = scalar_owner.score_scalar_trace(trace, scored_rows, references,
            split="exposed_development" if name == "exposed_v3_48" else "training",
            codec=lane["donor"]["codec"], input_transform=lane["donor"]["input_transform"],
            source_contexts=sources["source_contexts"], validate_rule=lane["validate_rule"], deadline=score_deadline)
        fidelity = fidelity_owner.score_predictions(references, predictions["predictions"],
            codec=lane["donor"]["codec"], validate_rule=lane["validate_rule"], output_limit=512,
            validator_id=lane["validator_id"])
        require(fidelity["complete_evaluation"] is True and len(fidelity["rows"]) == 48
            and time.monotonic() < score_deadline, "complete bounded formula evaluation required")
        joined = join_scalar_formula(scalar, fidelity, references)
        folder = args.output / record["arm"] / record["role"] / name
        scalar_ref = durable(save, folder / "posthoc-scalar-score.json", scalar)
        fidelity_ref = durable(save, folder / "actual-formula-fidelity.json", fidelity)
        join_ref = durable(save, folder / "scalar-formula-join.json", joined)
        results.append(dict(record, scalar_score_ref=scalar_ref, formula_fidelity_ref=fidelity_ref,
            scalar_formula_join_ref=join_ref, formula_metrics=fidelity["metrics"],
            seven_facets={f: dict(correct=fidelity["by_facet"][f]["correct"], total=fidelity["by_facet"][f]["total"])
                for f in FACETS}, scalar_by_field=joined["per_field"], paragraphs=48, rules=180,
            scalar_reference_sites=720, scoring_seconds=time.monotonic() - started_score, **FALSE))
        del scalar, fidelity, joined, trace, predictions
    after = owner.source_inventory(previous, ctx)
    require(all(after.get(p) == wanted for p, wanted in before.items()), "resident source changed")
    recheck()
    result = dict(PROFILE, complete=True, panels=results, elapsed_seconds=time.monotonic() - started,
        source_dependencies=after, models_executed=True, optimizer_steps=0,
        initial_candidate_bank_all_four_scalars_correct=summary["initial_balanced_bank_all_four_scalars_correct"],
        interpretation_if_initial_bank_perfect="confidence/coverage comparison; no classification-repair claim",
        timing_scope="source-only generation and pure reference scoring; no encoder or IR/prover throughput",
        reference_denominators_preserved=True, all_v3_references_after_durable_prediction_barrier=True,
        explicit_v3_reference_parse_scope="this writer; frozen initializer retains its historical metadata access",
        withheld_reference_blinding_claimed=False, original_meanings_previously_exposed=True,
        source_alignment_is_authored_positional_fixture=True, source_alignment_verified_as_law=False,
        original_family_and_Lake_gates_preserved=True, no_semantic_or_proof_admission_granted=True)
    durable(save, args.output / "summary.json", result)
    return result


def bound_output(ref):
    require(sha(ref["path"]) == ref["sha256"], "durable output changed before reference join")
    return json.loads(Path(ref["path"]).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dependency-root", "extension-root", "manifest", "plan", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", choices=("evaluation",), required=True)
    execute(parser.parse_args())


if __name__ == "__main__":
    main()
