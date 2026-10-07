"""Posthoc intersection of saved valid parent/candidate proposal emissions.

No numerical module, model, optimizer or Torch is imported. This diagnostic
policy was chosen after final exposure and cannot be a fresh policy evaluation.
It changes neither selections nor weights and is not a learned probability.
"""
import argparse
from collections import Counter
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import sys
import types

PANEL_SCHEMA = "support-action-posthoc-retained-boundary-panel/v1"
COMPOSITE_SCHEMA = "source-proposal-status-intersection/v1"
GERUND_AGENT = "gerund_object_agent_modal_condition"
POLICY = "emit_candidate_iff_parent_status_predicted_AND_candidate_status_predicted"
FLAGS = {"policy_developed_after_final_exposure": True, "posthoc_diagnostic_only": True,
         "model_forward_calls": 0, "optimizer_calls": 0, "selection_changed": False,
         "learned_probability_model": False, "default_promotion": False,
         "legal_gold": False, "Lake_executed": False}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def pin(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def load(reference):
    path = Path(reference["path"]).resolve(); raw = path.read_bytes()
    require({"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()} == reference,
            "pinned artifact differs: " + reference["path"])
    return json.loads(raw)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try: os.fsync(fd)
    finally: os.close(fd)


def mkdir_durable(path):
    missing, current = [], path
    while not current.exists(): missing.append(current); current = current.parent
    path.mkdir(parents=True, exist_ok=True)
    for created in reversed(missing): sync_directory(created.parent)


def write(path, value):
    mkdir_durable(path.parent)
    with path.open("x") as out:
        json.dump(value, out, ensure_ascii=False, allow_nan=False, indent=2)
        out.write("\n"); out.flush(); os.fsync(out.fileno())
    sync_directory(path.parent)
    return pin(path)


def pure_owner(package_root):
    for name, relative in (("ipfs_datasets_py", "ipfs_datasets_py"),
        ("ipfs_datasets_py.logic", "ipfs_datasets_py/logic"),
        ("ipfs_datasets_py.logic.formalization", "ipfs_datasets_py/logic/formalization"),
        ("ipfs_datasets_py.logic.formalization.autoencoder", "ipfs_datasets_py/logic/formalization/autoencoder"),
        ("ipfs_datasets_py.logic.legal_ir", "ipfs_datasets_py/logic/legal_ir")):
        require(name not in sys.modules, "standalone pure-owner process required")
        stub = types.ModuleType(name); stub.__path__ = [str(package_root / relative)]; sys.modules[name] = stub
    return importlib.import_module("ipfs_datasets_py.logic.formalization.autoencoder.legal_scope_span_proposal")


def validate_panel(panel, sources, role, owner):
    require(set(panel) == {"schema", "rows", "references_accessed_by_inference"}
            and panel["schema"] == "support-action-source-only-panel/v1"
            and panel["references_accessed_by_inference"] is False, "saved source-only panel header required")
    rows = panel["rows"]
    require(type(rows) is list and len(rows) == len(sources) == 128
            and {r["id"] for r in rows} == set(sources), "complete unique 128-row panel required")
    by_id = {}
    for row in rows:
        require(set(row) == {"id", "source_group", "source_sha256", "class_logits", "prediction"}, "closed saved row required")
        source = sources[row["id"]]; result = row["prediction"]
        require(row["source_group"] == source["source_group"] and row["source_sha256"] == source["source_sha256"], "source identity differs")
        require(result["schema"] == ("legal-scope-trigger-readout-result/v1" if role == "parent" else "legal-scope-support-action-result/v1"),
                "known saved model result schema required")
        require(result["status"] in ("predicted", "abstained", "blocked") and result["model_executed"] is True
                and result["formal_output"] is None, "saved model execution/authority fields invalid")
        require(all(result[k] is False for k in ("target_access", "targets_used_at_inference", "source_semantics_verified",
            "proof_ready", "proof_authority", "qualified", "accepted", "formalized")), "saved result gained authority/targets")
        logits = row["class_logits"]
        require(type(logits) is list and len(logits) == 3 and all(type(v) is float and math.isfinite(v) for v in logits)
                and logits == result["modality_logits"], "finite saved class logits required")
        require(result["raw_prediction"]["modality"] == ("O", "P", "F")[max(range(3), key=logits.__getitem__)],
                "saved raw modality differs from its source logits")
        probability = result["support_probability"]
        require(type(probability) is float and math.isfinite(probability) and 0 <= probability <= 1
                and result["support_threshold"] == .5, "saved source support metadata invalid")
        if result["status"] == "predicted":
            require(result["prediction"] is not None and result["proposal"] is not None
                    and set(result["masks"]) == set(owner.scope.MASKS)
                    and not any(result["masks"].values()) and not any(result["proposal"]["masks"].values()), "saved emitted proposal authority invalid")
            verified = owner.propose_scope_from_spans(source["source_text"], result["prediction"],
                expected_source_sha256=source["source_sha256"])
            require(verified == result["proposal"] and not any(verified["masks"].values()),
                    "saved predicted status lacks exact structurally valid owner transport")
        else:
            require(result["prediction"] is None and result["proposal"] is None, "nonemission cannot carry wire/proposal")
        by_id[row["id"]] = row
    return by_id


def raw_whole(result, gold):
    return result["status"] == "predicted" and result["prediction"] == gold


def score_composite(rows, sources, references, parent, candidate):
    refs = {r["id"]: r for r in references}
    require(len(refs) == len(rows) == 128 and set(refs) == set(sources), "complete reference join required")
    counts = Counter(); paired = Counter(); templates = {}; categories = {}
    parent_emitted = {key for key, r in parent.items() if r["prediction"]["status"] == "predicted"}
    candidate_emitted = {key for key, r in candidate.items() if r["prediction"]["status"] == "predicted"}
    emitted = {r["id"] for r in rows if r["composite"]["emission_allowed"]}
    require(emitted == parent_emitted & candidate_emitted, "composite must equal strict valid-emission intersection")
    for row in rows:
        ref = refs[row["id"]]; source = sources[row["id"]]; out = row["composite"]
        old = parent[row["id"]]["prediction"]; new = candidate[row["id"]]["prediction"]
        require(ref["source_sha256"] == row["source_sha256"] and ref["source_group"] == row["source_group"], "reference identity differs")
        require(ref["independent_legal_review"] is False and not any(ref["admission_masks"].values()), "authored engineering references required")
        if ref["supported"]:
            gold = ref["prediction"]; exact = out["emission_allowed"] and out["wire"] == gold
            old_exact = raw_whole(old, gold); new_exact = raw_whole(new, gold)
            counts["positive_count"] += 1; counts["positive_emitted_count"] += out["emission_allowed"]
            counts["positive_whole_exact_count"] += exact; counts["parent_positive_whole_exact_count"] += old_exact
            counts["raw_candidate_positive_whole_exact_count"] += new_exact
            condition = gold["spans"]["condition"] is not None
            counts["nonempty_condition_count"] += condition; counts["nonempty_condition_whole_exact_count"] += condition and exact
            counts["parent_nonempty_condition_whole_exact_count"] += condition and old_exact
            counts["raw_candidate_nonempty_condition_whole_exact_count"] += condition and new_exact
            paired["both_whole_exact" if old_exact and exact else "parent_whole_exact_lost" if old_exact
                   else "composite_whole_exact_gained" if exact else "both_whole_inexact"] += 1
            entry = templates.setdefault(source["template"], {"count":0,"parent_whole_exact":0,"raw_candidate_whole_exact":0,"composite_whole_exact":0,"composite_emitted":0})
            entry["count"] += 1; entry["parent_whole_exact"] += old_exact; entry["raw_candidate_whole_exact"] += new_exact
            entry["composite_whole_exact"] += exact; entry["composite_emitted"] += out["emission_allowed"]
        else:
            require(ref["prediction"] is None, "unsupported row cannot have a target wire")
            counts["negative_count"] += 1; counts["unsupported_emitted_count"] += out["emission_allowed"]
            counts["parent_unsupported_emitted_count"] += old["status"] == "predicted"
            counts["raw_candidate_unsupported_emitted_count"] += new["status"] == "predicted"
            entry = categories.setdefault(ref["unsupported_category"], {"count":0,"parent_emitted":0,"raw_candidate_emitted":0,"composite_emitted":0})
            entry["count"] += 1; entry["parent_emitted"] += old["status"] == "predicted"
            entry["raw_candidate_emitted"] += new["status"] == "predicted"; entry["composite_emitted"] += out["emission_allowed"]
    require(counts["positive_count"] == counts["negative_count"] == 64 and counts["nonempty_condition_count"] == 32,
            "complete authored denominators required")
    require(GERUND_AGENT in templates and templates[GERUND_AGENT]["count"] == 8, "exact eight-case gerund-agent key required")
    require(counts["unsupported_emitted_count"] <= counts["parent_unsupported_emitted_count"], "intersection added unsupported emissions")
    return {"counts":dict(counts),"whole_exact_transitions_vs_parent":dict(paired),"templates":templates,
        "gerund_agent_template_key":GERUND_AGENT,"gerund_agent":templates[GERUND_AGENT],"unsupported_categories":categories,
        "emission_subset_proof":{"composite_emission_ids":sorted(emitted),"parent_emission_ids":sorted(parent_emitted),
            "candidate_emission_ids":sorted(candidate_emitted),"strict_intersection_equal":True,
            "added_parent_boundary_emissions":0,"added_unsupported_emissions":0},
        "no_learned_probability_or_refusal_metric":True, **FLAGS}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(); root = Path(__file__).resolve().parent
    output = (args.output or root/"retained-boundary").resolve()
    require(not output.exists(), "diagnostic output already exists")
    require(not any(n == "torch" or n.startswith("torch.") for n in sys.modules), "no Torch allowed")
    sys.dont_write_bytecode = True
    script_ref = pin(Path(__file__)); plan_ref = pin(root/"experiment-plan.json"); plan = load(plan_ref)
    result_root = args.results.resolve(); result_ref = pin(result_root/"training-results.json"); result = load(result_ref)
    require(result["status"] == "completed" and result["plan"] == plan_ref, "completed pinned raw experiment required")
    require(result["producer_pins"] == plan["producer_pins"], "producer metadata differs")
    raw_barrier_ref = result["predictions_barrier"]; raw_barrier = load(raw_barrier_ref)
    require(raw_barrier["schema"] == "support-action-output-barrier/v1" and raw_barrier["evaluation_references_parsed"] is False,
            "original nine-panel source-only barrier required")
    package_root = root/"datasets"; owner = pure_owner(package_root)
    require(pin(Path(owner.__file__))["sha256"] == plan["producer_pins"]["trigger_producer"]["donor_producer"]["proposal_sha256"]
        and pin(Path(owner.scope.__file__))["sha256"] == plan["producer_pins"]["trigger_producer"]["donor_producer"]["scope_sha256"], "pure transport owners differ")
    producer_files = {}
    for relative, expected in (
        ("ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_support_action.py", plan["producer_pins"]["implementation_sha256"]),
        ("ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_trigger_readout.py",plan["producer_pins"]["trigger_producer"]["implementation_sha256"]),
        ("ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_decoder.py",plan["producer_pins"]["trigger_producer"]["donor_producer"]["implementation_sha256"]),
        ("ipfs_datasets_py/logic/formalization/autoencoder/legal_scope_span_proposal.py",plan["producer_pins"]["trigger_producer"]["donor_producer"]["proposal_sha256"]),
        ("ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py",plan["producer_pins"]["trigger_producer"]["donor_producer"]["scope_sha256"])):
        reference=pin(package_root/relative);require(reference["sha256"]==expected,"frozen producer file changed");producer_files[relative]=reference
    selected={}
    for kind in ("linear","mlp"):
        reference=pin(result_root/kind/"selected.json"); choice=load(reference)
        require(choice==result["arms"][kind]["selected"],"selected receipt differs")
        require(pin(choice["checkpoint"]["path"])==choice["checkpoint"],"selected checkpoint bytes changed")
        selected[kind]={"selected_receipt":reference,"checkpoint":choice["checkpoint"],"completed_updates":choice["completed_updates"]}
    cohorts={"fresh_final":{"inputs":plan["inputs"]["final"],"references":plan["references"]["final"]},**plan["retention"]}
    panels={}; sources_by_cohort={}; raw_by_cohort={}; panel_refs={}; retransported=0
    mkdir_durable(output)
    for cohort, definition in cohorts.items():
        inputs=load(definition["inputs"]);sources={r["id"]:r for r in inputs}
        require(len(inputs)==len(sources)==128,"unique bounded inputs required")
        for source in inputs:
            require(set(source)=={"id","source_group","template","condition_attachment","source_text","source_sha256"}
                and sha256(source["source_text"].encode()).hexdigest()==source["source_sha256"],"closed exact-byte source input required")
        raw={kind:validate_panel(load(raw_barrier["panels"][kind+"/"+cohort]),sources,kind,owner) for kind in ("parent","linear","mlp")}
        sources_by_cohort[cohort]=sources;raw_by_cohort[cohort]=raw
        for kind in ("linear","mlp"):
            rows=[]
            for source in inputs:
                key=source["id"];old=raw["parent"][key];new=raw[kind][key];parent=old["prediction"];candidate=new["prediction"]
                require(old["class_logits"]==new["class_logits"] and parent["raw_prediction"]["presence"]==candidate["raw_prediction"]["presence"]
                    and all(parent["raw_prediction"]["token_spans"][f]==candidate["raw_prediction"]["token_spans"][f]
                            for f in ("modality","actor","object","condition")),"frozen raw fields differ")
                allowed=parent["status"]=="predicted" and candidate["status"]=="predicted"
                wire=candidate["prediction"] if allowed else None;transported=None
                if allowed:
                    transported=owner.propose_scope_from_spans(source["source_text"],wire,expected_source_sha256=source["source_sha256"])
                    require(transported==candidate["proposal"] and not any(transported["masks"].values()),"allowed candidate transport differs or gained authority")
                    retransported+=1
                composite={"schema":COMPOSITE_SCHEMA,"decision":"emit_candidate" if allowed else "withhold",
                    "emission_allowed":allowed,"wire":wire,"proposal":transported,"parent_status":parent["status"],
                    "candidate_status":candidate["status"],"parent_saved_result_sha256":sha256(canonical(parent)).hexdigest(),
                    "candidate_saved_result_sha256":sha256(canonical(candidate)).hexdigest(),"formal_output":None,
                    "masks":dict.fromkeys(owner.scope.MASKS,0),"proof_ready":False,"proof_authority":False,
                    "source_semantics_verified":False,"accepted":False,"qualified":False,"formalized":False,
                    "model_executed":False,"references_used_for_composition":False,**FLAGS}
                rows.append({"id":key,"source_group":source["source_group"],"source_sha256":source["source_sha256"],"composite":composite})
            panels[(kind,cohort)]=rows
            panel_refs[kind+"/"+cohort]=write(output/kind/(cohort+"-composite-proposals.json"),
                {"schema":PANEL_SCHEMA,"policy":POLICY,"input":definition["inputs"],"parent_panel":raw_barrier["panels"]["parent/"+cohort],
                 "candidate_panel":raw_barrier["panels"][kind+"/"+cohort],"rows":rows,"references_joined":False,**FLAGS})
    # All six source-derived composites are fsynced BEFORE any reference parse.
    barrier_ref=write(output/"all-composites-before-reference-joins.json",{"schema":"posthoc-retained-boundary-reference-barrier/v1",
        "panels":panel_refs,"references_joined":False,"policy":POLICY,**FLAGS})
    scores={}
    for cohort, definition in cohorts.items():
        references=load(definition["references"])
        scores[cohort]={kind:score_composite(panels[(kind,cohort)],sources_by_cohort[cohort],references,
                         raw_by_cohort[cohort]["parent"],raw_by_cohort[cohort][kind]) for kind in ("linear","mlp")}
    require(not any(n=="torch" or n.startswith("torch.") for n in sys.modules),"diagnostic imported Torch")
    require(not any(n.endswith((".legal_scope_support_action",".legal_scope_trigger_readout",".legal_scope_span_decoder")) for n in sys.modules),
            "diagnostic imported a numerical module")
    require(pin(Path(__file__))==script_ref,"diagnostic source changed during execution")
    receipt={"schema":"support-action-posthoc-retained-boundary-results/v1","status":"completed","policy":POLICY,**FLAGS,
        "source":script_ref,"plan":plan_ref,"raw_training_results":result_ref,"raw_prediction_barrier":raw_barrier_ref,
        "selected_checkpoints_unchanged":selected,"frozen_producer_files":producer_files,"pure_proposal_owner":pin(Path(owner.__file__)),
        "pure_scope_owner":pin(Path(owner.scope.__file__)),"composite_panels":panel_refs,"composition_barrier":barrier_ref,
        "inputs":{name:value["inputs"] for name,value in cohorts.items()},"references_joined_only_for_posthoc_scores":{name:value["references"] for name,value in cohorts.items()},
        "composite_rows":768,"retransported_allowed_candidate_proposals":retransported,"scores":scores,
        "interpretation":"Source-derived strict intersection cannot add emissions outside the parent's valid-proposal boundary. Existing parent unsupported emissions may remain. Whole-proposal gains within that boundary are a posthoc diagnostic, not fresh policy or classifier performance.",
        "limitations":["Policy chosen after observing exposed final tradeoff; requires a future sealed trial before evaluation.",
            "Not pooled with raw model metrics, no calibrated support probability or newly learned refusal claim.",
            "Intersection cannot recover parent refusals/structural blocks and does not establish source completeness or law semantics.",
            "Authored engineering targets only; all masks0 and formal output null; no default/runtime promotion."]}
    result_ref=write(output/"retained-boundary-results.json",receipt)
    print(json.dumps({"status":"completed","source":script_ref,"results":result_ref,
        "metrics":{name:{kind:{"whole_exact":score["counts"].get("positive_whole_exact_count",0),
            "condition_exact":score["counts"].get("nonempty_condition_whole_exact_count",0),
            "unsupported_emitted":score["counts"].get("unsupported_emitted_count",0),"gerund_agent":score["gerund_agent"],
            "paired_whole":score["whole_exact_transitions_vs_parent"]} for kind,score in cohort.items()} for name,cohort in scores.items()}}))


if __name__=="__main__":main()
