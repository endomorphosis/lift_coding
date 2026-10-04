"""Transcribe frozen TRAIN identities into an unadmitted relation ledger."""
from __future__ import annotations

import hashlib
import importlib.abc
import json
import os
import stat
import sys
import types
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
OUTPUT = CAMPAIGN / "masked-contrastive-01"
PRIOR = CAMPAIGN / "stage-workflow-01/validation.json"
PRIOR_SHA = "9a3b95bd6b460abe9938923e012ac70e46783cf3e15ae9953b11c1f44a023fd8"
FIT = CAMPAIGN / "stage-workflow-01/inputs/fit_declaration.json"
FIT_SHA = "ee39e5dd10af3811551229197fe2fac31f1acdce1e0ff9139dbeade669152f09"
FIT_PINS = CAMPAIGN / "stage-workflow-01/inputs/fit_expected_bindings.json"
FIT_PINS_SHA = "99112c59b3cb656236f86d2e0302771f537900899846f84e980905b0a19eaf1a"
FORBIDDEN = {"torch", "numpy", "scipy", "transformers", "sentence_transformers", "spacy", "safetensors",
             "tensorflow", "jax", "lean", "z3", "cvc5"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def seal(value):
    require("content_sha256" not in value, "fresh unsealed object required")
    return {**value, "content_sha256": digest(value)}


def file_identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read(path, sha=None, *, parse=True):
    path = Path(path).absolute()
    require(all(not item.is_symlink() for item in (path, *path.parents)), "symlink input forbidden")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= 16 * 1024**2,
                "bounded regular input required")
        data = stream.read(16 * 1024**2 + 1)
        after = os.fstat(stream.fileno())
    require(len(data) == before.st_size and file_identity(before) == file_identity(after) == file_identity(path.lstat()),
            "input changed while reading")
    observed = {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    require(sha is None or observed["sha256"] == sha, "external file selection differs")
    if not parse:
        return None, observed

    def pairs(values):
        value = {}
        for key, item in values:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def nonfinite(value):
        raise ValueError("nonfinite JSON constant: " + value)

    value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    raw(value)
    if type(value) is dict and "content_sha256" in value:
        require(value["content_sha256"] == digest({key: item for key, item in value.items() if key != "content_sha256"}),
                "sealed input differs")
    return value, observed


class RejectOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in FORBIDDEN:
            raise ImportError("numerical and prover stacks excluded from relation readiness")
        return None


def owners():
    require(not FORBIDDEN.intersection(sys.modules), "optional stack already imported")
    if not any(type(finder) is RejectOptional for finder in sys.meta_path):
        sys.meta_path.insert(0, RejectOptional())
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(REPO))
    for name, relative in (("ipfs_datasets_py", "ipfs_datasets_py"), ("ipfs_datasets_py.logic", "ipfs_datasets_py/logic"),
                           ("ipfs_datasets_py.logic.formalization", "ipfs_datasets_py/logic/formalization"),
                           ("ipfs_datasets_py.logic.formalization.autoencoder", "ipfs_datasets_py/logic/formalization/autoencoder")):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__path__ = [str(REPO / relative)]
            module.__package__ = name
            sys.modules[name] = module
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_relation_declarations as relations,
    )
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_stage_declarations as stages,
    )

    for module, filename in ((relations, "alignment_relation_declarations.py"), (stages, "alignment_stage_declarations.py")):
        require(Path(module.__file__).resolve() == REPO / "ipfs_datasets_py/logic/formalization/autoencoder" / filename,
                "exact canonical checkout owner required")
    return relations, stages


def prepare_assay():
    """Return the exact source-bound ledger and pins without writes or Torch."""
    relations, stages = owners()
    prior, prior_binding = read(PRIOR, PRIOR_SHA)
    fit, fit_binding = read(FIT, FIT_SHA)
    fit_pins, fit_pins_binding = read(FIT_PINS, FIT_PINS_SHA)
    fit_validation = stages.validate_fit_declaration(fit, expected_bindings=fit_pins)
    require(fit_validation["status"] == "blocked_no_contrastive_admission"
            and fit_validation["row_count"] == 16 and fit_validation["optimizer_updates"] == 0,
            "original semantic fit gate changed")
    require(prior["diagnostic_stage_replay"]["original_train_count"] == 16,
            "prior generation membership changed")
    train = fit["train_manifest"]
    ledger_rows = []
    for left in train["rows"]:
        for right in train["rows"]:
            identical = left["formal_view_sha256"] == right["formal_view_sha256"]
            ledger_rows.append({"left_id": left["id"], "right_id": right["id"],
                "left_input_sha256": left["input_sha256"], "right_input_sha256": right["input_sha256"],
                "left_formal_view_sha256": left["formal_view_sha256"], "right_formal_view_sha256": right["formal_view_sha256"],
                "relation_status": "weak_structural_identity" if identical else "unknown", "evidence_sha256": None,
                "reason": "Exact bound formal-view identity; source fidelity unreviewed." if identical
                          else "No admitted relation evidence; unequal formal digests do not establish a semantic negative.",
                "positive_mask": False, "permitted_negative_mask": False})
    policy = seal({"schema": relations.POLICY_SCHEMA, "mode": relations.MODE, "pair_order": relations.PAIR_ORDER,
        "weak_structural_policy": relations.WEAK_STRUCTURAL_POLICY,
        "family_coercion_policy": relations.FAMILY_COERCION_POLICY,
        "source_family_id": None, "target_family_id": None,
        "source_profile_sha256": fit["lane_validation"]["profile_sha256"], "target_profile_sha256": None})
    ledger = seal({"schema": relations.LEDGER_SCHEMA, "rows": ledger_rows})
    roles = {"lane_validation": fit["lane_validation"], "train_manifest": train,
             "relation_policy": policy, "pair_ledger": ledger}
    declaration = seal({"schema": relations.SCHEMA, **roles})
    expected = stages._bindings(roles)
    validation = relations.validate_relation_declaration(declaration, expected_bindings=expected)
    require(validation["declared_relation_counts"] == {"unknown": 240, "weak_structural_identity": 16,
                "declared_positive": 0, "declared_negative": 0}, "original256 declared relation accounting differs")
    require(all(value is False for matrix in (validation["positive_mask"], validation["permitted_negative_mask"])
                for row in matrix for value in row), "historical relation ledger admitted a pair")
    source_paths = (Path(__file__), REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_relation_declarations.py",
                    REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_lane_bundle.py",
                    REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_stage_declarations.py")
    sources = [read(path, parse=False)[1] for path in source_paths]
    return {"declaration": declaration, "expected_bindings": expected, "validation": validation,
            "input_file_bindings": [prior_binding, fit_binding, fit_pins_binding], "source_bindings": sources,
            "fit_readiness_replay": fit_validation}


def save(directory, name, value):
    data = raw(value) + b"\n"
    require(len(data) <= 16 * 1024**2, "bounded output required")
    path = directory / name
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    prepared = prepare_assay()
    require(not OUTPUT.exists(), "fresh masked-contrastive generation required")
    for selected in (*prepared["input_file_bindings"], *prepared["source_bindings"]):
        require(read(selected["path"], selected["sha256"], parse=False)[1] == selected, "selected input/code changed")
    OUTPUT.mkdir(mode=0o700)
    directory = OUTPUT / "relations"
    directory.mkdir(mode=0o700)
    artifacts = {name: save(directory, name + ".json", prepared[name])
                 for name in ("declaration", "expected_bindings", "validation")}
    report = seal({"schema": "alignment-relation-readiness-assay/v1", "created_utc": datetime.now(UTC).isoformat(),
        "status": "blocked_no_admitted_relations", "input_file_bindings": prepared["input_file_bindings"],
        "source_bindings": prepared["source_bindings"], "artifacts": artifacts,
        "train_row_count": 16, "pair_count": 256, "weak_structural_identity_pair_count": 16,
        "unknown_pair_count": 240, "admitted_positive_pair_count": 0, "permitted_negative_pair_count": 0,
        "positive_mask_true_count": 0, "negative_mask_true_count": 0,
        "masked_numerical_loss_eligible": False, "masked_numerical_loss_executed": False,
        "train_formal_payload_read": False, "query_reference_panel_accessed": False, "human_review_packages_accessed": False,
        "torch_imported": False, "encoder_calls": 0, "model_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
        "labels_admitted": 0, "semantic_label_admission": False, "source_fidelity_established": False,
        "proof_authority": False, "qualified": False, "accepted": False,
        "family_eligibility_verified": False, "producer_runtime_attestation_established": False,
        "original_semantic_fit_readiness_replayed": True, "original_train_masks_modified": False,
        "weak_identity_promoted_to_semantic_positive": False, "weak_diagnostic_fit_policy_created": False,
        "masks": dict.fromkeys(prepared["validation"]["masks"], 0),
        "dependency_binding_scope": "four_explicit_stdlib_owners_not_complete_dependency_closure"})
    for selected in (*prepared["input_file_bindings"], *prepared["source_bindings"], *artifacts.values()):
        require(read(selected["path"], selected["sha256"], parse=False)[1] == selected, "publication input/code/artifact changed")
    report_binding = save(directory, "assay.json", report)
    for path in (directory, OUTPUT, OUTPUT.parent):
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    print(raw({"assay_binding": report_binding, "pair_count": 256, "admitted_pairs": 0}).decode())


if __name__ == "__main__":
    main()
