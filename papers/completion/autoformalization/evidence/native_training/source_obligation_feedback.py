"""Native compiler-contract feedback from actual train-only modal artifacts.

This checks structural compiler obligations, not the meaning or truth of legal
source text.  The supported fragment is deliberately finite: native operator
registry membership, nonempty predicate, and source-span well-formedness.
Every other generated obligation remains in the coverage denominator.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, Sequence

SCHEMA = "af029-source-compiler-feedback/v1"
SUPPORTED = frozenset({"modal_well_formedness", "provenance_preservation"})
PARSER_CHARS = 4096
TRAIN_EXPORT_SHA256 = "4e54b902980cef97ae4cd5c8516f0b038505adf3251bde5a2aedd6d4e2abd532"
TRAIN_ROWS_SHA256 = "9a367c2ac6625c32d48e8bf1aca0aa73b705701ea2dfc50c96ddd47fd5beaaff"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def registry_rows() -> list[list[str]]:
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_registry import DEFAULT_MODAL_REGISTRY
    return sorted({(p.family.value, p.system.value, op.symbol)
                   for p in DEFAULT_MODAL_REGISTRY.all_profiles() for op in p.operators})


def native_source_bindings() -> dict[str, str]:
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_modal_parser, modal_registry, modal_ir
    from ipfs_datasets_py.logic.integration.reasoning import legal_ir_obligations, legal_ir_proof_feedback
    return {str(Path(inspect.getfile(m)).resolve()): file_sha(Path(inspect.getfile(m)))
            for m in (legal_modal_parser, modal_registry, modal_ir,
                      legal_ir_obligations, legal_ir_proof_feedback)}


def _string(value: str) -> str:
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        raise ValueError("invalid structured compiler atom")
    return json.dumps(value, ensure_ascii=False)


def _atom_literal(value: str) -> str:
    _string(value)  # validate; encode every character, without truncation/hash
    return "[" + ", ".join(str(ord(c)) for c in value) + "]"


def render_goals(artifact: Mapping[str, Any], obligations: Sequence[Mapping[str, Any]],
                 registry: Sequence[Sequence[str]]) -> tuple[str, list[dict[str, Any]]]:
    """Lower actual generated structural obligations; no goal assumptions."""
    formulas = {f["formula_id"]: f for f in artifact["formulas"]}
    if len(formulas) != len(artifact["formulas"]):
        raise ValueError("duplicate compiler formula identity")
    triples = ", ".join("(" + ", ".join(_atom_literal(v) for v in row) + ")" for row in registry)
    lines = ["-- Finite native compiler contracts; no legal-fidelity claim.",
             f"def approvedOperators : List (List Nat × List Nat × List Nat) := [{triples}]"]
    coverage = []
    names = set()
    for obligation in obligations:
        item = {"obligation_id": obligation["obligation_id"],
                "obligation_sha256": digest(obligation), "kind": obligation["kind"],
                "formula_id": obligation["formula_id"], "status": "unsupported_fragment"}
        if obligation["kind"] not in SUPPORTED:
            coverage.append(item)
            continue
        formula = formulas.get(obligation["formula_id"])
        if formula is None:
            raise ValueError("generated obligation has no exact compiler formula")
        name = "af029_" + digest(obligation)[:24]
        if name in names:
            raise ValueError("duplicate generated obligation")
        names.add(name)
        operator, predicate, provenance = (formula[k] for k in ("operator", "predicate", "provenance"))
        start, end = provenance["start_char"], provenance["end_char"]
        if type(start) is not int or type(end) is not int:
            raise ValueError("source span is not integral")
        # Ints retain invalid negative bounds so the actual kernel rejects them.
        span = (f"(0 : Int) ≤ ({start} : Int) ∧ ({start} : Int) < ({end} : Int) ∧ "
                f"({end} : Int) ≤ ({len(artifact['normalized_text'])} : Int)")
        if obligation["kind"] == "modal_well_formedness":
            triple = "(" + ", ".join(_atom_literal(operator[k]) for k in ("family", "system", "symbol")) + ")"
            # The generated native obligation carries the expected predicate
            # signature separately. Check its complete name/arity/role against
            # the canonical formula, without assuming that target signature.
            atom = lambda value, fallback: re.sub(r"[^a-z0-9_.:-]+", "_", str(value or '').strip().lower()).strip('_') or fallback
            signature = f"{atom(predicate['name'], 'predicate')}/arity:{len(predicate['arguments'])}/role:{atom(predicate.get('role'), 'none')}"
            expected = obligation["metadata"]["predicate_signature"]
            family = f"({_atom_literal(operator['family'])} : List Nat) = {_atom_literal(obligation['logic_family'])}"
            signature_check = f"({_atom_literal(signature)} : List Nat) = {_atom_literal(expected)}"
            goal = f"approvedOperators.contains {triple} = true ∧ ({family}) ∧ ({signature_check}) ∧ (0 : Nat) < {len(predicate['name'])} ∧ ({span})"
        else:
            # The native generated provenance obligation checks this formula's
            # own source ID and concrete interval, not an arbitrary hash comment.
            goal = f"{_string(provenance['source_id'])} = {_string(artifact['document_id'])} ∧ ({span})"
        lines.extend([f"theorem {name} : {goal} := by decide", f"#print axioms {name}"])
        item.update(status="awaiting_native_kernel", theorem=name, goal_sha256=hashlib.sha256(goal.encode()).hexdigest())
        coverage.append(item)
    return "\n".join(lines) + "\n", coverage


def build_packet(row: Mapping[str, Any], sample: Any, teacher: Mapping[str, Any]) -> dict[str, Any]:
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_modal_parser import LegalModalParser
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_obligations import generate_legal_ir_proof_obligations
    if teacher.get("split") != "train" or row["record_id"] != teacher["record_id"]:
        raise ValueError("feedback is restricted to the bound train row")
    if teacher.get("source_gold") or teacher.get("independent_gold"):
        raise ValueError("compiler feedback cannot acquire human-gold authority")
    # AF004 document_sha256 commits to the upstream document/version, not
    # necessarily this exported text. The production entry binds the complete
    # unchanged export below; preserve both identities without conflating them.
    if not re.fullmatch(r"[0-9a-f]{64}", row["document_sha256"]):
        raise ValueError("invalid upstream document digest")
    if (sample.text != row["text"][:PARSER_CHARS] or sample.sample_id != teacher["sample_id"]
            or teacher["input_document_sha256"] != row["document_sha256"]):
        raise ValueError("sample/teacher/source identity differs")
    # Recompute with the actual parser rather than accepting a caller's
    # hash-labeled artifact or interpreting a source string as proof code.
    reparsed = LegalModalParser().parse(sample.text, document_id=sample.sample_id,
                                       source="us_code", citation=sample.citation)
    artifact = sample.modal_ir.to_dict()
    if reparsed.to_dict() != artifact:
        raise ValueError("sample modal artifact differs from native source compilation")
    obligations = [o.to_dict() for o in generate_legal_ir_proof_obligations(sample)]
    registry = registry_rows()
    lean, coverage = render_goals(artifact, obligations, registry)
    packet = {"schema": SCHEMA, "record_id": row["record_id"], "split": "train",
              "source_sha256": row["document_sha256"], "sample_id": sample.sample_id,
              "source_sha256_semantics": "upstream_document_version_commitment",
              "source_text_sha256": hashlib.sha256(row["text"].encode()).hexdigest(),
              "source_record_sha256": digest(row),
              "parser_window_sha256": hashlib.sha256(sample.text.encode()).hexdigest(),
              "parser_window_chars": len(sample.text), "full_source_chars": len(row["text"]),
              "teacher_sha256": digest(teacher), "teacher_artifact_sha256": teacher["artifact_sha256"],
              "modal_artifact": artifact, "modal_artifact_sha256": digest(artifact),
              "native_obligations": obligations, "registry": registry,
              "registry_sha256": digest(registry), "coverage": coverage,
              "lean_source": lean, "lean_source_sha256": hashlib.sha256(lean.encode()).hexdigest(),
              "scope": "native_compiler_structural_contracts_only",
              "semantic_fidelity_measured": False, "native_sources": native_source_bindings()}
    packet["packet_sha256"] = digest(packet)
    return packet


def verify_packet(packet: Mapping[str, Any]) -> None:
    if digest({k: v for k, v in packet.items() if k != "packet_sha256"}) != packet["packet_sha256"]:
        raise ValueError("feedback packet drift")
    for path, expected in packet["native_sources"].items():
        if file_sha(Path(path)) != expected:
            raise ValueError("native source drift")
    if digest(packet["modal_artifact"]) != packet["modal_artifact_sha256"] or digest(packet["registry"]) != packet["registry_sha256"]:
        raise ValueError("compiler/registry binding drift")
    source, coverage = render_goals(packet["modal_artifact"], packet["native_obligations"], packet["registry"])
    if source != packet["lean_source"] or coverage != packet["coverage"]:
        raise ValueError("actual goal lowering drift")


def execute_packet(packet: Mapping[str, Any], *, lean_path: Path, output_dir: Path,
                   timeout_seconds: float = 10.0) -> dict[str, Any]:
    verify_packet(packet)
    lean = lean_path.resolve(strict=True)
    if not lean.is_file() or not os.access(lean, os.X_OK) or not 0 < timeout_seconds <= 30:
        raise ValueError("invalid native checker/budget")
    output_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(output_dir, 0o700)
    source_path = output_dir / "obligations.lean"
    write_bytes(output_dir / "packet.json", canonical(packet) + b"\n")
    write_bytes(source_path, packet["lean_source"].encode())
    selected = [x for x in packet["coverage"] if x["status"] == "awaiting_native_kernel"]
    started = time.perf_counter()
    argv = [str(lean), str(source_path)]
    returncode, status, stdout, stderr = None, "unsupported_fragment", b"", b""
    binary_sha = file_sha(lean)
    if selected:
        try:
            run = subprocess.run(argv, capture_output=True, timeout=timeout_seconds, check=False)
            returncode, stdout, stderr = run.returncode, run.stdout, run.stderr
            status = "checked" if returncode == 0 else "kernel_rejected"
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or b"", exc.stderr or b""
            status = "timeout"
    elapsed = time.perf_counter() - started
    # Generated source has no imports, assumptions, arbitrary tactic text, or
    # unsafe declarations. Require the actual kernel's axiom-free report too.
    decoded = stdout.decode("utf-8", errors="replace")
    axioms_clear = all(f"'{r['theorem']}' does not depend on any axioms" in decoded for r in selected)
    if status == "checked" and not axioms_clear:
        status = "axiom_report_missing"
    verify_packet(packet)
    if file_sha(lean) != binary_sha or file_sha(source_path) != packet["lean_source_sha256"]:
        raise ValueError("checker or checked source changed")
    write_bytes(output_dir / "stdout.txt", stdout)
    write_bytes(output_dir / "stderr.txt", stderr)
    receipt = {"schema": SCHEMA, "packet_sha256": packet["packet_sha256"],
               "source_sha256": packet["source_sha256"], "modal_artifact_sha256": packet["modal_artifact_sha256"],
               "source_text_sha256": packet["source_text_sha256"], "source_record_sha256": packet["source_record_sha256"],
               "lean_source_sha256": packet["lean_source_sha256"], "argv": argv,
               "binary_sha256": binary_sha, "exit_code": returncode, "status": status,
               "elapsed_seconds": elapsed, "cpu_seconds": None,
               "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
               "generated_obligation_count": len(packet["coverage"]),
               "supported_obligation_count": len(selected), "axiom_free": axioms_clear,
               "checked_theorems": [x["theorem"] for x in selected] if status == "checked" else [],
               "scope": packet["scope"], "semantic_fidelity_measured": False}
    receipt["receipt_sha256"] = digest(receipt)
    write_bytes(output_dir / "receipt.json", canonical(receipt) + b"\n")
    return receipt


def feedback_records(packet: Mapping[str, Any], receipt: Mapping[str, Any], *, versions: Any) -> list[Any]:
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_proof_feedback import (
        build_legal_ir_proof_feedback_record, ProofFeedbackPartitionPolicy)
    verify_packet(packet)
    if digest({k: v for k, v in receipt.items() if k != "receipt_sha256"}) != receipt["receipt_sha256"]:
        raise ValueError("native receipt drift")
    for key in ("packet_sha256", "source_sha256", "source_text_sha256", "source_record_sha256", "modal_artifact_sha256", "lean_source_sha256"):
        if receipt[key] != packet[key]:
            raise ValueError("native receipt belongs to another source/goal")
    if receipt["status"] != "checked" or receipt["exit_code"] != 0 or receipt["axiom_free"] is not True:
        return []
    selected = [x for x in packet["coverage"] if x["status"] == "awaiting_native_kernel"]
    if receipt["checked_theorems"] != [x["theorem"] for x in selected] or not selected:
        raise ValueError("missing actual theorem checks")
    by_id = {x["obligation_id"]: x for x in packet["native_obligations"]}
    receipt_id = "af029-contract-" + receipt["receipt_sha256"]
    records = []
    for item in selected:
        obligation = by_id[item["obligation_id"]]
        record = build_legal_ir_proof_feedback_record(
            obligation, reconstruction_receipt={"native_reconstruction": True,
                "native_reconstruction_verified": True, "reconstruction_status": "verified",
                "checker": "lean", "receipt_id": receipt_id},
            evidence_ids=("modal-" + packet["modal_artifact_sha256"], "source-" + packet["source_sha256"]),
            receipt_ids=(receipt_id,), versions=versions, partition_key=packet["record_id"],
            partition_policy=ProofFeedbackPartitionPolicy(holdout_fraction=0.0),
            deterministic_trusted=False)
        if not record.eligible_for_training:
            raise ValueError("native feedback refused actual kernel receipt")
        records.append(record)
    return records


def produce_source_feedback(*, train_rows: Sequence[Mapping[str, Any]], train_samples: Sequence[Any],
                            teacher_rows: Sequence[Mapping[str, Any]], versions: Any,
                            output_dir: Path, lean_path: Path) -> tuple[list[Any], list[dict[str, Any]], dict[str, Any]]:
    train_teachers = [x for x in teacher_rows if x["split"] == "train"]
    teachers = {x["record_id"]: x for x in train_teachers}
    if (len(train_rows) != 69 or len(train_samples) != 69 or len(train_teachers) != 69
            or len(teachers) != 69 or len({s.sample_id for s in train_samples}) != 69
            or {r["record_id"] for r in train_rows} != set(teachers)):
        raise ValueError("feedback requires the complete frozen69-row training denominator")
    if digest(list(train_rows)) != TRAIN_ROWS_SHA256:
        raise ValueError("training export differs from the exact frozen AF004 rows")
    output_dir.mkdir(parents=True, exist_ok=False)
    records, receipts, coverage = [], [], []
    for index, (row, sample) in enumerate(zip(train_rows, train_samples)):
        packet = build_packet(row, sample, teachers[row["record_id"]])
        receipt = execute_packet(packet, lean_path=lean_path, output_dir=output_dir / f"row-{index:03d}")
        admitted = feedback_records(packet, receipt, versions=versions)
        records.extend(admitted)
        receipts.append(receipt)
        coverage.append({"record_id": row["record_id"], "packet_sha256": packet["packet_sha256"],
                         "receipt_sha256": receipt["receipt_sha256"], "status": receipt["status"],
                         "admitted_records": len(admitted), "obligations": packet["coverage"]})
    report = {"schema": SCHEMA, "train_rows": 69, "selection_rows": 0, "final_rows": 0,
              "frozen_train_export_sha256": TRAIN_EXPORT_SHA256, "frozen_train_rows_sha256": TRAIN_ROWS_SHA256,
              "admitted_records": len(records), "rows": coverage,
              "scope": "native_compiler_structural_contracts_only", "semantic_fidelity_measured": False,
              "all_generated_obligations": sum(r["generated_obligation_count"] for r in receipts),
              "supported_obligations": sum(r["supported_obligation_count"] for r in receipts),
              "prior_trivial_checks": {"admissible": False, "count": 138, "history_and_costs_must_be_preserved": True}}
    write_bytes(output_dir / "coverage.json", canonical(report) + b"\n")
    return records, receipts, report
