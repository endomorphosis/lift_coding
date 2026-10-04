"""Authored CodebaseIR controls; expectations never grant evidence authority.

This module uses only Python's standard library. Raw source bytes, requirement
spans, and expected dispositions are exported for an independently owned route
to consume. It neither executes fixture repository code nor signs observations.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "codebase-ir-acceptance-fixtures@1"
PROFILE = "python-integer-offset-finite@1"
TYPE_CLAUSE = "finite-integer-type-goal"
OFFSET_CLAUSE = "finite-integer-offset-goal"
INPUTS = [-2, -1, 0, 1, 2]
FALSE_AUTHORITY = (
    "source_semantics_verified", "runtime_behavior_verified", "behavior_authority",
    "proof_authority", "execution_authority", "completion_authority", "mutation_authority",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def structured_sha256(value: Any) -> str:
    return sha256(canonical_bytes(value))


def finite_prompt(*, offset: int = 2, inputs: list[int] | None = None,
                  path: str = "calc.py", function_name: str = "increment") -> str:
    domain = json.dumps(INPUTS if inputs is None else inputs, separators=(",", ":"))
    prefix = f"Under {PROFILE}, {path}::{function_name}(n) must return "
    suffix = f" for inputs {domain}."
    sign = "+" if offset >= 0 else "-"
    return prefix + "an exact int" + suffix + "\n" + prefix + f"n {sign} {abs(offset)}" + suffix


def source_function(offset: int = 1) -> bytes:
    return f"def increment(n: int) -> int:\n    return n + {offset}\n".encode("ascii")


def source_inventory() -> dict[str, bytes]:
    return {
        "calc.py": source_function(),
        "decoy.py": source_function(2),
        "helpers.py": b"def plus_one(n: int) -> int:\n    return n + 1\n",
        "consumer.py": (b"from calc import increment\nfrom helpers import plus_one\n\n"
                        b"def combine(n: int) -> int:\n    return increment(plus_one(n))\n"),
        "effectful.py": (b"def persist(n: int) -> int:\n    print(n)\n    return n + 1\n"),
    }


def _byte_offset(raw_lines: list[bytes], line: int, column: int) -> int:
    """AST columns count UTF-8 bytes; retain original CRLF line widths."""
    return sum(map(len, raw_lines[:line - 1])) + column


def source_record(path: str, raw: bytes) -> dict[str, Any]:
    if (type(path) is not str or PurePosixPath(path).as_posix() != path
            or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts):
        raise ValueError("canonical repository-relative source path required")
    tree = ast.parse(raw.decode("utf-8"))
    lines = raw.splitlines(keepends=True)
    symbols = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        start = _byte_offset(lines, node.lineno, node.col_offset)
        end = _byte_offset(lines, node.end_lineno, node.end_col_offset)
        selected = raw[start:end]
        symbols.append({"symbol_name": node.name, "kind": type(node).__name__,
            "start_byte": start, "end_byte": end, "source_slice_sha256": sha256(selected),
            "selector_id": structured_sha256({"path": path, "source_sha256": sha256(raw),
                "symbol_name": node.name, "start_byte": start, "end_byte": end})})
    imported_paths = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_paths.append(node.module.replace(".", "/") + ".py")
        elif isinstance(node, ast.Import):
            imported_paths.extend(alias.name.replace(".", "/") + ".py" for alias in node.names)
    return {"path": path, "sha256": sha256(raw), "size_bytes": len(raw),
        "symbols": symbols, "dependencies": sorted(set(imported_paths))}


def requirement_ledger(prompt: str, *, path: str, function_name: str,
                       desired_offset: int, domain_inputs: list[int],
                       meaning: str = "finite") -> dict[str, Any]:
    """Independent authored requirement input, outside captured training truth."""
    clauses = []
    cursor = 0
    for index, text in enumerate(prompt.split("\n")):
        clause_id = (TYPE_CLAUSE, OFFSET_CLAUSE)[index] if index < 2 else f"additional-clause:{index}"
        start, end = cursor, cursor + len(text)
        byte_start = len(prompt[:start].encode("utf-8"))
        byte_end = len(prompt[:end].encode("utf-8"))
        clauses.append({"clause_id": clause_id, "text": text,
            "start_char": start, "end_char": end,
            "start_byte": byte_start, "end_byte": byte_end,
            "meaning": meaning if index > 0 else "finite_exact_integer_type"})
        cursor = end + 1
    body = {"schema": "codebase-ir-authored-requirement-ledger@1",
        "source_sha256": sha256(prompt.encode("utf-8")), "original_prompt": prompt,
        "clauses": clauses, "target": {"path": path, "function_name": function_name, "parameter": "n"},
        "domain_inputs": domain_inputs, "desired_offset": desired_offset,
        "requirement_origin": "authored_qualification_control",
        "review_ref": "review:authored-fixture-requirements@1",
        "review_is_production_authority": False,
        "training_truth_is_requirement_input": False}
    return dict(body, ledger_sha256=structured_sha256(body))


def _eval_arithmetic(node: ast.AST, n: int) -> int | bool:
    if isinstance(node, ast.Name) and node.id == "n":
        return n
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in {ast.Add, ast.Sub}:
        left, right = _eval_arithmetic(node.left, n), _eval_arithmetic(node.right, n)
        if type(left) is not int or type(right) is not int:
            raise ValueError("exact integer arithmetic required")
        return left + right if isinstance(node.op, ast.Add) else left - right
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        left, right = _eval_arithmetic(node.left, n), _eval_arithmetic(node.comparators[0], n)
        comparisons = {ast.GtE: lambda: left >= right, ast.Gt: lambda: left > right,
                       ast.LtE: lambda: left <= right, ast.Lt: lambda: left < right,
                       ast.Eq: lambda: left == right}
        if type(node.ops[0]) in comparisons:
            return comparisons[type(node.ops[0])]()
    raise ValueError("reference arithmetic excludes calls, effects, names and other syntax")


def authored_reference_rows(raw: bytes, inputs: list[int]) -> list[dict[str, int]]:
    """Interpret only authored arithmetic; this is an oracle, not native evidence."""
    tree = ast.parse(raw.decode("utf-8"))
    if len(tree.body) != 1 or type(tree.body[0]) is not ast.FunctionDef:
        raise ValueError("one authored function required")
    function = tree.body[0]
    rows = []
    for n in inputs:
        if type(n) is not int:
            raise ValueError("exact integer reference input required")
        def returned(statements: list[ast.stmt], argument: int) -> int | None:
            for statement in statements:
                if isinstance(statement, ast.Return):
                    value = _eval_arithmetic(statement.value, argument)
                    if type(value) is not int:
                        raise ValueError("exact integer reference return required")
                    return value
                if isinstance(statement, ast.If):
                    result = returned(statement.body if _eval_arithmetic(statement.test, argument) else statement.orelse, argument)
                    if result is not None:
                        return result
                else:
                    raise ValueError("reference interpreter excludes effects and unsupported statements")
            return None
        value = returned(function.body, n)
        if value is None:
            raise ValueError("reference function has no return")
        rows.append({"input": n, "output": value})
    return rows


def _training_truth(raw: bytes) -> dict[str, Any]:
    tree = ast.parse(raw.decode("utf-8"))
    offset = None
    if len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef):
        body = tree.body[0].body
        if len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.BinOp):
            expression = body[0].value
            if isinstance(expression.left, ast.Name) and expression.left.id == "n" and isinstance(expression.right, ast.Constant):
                if type(expression.right.value) is int and type(expression.op) in {ast.Add, ast.Sub}:
                    offset = expression.right.value * (-1 if isinstance(expression.op, ast.Sub) else 1)
    return {"schema": "codebase-ir-captured-training-truth@1", "origin": "captured_source_bytes",
        "source_sha256": sha256(raw), "body_offset": offset,
        "normalized_ast": ast.dump(tree, annotate_fields=True, include_attributes=False),
        "desired_requirement_excluded": True, "authority": "source_label_only"}


def scenarios() -> list[dict[str, Any]]:
    inventory, prompt = source_inventory(), finite_prompt()
    controls = [
        ("baseline", {}, prompt, "finite", "supported_finite", 2, INPUTS),
        ("successor", {"calc.py": source_function(2)}, prompt, "finite", "supported_finite", 2, INPUTS),
        ("changed_literal", {"calc.py": source_function(3)}, prompt, "finite", "supported_finite", 2, INPUTS),
        ("changed_guard", {"calc.py": b"def increment(n: int) -> int:\n    if n >= 0:\n        return n + 1\n    return n + 2\n"}, prompt, "finite", "unsupported_source", 2, INPUTS),
        ("changed_guard_polarity", {"calc.py": b"def increment(n: int) -> int:\n    if n < 0:\n        return n + 1\n    return n + 2\n"}, prompt, "finite", "unsupported_source", 2, INPUTS),
        ("unicode_span", {"calc.py": b"# caf\xc3\xa9 \xf0\x9f\x8c\xb1\n" + source_function()}, prompt, "finite", "unsupported_source", 2, INPUTS),
        ("crlf_span", {"calc.py": source_function().replace(b"\n", b"\r\n")}, prompt, "finite", "unsupported_source", 2, INPUTS),
        ("unicode_crlf_span", {"calc.py": b"# caf\xc3\xa9 \xf0\x9f\x8c\xb1\r\n" + source_function().replace(b"\n", b"\r\n")}, prompt, "finite", "unsupported_source", 2, INPUTS),
        ("formatting", {"calc.py": b"# exact authored formatting variant\n\n" + source_function()}, prompt, "finite", "supported_finite", 2, INPUTS),
        ("changed_requirement", {}, finite_prompt(offset=3), "finite", "supported_finite", 3, INPUTS),
        ("changed_domain", {}, finite_prompt(inputs=[0, 1, 2]), "finite", "supported_finite", 2, [0, 1, 2]),
        ("unbounded", {}, prompt.replace("for inputs [-2,-1,0,1,2]", "for every Python integer"), "unbounded", "refusal_invalid_cnl", 2, INPUTS),
        ("prohibition", {}, prompt.replace("must return n + 2", "must not return n + 2"), "prohibition", "refusal_invalid_cnl", 2, INPUTS),
        ("ambiguous", {}, prompt.replace("must return n + 2", "must return a better value"), "ambiguous", "refusal_invalid_cnl", 2, INPUTS),
        ("effect_requirement", {}, prompt + "\nDo not print, write files, or access the network.", "effect_prohibition", "refusal_invalid_cnl", 2, INPUTS),
        ("changed_requirement_guard", {}, prompt.replace("must return n + 2", "must return n + 2 when n >= 0"), "conditional", "refusal_invalid_cnl", 2, INPUTS),
        ("wrong_named_target", {}, finite_prompt(path="decoy.py"), "finite", "supported_finite", 2, INPUTS),
    ]
    result = []
    for scenario_id, changes, request, meaning, disposition, desired_offset, inputs in controls:
        sources = dict(inventory, **changes)
        selected_path = "decoy.py" if scenario_id == "wrong_named_target" else "calc.py"
        ledger = requirement_ledger(request, path=selected_path, function_name="increment",
            desired_offset=desired_offset, domain_inputs=inputs, meaning=meaning)
        records = [source_record(path, raw) for path, raw in sorted(sources.items())]
        source_snapshot = structured_sha256([{key: row[key] for key in ("path", "sha256", "size_bytes")} for row in records])
        rows = authored_reference_rows(sources[selected_path], inputs)
        expected_eligible = []
        clause_ids = [row["clause_id"] for row in ledger["clauses"]]
        if disposition == "supported_finite":
            expected_eligible = [TYPE_CLAUSE]
            if all(row["output"] == row["input"] + desired_offset for row in rows):
                expected_eligible.append(OFFSET_CLAUSE)
        residual = sorted(set(clause_ids) - set(expected_eligible))
        expected = {"authority": "authored_expectations_only", "route_disposition": disposition,
            "eligible_clause_ids_after_fresh_native_check": sorted(expected_eligible),
            "residual_clause_ids": residual, "preserved_clause_ids": sorted(clause_ids),
            "reference_rows": rows,
            "counterexamples": [{"statement_id": OFFSET_CLAUSE,
                "input": row["input"], "observed_output": row["output"],
                "expected_output": row["input"] + desired_offset} for row in rows
                if row["output"] != row["input"] + desired_offset] if disposition == "supported_finite" else [],
            "unbounded_behavior_status": "unresolved", "must_not_grant_authority": list(FALSE_AUTHORITY),
            "unsupported_inventory_paths": ["consumer.py", "effectful.py"],
            "unit_dispositions": {path: ("unsupported_finite_source" if path in {"consumer.py", "effectful.py"}
                or (path == selected_path and disposition == "unsupported_source") else
                "selected_finite_source" if path == selected_path else "unselected_captured_source") for path in sorted(sources)},
            "parser_refusal_must_preserve_original_ledger": disposition == "refusal_invalid_cnl"}
        selected = next(row for row in records if row["path"] == selected_path)
        selector = next(row for row in selected["symbols"] if row["symbol_name"] == "increment")
        result.append({"scenario_id": scenario_id, "repository_path": f"scenarios/{scenario_id}/source",
            "revision_marker": "authored-same-head-control@1", "revision_marker_is_git_head": False,
            "source_snapshot_sha256": source_snapshot, "sources": records,
            "selected": {"path": selected_path, "function_name": "increment", "parameter": "n",
                "source_sha256": selected["sha256"], "selector": selector},
            "requirements": ledger, "training_truth": _training_truth(sources[selected_path]),
            "expected": expected, "source_bytes": sources})
    return result


def evidence_mutation_specs(baseline: dict[str, Any]) -> list[dict[str, Any]]:
    """Concrete mutation operations on genuine owner records, never fake proofs."""
    controls = [
        ("same_head_source_edit", "live_repository", "calc.py", "replace_source_with_successor", "source byte drift must refuse old generation"),
        ("wrong_symbol_identity", "source_selector", "path", "decoy.py", "same-name decoy cannot discharge selected calc.py"),
        ("wrong_source_digest", "observation", "source_sha256", "0" * 64, "exact selected source binding must fail"),
        ("wrong_domain", "observation", "domain_inputs", [0, 1, 2], "finite trace domain must match reviewed input set"),
        ("missing_trace_row", "observation", "observations", "remove_last_row", "complete domain coverage required"),
        ("altered_trace_output", "observation", "observations[0].output", 999, "rechecked recorded table must agree with captured body"),
        ("authority_escalation", "observation", "behavior_authority", True, "finite table cannot assert unrestricted behavior"),
        ("wrong_checkpoint", "generation_envelope", "selected_model_checkpoint", "sha256:" + "0" * 64, "selected model identity or explicit model-off must agree at all crossings"),
        ("wrong_policy", "generation_envelope", "policy_root", "sha256:" + "0" * 64, "live owner policy roots must agree"),
        ("caller_preview_admission", "preview_receipt", "production_admitted", True, "preview flags cannot grant independent native admission"),
        ("wrong_requirement", "requirement_ledger", "desired_offset", 3, "different clause meaning cannot reuse original evidence"),
        ("missing_clause", "requirement_ledger", "clauses", "remove_last_clause", "every normative clause must retain a disposition"),
        ("changed_effect", "operation_binding", "operation", "delete", "worker effects must match reviewed update operation"),
    ]
    return [{"mutation_id": mutation_id, "apply_to": record, "field": field, "replacement": replacement,
        "baseline_scenario_id": baseline["scenario_id"],
        "expected_disposition": "refusal", "assertion": assertion,
        "execution_status": "specified_for_genuine_owner_record", "evidence_generated": False}
        for mutation_id, record, field, replacement, assertion in controls]


def corpus_audit_input(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Deliberately leaky cohort used to check the independent split auditor."""
    base = cases[0]
    units = []
    for path, raw in sorted(base["source_bytes"].items()):
        record = next(row for row in base["sources"] if row["path"] == path)
        units.append({"id": f"baseline:{path}", "role": "train" if path != "consumer.py" else "final",
            "repository_id": "repository:authored-acceptance-corpus", "path": path, "revision": "fixture:initial",
            "content_sha256": record["sha256"], "source": {"bytes_hex": raw.hex()},
            "dependencies": [f"baseline:{dependency}" for dependency in record["dependencies"]],
            "dependencies_complete": True, "related_revisions": [], "revision_relations_complete": True})
    for scenario_id, role in (("formatting", "tune"), ("successor", "canary"), ("changed_literal", "final")):
        case = next(case for case in cases if case["scenario_id"] == scenario_id)
        raw = case["source_bytes"]["calc.py"]
        units.append({"id": f"{scenario_id}:calc.py", "role": role,
            "repository_id": "repository:authored-acceptance-corpus", "path": "calc.py", "revision": f"fixture:{scenario_id}",
            "content_sha256": sha256(raw), "source": {"bytes_hex": raw.hex()}, "dependencies": [],
            "dependencies_complete": True, "related_revisions": ["baseline:calc.py"],
            "revision_relations_complete": True})
    return {"schema": "codebase-ir-corpus-audit-input@1", "units": units,
        "native_records": [], "ancestral_training": [], "ancestry_complete": True}


def generate(output: Path) -> dict[str, Any]:
    """Write exclusively to a fresh private output directory."""
    output = output.resolve()
    if output.exists():
        raise ValueError("output must be a fresh directory")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    cases = scenarios()
    exported = []
    for case in cases:
        directory = output / case["repository_path"]
        directory.mkdir(mode=0o700, parents=True)
        for path, raw in case["source_bytes"].items():
            with (directory / path).open("xb") as stream:
                stream.write(raw)
        prompt_path = directory.parent / "prompt.txt"
        with prompt_path.open("xb") as stream:
            stream.write(case["requirements"]["original_prompt"].encode("utf-8"))
        exported.append({key: value for key, value in case.items() if key != "source_bytes"})
    body = {"schema": SCHEMA, "profile": PROFILE, "production_qualified": False,
        "authority": "authored_expectations_only", "fixture_code_executed": False,
        "scenarios": exported, "evidence_mutations": evidence_mutation_specs(cases[0]),
        "integration_gates": {
            "source_inventory": "all five units retained; effectful/consumer units explicitly unsupported",
            "entity_binding": "calc.py::increment differs from decoy.py::increment despite equal symbol names",
            "requirements": "both stable finite clause IDs bound to original prompt, domain and selected bytes",
            "training_truth": "baseline n+1 body remains target; authored desired n+2 is separate",
            "admission": "independent native owner compares full frozen envelope with freshly observed roots",
            "launch": "fresh reservation and complete signed task population retained",
            "successor": "same-HEAD byte change refuses old source; fresh capture and recheck required",
            "history": "retained preview/evidence readback is historical; no current authority inferred",
        }, "current_interface_limits": {
            "native_source_profile": "one ASCII/LF integer-offset function per selected complete module",
            "native_prompt_profile": "exactly two canonical finite integer sentences",
            "proof_vs_source": "Lean table arithmetic does not establish universal CPython equivalence",
            "worker_admission": "not exercised by this fixture generator",
        }}
    manifest = dict(body, manifest_sha256=structured_sha256(body))
    for name, value in (("manifest.json", manifest), ("corpus_audit_input.json", corpus_audit_input(cases))):
        with (output / name).open("xb") as stream:
            stream.write(canonical_bytes(value) + b"\n")
    return manifest


def validate_materialized_sources(output: Path, manifest: dict[str, Any]) -> None:
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("schema") != SCHEMA or manifest.get("manifest_sha256") != structured_sha256(body):
        raise ValueError("fixture manifest identity differs")
    for case in manifest["scenarios"]:
        for row in case["sources"]:
            raw = (output / case["repository_path"] / row["path"]).read_bytes()
            if source_record(row["path"], raw) != row:
                raise ValueError(f"materialized exact source or byte selector differs: {case['scenario_id']}:{row['path']}")


def validate_native_result(result: dict[str, Any], case: dict[str, Any]) -> None:
    """Compare a genuine matcher return with the oracle, without granting trust.

    This validates integration assertions only. The owner must authenticate and
    independently check result bytes/custody before admission. A caller can forge
    a structurally matching dictionary; passing this function cannot admit it.
    """
    expected = case["expected"]
    if expected["route_disposition"] == "refusal_invalid_cnl":
        raise ValueError("this control requires parser refusal with external ledger preservation")
    for name in FALSE_AUTHORITY:
        if result.get(name) is not False:
            raise ValueError(f"finite result escalates or omits authority field: {name}")
    if result.get("scope") != "explicit_finite_domain_only" or result.get("unbounded_behavior_status") != "unresolved":
        raise ValueError("finite scope or unbounded residual differs")
    if result.get("eligible_clause_ids") != expected["eligible_clause_ids_after_fresh_native_check"]:
        raise ValueError("eligible clauses differ")
    if result.get("residual_clause_ids") != expected["residual_clause_ids"]:
        raise ValueError("residual clauses differ")
    if result.get("removed_task_ids") != []:
        raise ValueError("initial task population cannot be silently reduced")
    typed = result.get("typed_intent", {})
    mapping = typed.get("metadata", {}).get("requirement_predicate_ids", {})
    if set(mapping) != set(expected["preserved_clause_ids"]) or len(set(mapping.values())) != len(mapping):
        raise ValueError("complete distinct requirement predicates required")
    clause_results = result.get("clause_results", [])
    if type(clause_results) is not list or len(clause_results) != len(mapping):
        raise ValueError("complete unique clause results required")
    by_clause = {row["statement_id"]: row for row in clause_results}
    if set(by_clause) != set(expected["preserved_clause_ids"]):
        raise ValueError("every clause needs a result disposition")
    if any(by_clause[clause].get("predicate_id") != predicate for clause, predicate in mapping.items()):
        raise ValueError("clause ordering swapped a predicate binding")
    facts = result.get("current_facts", [])
    expected_predicates = {mapping[clause] for clause in expected["eligible_clause_ids_after_fresh_native_check"]}
    if (len(facts) != len(expected_predicates)
            or {fact.get("predicate", {}).get("predicate_id") for fact in facts} != expected_predicates):
        raise ValueError("facts must bind precisely to eligible clause predicates")
    for fact in facts:
        if (fact.get("authority") != "bounded_observation" or fact.get("truth") != "true"
                or not result.get("current_root_id") or fact.get("current_root_id") != result["current_root_id"]):
            raise ValueError("finite fact authority or current source root differs")
    observation = result.get("observation")
    if type(observation) is not dict or observation.get("source_path") != case["selected"]["path"]:
        raise ValueError("selected source path differs or observation absent")
    if observation.get("source_sha256") != case["selected"]["source_sha256"]:
        raise ValueError("selected source bytes differ")
    domain = observation.get("domain_inputs")
    if (type(domain) is not list or any(type(value) is not int for value in domain)
            or domain != case["requirements"]["domain_inputs"]):
        raise ValueError("explicit finite domain differs")
    contract = observation.get("contract", {})
    target = case["requirements"]["target"]
    if any(contract.get(key) != target[key] for key in ("path", "function_name", "parameter")) or contract.get("offset") != case["requirements"]["desired_offset"]:
        raise ValueError("reviewed desired contract differs")
    if expected["route_disposition"] == "unsupported_source":
        if observation.get("status") != "unsupported" or facts or result.get("finite_counterexamples") != []:
            raise ValueError("unsupported source cannot acquire finite facts or refutations")
    else:
        expected_rows = [{"input": row["input"], "output": row["output"],
                          "input_type": "int", "output_type": "int"} for row in expected["reference_rows"]]
        actual_rows = observation.get("observations")
        if (type(actual_rows) is not list or any(type(row) is not dict
                or type(row.get("input")) is not int or type(row.get("output")) is not int for row in actual_rows)):
            raise ValueError("observation rows require exact integer inputs and outputs")
        if observation.get("status") != "observed" or actual_rows != expected_rows:
            raise ValueError("complete finite observed table differs")
        counterexamples = result.get("finite_counterexamples")
        if (type(counterexamples) is not list or any(type(row) is not dict or any(type(row.get(key)) is not int
                for key in ("input", "observed_output", "expected_output")) for row in counterexamples)):
            raise ValueError("counterexamples require exact integer witnesses")
        if counterexamples != expected["counterexamples"]:
            raise ValueError("applicable finite counterexamples differ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="fresh private fixture output directory")
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.output)
        validate_materialized_sources(args.output.resolve(), manifest)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"fixture generation failed: {exc}\n")
    print(json.dumps({"manifest": str(args.output.resolve() / "manifest.json"),
        "scenarios": len(manifest["scenarios"]), "evidence_mutations": len(manifest["evidence_mutations"]),
        "manifest_sha256": manifest["manifest_sha256"], "production_qualified": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
