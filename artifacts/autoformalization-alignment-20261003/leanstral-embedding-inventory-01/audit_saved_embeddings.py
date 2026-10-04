#!/usr/bin/env python3
"""Audit saved Leanstral vectors with bounded stdlib reads; never run a model."""

import difflib
import hashlib
import json
import math
import os
import struct
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/home/barberb/lift_coding")
CAMPAIGN = ROOT / "artifacts/autoformalization-alignment-20261003"
SAVED = ROOT / "artifacts/autoformal-leanstral4096-800x20-20261004-fixed16"
FAILED = ROOT / "artifacts/autoformal-leanstral4096-800x20-20261003"
CACHE = Path("/home/barberb/.cache/ipfs_accelerate_py/llama_cpp")
SOURCE = CACHE / "source/llama.cpp"
MODEL = CACHE / "models/cid-v1/bafkreicgnd6su3jhmtpckbejqurdb2lchdvvydluswdg5m5zy3cpvroh3i/Leanstral-1.5-119B-A6B-NVFP4.gguf"
ASSET_MANIFEST = CACHE / "models/refs/Frosty40_Leanstral-1.5-119B-A6B-GGUF-NVFP4/Leanstral-1.5-119B-A6B-NVFP4.gguf.json"
OUTPUT = Path(__file__).resolve().parent / "inventory.json"
HEADER_BYTES = 8_385_220
MAX_SMALL_JSON = 8 * 1024 * 1024
MAX_BOUND_FILE = 128 * 1024 * 1024
CHUNK = 262_144
MAX_ROW_BUFFER = 2 * 1024 * 1024
EXPECTED_REPORT = "c222de3846619794db32c7b534cc942dd29f8f1561d270573a5923930eedebcc"
EXPECTED_FAILED_REPORT = "bde78bb39fe0472d92bcdea846d5c41018f0f539947b8ce37e464d21f38ab2b3"
EXPECTED_REVISION = "571d0d540df04f25298d0e159e520d9fc62ed121"
EXPECTED_HEADER = "550c9abbf62aa6acee190e8a3f621910c111b26ca32cf6cfbfbb4203ed7c77b4"
EXPECTED_EXECUTED = "6bc0f6fb48b5378bea4583df45e32a6c49b8ceaef5b8a35ad2757067238350c4"
EXPECTED_CURRENT = "6a33b3f75ba247d46977422a5d27978d9835fcceadf46bf2b935f9a09b7b6980"


def registered_digest(value):
    """Use the unchanged historical producer's exact digest recipe."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def seal_digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("nonfinite JSON constant")


def read_json(path):
    assert path.stat().st_size <= MAX_SMALL_JSON
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                      parse_constant=reject_constant)


def file_binding(path):
    size = path.stat().st_size
    assert size <= MAX_BOUND_FILE, "no whole-model or unbounded hashing"
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "bytes": size, "sha256": digest}


def iter_rows(path):
    """Stream the exact saved JSON array, keeping at most one bounded row."""
    decoder = json.JSONDecoder(object_pairs_hook=unique_pairs,
                               parse_constant=reject_constant)
    assert path.stat().st_size <= MAX_BOUND_FILE
    with path.open("r", encoding="utf-8") as stream:
        buffer = stream.read(CHUNK).lstrip()
        assert buffer.startswith("[")
        buffer = buffer[1:]
        first = True
        while True:
            buffer = buffer.lstrip()
            if not buffer:
                more = stream.read(CHUNK)
                assert more
                buffer += more
                continue
            if buffer[0] == "]":
                assert not (buffer[1:] + stream.read()).strip()
                return
            if not first:
                assert buffer[0] == ","
                buffer = buffer[1:].lstrip()
            while True:
                try:
                    row, end = decoder.raw_decode(buffer)
                    break
                except json.JSONDecodeError:
                    more = stream.read(CHUNK)
                    assert more
                    buffer += more
                    assert len(buffer) < MAX_ROW_BUFFER
            yield row
            buffer = buffer[end:]
            first = False


def inspect_header():
    """Read exactly the frozen metadata prefix, stopping before tensor headers."""
    with MODEL.open("rb") as stream:
        buffer = stream.read(HEADER_BYTES)
    assert len(buffer) == HEADER_BYTES
    header_hash = hashlib.sha256(buffer).hexdigest()
    assert header_hash == EXPECTED_HEADER
    assert buffer[:4] == b"GGUF"
    version = struct.unpack_from("<I", buffer, 4)[0]
    tensor_count = struct.unpack_from("<Q", buffer, 8)[0]
    kv_count = struct.unpack_from("<Q", buffer, 16)[0]
    assert (version, tensor_count, kv_count) == (3, 615, 58)
    position = 24
    formats = {0: "B", 1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f",
               7: "?", 10: "Q", 11: "q", 12: "d"}

    def number(fmt):
        nonlocal position
        size = struct.calcsize("<" + fmt)
        assert position + size <= len(buffer)
        value = struct.unpack_from("<" + fmt, buffer, position)[0]
        position += size
        return value

    def string(capture):
        nonlocal position
        size = number("Q")
        assert size <= HEADER_BYTES and position + size <= len(buffer)
        value = buffer[position:position + size].decode("utf-8") if capture else None
        position += size
        return value

    def value(kind, capture=False):
        if kind in formats:
            return number(formats[kind])
        if kind == 8:
            return string(capture)
        if kind == 9:
            element = number("I")
            count = number("Q")
            assert element != 9 and count <= 1_048_576
            for _ in range(count):
                value(element)
            return {"array_length": count, "element_type": element}
        raise ValueError("unknown GGUF metadata type")

    selected = {
        "general.architecture", "general.type", "general.base_model.0.name",
        "general.base_model.0.version", "general.base_model.0.organization",
        "general.base_model.0.repo_url", "general.file_type", "general.quantization_version",
        "deepseek2.block_count", "deepseek2.context_length", "deepseek2.embedding_length",
        "deepseek2.vocab_size", "deepseek2.expert_count", "deepseek2.expert_used_count",
        "tokenizer.ggml.model", "tokenizer.ggml.pre", "tokenizer.ggml.tokens",
        "tokenizer.ggml.bos_token_id", "tokenizer.ggml.eos_token_id",
        "tokenizer.ggml.add_bos_token", "tokenizer.ggml.add_eos_token",
    }
    fields = {}
    for _ in range(kv_count):
        key = string(True)
        kind = number("I")
        item = value(kind, key in selected)
        if key in selected:
            fields[key] = item
    assert position == HEADER_BYTES
    assert fields["general.architecture"] == "deepseek2"
    assert fields["deepseek2.embedding_length"] == 4096
    assert fields["deepseek2.block_count"] == 36
    assert fields["deepseek2.vocab_size"] == 131_072
    return {"metadata_bytes": HEADER_BYTES, "metadata_prefix_sha256": header_hash,
            "version": version, "tensor_count": tensor_count, "metadata_kv_count": kv_count,
            "metadata_end_offset": position, "selected_metadata": fields,
            "tensor_headers_or_weights_read": False, "tensors_loaded": False,
            "full_model_hash_verified": False}


def current_memory():
    selected = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        key, _, text = line.partition(":")
        if key in {"VmRSS", "VmHWM"}:
            selected[key + "_KiB"] = int(text.split()[0])
    return selected


def main():
    assert not OUTPUT.exists(), "immutable output already exists"
    started = time.monotonic()
    bindings = {}

    def bind(path):
        result = file_binding(path)
        previous = bindings.get(str(path))
        assert previous is None or previous == result
        bindings[str(path)] = result
        return result

    report_path = SAVED / "report.json"
    assert bind(report_path)["sha256"] == EXPECTED_REPORT
    assert bind(FAILED / "report.json")["sha256"] == EXPECTED_FAILED_REPORT
    report = read_json(report_path)
    failed = read_json(FAILED / "report.json")
    assert report["status"] == "completed" and failed["status"] == "failed"
    assert report["original_service_restored"] is True
    assert report["dimension"] == 4096 and report["pooling"] == "last"
    assert report["normalization"] == "l2"
    assert report["input"] == "exact raw source, no chat template"
    assert report["model_path"] == str(MODEL)
    assert report["cpu_threads"] == 20
    assert report["server_cpu_affinity"] == list(range(20))
    assert report["server_props"]["total_slots"] == 16
    assert report["server_props"]["build_info"] == "b1-571d0d5"

    workload_path = SAVED / "workload.json"
    bind(workload_path)
    workload = read_json(workload_path)
    assert len(workload) == report["transactions_per_run"] == 800
    assert len({row["id"] for row in workload}) == 800
    source_hashes = {hashlib.sha256(row["source_text"].encode("utf-8")).hexdigest()
                     for row in workload}
    assert len(source_hashes) == 800
    assert registered_digest(workload) == report["workload_sha256"] == failed["workload_sha256"]
    assert len(report["token_receipts"]) == 800
    assert all(source["id"] == tokens["id"] for source, tokens in
               zip(workload, report["token_receipts"], strict=True))
    native_tokens = sum(len(row["tokens"]) for row in report["token_receipts"])
    assert native_tokens == 8600

    output_checks = []
    for run in report["runs"]:
        path = SAVED / f"outputs-{run['repeat']}.json"
        binding = bind(path)
        digest = hashlib.sha256()
        digest.update(b"[")
        count = 0
        min_norm, max_norm = 2.0, 0.0
        for source, row in zip(workload, iter_rows(path), strict=True):
            assert type(row) is dict and set(row) == {"id", "embedding"}
            assert row["id"] == source["id"]
            vector = row["embedding"]
            assert type(vector) is list and len(vector) == 4096
            assert all(type(item) in (int, float) and math.isfinite(item) for item in vector)
            norm = math.hypot(*vector)
            assert abs(norm - 1) < 1e-4
            min_norm, max_norm = min(min_norm, norm), max(max_norm, norm)
            if count:
                digest.update(b",")
            digest.update(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode())
            count += 1
        digest.update(b"]")
        assert count == 800 and digest.hexdigest() == run["outputs_sha256"]
        assert run["native_input_tokens"] == native_tokens
        assert math.isclose(run["transactions_per_second"], 800 / run["wall_seconds"])
        output_checks.append({"repeat": run["repeat"], "row_count": count,
                              "finite_4096_value_count": count * 4096,
                              "exact_workload_id_joins": count,
                              "norm_min": min_norm, "norm_max": max_norm,
                              "payload_sha256": digest.hexdigest(),
                              "file_sha256": binding["sha256"],
                              "registered_payload_hash_matches": True})
    assert len(output_checks) == 3
    assert len({row["file_sha256"] for row in output_checks}) == 1
    assert len({row["payload_sha256"] for row in output_checks}) == 1

    canary_path = SAVED / "canary.json"
    bind(canary_path)
    canary = read_json(canary_path)
    for name, expected_count in [("single", 1), ("batch", 16), ("replay", 1)]:
        assert len(canary[name]) == expected_count
        for row in canary[name]:
            assert len(row["embedding"]) == 4096
            assert all(type(item) in (int, float) and math.isfinite(item)
                       for item in row["embedding"])
            assert abs(math.hypot(*row["embedding"]) - 1) < 1e-4
    assert canary["single"][0]["id"] == canary["batch"][0]["id"] == canary["replay"][0]["id"] == workload[0]["id"]

    def distance(left, right):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)))

    single_batch = distance(canary["single"][0]["embedding"], canary["batch"][0]["embedding"])
    replay = distance(canary["single"][0]["embedding"], canary["replay"][0]["embedding"])
    assert single_batch == report["canary"]["single_vs_batch_l2"]
    assert replay == report["canary"]["a_b_a_replay_l2"] == 0
    assert report["canary"]["single_batch_equivalent_at_1e_3"] is False
    assert single_batch > report["canary"]["tolerance_l2"] == 0.001
    assert canary["metrics"] == report["canary"]

    old_path = CAMPAIGN / "typed-anchor-decoder-recovery-01/inference_requests.json"
    new_path = CAMPAIGN / "binding-review-packet-01/reviewer_items.json"
    bind(old_path)
    bind(new_path)
    old = read_json(old_path)
    new = read_json(new_path)
    assert len(old["rows"]) == old["row_count"] == 34 and len(new["items"]) == 64
    old_hashes = {hashlib.sha256(row["source_text"].encode("utf-8")).hexdigest()
                  for row in old["rows"]}
    new_hashes = {hashlib.sha256(row["source_text"].encode("utf-8")).hexdigest()
                  for row in new["items"]}
    assert len(old_hashes) == 33 and len(new_hashes) == 64
    assert not source_hashes & old_hashes and not source_hashes & new_hashes

    bind(ASSET_MANIFEST)
    asset = read_json(ASSET_MANIFEST)
    stat = MODEL.stat()
    assert stat.st_size == asset["size_bytes"] == report["model_bytes"] == 67_135_119_264
    assert asset["content_cid_v1_path"] == str(MODEL)
    header = inspect_header()
    runtime_path = SAVED / "runtime-mapped-binaries.json"
    bind(runtime_path)
    runtime = read_json(runtime_path)
    assert runtime["source_revision"] == EXPECTED_REVISION
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=SOURCE,
                              check=True, capture_output=True, text=True, timeout=5).stdout.strip()
    assert revision == EXPECTED_REVISION
    binary_checks, source_checks = [], []
    for path, previous in runtime["binary_bindings"].items():
        binding = bind(Path(path))
        assert binding["bytes"] == previous["bytes"] and binding["sha256"] == previous["sha256"]
        binary_checks.append({**binding, "matches_saved_runtime_binding": True})
    for path, expected_hash in runtime["source_bindings"].items():
        binding = bind(SOURCE / path)
        assert binding["sha256"] == expected_hash
        source_checks.append({**binding, "matches_saved_runtime_binding": True})
    assert len(binary_checks) == 9 and len(source_checks) == 4
    assert report["binary_sha256"] == bindings[str(CACHE / "build/bin/llama-server")]["sha256"]

    executed_path = SAVED / "executed-producer.py"
    current_path = ROOT / "scripts/benchmark_leanstral_embeddings.py"
    assert bind(executed_path)["sha256"] == report["producer_sha256"] == EXPECTED_EXECUTED
    assert bind(current_path)["sha256"] == EXPECTED_CURRENT
    executed = executed_path.read_text(encoding="utf-8")
    current = current_path.read_text(encoding="utf-8")
    diff = "".join(difflib.unified_diff(executed.splitlines(True), current.splitlines(True),
                                     fromfile="executed-producer.py", tofile="current-script", n=2))
    # The inference/measurement body is unchanged; differences surround service cleanup.
    inference_start = "        def erase(slot):"
    inference_end = "    except BaseException as error:"
    executed_body = executed.split(inference_start, 1)[1].split(inference_end, 1)[0]
    current_body = current.split(inference_start, 1)[1].split(inference_end, 1)[0]
    assert executed_body == current_body
    bind(SAVED / "benchmark_autoformal_outputs.py")
    bind(SAVED / "restoration-validation.json")
    restoration = read_json(SAVED / "restoration-validation.json")
    assert restoration["original_service_restored"] is True
    assert restoration["original_argv_restored_exactly"] is True
    log_path = SAVED / "embedding-server.log"
    bind(log_path)
    log = log_path.read_text(encoding="utf-8")
    resource_lines = [line for line in log.splitlines()
                      if "memory peak" in line and "leanstral-throughput-embedding-benchmark.service:" in line]
    assert len(resource_lines) == 2
    assert "62.8G memory peak" in resource_lines[0] and "47.5G memory peak" in resource_lines[1]
    assert all("0B memory swap peak" in line for line in resource_lines)
    assert "n_slots = 16, n_ctx_slot = 512" in log
    for path in [ROOT / "scripts/run_leanstral_ephemeral.py",
                 ROOT / "scripts/run_leanstral_ephemeral.md",
                 ROOT / "JevOps/jevops/leanstral.py",
                 ROOT / "scripts/summarize_standalone_zk_leanstral.py",
                 SOURCE / "common/arg.cpp", SOURCE / "tools/server/README.md",
                 Path(__file__).resolve()]:
        bind(path)

    false_flags = {
        "model_loaded_this_stage": False, "model_inference_executed_this_stage": False,
        "new_embeddings_generated": False, "gpu_admission_attempted": False,
        "service_started_stopped_or_reconfigured": False, "model_or_source_files_modified": False,
        "training_executed": False, "retrieval_quality_evaluated": False,
        "source_fidelity_established": False, "proof_authority": False,
        "qualified": False, "accepted": False,
        "independent_semantic_review_completed": False,
        "actual_training_or_evaluation_admission": False,
    }
    inventory = {
        "schema": "leanstral-saved-embedding-static-inventory/v1",
        "created_utc": datetime.now(UTC).isoformat(),
        "audit_scope": "read-only stdlib replay of saved bytes; no model or live embedding request",
        "audit_execution": {"static_elapsed_seconds": time.monotonic() - started,
                            "stream_chunk_bytes": CHUNK, "max_row_parse_buffer_bytes": MAX_ROW_BUFFER,
                            "max_small_json_bytes": MAX_SMALL_JSON,
                            "largest_hashed_file_bound_bytes": MAX_BOUND_FILE,
                            "linux_process_memory": current_memory(),
                            "subprocess_scope": "git rev-parse HEAD only"},
        "saved_run_identity": {"report_file_sha256": EXPECTED_REPORT,
                               "workload_sha256": report["workload_sha256"],
                               "source_revision": revision,
                               "build_info": report["server_props"]["build_info"],
                               "runtime_manifest_file_sha256": bindings[str(runtime_path)]["sha256"]},
        "workload_joins": {"rows": 800, "unique_ids": 800, "unique_exact_source_sha256": 800,
                           "token_receipt_id_joins": 800, "registered_workload_digest_matches": True,
                           "native_tokens": native_tokens,
                           "historical_workload_row_keys": sorted(workload[0]),
                           "non_source_metadata_scope": "historical vocabulary fields were deserialized and covered by workload digest; only id/source_text used for source joins, no quality assessment"},
        "vector_checks": {"runs": output_checks, "total_rows": 2400,
                          "total_finite_4096_values": 9_830_400,
                          "all_three_output_files_byte_identical": True,
                          "fixed_profile_repeatability_only": True},
        "canary_checks": {"single_rows": 1, "batch_rows": 16, "replay_rows": 1,
                          "vectors_finite_unit_norm_4096": True,
                          "single_vs_batch_l2": single_batch, "a_b_a_replay_l2": replay,
                          "registered_tolerance_l2": 0.001,
                          "single_batch_equivalent_at_tolerance": False,
                          "saved_report_metrics_exactly_recomputed": True},
        "prior_failed_run": {"report_file_sha256": EXPECTED_FAILED_REPORT,
                             "status": failed["status"], "full_workload_run_count": len(failed["runs"]),
                             "single_vs_batch_l2": failed["canary"]["single_vs_batch_l2"],
                             "original_service_restored_declared": failed["original_service_restored"]},
        "current_panel_overlap": {"comparison": "SHA256 exact UTF8 source_text only; no context, targets or vector values in matching",
                                  "old_request_rows": 34, "old_unique_source_texts": len(old_hashes),
                                  "new_public_packet_rows": 64, "new_unique_source_texts": 64,
                                  "old_exact_source_overlap": 0, "new_exact_source_overlap": 0,
                                  "cached_vectors_directly_join_current_panels": False},
        "model_asset": {"path": str(MODEL), "observed_stat_bytes": stat.st_size,
                        "observed_stat_mtime_ns": stat.st_mtime_ns,
                        "manifest_path": str(ASSET_MANIFEST),
                        "manifest_file_sha256": bindings[str(ASSET_MANIFEST)]["sha256"],
                        "manifest_declared_model_sha256": asset["content_sha256"],
                        "manifest_declared_cid_v1": asset["content_cid_v1"],
                        "declared_model_digest_independently_verified_this_stage": False,
                        "whole_model_bytes_hashed_this_stage": 0,
                        "header": header,
                        "separate_user_finetuned_checkpoint_established": False},
        "backend_checks": {"binaries": binary_checks, "sources": source_checks,
                           "native_hidden_width": 4096, "vocabulary_logits_width": 131072,
                           "last_transformer_block_index": 35,
                           "extraction_location": "src/models/deepseek2.cpp:426-430 final RMS-normalized t_embd, preceding lm_head/t_logits",
                           "source_output_routes": {"generation_client": "JevOps/jevops/leanstral.py chat_completion",
                                                    "pooled_embedding": "/v1/embeddings requires --embeddings and pooling other than none",
                                                    "per_token_embedding": "/embeddings with pooling none; not exercised by saved run"}},
        "producer_checks": {"executed_producer_sha256": EXPECTED_EXECUTED,
                            "current_script_sha256": EXPECTED_CURRENT,
                            "executed_producer_matches_saved_report": True,
                            "current_script_identical_to_executed": False,
                            "unified_diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
                            "embedding_inference_measurement_body_unchanged": True,
                            "diff_scope": "current script sets restoration guard before stopping service and protects stop/log collection/restoration/final report on failure",
                            "executed_source_not_imported_or_run": True,
                            "historical_service_unit_content_not_exported": True},
        "registered_embedding_profile": {"pooling": "last", "normalization": "l2",
                                         "input": report["input"], "request_route": "/v1/embeddings",
                                         "chat_template_applied": False,
                                         "tokenizer": "Tekken; GGUF gpt2 tokenization frontend",
                                         "add_bos_token": True, "add_eos_token": False,
                                         "tokenizer_flags_in_saved_request": {"add_special": True, "parse_special": True},
                                         "cpu_threads": 20, "parallel_slots": 16,
                                         "context_total_requested": 8192, "context_per_slot_observed": 512,
                                         "batch_size": 512, "physical_microbatch_size": 512,
                                         "gpu": "CUDA0", "gpu_layers_requested": 36, "fit": "off",
                                         "cache_policy": report["cache_policy"],
                                         "exact_server_argv_file_scope": "retained report, not copied here"},
        "reported_historical_cost": {"new_benchmark_executed": False,
                                     "load_seconds": report["server_load_seconds"],
                                     "medians": report["medians"], "timing_scope": report["timing_scope"],
                                     "mixed_journal_earlier_failed_memory_peak": "62.8G",
                                     "selected_completed_unit_memory_peak": "47.5G",
                                     "selected_completed_unit_swap_peak": "0B",
                                     "resource_scope": "saved systemd unit journal, not current host admission or model allocation guarantee",
                                     "service_restoration_report_and_saved_receipt_agree": True},
        "limitations": [
            "Saved fixed-order 16-slot repeats do not establish batch-peer, order, padding or slot independence.",
            "The observed single-vs-batch failure has no established cause; representation cache identity must retain batching policy until qualified.",
            "Mean pooling, per-token extraction and long-context behavior were not exercised by these saved outputs.",
            "The historical benchmark replaces the managed generation service and does not share the ephemeral runner GPU lock/admission envelope.",
            "Current resource readiness is owned by root's separate read-only preflight; this stage does not admit residency.",
            "Cached throughput sources have no exact match in the current34/64 panels and cannot supply their embeddings.",
            "Historical synthetic throughput and vector validity establish neither retrieval quality nor autoformalization/source fidelity.",
            "GGUF header/stat and manifest-declared digest do not independently authenticate all current weight bytes or a separately fine-tuned checkpoint.",
        ],
        "file_bindings": sorted(bindings.values(), key=lambda item: item["path"]),
        "false_flags": false_flags,
        "seal_recipe": "SHA256 canonical sorted compact UTF8 JSON, ensure_ascii=False, allow_nan=False, excluding content_sha256",
    }
    inventory["content_sha256"] = seal_digest(inventory)
    raw = (json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True,
                      allow_nan=False) + "\n").encode("utf-8")
    descriptor = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    saved = read_json(OUTPUT)
    content_hash = saved.pop("content_sha256")
    assert seal_digest(saved) == content_hash
    print(json.dumps({"inventory": str(OUTPUT), "file_sha256": hashlib.sha256(raw).hexdigest(),
                      "bytes": len(raw), "content_sha256": content_hash,
                      "bound_files": len(bindings), "vectors_checked": 2400,
                      "new_model_calls": 0, "source_fidelity_established": False}))


if __name__ == "__main__":
    main()
