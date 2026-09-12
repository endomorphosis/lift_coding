#!/usr/bin/env python3
"""AF-019 cross-domain statistical transfer bound.

Evaluate Legal/Security/Intent/software on frozen profiles, populations,
formal-target provenance, actual checkpoints and deterministic baselines.
Score structural compatibility, learned transfer, and valid semantic proof
transfer as three distinct claim classes. Independent source-semantic gold
is unavailable (AF-005/AF-028) and is never implied by prover, teacher, or
adapter success. OCR/ASR has no measured extraction route.

Standard library only. Domain adapters, feature-transfer code, and the
image/OCR processor are inspected and hashed, not imported. AF-029 packed
checkpoint payloads are identity-bound and not loaded.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "autoformalization-domain-transfer-result/v1"
MATRIX_SCHEMA = "autoformalization-domain-scope-matrix/v1"
TASK_ID = "AF-019"
POOL_ID = "AF-019-protected-write-composition/v1"
CHECKER_ID = "AF-010-shared-target-checker/v1"
CHECKER_DIGEST = "0d22c6e92be47a464452266e1a09d3b1d072f98ce3e5fec19bdbe9f47273f052"
AF011_T0_T2 = "5975e52cd3db3f1ac7e8be248351d685782e102a56d69dd17ecb4b1ef1d23737"
AF011_T1 = {
    104729: "1a1bb5919cbc0808381e69de3629c3a9da2f65de88994661b0e89a0ab63feba9",
    130363: "f25507dfc60b2dd8a0093bb96c0f4633a665d1dc95713799a6349abe331f9e34",
    155921: "b628a9466f2ecd660ec674c51a5bcd9e07dde3fb30b30829908527e6fa52c0e3",
}
AF011_CONFIG = "082d9a574705aabef0f46ba17f95c256118759fe3bb8a467110a12d19d1bfbdd"
AF011_DATASET = "1ccdbe48451a8b81d5c76a8494a4c2e84d53ce653236d1e5799de9cf58955c47"
AF029_T2 = (
    "00b940fcd4a96a67fdccde88310b5956e790e3a5d66055984d19cd1b3c61a8d8",
    "095147ede126c6a6f4f9f2817c208ce78e6662c3ce9d8ec6979a42aceac0ebf0",
    "cb766e9e811216a00f47ca8d96263c1d7dce4ec8c458f417ae36b11db8304c2b",
)
AF029_T3 = (
    "def483e87bb57d27a8f24a3939a063d1039af95c111ec6d5733b452f612b5cbc",
    "c90b4b9e7fd0120a7507b5e98bf7130e6c1e63091c14200afd3c2ee137ca5faf",
    "a4e7a375e63e8a62c13691673342560596418095a0b1f0835ad6929d66d18be8",
)
SEEDS = (104729, 130363, 155921)
NATIVE_TOOLS = ("lean", "lake", "elan", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle")
OCR_ASR_TOOLS = ("tesseract", "whisper", "easyocr", "ffmpeg")
PYTHON_MODULES = (
    "numpy", "torch", "transformers", "sentence_transformers", "faiss",
    "pytesseract", "easyocr", "whisper", "cv2", "PIL",
)
SHARED_CONTRACT_TOKENS = (
    "FormalizationSample",
    "FormalizationCompiler",
    "FormalizationArtifact",
    "ViewRegistry",
    "declaration_digest",
    "sample_id",
    "provenance",
)
Q1_TEXT = "Protected(r) and not Approved(a,r,t) implies not Write(a,r,t)"
Q2_TEXT = "Write(a,r,t) implies exists u in [t, t+2]. Audit(a,r,u)"

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]

INSPECTED_SOURCES = {
    "formalization_samples.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/formalization/samples.py",
        "imported": False,
        "note": "Domain-neutral FormalizationSample contract.",
    },
    "formalization_compiler.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/formalization/compiler.py",
        "imported": False,
        "note": "FormalizationCompiler protocol and artifact; no proof execution.",
    },
    "legal_adapter.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/adapter.py",
        "imported": False,
        "note": "legal-ir-formalization-adapter/v1; Legal domain compile() on FormalizationSample.",
    },
    "canonical_roundtrip.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_roundtrip.py",
        "imported": False,
        "note": "Legal production composition; inspected, not executed.",
    },
    "security_adapter.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/formalization_adapter.py",
        "imported": False,
        "note": "security-ir-formalization-adapter/v1; declaration features only.",
    },
    "intent_compiler.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/formalize/compiler.py",
        "imported": False,
        "note": "intent-formalization-compiler/v1; syntactic multi-view compiler.",
    },
    "feature_transfer.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/modal_autoencoder_feature_transfer.py",
        "imported": False,
        "note": "Legacy architecture-version feature copy, not Legal-to-Security transfer.",
    },
    "image_processor.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/processors/file_converter/image_processor.py",
        "imported": False,
        "note": "Optional Tesseract wrapper; not a measured OCR evaluation route.",
    },
    "bridge_cases.py": {
        "path": "papers/completion/autoformalization/evaluation/bridge_cases.py",
        "imported": False,
        "note": "AF-015 Q1/Q2 finite evaluators are replicated here, not imported.",
    },
    "structural_evidence_scope.json": {
        "path": "papers/completion/autoformalization/config/structural_evidence_scope.json",
        "imported": False,
        "note": "AF-028 policy: checker/teacher success is not source-semantic gold.",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [canonical_dumps(row) + "\n" for row in rows]
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text("".join(lines), encoding="utf-8")
    temporary.replace(path)


def implication(left: bool, right: bool) -> bool:
    return (not left) or right


def q1_holds(protected: bool, approved: bool, write: bool) -> bool:
    return implication(protected and not approved, not write)


def guarded_write(protected: bool, approved: bool) -> bool:
    return (not protected) or approved


def unguarded_write(_protected: bool, _approved: bool) -> bool:
    return True


def q1_assignments(write_fn) -> list[dict[str, Any]]:
    rows = []
    for protected in (True, False):
        for approved in (True, False):
            write = bool(write_fn(protected, approved))
            rows.append({
                "protected": protected,
                "approved": approved,
                "write": write,
                "q1": q1_holds(protected, approved, write),
            })
    return rows


def probe_tool(name: str) -> dict[str, Any]:
    resolved = shutil.which(name)
    return {
        "name": name,
        "resolved_path": resolved,
        "status": "available" if resolved else "unavailable",
        "usable_in_sealed_validation": bool(resolved),
    }


def probe_module(name: str) -> dict[str, Any]:
    try:
        module = __import__(name)
    except Exception as exc:
        return {"name": name, "status": "unavailable", "detail": f"{type(exc).__name__}: {exc}"}
    version = getattr(module, "__version__", None)
    return {"name": name, "status": "imported", "version": version, "file": getattr(module, "__file__", None)}


def inspect_source(spec: Mapping[str, Any]) -> dict[str, Any]:
    path = REPO_ROOT / spec["path"]
    text = path.read_text(encoding="utf-8")
    tokens = {token: token in text for token in SHARED_CONTRACT_TOKENS}
    return {
        **spec,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "exists": True,
        "imported": False,
        "shared_contract_tokens": tokens,
        "token_hits": sum(1 for present in tokens.values() if present),
        "compile_method": "def compile(" in text,
        "view_registry": "ViewRegistry" in text,
        "domain_constant_legal": 'DOMAIN: Final = "legal"' in text or 'LEGAL_IR_DOMAIN: Final = "legal"' in text,
        "domain_constant_security": 'DOMAIN: Final = "security"' in text or 'SECURITY_IR_FORMALIZATION_DOMAIN: Final = "security"' in text,
        "domain_constant_intent": 'DOMAIN: Final = "intent"' in text or 'INTENT_FORMALIZATION_DOMAIN: Final = "intent"' in text,
        "imports_proof_results": "never imports proof results" in text or "does not invoke a model, theorem prover" in text,
        "feature_transfer_not_cross_domain": "proof heads and sample memory are never synthesized" in text,
        "ocr_optional_tesseract": "Tesseract" in text or "tesseract" in text,
    }


def empty_status(status: str, *, score: float | None = None, detail: str = "") -> dict[str, Any]:
    payload = {"status": status, "score": score}
    if detail:
        payload["detail"] = detail
    return payload


def source_facets_unmeasured() -> dict[str, Any]:
    return {
        "independent_gold_present": False,
        "all_facet_match": None,
        "ambiguity": {"status": "unmeasured_not_collected", "labels": []},
        "status": "unmeasured_not_collected",
        "human_agreement": "unmeasured_not_collected",
        "source_semantic_fidelity": "unmeasured_not_collected",
        "admitted_as_source_gold": False,
        "note": "AF-005/AF-028: independent human labels were not collected; checker/teacher success is not source gold.",
    }


def cost_block(elapsed: float | None = 0.0) -> dict[str, Any]:
    return {
        "elapsed_seconds": elapsed,
        "cpu_seconds": None,
        "gpu_seconds": 0.0,
        "provider_units": 0.0,
        "memory_gib": None,
        "human_review_seconds": 0.0,
    }


def observation(
    *,
    record_id: str,
    source_id: str,
    domain: str,
    claim_class: str,
    experiment_arm: str,
    execution_status: str,
    result_kind: str,
    split: str,
    constructed_control: bool,
    fixture: bool,
    eligible: bool,
    notes: str,
    identities: Mapping[str, Any],
    proof: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
    elapsed: float = 0.0,
) -> dict[str, Any]:
    body = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "kind": "observation",
        "record_id": record_id,
        "source_id": source_id,
        "source_family_time_group": f"{domain}:{POOL_ID}",
        "split": split,
        "experiment_arm": experiment_arm,
        "claim_class": claim_class,
        "domain": domain,
        "eligible": eligible,
        "eligible_for_natural_table": False,
        "fixture": fixture,
        "constructed_control": constructed_control,
        "execution_status": execution_status,
        "result_kind": result_kind,
        "parse": empty_status("success" if execution_status == "measured" else execution_status),
        "elaboration": empty_status("success" if execution_status == "measured" else execution_status),
        "source_facets": source_facets_unmeasured(),
        "source_maps": empty_status(
            "unmeasured",
            detail="Natural source-map spans are not opened; constructed identifiers are explicit.",
        ),
        "reconstruction": {
            "forward": empty_status("unmeasured"),
            "cycle": empty_status("unmeasured"),
            "final": empty_status("unmeasured"),
        },
        "consistency": empty_status("success" if execution_status == "measured" else execution_status),
        "proof": dict(proof),
        "identities": {
            "experiment_arm": experiment_arm,
            "model": identities.get("model"),
            "tool": identities.get("tool", "papers/completion/autoformalization/receipts/snapshots/AF-019/measure_domain_transfer.py"),
            "checker": identities.get("checker"),
            "compiler": identities.get("compiler"),
            **{k: v for k, v in identities.items() if k not in {"model", "tool", "checker", "compiler"}},
        },
        "cost": cost_block(elapsed),
        "artifacts": {"raw_sha256": "0" * 64},
        "notes": notes,
        "pool_id": POOL_ID,
        "independent_source_semantic_gold": False,
        "counts_as_native_checked_proof": False,
        "counts_as_source_semantic_transfer": False,
    }
    if extra:
        body.update(extra)
    body["artifacts"] = {"raw_sha256": sha256_obj({k: v for k, v in body.items() if k != "artifacts"})}
    return body


def frozen_inputs() -> dict[str, str]:
    mapping = {
        "structural_evidence_scope_sha256": PAPER_ROOT / "config" / "structural_evidence_scope.json",
        "environment_manifest_sha256": PAPER_ROOT / "config" / "environment_manifest.json",
        "experiment_plan_sha256": PAPER_ROOT / "config" / "experiment_plan.json",
        "corpus_manifest_sha256": PAPER_ROOT / "data" / "corpus_manifest.json",
        "splits_sha256": PAPER_ROOT / "data" / "splits.json",
        "teacher_manifest_sha256": PAPER_ROOT / "data" / "teacher_manifest.json",
        "policy_code_trace_cases_sha256": PAPER_ROOT / "data" / "policy_code_trace_cases.json",
        "baseline_checkpoint_manifest_sha256": PAPER_ROOT / "checkpoints" / "baselines" / "manifest.json",
        "native_checkpoint_manifest_sha256": PAPER_ROOT / "checkpoints" / "native_training" / "manifest.json",
        "eligible_checkpoint_binding_sha256": PAPER_ROOT / "evidence" / "native_training" / "eligible_checkpoint_binding.json",
        "runtime_capability_matrix_sha256": PAPER_ROOT / "evidence" / "runtime_capability_matrix.json",
        "result_schema_sha256": PAPER_ROOT / "evaluation" / "result_schema.json",
    }
    return {key: sha256_file(path) for key, path in mapping.items()}


def load_legal_train_ids() -> list[str]:
    rows = load_jsonl(PAPER_ROOT / "runs" / "training_baselines" / "results.jsonl")
    ids = sorted({
        row["source_record_id"]
        for row in rows
        if row.get("record_kind") == "item" and row.get("split") == "train" and row.get("source_record_id")
    })
    return ids


def constructed_examples() -> list[dict[str, Any]]:
    identity = {"actor": "alice", "resource": "r1", "tenant": "tenant-a", "request": "req-1"}
    return [
        {
            "example_id": "legal.protected-write-constraint",
            "domain": "legal",
            "kind": "constraint",
            "split": "constructed_control",
            "formal_target": {"property_id": "Q1", "text": Q1_TEXT, "profile_id": "legal-ir-view/deontic/v1"},
            "payload": {"constraint": Q1_TEXT, "modality": "obligation"},
            "identity": identity,
        },
        {
            "example_id": "intent.plan-request-approve-write",
            "domain": "intent",
            "kind": "plan",
            "split": "constructed_control",
            "formal_target": {
                "property_id": "plan-postcondition-not-occurrence",
                "text": "Request then Approve then Write is a plan, not an execution record",
                "profile_id": "intent-ir-view/action-hoare/v1",
            },
            "payload": {"actions": ["RequestApproval", "Write"], "postcondition": "Write"},
            "identity": identity,
        },
        {
            "example_id": "security.guarded-implementation",
            "domain": "security",
            "kind": "implementation",
            "split": "constructed_control",
            "formal_target": {"property_id": "Q1", "text": Q1_TEXT, "profile_id": "guarded-implementation-fol/v1"},
            "payload": {"implementation": "guarded", "write_rule": "not Protected or Approved"},
            "identity": identity,
        },
        {
            "example_id": "security.unguarded-implementation",
            "domain": "security",
            "kind": "implementation",
            "split": "constructed_control",
            "formal_target": {"property_id": "Q1", "text": Q1_TEXT, "profile_id": "guarded-implementation-fol/v1"},
            "payload": {"implementation": "unguarded", "write_rule": "always Write"},
            "identity": identity,
        },
        {
            "example_id": "software.guarded-write-function",
            "domain": "software",
            "kind": "constructed_snippet",
            "split": "constructed_control",
            "formal_target": {"property_id": "Q1", "text": Q1_TEXT, "profile_id": "guarded-implementation-fol/v1"},
            "payload": {
                "snippet": "write = (not protected) or approved",
                "note": "Constructed control, not the SkillCenter natural code inventory.",
            },
            "identity": identity,
        },
        {
            "example_id": "trace.timely-audit",
            "domain": "trace",
            "kind": "observation",
            "split": "constructed_control",
            "formal_target": {"property_id": "Q2", "text": Q2_TEXT, "profile_id": "bounded-audit-trace/v1"},
            "payload": {"write_t": 0, "audit_t": 1, "capture_complete_through": 2, "deadline_offset": 2},
            "identity": identity,
        },
        {
            "example_id": "trace.wrong-tenant",
            "domain": "trace",
            "kind": "observation",
            "split": "constructed_control",
            "formal_target": {"property_id": "Q2", "text": Q2_TEXT, "profile_id": "bounded-audit-trace/v1"},
            "payload": {"write_t": 0, "audit_t": 1, "capture_complete_through": 2, "deadline_offset": 2},
            "identity": {"actor": "alice", "resource": "r1", "tenant": "tenant-b", "request": "req-1"},
        },
        {
            "example_id": "media.scanned-policy-page",
            "domain": "media",
            "kind": "unextracted_image",
            "split": "constructed_control",
            "formal_target": {"property_id": None, "text": None, "profile_id": None},
            "payload": {"media_type": "image/png", "extraction_route": None},
            "identity": identity,
        },
    ]


def mappings() -> list[dict[str, Any]]:
    return [
        {
            "mapping_id": "adapter.shared-formalization-sample",
            "kind": "adapter",
            "status": "admitted_contract_only",
            "review": "Legal/Security/Intent adapters share FormalizationSample/Compiler/Artifact contracts. Shared infrastructure is not semantic identity or statistical transfer.",
        },
        {
            "mapping_id": "entity.admitted.tenant-a",
            "kind": "entity",
            "status": "admitted",
            "fields": ["actor", "resource", "tenant", "request"],
            "value": {"actor": "alice", "resource": "r1", "tenant": "tenant-a", "request": "req-1"},
            "review": "Exact constructed-identifier equality. Not a natural-document entity linker.",
        },
        {
            "mapping_id": "entity.rejected.wrong-tenant",
            "kind": "entity",
            "status": "rejected",
            "fields": ["tenant"],
            "value": {"policy_tenant": "tenant-a", "trace_tenant": "tenant-b"},
            "review": "A shared actor/resource name is not sufficient to join tenants.",
        },
        {
            "mapping_id": "time.discrete-index.deadline-2",
            "kind": "time",
            "status": "admitted",
            "clock": "trace-step-index",
            "deadline_offset": 2,
            "review": "Discrete constructed-trace steps; not wall-clock alignment of natural logs.",
        },
        {
            "mapping_id": "intent-plan.not-occurrence",
            "kind": "adapter",
            "status": "rejected_as_execution_evidence",
            "review": "An Intent plan postcondition is not evidence that the write occurred.",
        },
    ]


def measure_structural(inspected: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    adapter_keys = {
        "legal": "legal_adapter.py",
        "security": "security_adapter.py",
        "intent": "intent_compiler.py",
    }
    required = len(SHARED_CONTRACT_TOKENS)
    for domain, key in adapter_keys.items():
        info = inspected[key]
        hits = int(info["token_hits"])
        score = hits / required
        compatible = hits == required and bool(info["compile_method"])
        extra = {
            "structural": {
                "compatible": compatible,
                "token_hits": hits,
                "token_required": required,
                "score": score,
                "compile_method": info["compile_method"],
                "shared_contract_tokens": info["shared_contract_tokens"],
                "claim": "infrastructure_compatibility",
                "not_statistical_transfer": True,
                "not_semantic_proof_transfer": True,
            }
        }
        rows.append(observation(
            record_id=f"structural:{domain}",
            source_id=info["path"],
            domain=domain,
            claim_class="structural_compatibility",
            experiment_arm="structural.adapter_contract",
            execution_status="measured",
            result_kind="bounded_observation",
            split="constructed_control",
            constructed_control=True,
            fixture=True,
            eligible=True,
            notes=(
                f"{domain} adapter/compiler presents {hits}/{required} shared FormalizationSample "
                f"contract tokens; compile()={'present' if info['compile_method'] else 'absent'}. "
                "This is infrastructure compatibility, not learned or proof transfer."
            ),
            identities={
                "model": None,
                "checker": "source_contract_inspection",
                "compiler": info["path"],
                "checkpoint": AF011_T0_T2,
                "baseline": "domain_adapter_source",
            },
            proof={
                "useful": False,
                "false_transfer": False,
                "checker_class": "none",
                "receipt_sha256": None,
                "theorem": None,
                "fragment": "shared-formalization-contract",
            },
            extra=extra,
        ))
    legal_views = {"legal-ir-view/deontic/v1", "legal-ir-view/frame-logic/v1", "legal-ir-view/tdfol/v1", "legal-ir-view/cec/v1"}
    security_views = {"security-ir-view/threat/v1", "security-ir-view/policy/v1", "security-ir-view/transition/v1", "security-ir-view/claim/v1"}
    intent_views = {
        "intent-ir-view/facts/v1",
        "intent-ir-view/intention-deontic/v1",
        "intent-ir-view/action-hoare/v1",
        "intent-ir-view/workflow-temporal/v1",
        "intent-ir-view/invariant/v1",
    }
    overlap = (legal_views & security_views) | (legal_views & intent_views) | (security_views & intent_views)
    rows.append(observation(
        record_id="structural:view-id-disjointness",
        source_id="view-registries",
        domain="shared",
        claim_class="structural_compatibility",
        experiment_arm="structural.view_ids",
        execution_status="measured",
        result_kind="bounded_observation",
        split="constructed_control",
        constructed_control=True,
        fixture=True,
        eligible=True,
        notes=(
            "Pinned Legal/Security/Intent view identifiers are pairwise disjoint. "
            "Shared names are not used as a blended latent space."
        ),
        identities={"model": None, "checker": "view_id_set_comparison", "compiler": None, "checkpoint": AF011_T0_T2, "baseline": "declared_view_ids"},
        proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": "view-ids"},
        extra={"structural": {"compatible": overlap == set(), "view_id_overlap": sorted(overlap), "score": 1.0 if not overlap else 0.0, "not_statistical_transfer": True}},
    ))
    feature = inspected["feature_transfer.py"]
    rows.append(observation(
        record_id="structural:feature-transfer-is-architecture-migration",
        source_id=feature["path"],
        domain="shared",
        claim_class="structural_compatibility",
        experiment_arm="structural.feature_transfer_module",
        execution_status="measured",
        result_kind="bounded_observation",
        split="constructed_control",
        constructed_control=True,
        fixture=True,
        eligible=True,
        notes=(
            "modal_autoencoder_feature_transfer copies legacy architecture rows into v2/v3 "
            "capacity groups. It is not a Legal-to-Security statistical transfer operator."
        ),
        identities={"model": "AdaptiveModalAutoencoder", "checker": "source_inspection", "compiler": None, "checkpoint": AF011_T0_T2, "baseline": "legacy_dense_v1_to_v2"},
        proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
        extra={"structural": {"cross_domain_operator": False, "architecture_migration": True, "score": 0.0, "not_statistical_transfer": True}},
    ))
    return rows


def measure_learned(examples: Sequence[Mapping[str, Any]], train_ids: Sequence[str], modules: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    target_domains = ("security", "intent", "software")
    example_ids = [ex["example_id"] for ex in examples if ex["domain"] in target_domains]
    overlap = sorted(set(train_ids) & set(example_ids))
    t0_equals_t2 = True
    module_by_name = {row["name"]: row for row in modules}
    minilm = module_by_name.get("sentence_transformers", {})
    torch = module_by_name.get("torch", {})
    numpy = module_by_name.get("numpy", {})
    payload_path = PAPER_ROOT / "evidence" / "native_training" / "states" / "T2-104729-final.json"
    payload_present = payload_path.is_file()
    af029_apply = (
        payload_present
        and minilm.get("status") == "imported"
        and torch.get("status") == "imported"
        and numpy.get("status") == "imported"
    )
    for domain in target_domains:
        domain_examples = [ex for ex in examples if ex["domain"] == domain]
        rows.append(observation(
            record_id=f"learned:AF011-T2:{domain}",
            source_id=f"{POOL_ID}:{domain}",
            domain=domain,
            claim_class="learned_transfer",
            experiment_arm="learned.AF011-T2-vs-T0",
            execution_status="measured",
            result_kind="bounded_observation",
            split="constructed_control",
            constructed_control=True,
            fixture=True,
            eligible=True,
            notes=(
                "AF-011 python-backend T2 accepted 0 shared-parameter epochs; final identity "
                f"{AF011_T0_T2} equals T0. There is no legal-trained shared-parameter change "
                f"to apply to {len(domain_examples)} frozen {domain} constructed examples. "
                "Null shared-parameter delta is not source-semantic transfer and is not a "
                "calibrated Security/Intent formalizer."
            ),
            identities={
                "model": "AdaptiveModalAutoencoder.python_backend",
                "checker": "checkpoint_identity_equality",
                "compiler": None,
                "checkpoint": AF011_T0_T2,
                "baseline": AF011_T0_T2,
                "config_id": AF011_CONFIG,
                "dataset_id": AF011_DATASET,
                "embedding_model": "mock:stable-sha256",
            },
            proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
            extra={
                "learned_transfer": {
                    "source_domain": "legal",
                    "target_domain": domain,
                    "n_examples": len(domain_examples),
                    "shared_parameter_delta": 0,
                    "t0_equals_t2": t0_equals_t2,
                    "calibrated_target_formalizer": False,
                    "source_semantic_gold": False,
                    "score": 0.0,
                    "precise_target": "AF-011 python-backend shared-parameter identity vs T0 codec",
                }
            },
        ))
        rows.append(observation(
            record_id=f"learned:AF011-T1-memory:{domain}",
            source_id=f"{POOL_ID}:{domain}",
            domain=domain,
            claim_class="learned_transfer",
            experiment_arm="learned.AF011-T1-sample-memory",
            execution_status="measured",
            result_kind="bounded_observation",
            split="constructed_control",
            constructed_control=True,
            fixture=True,
            eligible=True,
            notes=(
                f"T1 sample memory holds {len(train_ids)} legal CFR train IDs. Overlap with "
                f"{domain} constructed example IDs is {len(overlap)}. Sample-memory lookup "
                "cannot fire on other-domain identifiers. T1 is a memorization diagnostic, "
                "not a blind cross-domain learner."
            ),
            identities={
                "model": "AdaptiveModalAutoencoder.sample_memory",
                "checker": "sample_id_overlap",
                "compiler": None,
                "checkpoint": AF011_T1[104729],
                "baseline": "no_memory_T0",
                "t1_checkpoints": AF011_T1,
            },
            proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
            extra={
                "learned_transfer": {
                    "source_domain": "legal",
                    "target_domain": domain,
                    "memory_keys": len(train_ids),
                    "overlap": overlap,
                    "overlap_count": len(overlap),
                    "score": 0.0,
                    "precise_target": "T1 sample-memory key match on constructed other-domain IDs",
                    "source_semantic_gold": False,
                }
            },
        ))
        rows.append(observation(
            record_id=f"learned:AF029-T2:{domain}",
            source_id=f"{POOL_ID}:{domain}",
            domain=domain,
            claim_class="learned_transfer",
            experiment_arm="learned.AF029-T2-minilm-packed-cpu",
            execution_status="unavailable",
            result_kind="no_run",
            split="constructed_control",
            constructed_control=True,
            fixture=True,
            eligible=True,
            notes=(
                "AF-029 T2 packed_cpu changed shared Legal-IR view parameters on MiniLM-encoded "
                "CFR train/selection. Applying those parameters to Security/Intent/software "
                "requires the 5.8GiB checkpoint payloads, MiniLM, and packed_cpu/torch. "
                f"payload_present={payload_present}; sentence_transformers={minilm.get('status')}; "
                f"torch={torch.get('status')}; numpy={numpy.get('status')}. Unavailable is not zero "
                "transfer. Identities {', '.join(AF029_T2)} remain the actual transfer-source "
                "checkpoints; they are not executed on other-domain examples here."
            ),
            identities={
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "checker": None,
                "compiler": None,
                "checkpoint": AF029_T2[0],
                "baseline": "domain_specific_deterministic_control",
                "af029_t2_identities": list(AF029_T2),
                "af029_t3_identities": list(AF029_T3),
            },
            proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
            extra={
                "learned_transfer": {
                    "source_domain": "legal",
                    "target_domain": domain,
                    "application_status": "unavailable",
                    "payload_present": payload_present,
                    "apply_attempted": False,
                    "score": None,
                    "precise_target": "AF-029 T2 MiniLM packed_cpu shared parameters on other-domain encodings",
                    "source_semantic_gold": False,
                    "unavailable_is_not_zero": True,
                    "sealed_apply_possible": af029_apply,
                }
            },
        ))
    rows.append(observation(
        record_id="learned:legal-in-domain-is-not-cross-domain",
        source_id="af004.legal.train",
        domain="legal",
        claim_class="learned_transfer",
        experiment_arm="learned.legal-source-bound",
        execution_status="measured",
        result_kind="bounded_observation",
        split="train",
        constructed_control=False,
        fixture=False,
        eligible=True,
        notes=(
            "Legal is the training source (69 AF-004 train CFR units). In-domain AF-011/AF-029 "
            "measurements are not cross-domain transfer. Final-test 1913 units remain locked "
            "and are not opened here."
        ),
        identities={
            "model": "AdaptiveModalAutoencoder",
            "checker": None,
            "compiler": None,
            "checkpoint": AF011_T0_T2,
            "baseline": AF011_T0_T2,
        },
        proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
        extra={
            "learned_transfer": {
                "source_domain": "legal",
                "target_domain": "legal",
                "cross_domain": False,
                "score": None,
                "precise_target": "in-domain legal training is out of AF-019 transfer claim",
                "source_semantic_gold": False,
            }
        },
    ))
    return rows


def evaluate_q2(example: Mapping[str, Any], policy_identity: Mapping[str, str]) -> dict[str, Any]:
    payload = example["payload"]
    trace_identity = example["identity"]
    if trace_identity != policy_identity:
        return {
            "outcome": "unresolved_identity",
            "accepted_transfer": False,
            "false_transfer": False,
            "useful": False,
            "result_kind": "bounded_observation",
            "mapping_status": "rejected",
        }
    write_t = int(payload["write_t"])
    audit_t = payload["audit_t"]
    complete_through = int(payload["capture_complete_through"])
    deadline = write_t + int(payload["deadline_offset"])
    if complete_through < deadline:
        return {
            "outcome": "unknown_incomplete_window",
            "accepted_transfer": False,
            "false_transfer": False,
            "useful": False,
            "result_kind": "bounded_observation",
            "mapping_status": "admitted",
        }
    in_window = audit_t is not None and write_t <= int(audit_t) <= deadline
    if in_window:
        return {
            "outcome": "satisfied_within_observed_window",
            "accepted_transfer": False,
            "false_transfer": False,
            "useful": True,
            "result_kind": "bounded_observation",
            "mapping_status": "admitted",
        }
    return {
        "outcome": "violated_within_observed_window",
        "accepted_transfer": False,
        "false_transfer": False,
        "useful": False,
        "result_kind": "countermodel",
        "mapping_status": "admitted",
    }


def measure_proof(examples: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    policy_identity = {"actor": "alice", "resource": "r1", "tenant": "tenant-a", "request": "req-1"}
    guarded = q1_assignments(guarded_write)
    unguarded = q1_assignments(unguarded_write)
    guarded_ok = all(row["q1"] for row in guarded)
    unguarded_counter = any(not row["q1"] for row in unguarded)

    def proof_row(example_id: str, domain: str, extra_notes: str, outcome: Mapping[str, Any], fragment: str, theorem: str, arm: str) -> dict[str, Any]:
        example = next(item for item in examples if item["example_id"] == example_id)
        receipt = {
            "example_id": example_id,
            "domain": domain,
            "property": example["formal_target"],
            "outcome": outcome,
            "bridge_assumptions": [
                "Finite Boolean or discrete-trace constructed model.",
                "Entity join only under an admitted mapping.",
                "Plan postconditions are not execution records.",
                "No natural source extraction is claimed.",
            ],
        }
        receipt_sha = sha256_obj(receipt)
        return observation(
            record_id=f"proof:{example_id}",
            source_id=example_id,
            domain=domain,
            claim_class="semantic_proof_transfer",
            experiment_arm=arm,
            execution_status="measured",
            result_kind=outcome["result_kind"],
            split="constructed_control",
            constructed_control=True,
            fixture=True,
            eligible=True,
            notes=extra_notes,
            identities={
                "model": None,
                "checker": "stdlib_finite_enumeration",
                "compiler": None,
                "checkpoint": AF011_T0_T2,
                "baseline": "domain_specific_finite_control",
            },
            proof={
                "useful": outcome["useful"],
                "false_transfer": outcome["false_transfer"],
                "checker_class": "solver_local",
                "receipt_sha256": receipt_sha,
                "theorem": theorem,
                "fragment": fragment,
            },
            extra={
                "semantic_proof_transfer": {
                    "accepted_transfer": outcome.get("accepted_transfer", False),
                    "outcome": outcome["outcome"],
                    "preserved_property": theorem,
                    "mapping_status": outcome.get("mapping_status", "admitted"),
                    "not_structural_compatibility": True,
                    "not_learned_transfer": True,
                    "source_semantic_gold": False,
                    "natural_held_out": False,
                    "assignments": outcome.get("assignments"),
                }
            },
        )

    rows.append(proof_row(
        "security.guarded-implementation",
        "security",
        "Guarded Write = not Protected or Approved makes Q1 true on all four Boolean assignments. Accepted constructed consequence transfer; not learned transfer and not legal-source fidelity.",
        {
            "outcome": "q1_holds_on_guarded_model",
            "accepted_transfer": True,
            "false_transfer": False,
            "useful": True,
            "result_kind": "solver_local_result",
            "mapping_status": "admitted",
            "assignments": guarded,
            "all_hold": guarded_ok,
        },
        "q1-protected-write",
        "Q1",
        "proof.security-guarded-Q1",
    ))
    rows.append(proof_row(
        "security.unguarded-implementation",
        "security",
        "Unguarded always-write yields a Q1 countermodel (Protected and not Approved and Write). Accepted countermodel, not a false transfer of Q1 truth.",
        {
            "outcome": "q1_countermodel",
            "accepted_transfer": False,
            "false_transfer": False,
            "useful": False,
            "result_kind": "countermodel",
            "mapping_status": "admitted",
            "assignments": unguarded,
            "has_countermodel": unguarded_counter,
        },
        "q1-protected-write",
        "Q1",
        "proof.security-unguarded-Q1",
    ))
    rows.append(proof_row(
        "software.guarded-write-function",
        "software",
        "Constructed software snippet uses the same guarded rule as the Security implementation. Exact-goal Q1 holds on the finite model. This is not SkillCenter natural-code transfer.",
        {
            "outcome": "q1_holds_on_guarded_model",
            "accepted_transfer": True,
            "false_transfer": False,
            "useful": True,
            "result_kind": "solver_local_result",
            "mapping_status": "admitted",
            "assignments": guarded,
            "all_hold": guarded_ok,
        },
        "q1-protected-write",
        "Q1",
        "proof.software-guarded-Q1",
    ))
    rows.append(proof_row(
        "legal.protected-write-constraint",
        "legal",
        "The Legal declaration states Q1 as a deontic constraint. Stating the constraint is not a proof that an implementation enforces it, and is not Intent-plan occurrence.",
        {
            "outcome": "constraint_stated_not_implementation_proof",
            "accepted_transfer": False,
            "false_transfer": False,
            "useful": False,
            "result_kind": "bounded_observation",
            "mapping_status": "admitted",
        },
        "q1-protected-write",
        "Q1",
        "proof.legal-constraint-not-implementation",
    ))
    rows.append(proof_row(
        "intent.plan-request-approve-write",
        "intent",
        "Intent plan Request then Approve then Write is not evidence that Write occurred. Plan postcondition is rejected as execution evidence (App. P.1).",
        {
            "outcome": "plan_is_not_occurrence",
            "accepted_transfer": False,
            "false_transfer": False,
            "useful": False,
            "result_kind": "bounded_observation",
            "mapping_status": "rejected_as_execution_evidence",
        },
        "plan-postcondition-not-occurrence",
        "plan-postcondition",
        "proof.intent-plan-not-occurrence",
    ))
    timely = next(item for item in examples if item["example_id"] == "trace.timely-audit")
    wrong = next(item for item in examples if item["example_id"] == "trace.wrong-tenant")
    timely_out = evaluate_q2(timely, policy_identity)
    wrong_out = evaluate_q2(wrong, policy_identity)
    rows.append(proof_row(
        "trace.timely-audit",
        "trace",
        "Matching identities, complete capture through t+2, write at 0 and audit at 1 satisfy Q2 on the observed event. One log is not a global program guarantee.",
        timely_out,
        "q2-bounded-audit",
        "Q2",
        "proof.trace-timely-Q2",
    ))
    rows.append(proof_row(
        "trace.wrong-tenant",
        "trace",
        "tenant-b does not join tenant-a. Unresolved identity is not Q2 satisfaction and is not a false transfer.",
        wrong_out,
        "q2-bounded-audit",
        "Q2",
        "proof.trace-wrong-tenant",
    ))
    native = [probe_tool(name) for name in NATIVE_TOOLS]
    missing = [row["name"] for row in native if row["status"] != "available"]
    rows.append(observation(
        record_id="proof:native-checker-unavailable",
        source_id="sealed-path",
        domain="shared",
        claim_class="semantic_proof_transfer",
        experiment_arm="proof.native-kernel",
        execution_status="unavailable",
        result_kind="no_run",
        split="constructed_control",
        constructed_control=True,
        fixture=True,
        eligible=True,
        notes=(
            "Sealed PATH has no Lean/Z3/CVC5/Isabelle kernel. Finite stdlib enumeration is "
            f"solver_local, not native_checked_proof. missing={missing}."
        ),
        identities={"model": None, "checker": None, "compiler": None, "checkpoint": AF011_T0_T2, "baseline": "native_kernel"},
        proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
        extra={"native_checkers": native, "missing_native_checkers": missing, "semantic_proof_transfer": {"native_checked": False, "source_semantic_gold": False}},
    ))
    return rows


def measure_multimodal(inspected: Mapping[str, dict[str, Any]], tools: Sequence[Mapping[str, Any]], modules: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    image = inspected["image_processor.py"]
    available_tools = [row["name"] for row in tools if row["status"] == "available"]
    available_modules = [row["name"] for row in modules if row["status"] == "imported"]
    measured_route = bool(available_tools) and image.get("ocr_optional_tesseract") and "pytesseract" in available_modules
    rows = []
    for media, arm in (("ocr", "multimodal.ocr"), ("asr", "multimodal.asr")):
        rows.append(observation(
            record_id=f"multimodal:{media}",
            source_id="media.scanned-policy-page" if media == "ocr" else "media.spoken-policy",
            domain="media",
            claim_class="multimodal_extraction",
            experiment_arm=arm,
            execution_status="unsupported" if not measured_route else "measured",
            result_kind="no_run",
            split="constructed_control",
            constructed_control=True,
            fixture=True,
            eligible=False,
            notes=(
                f"No concrete measured {media.upper()} extraction route ran. Capability matrix R07 "
                "is unsupported. ImageProcessor is an optional Tesseract wrapper, not a held-out "
                "OCR/ASR benchmark. No WER, CER, or accuracy is reported."
            ),
            identities={"model": None, "checker": None, "compiler": None, "checkpoint": AF011_T0_T2, "baseline": None},
            proof={"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
            extra={
                "multimodal": {
                    "media": media,
                    "measured_extraction_route": False,
                    "performance_claimed": False,
                    "wer": None,
                    "cer": None,
                    "accuracy": None,
                    "available_tools": available_tools,
                    "available_modules": available_modules,
                    "image_processor_sha256": image["sha256"],
                    "capability_route": "R07",
                }
            },
        ))
    return rows


def domain_matrix(
    *,
    inspected: Mapping[str, dict[str, Any]],
    corpus: Mapping[str, Any],
    splits: Mapping[str, Any],
    teacher: Mapping[str, Any],
    gold_rows: int,
    gold_labeled: int,
    observations: Sequence[Mapping[str, Any]],
    env: Mapping[str, Any],
) -> dict[str, Any]:
    def score_rows(claim: str, domain: str | None = None) -> list[dict[str, Any]]:
        rows = [row for row in observations if row.get("claim_class") == claim]
        if domain is not None:
            rows = [row for row in rows if row.get("domain") == domain]
        return rows

    def class_summary(claim: str) -> dict[str, Any]:
        rows = score_rows(claim)
        measured = [row for row in rows if row.get("execution_status") == "measured"]
        return {
            "n_rows": len(rows),
            "n_measured": len(measured),
            "n_unavailable": sum(1 for row in rows if row["execution_status"] == "unavailable"),
            "n_unsupported": sum(1 for row in rows if row["execution_status"] == "unsupported"),
            "source_semantic_gold_implied": False,
        }

    legal_counts = splits["counts"]
    coding = corpus["inventories"]["coding_requirements_and_implementation"]
    trace_inv = corpus["inventories"]["trace_material"]
    domains = {
        "legal": {
            "evaluated": True,
            "profile": {
                "supported": True,
                "profile_id": "legal-ir-formalization-adapter/v1",
                "producer_id": "legal-ir-formalization-adapter",
                "views": ["legal-ir-view/deontic/v1", "legal-ir-view/frame-logic/v1", "legal-ir-view/tdfol/v1", "legal-ir-view/cec/v1"],
                "source": inspected["legal_adapter.py"]["path"],
                "sha256": inspected["legal_adapter.py"]["sha256"],
            },
            "population": {
                "kind": "natural_legal_policy",
                "frozen": True,
                "split_counts": legal_counts,
                "train_units": legal_counts["train"]["natural_source_units"],
                "selection_units": legal_counts["selection"]["natural_source_units"],
                "fixed_canary_units": legal_counts["fixed_canary"]["natural_source_units"],
                "final_test_units": legal_counts["final_test"]["natural_source_units"],
                "final_test_locked": True,
                "bodies_opened": False,
            },
            "formal_target_provenance": {
                "property_id": "Q1",
                "text": Q1_TEXT,
                "teacher_compiler_targets": teacher["compiler_and_view_targets"]["targets_produced"],
                "independent_gold_rows_with_values": gold_labeled,
                "source": "App. P.1 constructed constraint plus AF-004 legal inventory",
            },
            "checkpoint": {
                "af011_t0_t2": AF011_T0_T2,
                "af011_t1": AF011_T1,
                "af029_t2": list(AF029_T2),
                "actual": True,
            },
            "baseline": {"id": "T0-deterministic-codec", "identity": AF011_T0_T2, "actual": True},
            "independent_labels": {"available": False, "status": "unmeasured_not_collected"},
            "claim_classes": {
                "structural_compatibility": {"scored": True, "status": "measured"},
                "learned_transfer": {"scored": True, "status": "measured", "cross_domain_role": "source_only"},
                "semantic_proof_transfer": {"scored": True, "status": "measured", "note": "constraint stated; not implementation proof"},
            },
            "source_semantic_gold": False,
        },
        "security": {
            "evaluated": True,
            "profile": {
                "supported": True,
                "profile_id": "security-ir-formalization-adapter/v1",
                "producer_id": "security-ir-formalization-adapter",
                "views": ["security-ir-view/threat/v1", "security-ir-view/policy/v1", "security-ir-view/transition/v1", "security-ir-view/claim/v1"],
                "source": inspected["security_adapter.py"]["path"],
                "sha256": inspected["security_adapter.py"]["sha256"],
            },
            "population": {
                "kind": "constructed_control",
                "frozen": True,
                "n_examples": 2,
                "natural_admitted": 0,
                "examples": ["security.guarded-implementation", "security.unguarded-implementation"],
            },
            "formal_target_provenance": {
                "property_id": "Q1",
                "text": Q1_TEXT,
                "profile_id": "guarded-implementation-fol/v1",
                "source": "AF-015/AF-006 finite protected-write models",
            },
            "checkpoint": {"af011_t0_t2": AF011_T0_T2, "af029_t2": list(AF029_T2), "actual": True},
            "baseline": {"id": "domain_specific_finite_Q1", "actual": True},
            "independent_labels": {"available": False, "status": "unmeasured_not_collected"},
            "claim_classes": {
                "structural_compatibility": {"scored": True, "status": "measured"},
                "learned_transfer": {"scored": True, "status": "measured_null_AF011_unavailable_AF029"},
                "semantic_proof_transfer": {"scored": True, "status": "measured"},
            },
            "source_semantic_gold": False,
        },
        "intent": {
            "evaluated": True,
            "profile": {
                "supported": True,
                "profile_id": "intent-formalization-compiler/v1",
                "producer_id": "intent-formalization-compiler",
                "views": [
                    "intent-ir-view/facts/v1",
                    "intent-ir-view/intention-deontic/v1",
                    "intent-ir-view/action-hoare/v1",
                    "intent-ir-view/workflow-temporal/v1",
                    "intent-ir-view/invariant/v1",
                ],
                "source": inspected["intent_compiler.py"]["path"],
                "sha256": inspected["intent_compiler.py"]["sha256"],
            },
            "population": {
                "kind": "constructed_control",
                "frozen": True,
                "n_examples": 1,
                "natural_admitted": 0,
                "examples": ["intent.plan-request-approve-write"],
            },
            "formal_target_provenance": {
                "property_id": "plan-postcondition-not-occurrence",
                "profile_id": "intent-ir-view/action-hoare/v1",
                "source": "App. P.1 Intent plan vs occurrence distinction",
            },
            "checkpoint": {"af011_t0_t2": AF011_T0_T2, "af029_t2": list(AF029_T2), "actual": True},
            "baseline": {"id": "plan_is_not_occurrence", "actual": True},
            "independent_labels": {"available": False, "status": "unmeasured_not_collected"},
            "claim_classes": {
                "structural_compatibility": {"scored": True, "status": "measured"},
                "learned_transfer": {"scored": True, "status": "measured_null_AF011_unavailable_AF029"},
                "semantic_proof_transfer": {"scored": True, "status": "measured"},
            },
            "source_semantic_gold": False,
        },
        "software": {
            "evaluated": True,
            "profile": {
                "supported": True,
                "profile_id": "guarded-implementation-fol/v1",
                "note": "Constructed snippet reuses the Security guarded-write profile; no natural code adapter is admitted.",
            },
            "population": {
                "kind": "constructed_control",
                "frozen": True,
                "n_examples": 1,
                "natural_admitted": coding["natural_admitted"],
                "natural_admission": coding["admission"],
                "examples": ["software.guarded-write-function"],
            },
            "formal_target_provenance": {"property_id": "Q1", "text": Q1_TEXT, "profile_id": "guarded-implementation-fol/v1"},
            "checkpoint": {"af011_t0_t2": AF011_T0_T2, "af029_t2": list(AF029_T2), "actual": True},
            "baseline": {"id": "domain_specific_finite_Q1", "actual": True},
            "independent_labels": {"available": False, "status": "unmeasured_not_collected"},
            "claim_classes": {
                "structural_compatibility": {"scored": True, "status": "measured", "note": "no dedicated software FormalizationSample adapter; uses Security profile"},
                "learned_transfer": {"scored": True, "status": "measured_null_AF011_unavailable_AF029"},
                "semantic_proof_transfer": {"scored": True, "status": "measured"},
            },
            "source_semantic_gold": False,
        },
        "trace": {
            "evaluated": True,
            "profile": {"supported": True, "profile_id": "bounded-audit-trace/v1"},
            "population": {
                "kind": "constructed_control",
                "frozen": True,
                "n_examples": 2,
                "natural_admitted": trace_inv["natural_admitted"],
                "natural_admission": trace_inv["admission"],
                "examples": ["trace.timely-audit", "trace.wrong-tenant"],
            },
            "formal_target_provenance": {"property_id": "Q2", "text": Q2_TEXT, "profile_id": "bounded-audit-trace/v1"},
            "checkpoint": {"af011_t0_t2": AF011_T0_T2, "actual": True},
            "baseline": {"id": "identity_and_window_rules", "actual": True},
            "independent_labels": {"available": False, "status": "unmeasured_not_collected"},
            "claim_classes": {
                "structural_compatibility": {"scored": False, "status": "not_an_ir_adapter"},
                "learned_transfer": {"scored": False, "status": "not_a_learned_target"},
                "semantic_proof_transfer": {"scored": True, "status": "measured"},
            },
            "source_semantic_gold": False,
        },
        "media": {
            "evaluated": False,
            "profile": {"supported": False, "profile_id": None, "capability_route": "R07"},
            "population": {"kind": "unextracted_media", "frozen": False, "natural_admitted": 0},
            "formal_target_provenance": {"property_id": None, "status": "no_extracted_formal_target"},
            "checkpoint": {"actual": True, "identity": AF011_T0_T2, "note": "checkpoint exists but is not an OCR/ASR model"},
            "baseline": {"actual": False, "status": "no_measured_extraction_baseline"},
            "independent_labels": {"available": False, "status": "unmeasured_not_collected"},
            "claim_classes": {
                "structural_compatibility": {"scored": False, "status": "unsupported"},
                "learned_transfer": {"scored": False, "status": "unsupported"},
                "semantic_proof_transfer": {"scored": False, "status": "unsupported"},
            },
            "extraction_route": {
                "measured": False,
                "ocr_performance_claimed": False,
                "asr_performance_claimed": False,
            },
            "source_semantic_gold": False,
        },
        "ui": {
            "evaluated": False,
            "profile": {"supported": False, "profile_id": None},
            "population": {"kind": "unavailable", "natural_admitted": 0},
            "formal_target_provenance": {"status": "no_supported_ui_profile"},
            "checkpoint": {"actual": True, "identity": AF011_T0_T2, "note": "legal-trained checkpoint is not a UI extractor"},
            "baseline": {"actual": False, "status": "no_ui_baseline"},
            "independent_labels": {"available": False},
            "claim_classes": {
                "structural_compatibility": {"scored": False, "status": "unsupported"},
                "learned_transfer": {"scored": False, "status": "unsupported"},
                "semantic_proof_transfer": {"scored": False, "status": "unsupported"},
            },
            "source_semantic_gold": False,
        },
    }
    return {
        "schema": MATRIX_SCHEMA,
        "task_id": TASK_ID,
        "pool_id": POOL_ID,
        "policy_id": "AF-028/structural-evidence-scope/v1",
        "source_scoring_rule": (
            "A checker proves the submitted formal statement within its profile. "
            "Whether that statement faithfully captures the source remains unmeasured "
            "without separate valid evidence. No proof/checker pass, automatic teacher "
            "label, reconstruction score, or constructed witness is original-source semantic gold."
        ),
        "independent_source_semantic_labels": {
            "available": False,
            "gold_rows": gold_rows,
            "gold_rows_with_values": gold_labeled,
            "human_agreement": "unmeasured_not_collected",
            "adjudication_status": "not_performed",
            "implied_by_prover_or_teacher": False,
        },
        "claim_classes": {
            "structural_compatibility": {
                **class_summary("structural_compatibility"),
                "description": "Shared FormalizationSample/Compiler/Artifact contracts and disjoint view IDs.",
            },
            "learned_transfer": {
                **class_summary("learned_transfer"),
                "description": "Legal-trained shared parameters vs deterministic/domain-specific controls on other-domain examples.",
            },
            "semantic_proof_transfer": {
                **class_summary("semantic_proof_transfer"),
                "description": "Property-specific finite consequence transfer with admitted entity/time mappings.",
            },
            "multimodal_extraction": {
                **class_summary("multimodal_extraction"),
                "description": "OCR/ASR only after a concrete measured extraction route.",
            },
        },
        "domains": domains,
        "mappings": mappings(),
        "checkpoints": {
            "af011_t0_t2": AF011_T0_T2,
            "af011_t1": AF011_T1,
            "af011_config_id": AF011_CONFIG,
            "af011_dataset_id": AF011_DATASET,
            "af029_t2": list(AF029_T2),
            "af029_t3": list(AF029_T3),
            "af029_payloads_present": False,
        },
        "baselines": {
            "t0_codec": AF011_T0_T2,
            "domain_specific_finite_Q1": "stdlib_finite_enumeration",
            "intent_plan_is_not_occurrence": "App.P.1",
        },
        "environment": env,
        "limitations": [
            "Independent human source-semantic labels are unavailable; human agreement is unmeasured.",
            "AF-011 T2 python-backend accepted 0 shared-parameter epochs; null delta is not a calibrated transfer.",
            "AF-029 T2 MiniLM packed_cpu application to other domains is unavailable under sealed PATH.",
            "Constructed_control results do not fill natural held-out table cells.",
            "No OCR/ASR performance is claimed.",
            "Finite Q1/Q2 checks are solver_local constructed witnesses, not native kernel proofs.",
            "Legal/Security/Intent adapter compatibility is not statistical transfer.",
        ],
    }


def gold_inventory() -> tuple[int, int]:
    path = PAPER_ROOT / "data" / "gold_facets.jsonl"
    rows = load_jsonl(path)
    labeled = 0
    for row in rows:
        facets = row.get("facets") or {}
        if not isinstance(facets, Mapping):
            continue
        for facet in facets.values():
            if isinstance(facet, Mapping) and facet.get("values"):
                labeled += 1
                break
    return len(rows), labeled


def main() -> int:
    started = time.perf_counter()
    path_value = os.environ.get("PATH", "")
    home = os.environ.get("HOME", "")
    env = {
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "path": path_value,
        "home": home,
        "home_is_validation_private": Path(home).name.startswith("ipfs-accelerate-validation-home-") if home else False,
        "tools": [probe_tool(name) for name in NATIVE_TOOLS],
        "ocr_asr_tools": [probe_tool(name) for name in OCR_ASR_TOOLS],
        "python_modules": [probe_module(name) for name in PYTHON_MODULES],
    }
    inspected = {key: inspect_source(spec) for key, spec in INSPECTED_SOURCES.items()}
    frozen = frozen_inputs()
    corpus = load_json(PAPER_ROOT / "data" / "corpus_manifest.json")
    splits = load_json(PAPER_ROOT / "data" / "splits.json")
    teacher = load_json(PAPER_ROOT / "data" / "teacher_manifest.json")
    gold_rows, gold_labeled = gold_inventory()
    train_ids = load_legal_train_ids()
    examples = constructed_examples()

    observations: list[dict[str, Any]] = []
    observations.extend(measure_structural(inspected))
    observations.extend(measure_learned(examples, train_ids, env["python_modules"]))
    observations.extend(measure_proof(examples))
    observations.extend(measure_multimodal(inspected, env["ocr_asr_tools"], env["python_modules"]))

    by_class: dict[str, int] = {}
    for row in observations:
        by_class[row["claim_class"]] = by_class.get(row["claim_class"], 0) + 1
    evaluated_domains = sorted({
        row["domain"]
        for row in observations
        if row["claim_class"] in {"structural_compatibility", "learned_transfer", "semantic_proof_transfer"}
        and row["domain"] not in {"shared", "media", "ui"}
    })
    summary = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "kind": "summary",
        "record_id": "AF-019-SUMMARY",
        "source_id": POOL_ID,
        "source_family_time_group": f"shared:{POOL_ID}",
        "split": "constructed_control",
        "experiment_arm": "AF-019-domain-transfer",
        "claim_class": "summary",
        "domain": "shared",
        "eligible": True,
        "eligible_for_natural_table": False,
        "fixture": True,
        "constructed_control": True,
        "execution_status": "measured",
        "result_kind": "bounded_observation",
        "parse": empty_status("success"),
        "elaboration": empty_status("success"),
        "source_facets": source_facets_unmeasured(),
        "source_maps": empty_status("unmeasured"),
        "reconstruction": {"forward": empty_status("unmeasured"), "cycle": empty_status("unmeasured"), "final": empty_status("unmeasured")},
        "consistency": empty_status("success"),
        "proof": {"useful": False, "false_transfer": False, "checker_class": "none", "receipt_sha256": None, "theorem": None, "fragment": None},
        "identities": {
            "experiment_arm": "AF-019-domain-transfer",
            "model": None,
            "tool": "papers/completion/autoformalization/receipts/snapshots/AF-019/measure_domain_transfer.py",
            "checker": CHECKER_ID,
            "compiler": None,
            "checker_digest": CHECKER_DIGEST,
        },
        "cost": cost_block(round(time.perf_counter() - started, 6)),
        "artifacts": {"raw_sha256": "0" * 64},
        "notes": "Three claim classes scored separately; no source-semantic gold; no OCR/ASR performance.",
        "pool_id": POOL_ID,
        "independent_source_semantic_gold": False,
        "counts_as_native_checked_proof": False,
        "counts_as_source_semantic_transfer": False,
        "n_observations": len(observations),
        "rows_by_claim_class": by_class,
        "evaluated_domains": evaluated_domains,
        "frozen_inputs": frozen,
        "inspected_sources": {key: {"path": val["path"], "sha256": val["sha256"], "imported": False} for key, val in inspected.items()},
        "environment": env,
        "legal_train_ids": len(train_ids),
        "gold_rows": gold_rows,
        "gold_rows_with_values": gold_labeled,
    }
    summary["artifacts"] = {"raw_sha256": sha256_obj({k: v for k, v in summary.items() if k != "artifacts"})}

    matrix = domain_matrix(
        inspected=inspected,
        corpus=corpus,
        splits=splits,
        teacher=teacher,
        gold_rows=gold_rows,
        gold_labeled=gold_labeled,
        observations=observations,
        env=env,
    )
    matrix["frozen_inputs"] = frozen
    matrix["inspected_sources"] = {key: {"path": val["path"], "sha256": val["sha256"], "imported": False, "note": val["note"]} for key, val in inspected.items()}

    results_path = PAPER_ROOT / "runs" / "domain_transfer" / "results.jsonl"
    matrix_path = PAPER_ROOT / "evidence" / "domain_scope_matrix.json"
    write_jsonl(results_path, [*observations, summary])
    write_json(matrix_path, matrix)
    report = {
        "task_id": TASK_ID,
        "results": str(results_path.relative_to(REPO_ROOT)),
        "matrix": str(matrix_path.relative_to(REPO_ROOT)),
        "n_observations": len(observations),
        "rows_by_claim_class": by_class,
        "evaluated_domains": evaluated_domains,
        "gold_rows_with_values": gold_labeled,
        "ocr_asr_performance_claimed": False,
        "source_semantic_gold": False,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    print(canonical_dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
