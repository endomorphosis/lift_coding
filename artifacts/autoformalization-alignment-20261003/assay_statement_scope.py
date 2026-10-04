"""Replay saved unaccepted candidates into the scope carrier without inference."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
DIRECTORY = CAMPAIGN / "statement-scope-01"
GENERATION = CAMPAIGN / "typed-anchor-decoder-recovery-01/seed1729-source_final_anchor_final-generation.json"
GENERATION_SHA = "dcf45067e366d9faa89a696ae544795b9c977d690f68e78cf2e0141474391ff3"
REQUESTS = CAMPAIGN / "typed-anchor-decoder-recovery-01/inference_requests.json"
REQUESTS_SHA = "1740f42c497901e974ec7cb8f8892bd6208f643c7708313000870ecde9f10595"
PACKET = CAMPAIGN / "binding-review-packet-01/reviewer_items.json"
PACKET_SHA = "8a8303ea83fe22899f798703e7931b1f48a8aa0afb01c7d6980a7d3e9301701e"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load_pinned(path, expected_sha):
    require(binding(path)["sha256"] == expected_sha, "saved input file changed")
    value = json.loads(path.read_bytes())
    if "content_sha256" in value:
        require(value["content_sha256"] == digest({k: v for k, v in value.items()
                                                   if k != "content_sha256"}), "saved input content seal differs")
    return value


def candidate_declaration(proposal, request):
    """Lift exact existing leaves; infer neither extra scope nor full coverage."""
    occurrences = []
    paths = {}
    for index, anchor in enumerate(proposal["anchors"]):
        identity = f"occurrence-{index}"
        paths[anchor["field_path"]] = identity
        occurrences.append({"occurrence_id": identity, "facet": anchor["facet"],
                            "canonical_symbol": anchor["canonical_symbol"],
                            "anchor": {"origin": "source", "start": anchor["start"], "end": anchor["end"],
                                       "text": anchor["source_text"], "offset_unit": anchor["offset_unit"]}})
    flat = proposal["canonical_ir"]["rules"][0]
    qualifiers = {}
    for facet in ("conditions", "exceptions", "temporal"):
        children = [{"op": "leaf", "occurrence_id": paths[f"/rules/0/{facet}/{index}"]}
                    for index in range(len(flat[facet]))]
        qualifiers[facet] = ({"op": proposal["facet_operators"][facet], "children": children,
                              "operator_anchor": None} if children else None)
    declaration = {"schema": "canonical-normative-scope-declaration/v1", "family": "deontic",
                   "profile": "normative-occurrence-scope/v1", "input": request,
                   "input_sha256": digest(request), "occurrences": occurrences,
                   "rules": [{"rule_id": "rule-0", "body": {facet: paths.get(f"/rules/0/{facet}")
                                for facet in ("modality", "actor", "action", "object")},
                              "qualifiers": qualifiers}],
                   "statement_structure": {"op": "rule", "rule_id": "rule-0"}, "binders": [],
                   "coverage": {"declared_status": "unassessed", "segments": []}, "unresolved": []}
    return {**declaration, "content_sha256": digest(declaration)}


def main():
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir.canonical_byte_codec import validate_proposal
    from ipfs_datasets_py.logic.legal_ir.canonical_contracts import BridgeView
    from ipfs_datasets_py.logic.legal_ir.canonical_statement_scope import (
        assess_flat_profile_compatibility,
        validate_scope_declaration,
    )
    from ipfs_datasets_py.logic.legal_ir.canonical_statement_scope_bridge import (
        prepare_scope_bridge_view,
        validate_scope_bridge_view,
    )

    generation = load_pinned(GENERATION, GENERATION_SHA)
    requests = load_pinned(REQUESTS, REQUESTS_SHA)
    packet = load_pinned(PACKET, PACKET_SHA)
    require(len(generation["rows"]) == len(requests["rows"]) == 34 and len(packet["items"]) == 64,
            "source panel accounting differs")
    packet_inputs = {item["input_sha256"] for item in packet["items"]}
    require(all(all(value is None for value in item["annotation"].values()) for item in packet["items"]),
            "current64 annotations must remain blank")
    rows, matches, proposals = [], 0, 0
    for saved in generation["rows"]:
        original = requests["rows"][saved["position"]]
        require(saved["id"] == original["id"], "saved request position/identity differs")
        row = {"position": saved["position"], "saved_id": saved["id"], "saved_outcome": saved["outcome"],
               "saved_source_sha256": saved["source_sha256"], "declaration": None,
               "validation_summary": None, "flat_assessment": None, "bridge_view": None,
               "scope_payload_roundtrip_exact": None}
        source = saved["preflight"]["source_text"]
        require(hashlib.sha256(source.encode("utf-8")).hexdigest() == saved["source_sha256"], "saved source SHA differs")
        context_text = saved["preflight"]["context"]["text"]
        require(source == original["source_text"] and context_text == original["context_text"], "saved request text differs")
        role = "declared_context" if context_text else "required_unavailable" if original["requires_context_resolution"] else "none_required"
        request = {"source_text": source, "context": {"role": role,
                   "text": context_text, "bindings": {}, "sha256": hashlib.sha256(context_text.encode("utf-8")).hexdigest()}}
        matches += digest(request) in packet_inputs
        if saved.get("proposal") is not None:
            proposal = validate_proposal(saved["proposal"], source)
            declaration = candidate_declaration(proposal, request)
            validation = validate_scope_declaration(request, declaration, expected_input_sha256=digest(request))
            view = prepare_scope_bridge_view(request, declaration, expected_input_sha256=digest(request))
            serialized = view.to_dict()
            restored = BridgeView.from_dict(json.loads(raw(serialized)))
            bridge_validation = validate_scope_bridge_view(restored, request, expected_input_sha256=digest(request))
            require(raw(restored.to_dict()) == raw(serialized), "scope bridge view roundtrip differs")
            require(raw(restored.to_dict()["payload"]) == raw(declaration), "scope payload roundtrip differs")
            require(restored.payload_cid == view.payload_cid, "scope view payload CID changed")
            assessment = assess_flat_profile_compatibility(declaration)
            require(all(profile["status"] == "unavailable" for profile in assessment["profiles"].values()),
                    "unassessed candidate coverage must withhold compatibility")
            require(assessment["byte_encoding_capacity"]["checked"] is True, "legacy candidate encoding not checked")
            for value in (validation, assessment):
                require(all(mask == 0 and type(mask) is int for mask in value["masks"].values()), "mask promoted")
                require(value["accepted"] is value["source_fidelity_established"] is value["lowering_authorized"] is False,
                        "scope transport promoted authority")
            row.update(declaration=declaration,
                       validation_summary={k: v for k, v in validation.items() if k != "declaration"},
                       flat_assessment=assessment, bridge_view=serialized,
                       bridge_validation=bridge_validation, scope_payload_roundtrip_exact=True)
            proposals += 1
        rows.append(row)
    require(proposals == generation["proposal_count"] == 17 and matches == 0, "candidate/new64 join accounting differs")
    result = {"schema": "autoformalization-statement-scope-saved-candidate-assay/v1",
              "status": "passed_candidate_transport_only",
              "input_bindings": [binding(GENERATION), binding(REQUESTS), binding(PACKET)],
              "source_panel_count": 34, "saved_outcome_counts": dict(Counter(row["saved_outcome"] for row in rows)),
              "scope_declarations": proposals, "exact_scope_view_roundtrips": proposals,
              "candidate_declared_coverage": "unassessed", "current64_exact_input_joins": matches,
              "current64_annotation_fields_blank": True, "zero_mask_values": proposals * 5,
              "scope_declarations_are_reviews_or_gold": False, "history_model_execution_replayed": False,
              "historical_generation_metadata_loaded": True, "rows": rows,
              "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
              "labels_admitted": 0, "formal_targets_admitted": 0, "source_fidelity_established": False,
              "proof_authority": False, "lowering_authorized": False, "existing_checkpoint_files_modified": False,
              "seal_recipe": "SHA256 sorted compact UTF8 JSON excluding content_sha256; ensure_ascii=False; allow_nan=False"}
    result["content_sha256"] = digest(result)
    DIRECTORY.mkdir(exist_ok=True)
    output = DIRECTORY / "saved-candidate-assay.json"
    with output.open("xb") as stream:
        stream.write(raw(result) + b"\n")
    print(json.dumps({"assay_binding": binding(output), "source_rows": 34, "scope_roundtrips": proposals,
                      "current64_exact_input_joins": matches, "models_or_provers_executed": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
