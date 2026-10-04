"""Bind saved source representations to explicit identities without inference."""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import stat
import struct
import sys
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
OUTPUT = CAMPAIGN / "representation-boundary-01"
MAX_FILE_BYTES = 32 * 1024**2
MAX_AGGREGATE_BYTES = 32 * 1024**2
MAX_SECONDS = 60
PINS = {
    "source_inputs": ("richer-embedding-01/embedding_inputs.json", "072b5e7479499bd232715ec72bfe157c0dafb80c0bb9c140423c867c9f751f99"),
    "target_free_inputs": ("canonical-codec-01/target_free_inputs.json", "134f9a3bf917f0613fb474c04d8a5e414da443b133e12149f026cd3b5aa9473d"),
    "context_inputs": ("context-02/context_inputs.json", "cdc355cee220b2c2ff72ab28486f31a826e2d01164819d6c7760f559970d8f75"),
    "legacy8": ("richer-embedding-01/legacy8_embeddings.json", "aa929c0836f592d2217e748fa7ee452c955ef2466497ee72efca2a859e08930c"),
    "native384": ("richer-embedding-01/native384_embeddings.json", "14acf84a107d2bbdea3df8af9009f97ae670a3c45125e454c3a00312a78f7107"),
    "native768": ("richer-embedding-01/native768_embeddings.json", "d169295841e14829d896a81b48630d39f85537380df8e581b7440671ac49d2a9"),
    "learned384": ("checkpoint-01/representations.json", "03f4fe9914780f74a3f5507eb4c3c6a8b44f122b4da21e2f3bccc29fc2c68fea"),
}
CHECKPOINT = ROOT / "artifacts/source-reconstruction-v2-20261001/run-01/legal_ir/raw_ce-1729-checkpoint.json"
CHECKPOINT_SHA = "6e3f4d731d798aa2732afc37bd74fec34da3267a323844975d2dab78f59f9c61"
ENDPOINTS = {
    "residual_branch_8": ("learned_latent", 8),
    "residual_projection_384": ("learned_projection", 384),
    "formula_condition_32": ("decoder_condition", 32),
}
FORBIDDEN_IMPORTS = {"torch", "transformers", "sentence_transformers", "spacy", "safetensors"}
READ_TOTAL = 0
STARTED = 0.0


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def seal(value):
    return {**value, "content_sha256": digest(value)}


def strict_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("nonfinite JSON scalar: " + value)

    def number(value):
        parsed = float(value)
        require(math.isfinite(parsed), "nonfinite JSON number")
        return parsed

    return json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=unique,
                      parse_constant=invalid, parse_float=number)


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_file(path, expected=None, *, retain=True):
    """Bounded ordinary-file read; checkpoint bytes are hashed without parsing."""
    global READ_TOTAL
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        require(not parent.is_symlink(), "symlink input path forbidden")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    chunks, count, hasher = [], 0, hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_FILE_BYTES,
                "bounded nonempty regular input required")
        READ_TOTAL += before.st_size
        require(READ_TOTAL <= MAX_AGGREGATE_BYTES, "aggregate input byte bound exceeded")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            while chunk := stream.read(1024 * 1024):
                count += len(chunk)
                require(count <= MAX_FILE_BYTES, "input grew beyond byte bound")
                hasher.update(chunk)
                if retain:
                    chunks.append(chunk)
        after = os.fstat(descriptor)
        require(count == before.st_size and identity(before) == identity(after) == identity(path.lstat()),
                "input changed during bounded read")
    finally:
        os.close(descriptor)
    observed = {"path": str(path), "bytes": count, "sha256": hasher.hexdigest()}
    require(expected is None or observed["sha256"] == expected, "external input file pin differs")
    return b"".join(chunks) if retain else None, observed


def load_pinned(name):
    relative, expected = PINS[name]
    data, observed = read_file(CAMPAIGN / relative, expected)
    value = strict_json(data)
    require(type(value) is dict, "input must be a JSON object")
    for field in ("payload_sha256", "content_sha256"):
        if field in value:
            require(value[field] == digest({k: v for k, v in value.items() if k != field}),
                    "historical input content seal differs")
    return value, observed


def check_resources():
    require(time.monotonic() - STARTED <= MAX_SECONDS, "static assay deadline exceeded")
    require(not FORBIDDEN_IMPORTS.intersection(sys.modules), "optional numerical/model stack imported")
    require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss <= 512 * 1024,
            "fresh worker RSS bound exceeded")


class RejectNumericalImports:
    """Keep optional model/runtime imports outside this static assay."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in FORBIDDEN_IMPORTS:
            raise ImportError("numerical/model imports forbidden in static lane assay: " + fullname)
        return None


def install_import_guard():
    require(not FORBIDDEN_IMPORTS.intersection(sys.modules), "numerical stack already loaded")
    if not any(type(finder) is RejectNumericalImports for finder in sys.meta_path):
        sys.meta_path.insert(0, RejectNumericalImports())


def save(path, value):
    check_resources()
    data = raw(value) + b"\n"
    require(len(data) <= MAX_FILE_BYTES, "output byte bound exceeded")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def explicit_inputs(source_inputs, target_free, context_inputs):
    require(target_free["contains_canonical_ir"] is False and target_free["contains_target_token_ids"] is False,
            "target-bearing input artifact forbidden")
    require(len(source_inputs["rows"]) == len(target_free["rows"]) == 34
            and len(context_inputs["rows"]) == 68, "historical input row counts differ")
    originals = {}
    for row in context_inputs["rows"]:
        old_sha = row["original_input_sha256"]
        request = {"source_text": row["source_text"], "context": deepcopy(row["context"])}
        original = originals.setdefault(old_sha, {"request": request, "arms": {}})
        require(raw(original["request"]) == raw(request), "context arms contain different original envelopes")
        require(row["arm_id"] not in original["arms"], "duplicate original context arm")
        original["arms"][row["arm_id"]] = row["id"]
    inputs, joins = [], []
    for source, target in zip(source_inputs["rows"], target_free["rows"], strict=True):
        require(source["id"] == target["id"] and source["input_sha256"] == target["input_sha256"]
                and source["source_sha256"] == target["source_sha256"]
                and source["source_text"] == target["source_text"], "raw/target-free source identity differs")
        original = originals[source["input_sha256"]]
        require(set(original["arms"]) == {"source_frame_only", "declared_context"}, "both context arms required")
        request = original["request"]
        require(request["source_text"] == source["source_text"]
                and request["context"]["role"] == source["context_role"]
                and request["context"]["text"] == target["context_text"]
                and request["context"]["sha256"] == target["context_sha256"], "exact source/context join differs")
        new_sha = digest(request)
        inputs.append({"id": source["id"], "input": request, "input_sha256": new_sha})
        joins.append({"id": source["id"], "historical_authored_input_sha256": source["input_sha256"],
                      "explicit_envelope_input_sha256": new_sha, "source_sha256": source["source_sha256"],
                      "context_sha256": request["context"]["sha256"], "context_role": request["context"]["role"],
                      "context_arm_ids": original["arms"], "context_forwarded_to_raw_producers": False})
    return inputs, joins


def raw_profile(owner, lane):
    backend = lane["backend_evidence"]
    lane_id = lane["lane_id"]
    if lane_id == "legacy8":
        metadata = backend["production_evidence"]["model_identity"]
        model_id, revision = metadata["model_name"], metadata["model_version"]
        stage, precision, pooling, endpoint = "historical_linguistic_features", "decimal6", "none", "spacy_modal_codec.decode_embedding(dimensions=8)"
    else:
        stage, precision = "raw_embedding", "float32"
        pooling, endpoint = ("mean", "sentence_transformers.mean_pooling") if lane_id == "native384" else ("cls", "complete_model.encoder.last_hidden_state[:,0]")
        if lane_id == "native384":
            metadata = backend["production_evidence"]["model"]
            model_id, revision = metadata["model_id"], metadata["revision"]
        else:
            model_id = "Alibaba-NLP/gte-multilingual-base"
            revision = backend["production_evidence"]["assets"]["model_revision"]
    return seal({"schema": owner.PROFILE_SCHEMA, "lane_id": lane_id, "stage": stage,
                 "dimension": lane["dimension"], "producer": {"profile_id": backend["profile_id"],
                     "model_id": model_id, "model_revision": revision,
                     "code_sha256": digest(backend["implementation"]),
                     "model_assets_sha256": digest(backend["asset_evidence"]), "checkpoint_sha256": None},
                 "pooling": {"method": pooling, "endpoint": endpoint},
                 "normalization": {"kind": "l2", "unit_tolerance": 1e-5}, "precision": precision,
                 "fit_input_recipe": "exact_source_only/v1", "inference_input_recipe": "exact_source_only/v1"})


def learned_profile(owner, endpoint, representations, raw384_profile, checkpoint_binding):
    stage, dimension = ENDPOINTS[endpoint]
    producer = deepcopy(raw384_profile["producer"])
    producer.update(profile_id=representations["profile_id"] + ":endpoint=" + endpoint,
                    code_sha256=digest(representations["plan"]["executing_source_bindings"]),
                    checkpoint_sha256=checkpoint_binding["sha256"])
    return seal({"schema": owner.PROFILE_SCHEMA, "lane_id": "native384", "stage": stage,
                 "dimension": dimension, "producer": producer,
                 "pooling": {"method": "tensor_endpoint", "endpoint": endpoint},
                 "normalization": {"kind": "none", "unit_tolerance": None}, "precision": "float32",
                 "fit_input_recipe": "exact_source_only/v1", "inference_input_recipe": "exact_source_only/v1"})


def build_view(owner, inputs, profile, vectors, source_receipts, artifact, *, derived=False):
    """Transcribe immutable historical rows; do not attest or recompute them."""
    bindings, rows = [], []
    for selected, vector, source in zip(inputs, vectors, source_receipts, strict=True):
        binding = {"id": selected["id"], "input_sha256": selected["input_sha256"],
                   "encoder_text_sha256": hashlib.sha256(selected["input"]["source_text"].encode("utf-8")).hexdigest(),
                   "status": "available", "reason": None, "vector_sha256": digest(vector),
                   "upstream_vector_sha256": source["embedding_sha256"] if derived else None,
                   "token_receipt_sha256": source["token_input_sha256"]}
        bindings.append(binding)
        rows.append({**binding, "input": deepcopy(selected["input"]),
                     "encoder_text": selected["input"]["source_text"], "vector": deepcopy(vector),
                     "producer_row_sha256": digest(binding)})
    producer = seal({"schema": owner.PRODUCER_SCHEMA, "profile_sha256": digest(profile),
                     "artifact_binding": artifact, "rows": bindings})
    # These pins are independently selected by this assay from file-pinned
    # historical inputs, before the consumer bundle is assembled or admitted.
    expected = {"profile_sha256": digest(profile), "producer_receipt_sha256": digest(producer),
                "inputs": [{"id": row["id"], "input_sha256": row["input_sha256"]} for row in inputs]}
    bundle = seal({"schema": owner.SCHEMA, "profile": profile, "producer_receipt": producer, "rows": rows})
    return bundle, expected


def check_learned(representations, inputs, raw384, checkpoint_binding):
    require(representations["schema"] == "alignment-source384-representations/v1"
            and representations["profile_id"] == "frozen-source384-projection-endpoints/cpu-float32/v1"
            and representations["status"] == "produced" and representations["row_count"] == 34,
            "saved learned384 profile/status differs")
    require(representations["endpoint_dimensions"] == {key: value[1] for key, value in ENDPOINTS.items()},
            "saved learned endpoint widths differ")
    require(raw(representations["raw_lane"]) == raw(raw384), "learned endpoint upstream native lane differs")
    plan = representations["plan"]
    require(plan["expected_checkpoint_sha256"] == checkpoint_binding["sha256"]
            and plan["input_manifest_sha256"] == inputs["payload_sha256"]
            and plan["raw_lane_sha256"] == raw384["payload_sha256"]
            and plan["input_recipe"] == "saved_exact_source_gte384_vector_without_context_or_parser"
            and plan["endpoint_recipe"] == "x=(raw-mean)/scale;b=tanh(down(x));p=x+up(b);c=tanh(condition(p))",
            "saved learned checkpoint/recipe linkage differs")
    require(plan["payload_sha256"] == digest({k: v for k, v in plan.items() if k != "payload_sha256"}),
            "saved learned plan seal differs")
    for field in ("qualified", "proof_authority", "source_fidelity_established", "context_semantics_applied",
                  "context_resolution_executed", "training_executed", "query_reference_consumed",
                  "sample_memory_used", "target_safety_projection_used", "formula_generation_executed",
                  "parser_features_consumed", "runtime_cryptographically_attested"):
        require(representations[field] is False, "historical learned endpoint authority/scope differs")
    for selected, upstream, row in zip(inputs["rows"], raw384["receipts"], representations["rows"], strict=True):
        require(all(row[key] == selected[key] for key in ("id", "input_sha256", "source_sha256", "context_role"))
                and row["input_embedding_sha256"] == upstream["embedding_sha256"]
                and row["context_forwarded"] is False, "saved learned row input/upstream differs")
        require(set(row["endpoints"]) == set(ENDPOINTS), "complete learned endpoint set required")
        for name, (_, dimension) in ENDPOINTS.items():
            entry = row["endpoints"][name]
            values = entry["values"]
            require(type(values) is list and len(values) == dimension
                    and all(type(value) is float and math.isfinite(value)
                            and struct.unpack("<f", struct.pack("<f", value))[0] == value for value in values),
                    "saved learned endpoint must retain finite exact float32 values")
            require(entry["dimension"] == dimension and entry["values_sha256"] == digest(values)
                    and entry["norm"] == math.hypot(*values), "saved learned endpoint geometry/digest differs")


def prepare_assay():
    """Return six plain-data bundles and external pins without output writes."""
    global STARTED, READ_TOTAL
    STARTED, READ_TOTAL = time.monotonic(), 0
    install_import_guard()
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_context_embeddings as context_owner,
    )
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_lane_bundle as owner,
    )
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_richer_embeddings as raw_owner,
    )

    code_paths = [Path(__file__), Path(owner.__file__), Path(raw_owner.__file__), Path(context_owner.__file__)]
    code_bindings = [read_file(path, retain=False)[1] for path in code_paths]
    values, observations = {}, {}
    for name in PINS:
        values[name], observations[name] = load_pinned(name)
        check_resources()
    _, checkpoint_binding = read_file(CHECKPOINT, CHECKPOINT_SHA, retain=False)
    raw_owner.validate_richer_embedding_inputs(values["source_inputs"])
    context_owner.validate_context_embedding_inputs(values["context_inputs"])
    raw_validations = {}
    for lane_id in ("legacy8", "native384", "native768"):
        raw_validations[lane_id] = raw_owner.validate_embedding_lane(values[lane_id], values["source_inputs"])
        require(values["target_free_inputs"]["lane_bindings"][lane_id] == observations[lane_id],
                "target-free input lane file binding differs")
        for target, historical in zip(values["target_free_inputs"]["rows"], values[lane_id]["receipts"], strict=True):
            entry = target["embeddings"][lane_id]
            require(entry["embedding"] == historical["embedding"]
                    and entry["embedding_sha256"] == historical["embedding_sha256"]
                    and entry["token_input_sha256"] == historical["token_input_sha256"]
                    and entry["backend_input_id"] == historical["backend_input_id"]
                    and entry["profile_id"] == values[lane_id]["backend_evidence"]["profile_id"]
                    and target["id"] == historical["id"], "target-free/raw producer vector join differs")
    inputs, joins = explicit_inputs(values["source_inputs"], values["target_free_inputs"], values["context_inputs"])
    check_learned(values["learned384"], values["source_inputs"], values["native384"], checkpoint_binding)
    profiles = {lane_id: raw_profile(owner, values[lane_id]) for lane_id in ("legacy8", "native384", "native768")}
    builds = {}
    for lane_id in profiles:
        builds[lane_id + "_raw"] = build_view(owner, inputs, profiles[lane_id],
            [row["embedding"] for row in values[lane_id]["receipts"]], values[lane_id]["receipts"], observations[lane_id])
    for endpoint in ENDPOINTS:
        profile = learned_profile(owner, endpoint, values["learned384"], profiles["native384"], checkpoint_binding)
        builds[endpoint] = build_view(owner, inputs, profile,
            [row["endpoints"][endpoint]["values"] for row in values["learned384"]["rows"]],
            values["native384"]["receipts"], observations["learned384"], derived=True)
    check_resources()
    return {"bundles": {name: bundle for name, (bundle, _) in builds.items()},
            "expected_bindings": {name: expected for name, (_, expected) in builds.items()},
            "source_context_joins": joins, "input_file_bindings": observations,
            "checkpoint_file_binding": checkpoint_binding, "code_bindings": code_bindings,
            "raw_native_validations": raw_validations,
            "historical_lanes": {name: values[name] for name in profiles}}


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (30, 35))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    require(not OUTPUT.exists(), "fresh immutable assay directory required")
    prepared = prepare_assay()
    from ipfs_datasets_py.logic.formalization.autoencoder import alignment_lane_bundle as owner

    observations, checkpoint_binding, code_bindings = (prepared["input_file_bindings"],
        prepared["checkpoint_file_binding"], prepared["code_bindings"])
    joins, expected_sets, values = (prepared["source_context_joins"], prepared["expected_bindings"],
        prepared["historical_lanes"])
    OUTPUT.mkdir(mode=0o700)
    plan_binding = save(OUTPUT / "plan.json", seal({"schema": "representation-boundary-static-assay-plan/v1",
         "input_file_pins": {name: {"path": str(CAMPAIGN / path), "sha256": pin} for name, (path, pin) in PINS.items()},
         "checkpoint_file_pin": {"path": str(CHECKPOINT), "sha256": CHECKPOINT_SHA},
         "selected_views": list(prepared["bundles"]), "code_bindings": code_bindings,
         "max_aggregate_input_bytes": MAX_AGGREGATE_BYTES,
         "max_worker_rss_bytes": 512 * 1024**2, "max_wall_seconds": MAX_SECONDS,
         "max_worker_cpu_seconds": [30, 35], "no_model_or_prover_calls": True,
         "checkpoint_body_deserialized": False, "learned_projection_replayed": False,
         "producer_receipts_are_historical_association_transcriptions": True}))
    joins_binding = save(OUTPUT / "source_context_joins.json", seal({"schema": "representation-boundary-source-context-joins/v1",
         "historical_input_sha_recipe": "authored_source_context_identity_retained_in_raw_manifest",
         "explicit_input_sha_recipe": "SHA256 sorted compact UTF8 exact source_text/context envelope",
         "row_count": len(joins), "rows": joins, "context_resolved": False, "target_access": False}))
    expected_binding = save(OUTPUT / "expected_bindings.json", seal({
        "schema": "representation-boundary-externally-selected-bindings/v1", "views": expected_sets,
        "pin_origin": "assay transcription from immutable caller-selected historical file pins",
        "profile_pin_scope": "complete sealed profile JSON digest", "producer_pin_scope": "complete sealed producer-row receipt JSON digest"}))
    artifacts, summaries = {}, {}
    for name, bundle in prepared["bundles"].items():
        # The consumer receives the saved external pin object, never hashes
        # selected from a modified candidate bundle presented by another party.
        validation = owner.validate_lane_bundle(bundle, expected_bindings=expected_sets[name])
        require(validation["row_count"] == validation["available_count"] == 34
                and validation["unavailable_count"] == validation["zero_ablation_count"] == 0,
                "complete available representation rows required")
        require(all(type(mask) is int and mask == 0 for mask in validation["masks"].values())
                and all(validation[field] is False for field in owner.FALSE), "representation boundary promoted authority")
        vector_norms = [math.hypot(*row["vector"]) for row in bundle["rows"]]
        summaries[name] = {"lane_id": bundle["profile"]["lane_id"], "stage": bundle["profile"]["stage"],
            "dimension": bundle["profile"]["dimension"], "profile_sha256": expected_sets[name]["profile_sha256"],
            "producer_receipt_sha256": expected_sets[name]["producer_receipt_sha256"],
            "bundle_content_sha256": bundle["content_sha256"], "row_count": 34,
            "vector_norm_range": [min(vector_norms), max(vector_norms)],
            "normalization": bundle["profile"]["normalization"], "precision": bundle["profile"]["precision"],
            "pooling": bundle["profile"]["pooling"], "status_counts": dict(Counter(row["status"] for row in bundle["rows"])),
            "upstream_vector_bindings": sum(row["upstream_vector_sha256"] is not None for row in bundle["rows"]),
            "token_hash_bindings": sum(row["token_receipt_sha256"] is not None for row in bundle["rows"])}
        artifacts[name] = {"bundle": save(OUTPUT / (name + "_bundle.json"), bundle),
                           "validation": save(OUTPUT / (name + "_validation.json"), validation)}
        check_resources()
    # Confirm source/code/checkpoint bytes again without parsing checkpoint
    # weights. Every original retained artifact stays untouched.
    for observed in (*observations.values(), checkpoint_binding, *code_bindings):
        _, actual = read_file(Path(observed["path"]), observed["sha256"], retain=False)
        require(actual == observed, "input/code binding changed before publication")
    raw_context_counts = Counter(row["context_role"] for row in joins)
    report = {"schema": "representation-boundary-static-assay/v1", "status": "passed_declared_identity_only",
        "plan_file_binding": plan_binding,
        "input_file_bindings": observations, "checkpoint_file_binding": checkpoint_binding,
        "code_bindings": code_bindings, "expected_bindings_file": expected_binding,
        "source_context_joins_file": joins_binding, "artifacts": artifacts, "views": summaries,
        "raw_native_validations": prepared["raw_native_validations"], "raw_view_count": 3, "derived_view_count": 3,
        "raw_vector_count": 102, "derived_vector_count": 102, "total_vector_count": 204,
        "unique_original_input_count": 34, "unique_source_text_count": 33,
        "original_context_counts": dict(raw_context_counts), "context_forwarded_to_raw_or_derived_producers": False,
        "context_resolved": False, "all_vector_values_preserved_exactly": True,
        "backend_input_id_policy": "native384 source-span input IDs joined through full production receipts; outer row ID equality is not required",
        "backend_input_id_differs_from_outer_id_count": {name: sum(row["backend_input_id"] != row["id"] for row in values[name]["receipts"])
                                                       for name in values},
        "normalization_policy": "preserve declared historical normalization; raw8 decimal6 and raw neural unit vectors; learned endpoints none",
        "code_digest_recipe": "raw: SHA256 saved implementation mapping; derived: SHA256 saved executing_source_bindings list",
        "model_assets_digest_recipe": "SHA256 saved raw lane asset_evidence metadata; derived retains upstream384 asset declaration",
        "token_hash_scope": {"legacy8": "absent; normalized feature source hash and token count retained in historical receipt",
            "native384": "digest of complete saved input_ids/attention_mask/token_type_ids map; owner validates exact token/vector-bit linkage",
            "native768": "digest of input ID array as declared by producer; array is not saved so independent token hash recomputation is unavailable",
            "derived_native384": "unchanged upstream native384 token-map digest; no retokenization"},
        "producer_receipt_scope": "normalized declarations transcribe historical artifact associations; no cryptographic runtime attestation",
        "historical_execution_evidence_deserialized": True, "historical_numerical_execution_replayed": False,
        "standard_library_numeric_integrity_checks_executed": True,
        "optional_numerical_import_guard_enforced": True, "optional_numerical_modules_loaded": [],
        "learned_projection_replayed": False, "checkpoint_body_deserialized": False,
        "learned_branch8_is_complete_compressed_input": False, "raw8_is_learned_latent": False,
        "semantic_labels_or_reviews_read": False, "full_reference_panel_read": False,
        "leanstral_vectors_consumed": False, "leanstral_runtime_qualified": False,
        "new_encoder_production_executed": False, "source_files_or_retained_artifacts_modified": False,
        "observed_input_file_hashes_verified": True, "normalized_receipt_file_bindings_verified_by_wrapper": True,
        "dictionary_validator_file_bindings_verified": False, "identity_boundary_is_semantic_admission": False,
        "verification_status": "pending", "admission_status": "pending", "masks": dict.fromkeys(owner.MASKS, 0),
        "view_zero_mask_values": 6 * len(owner.MASKS), "labels_admitted": 0,
        "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
        "resources": {"worker_wall_seconds": time.monotonic() - STARTED,
            "worker_cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            "fresh_worker_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "aggregate_bytes_read_including_rechecks": READ_TOTAL, "max_input_bytes_including_rechecks": MAX_AGGREGATE_BYTES,
            "max_worker_rss_bytes": 512 * 1024**2, "max_wall_seconds": MAX_SECONDS,
            "cpu_limit_seconds": [30, 35], "address_space_limit_bytes": 512 * 1024**2},
        "seal_recipe": "SHA256 sorted compact UTF8 JSON excluding content_sha256; ensure_ascii=False; allow_nan=False",
        **owner.FALSE}
    report_binding = save(OUTPUT / "assay.json", seal(report))
    print(json.dumps({"report_binding": report_binding, "views": 6, "vectors": 204,
                      "model_or_prover_calls": 0}, sort_keys=True), flush=True)


if __name__ == "__main__":
    # A fresh child makes ru_maxrss refer to this static worker rather than an
    # inherited launcher high-water mark observed in earlier campaign runs.
    child = os.fork()
    if child == 0:
        main()
        os._exit(0)
    _, status = os.waitpid(child, 0)
    raise SystemExit(os.waitstatus_to_exitcode(status))
