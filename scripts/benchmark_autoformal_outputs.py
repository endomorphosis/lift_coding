#!/usr/bin/env python3
"""Reproducible CPU throughput comparison; saves inputs, outputs and timing scope.

Run with system python3 (which has the local encoder dependencies), not .venv.
The replacement fixture is synthetic; it is not the lost historical workload.
Groth16 v1 attests knowledge of a commitment, not translation correctness.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "external/ipfs_datasets"
sys.path.insert(0, str(REPO))
os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                  RAYON_NUM_THREADS="1", TOKENIZERS_PARALLELISM="false",
                  IPFS_DATASETS_PY_LAZY_INSTALL_ERGOAI="0", IPFS_DATASETS_ENABLE_GROTH16="1",
                  HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
LEXICAL = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fixture(count):
    actors = ("agency", "officer", "company", "department", "contractor")
    actions = ("retain", "submit", "review", "publish")
    rows = []
    for i in range(count):
        actor, action = actors[i % 5], actions[(i // 5) % 4]
        obj = f"record {i // 20}"
        rows.append({"id": f"tx-{i:04d}", "source_text": f"The {actor} shall {action} the {obj}.",
                     "vocabulary": {"actors": [actor], "actions": [action], "objects": [obj], "qualifiers": []}})
    return rows


def init_worker(method, ready):
    global ENGINE, DECODER
    if method == "spacy8":
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_lineages.legacy_v1._linguistic_snapshot.spacy_modal_codec import SpaCyLegalEncoder, SpaCyModalDecoder
        ENGINE, DECODER = SpaCyLegalEncoder(model_name="en_core_web_sm"), SpaCyModalDecoder()
        if ENGINE.used_fallback_model:
            raise RuntimeError("spaCy fallback forbidden")
    else:
        from ipfs_datasets_py.logic.legal_ir.canonical_compiler import TypedDeonticCanonicalCompiler
        from ipfs_datasets_py.logic.legal_ir.canonical_decompiler import SourceWithheldCanonicalDecompiler
        ENGINE, DECODER = TypedDeonticCanonicalCompiler(), SourceWithheldCanonicalDecompiler()
    ready.wait(timeout=300)
    return os.getpid()


def task(item):
    method, row = item
    started = time.perf_counter()
    if method == "spacy8":
        encoding = ENGINE.encode(row["source_text"], document_id=row["id"], citation=None, source="legal_text")
        output = {"embedding": DECODER.decode_embedding(encoding, dimensions=8), "native_tokens": len(encoding.tokens)}
    else:
        from ipfs_datasets_py.logic.legal_ir.canonical_contracts import CompilerRequest, DecompilerRequest
        compiled = ENGINE.compile(CompilerRequest(row["source_text"], row["id"], row["vocabulary"]))
        if compiled.canonical_ir is None or compiled.status.value != "success":
            raise RuntimeError(str(compiled.error))
        decompiled = DECODER.decompile(DecompilerRequest(compiled.canonical_ir, row["id"]))
        if decompiled.text is None or decompiled.status.value != "success":
            raise RuntimeError(str(decompiled.error))
        output = {"ir": compiled.canonical_ir.to_dict(), "text": decompiled.text,
                  "output_lexical_tokens": len(LEXICAL.findall(decompiled.text))}
        if method == "compiler_groth16_v1":
            from ipfs_datasets_py.logic.zkp.backends.groth16 import Groth16Backend
            # Bind the exact canonical IR to the theorem; v1 is commitment knowledge.
            theorem = "artifact_" + digest(output["ir"])
            backend = Groth16Backend(timeout_seconds=120)
            proof_started = time.perf_counter()
            proof = backend.generate_proof(theorem, [theorem], {"circuit_version": 1})
            proof_seconds = time.perf_counter() - proof_started
            verify_started = time.perf_counter()
            verified = backend.verify_proof(proof)
            if not verified:
                raise RuntimeError("Groth16 verification failed")
            output.update(proof=proof.to_dict(), verified=verified, proof_seconds=proof_seconds,
                          verify_seconds=time.perf_counter() - verify_started, theorem=theorem)
    return {"id": row["id"], "seconds": time.perf_counter() - started, **output}


def parallel(method, rows, cores):
    started = time.perf_counter()
    context = multiprocessing.get_context("spawn")
    ready = context.Barrier(cores)
    with ProcessPoolExecutor(max_workers=cores, initializer=init_worker, initargs=(method, ready),
                             mp_context=context) as pool:
        # Complete initial imports/model loading before steady measurement.
        warm = list(pool.map(task, [(method, row) for row in rows[:cores]], chunksize=1))
        setup_seconds = time.perf_counter() - started
        started = time.perf_counter()
        result = list(pool.map(task, [(method, row) for row in rows], chunksize=1))
        seconds = time.perf_counter() - started
    profile = {"workers": cores, "warmup_transactions": len(warm), "cache": "no output memoization",
               "worker_start_method": "spawn", "all_workers_ready_before_timing": True}
    if method == "compiler_groth16_v1":
        from ipfs_datasets_py.logic.zkp.backends.groth16 import Groth16Backend
        info = Groth16Backend().get_backend_info()
        info["binary_sha256"] = hashlib.sha256(Path(info["binary_path"]).read_bytes()).hexdigest()
        profile["backend"] = info
    return result, seconds, setup_seconds, profile


def dense(method, rows, cores, batch_size):
    import torch
    torch.set_num_threads(cores)
    settings = json.loads((REPO / "configs/autoencoders/alignment_embedding_development_v1.json").read_text())
    started = time.perf_counter()
    if method == "gte384":
        from sentence_transformers import SentenceTransformer
        from ipfs_datasets_py.optimizers.logic_theorem_optimizer import autoencoder_embedding_runtime as runtime
        path, assets = runtime._snapshot_assets(settings["gte384_snapshot"])
        model = SentenceTransformer(str(path), local_files_only=True, device="cpu")
        model.eval()
        runtime._validate_model(model, torch)
        tokenizer = model.tokenizer
        profile = {"dimension": 384, "pooling": "mean", "assets": assets}
    else:
        from ipfs_datasets_py.logic.formalization.autoencoder import source_embeddings_768_complete as complete
        assets_config = settings["gte768_assets"]
        assets = complete.reference._PROFILE.inspect_local_assets(REPO / assets_config["manifest"]["path"],
            expected_sha256=assets_config["manifest"]["sha256"], model_directory=assets_config["model_directory"],
            code_directory=assets_config["code_directory"])
        torch, tokenizer, model, loading = complete._load_backend(assets)
        profile = {"dimension": 768, "pooling": "cls", "assets": assets, "loading": loading}
    model.eval()
    texts = [row["source_text"] for row in rows]

    def infer(texts):
        tokens = tokenizer(texts, padding=True, truncation=False, return_tensors="pt")
        if tokens["input_ids"].shape[1] > (512 if method == "gte384" else 8192):
            raise ValueError("input over context limit")
        with torch.inference_mode():
            if method == "gte384":
                vector = model(tokens)["sentence_embedding"]
            else:
                vector = model(**tokens).last_hidden_state[:, 0, :]
            vector = torch.nn.functional.normalize(vector, p=2, dim=1)
        return vector.tolist(), tokens["attention_mask"].sum(dim=1).tolist()

    infer(texts[:batch_size])
    setup_seconds = time.perf_counter() - started
    result = []
    started = time.perf_counter()
    for offset in range(0, len(rows), batch_size):
        vectors, counts = infer(texts[offset:offset + batch_size])
        for row, vector, count in zip(rows[offset:offset + batch_size], vectors, counts, strict=True):
            if len(vector) != profile["dimension"] or not all(math.isfinite(x) for x in vector):
                raise ValueError("invalid native vector")
            result.append({"id": row["id"], "embedding": vector, "native_tokens": count})
    seconds = time.perf_counter() - started
    profile.update(threads=torch.get_num_threads(), batch_size=batch_size, device="cpu", precision="float32",
                   warmup_transactions=min(batch_size, len(rows)), normalization="l2")
    return result, seconds, setup_seconds, profile


def leanstral_probe(url):
    request = urllib.request.Request(url.rstrip("/") + "/v1/embeddings",
        data=json.dumps({"input": "The agency shall retain the file.", "model": "leanstral_local"}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        vector = result["data"][0]["embedding"]
        if len(vector) != 4096 or not all(math.isfinite(x) for x in vector):
            raise ValueError("invalid 4096D embedding")
        return {"status": "available", "canary_dimension": len(vector)}
    except Exception as error:
        body = error.read().decode() if hasattr(error, "read") else str(error)
        return {"status": "unavailable", "reason": body}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=800)
    parser.add_argument("--cores", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--methods", nargs="+", default=["compiler", "spacy8", "gte384", "gte768", "compiler_groth16_v1"])
    parser.add_argument("--leanstral-url", default="http://172.17.0.1:8080")
    args = parser.parse_args()
    if args.count < args.cores or args.cores < 1 or args.batch_size < 1:
        parser.error("positive batch size and count >= cores >= 1 required")
    cpus = sorted(os.sched_getaffinity(0))[:args.cores]
    if len(cpus) != args.cores:
        parser.error("not enough CPUs")
    os.sched_setaffinity(0, cpus)
    args.output.mkdir(parents=True, exist_ok=False)
    rows = fixture(args.count)
    write(args.output / "workload.json", rows)
    lexical = sum(len(LEXICAL.findall(row["source_text"])) for row in rows)
    report = {"schema": "autoformal-output-throughput/v1", "historical_workload_recovered": False,
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "workload_origin": "replacement synthetic controlled deontic fixture; caller supplies atom vocabulary",
              "workload_sha256": digest(rows), "transactions": len(rows), "cpu_affinity": cpus,
              "common_source_lexical_tokens": lexical, "token_definition": r"Unicode regex \w+|[^\w\s]; native tokenizer counts separately",
              "timing_scope": "warm wall time including input handling, inference, validation, and in-memory result collection; disk writes excluded",
              "proof_scope": "Groth16 v1 knowledge-of-axioms commitment bound to canonical IR digest; no claim of translation correctness",
              "host": os.uname().nodename, "python": sys.version, "methods": {},
              "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    report["source_bindings"] = {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [REPO / "ipfs_datasets_py/logic/legal_ir/canonical_compiler.py",
                     REPO / "ipfs_datasets_py/logic/legal_ir/canonical_decompiler.py",
                     REPO / "ipfs_datasets_py/logic/legal_ir/canonical_contracts.py",
                     REPO / "ipfs_datasets_py/logic/zkp/backends/groth16.py",
                     REPO / "ipfs_datasets_py/logic/zkp/backends/groth16_ffi.py"]}
    report["methods"]["leanstral4096"] = leanstral_probe(args.leanstral_url)
    write(args.output / "report.json", report)
    for method in args.methods:
        print(json.dumps({"method": method, "status": "running"}), flush=True)
        try:
            if method in {"gte384", "gte768"}:
                result, seconds, setup, profile = dense(method, rows, args.cores, args.batch_size)
            elif method in {"compiler", "spacy8", "compiler_groth16_v1"}:
                result, seconds, setup, profile = parallel(method, rows, args.cores)
            else:
                raise ValueError("unknown method: " + method)
            write(args.output / (method + "-outputs.json"), result)
            native = sum(row.get("native_tokens", 0) for row in result)
            generated = sum(row.get("output_lexical_tokens", 0) for row in result)
            summary = {"status": "completed", "completed_transactions": len(result), "wall_seconds": seconds,
                "setup_and_warmup_seconds": setup, "transactions_per_second": len(result) / seconds,
                "source_lexical_tokens_per_second": lexical / seconds, "native_input_tokens": native or None,
                "native_input_tokens_per_second": native / seconds if native else None,
                "output_lexical_tokens_per_second": generated / seconds if generated else None,
                "outputs_sha256": digest(result), "profile": profile}
        except Exception as error:
            summary = {"status": "failed", "reason": type(error).__name__ + ": " + str(error)}
        report["methods"][method] = summary
        write(args.output / "report.json", report)
        print(json.dumps({k: v for k, v in summary.items() if k != "profile"}, default=str), flush=True)
    lines = ["# 800-transaction replacement throughput comparison", "",
             "Original workload was not recovered. These are synthetic statements with supplied atom vocabulary.", "",
             "Twenty logical CPUs; warm wall time; shared-host contention is not controlled. Vector rows measure source encoding, not formalization.", "",
             "| Method | Transactions/s | Source lexical tokens/s | Native input tokens/s | Status |",
             "| --- | ---: | ---: | ---: | --- |"]
    for name, row in report["methods"].items():
        def fmt(key):
            value = row.get(key)
            return f"{value:.2f}" if value is not None else "—"
        lines.append(f"| {name} | {fmt('transactions_per_second')} | {fmt('source_lexical_tokens_per_second')} | {fmt('native_input_tokens_per_second')} | {row['status']} |")
    lines += ["", "Groth16 v1 proves knowledge of a commitment bound to the IR digest. It does not prove faithful source translation.",
              "Native tokens use each encoder's tokenizer, including special tokens for GTE. Vector coordinates are not output tokens.",
              "Setup and warmup, output hashes, actual vectors/proofs, and unavailable reasons are saved in report.json and method output files."]
    (args.output / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
