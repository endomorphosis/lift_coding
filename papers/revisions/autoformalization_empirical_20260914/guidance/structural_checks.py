"""Fixed structural checks over actual native ModalIRDocument outputs.

These checks validate representation and identifier/span binding. They provide
no independent legal-semantic annotation and cannot certify theorem validity.
An empty but well-shaped document may pass structure and has eligible=False.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, Mapping
from learned_route import digest, file_digest
from ipfs_datasets_py.optimizers.logic_theorem_optimizer import modal_ir, modal_registry, legal_modal_parser


def checker_contract() -> dict[str, Any]:
    return {
        "schema": "autoformalization-modal-structural-checks/v1",
        "callbacks_sha256": file_digest(Path(__file__)),
        "native_modules": {name: file_digest(Path(module.__file__)) for name, module in (("modal_ir", modal_ir), ("modal_registry", modal_registry), ("legal_modal_parser", legal_modal_parser))},
        "checks": ["modal_well_formedness", "provenance_preservation"],
        "empty_document": "schema validity separate from zero eligible formula coverage",
        "scope": "schema/registered operators and source identity/span binding, not independent source fidelity or kernel proofs",
    }


def _header(record: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors = []
    ir = record.get("canonical_ir")
    if not isinstance(ir, dict):
        return {}, ["canonical_ir_missing_or_not_object"]
    if record.get("checker_contract") != checker_contract():
        errors.append("checker_contract_mismatch")
    if record.get("record_id") != ir.get("document_id"):
        errors.append("record_document_identifier_mismatch")
    return ir, errors


def modal_well_formedness(record: dict[str, Any]) -> dict[str, Any]:
    ir, errors = _header(record)
    if ir.get("version") != "modal-ir-v1":
        errors.append("wrong_ir_schema")
    for field in ("document_id", "source"):
        if not isinstance(ir.get(field), str) or not ir[field]:
            errors.append(f"missing_{field}")
    if not isinstance(ir.get("normalized_text"), str):
        errors.append("normalized_text_not_string")
    formulas = ir.get("formulas")
    if not isinstance(formulas, list):
        formulas = []
        errors.append("formulas_not_array")
    seen = set()
    typed_formulas = []
    for i, formula in enumerate(formulas):
        prefix = f"formula[{i}]"
        if not isinstance(formula, dict):
            errors.append(f"{prefix}:not_object")
            continue
        formula_id = formula.get("formula_id")
        if not isinstance(formula_id, str) or not formula_id or formula_id in seen:
            errors.append(f"{prefix}:missing_or_duplicate_id")
        seen.add(str(formula_id))
        operator = formula.get("operator")
        predicate = formula.get("predicate")
        provenance = formula.get("provenance")
        if not all(isinstance(v, dict) for v in (operator, predicate, provenance)):
            errors.append(f"{prefix}:typed_fields_missing")
            continue
        try:
            profile = modal_registry.DEFAULT_MODAL_REGISTRY.get_profile(operator.get("family"), operator.get("system"))
            if operator.get("symbol") not in {op.symbol for op in profile.operators}:
                errors.append(f"{prefix}:unregistered_operator")
        except (ValueError, KeyError, TypeError):
            errors.append(f"{prefix}:unregistered_modal_profile")
        if not isinstance(operator.get("label"), str) or not operator["label"]:
            errors.append(f"{prefix}:operator_label_missing")
        if not isinstance(predicate.get("name"), str) or not predicate["name"]:
            errors.append(f"{prefix}:predicate_name_missing")
        arguments = predicate.get("arguments")
        if not isinstance(arguments, list) or not all(isinstance(v, str) for v in arguments):
            errors.append(f"{prefix}:predicate_arguments_not_strings")
        for field in ("conditions", "exceptions"):
            if not isinstance(formula.get(field), list) or not all(isinstance(v, str) for v in formula[field]):
                errors.append(f"{prefix}:{field}_not_strings")
        if not isinstance(formula.get("metadata"), dict):
            errors.append(f"{prefix}:metadata_not_object")
        try:
            typed_formulas.append(modal_ir.ModalIRFormula(
                formula_id=formula_id, operator=modal_ir.ModalIROperator(**operator),
                predicate=modal_ir.ModalIRPredicate(**predicate), provenance=modal_ir.ModalIRProvenance(**provenance),
                conditions=formula["conditions"], exceptions=formula["exceptions"], metadata=formula["metadata"],
            ))
        except (TypeError, KeyError):
            errors.append(f"{prefix}:native_type_construction_failed")
    # Native dataclasses serialize exact fields; explicit validation above is
    # needed because Python annotations alone do not check runtime values.
    return {"passed": not errors, "eligible": bool(formulas) and not errors,
            "formula_count": len(formulas), "typed_formula_count": len(typed_formulas),
            "errors": errors, "native_registry_used": True, "native_types_used": True}


def provenance_preservation(record: dict[str, Any]) -> dict[str, Any]:
    ir, errors = _header(record)
    source = record.get("source_text")
    if not isinstance(source, str):
        return {"passed": False, "eligible": False, "formula_count": 0, "errors": errors+["source_text_missing"], "span_bindings": []}
    if hashlib.sha256(source.encode()).hexdigest() != record.get("text_sha256"):
        errors.append("source_content_hash_mismatch")
    normalized = legal_modal_parser.LegalModalParser().normalize_text(source)
    if ir.get("normalized_text") != normalized:
        errors.append("normalized_source_text_mismatch")
    formulas = ir.get("formulas")
    if not isinstance(formulas, list):
        formulas = []
        errors.append("formulas_not_array")
    bindings = []
    for i, formula in enumerate(formulas):
        prefix = f"formula[{i}]"
        if not isinstance(formula, dict) or not isinstance(formula.get("provenance"), dict):
            errors.append(f"{prefix}:provenance_missing")
            continue
        prov = formula["provenance"]
        start, end = prov.get("start_char"), prov.get("end_char")
        if prov.get("source_id") != ir.get("document_id"):
            errors.append(f"{prefix}:source_identifier_mismatch")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(normalized):
            errors.append(f"{prefix}:source_span_out_of_bounds")
            continue
        fragment = normalized[start:end]
        # Bind the exact surviving source fragment; this does not label whether
        # that span expresses the intended legal meaning of the formula.
        bindings.append({"formula_id": formula.get("formula_id"), "start_char": start, "end_char": end,
                         "fragment_sha256": hashlib.sha256(fragment.encode()).hexdigest()})
    return {"passed": not errors, "eligible": bool(formulas) and not errors,
            "formula_count": len(formulas), "errors": errors, "span_bindings": bindings,
            "independent_semantic_fidelity_measured": False}


CHECKS = {"modal_well_formedness": modal_well_formedness, "provenance_preservation": provenance_preservation}
