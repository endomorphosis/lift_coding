#!/usr/bin/env python3
"""Campaign-owned offline GPT-2 backend for the real accelerator manager API.

This module never downloads a model or invokes an external provider. Generation
uses cached model weights, with a small token limit and an explicit CPU device.
"""
from __future__ import annotations
import argparse
import contextlib
import asyncio
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "gpt2"
SNAPSHOT = "607a30d783dfa663caf39e06633721c8d4cfcd7e"
MAX_INPUT_CHARS = 512
MAX_NEW_TOKENS = 4


def validate_request(model: str, input_data: str, max_new_tokens: int = MAX_NEW_TOKENS) -> None:
    if model != MODEL_ID:
        raise ValueError("Only the qualified cached gpt2 model is supported")
    if type(input_data) is not str or not input_data.strip() or len(input_data.encode("utf-8")) > MAX_INPUT_CHARS:
        raise ValueError("Input must be a nonempty string of at most 512 UTF-8 bytes")
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= MAX_NEW_TOKENS:
        raise ValueError("Generation must request 1..4 new tokens")


class OfflineGPT2Backend:
    device = "cpu"

    def __init__(self):
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.set_num_threads(2)
        self.snapshot = Path.home() / ".cache/huggingface/hub/models--gpt2/snapshots" / SNAPSHOT
        for name in ("config.json", "tokenizer.json", "model.safetensors"):
            if not (self.snapshot / name).is_file():
                raise RuntimeError("The qualified GPT-2 snapshot is not fully cached")
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.snapshot), local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(str(self.snapshot), local_files_only=True,
                                                        use_safetensors=True).to("cpu").eval()

    def generate_text(self, *, model_id=None, model=None, inputs=None, prompt=None,
                      max_new_tokens=MAX_NEW_TOKENS, **unused):
        identifier = model_id or model
        text = inputs if isinstance(inputs, str) else prompt
        validate_request(identifier, text, max_new_tokens)
        import torch
        encoded = self.tokenizer(text, return_tensors="pt")
        with torch.inference_mode():
            tokens = self.model.generate(**encoded, max_new_tokens=max_new_tokens,
                do_sample=False, pad_token_id=self.tokenizer.eos_token_id)
        new_ids = tokens[0, encoded["input_ids"].shape[1]:].tolist()
        if not new_ids:
            raise RuntimeError("The model returned no generated tokens")
        output = self.tokenizer.decode(tokens[0], skip_special_tokens=True)
        return {"output": output, "generated_text": self.tokenizer.decode(new_ids, skip_special_tokens=True),
                "generated_token_ids": new_ids, "generated_token_count": len(new_ids),
                "input_token_count": int(encoded["input_ids"].shape[1]), "model_snapshot": SNAPSHOT,
                "model_source": "cached-huggingface-safetensors", "offline": True,
                "simulated": False, "echo_fallback": False}


async def execute_native(output_dir: Path, *, model=MODEL_ID, input_data="short test",
                         max_new_tokens=MAX_NEW_TOKENS, qualification=False, backend=None, worker_context=None) -> dict:
    validate_request(model, input_data, max_new_tokens)
    output_dir = Path(output_dir).absolute()
    if any(parent.is_symlink() for parent in [output_dir, *output_dir.parents]):
        raise ValueError("Native execution output cannot use symlinks")
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(ROOT / "data/agent_supervisor/swissknife_visual_functional"):
        raise ValueError("Qualification outputs must remain in the campaign namespace")
    output_dir.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT / "external/ipfs_accelerate"))
    sdk = importlib.import_module("ipfs_accelerate_py.inference_backend_manager")
    manager_path = ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py"
    if Path(sdk.__file__).resolve() != manager_path.resolve():
        raise RuntimeError("Native manager import is not the pinned SDK file")
    InferenceBackendManager, BackendType, BackendCapabilities, BackendStatus = (
        sdk.InferenceBackendManager, sdk.BackendType, sdk.BackendCapabilities, sdk.BackendStatus)
    started = time.monotonic()
    if backend is None:
        backend = OfflineGPT2Backend()
    manager = InferenceBackendManager({"persist_registry": False, "enable_health_checks": False,
        "state_path": str(output_dir / "unused-registry.json"),
        "capability_registry_path": str(output_dir / "unused-capabilities.json")}, provider_registry={})
    # MCP describes the native execution owner; actual hardware remains CPU.
    ok = manager.register_backend("svf-offline-gpt2-cpu", BackendType.MCP,
        "SVF cached GPT-2 CPU", instance=backend,
        capabilities=BackendCapabilities(supported_tasks={"text-generation"}, supported_models={MODEL_ID},
            hardware_types={"cpu"}, protocols={"mcp"}), status=BackendStatus.HEALTHY,
        configured=True, authorized=True, reachable=True, live=True, ready=True, healthy=True, routable=True)
    if not ok:
        raise RuntimeError("Actual accelerator manager refused local backend registration")
    result = await manager.execute_task(task="text-generation", model=model,
        inputs=[input_data], parameters={"max_new_tokens": max_new_tokens})
    if result.get("generated_token_count", 0) < 1 or result.get("simulated") is not False:
        raise RuntimeError("No actual generated token evidence returned")
    value = {"schema": "swissknife.native-accelerate-qualification.v1" if qualification else "swissknife.native-accelerate-execution-result.v1", "owner": "ipfs_accelerate_py",
        "manager_api": "InferenceBackendManager.execute_task", "model": MODEL_ID,
        "model_snapshot": SNAPSHOT, "duration_seconds": round(time.monotonic()-started,3),
        "input": input_data, "result": result, "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "offline": True, "external_provider_called": False, "download_attempted": False,
        "inference_executed": True, "app_acceptance": False, "work_complete": False, "completion_authority": False}
    manager_path = ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py"
    value["manager_source_sha256"] = hashlib.sha256(manager_path.read_bytes()).hexdigest()
    value["model_cache_path"] = str(backend.snapshot)
    if worker_context is not None:
        value["warm_worker"] = dict(worker_context)
    (output_dir / ("qualification.json" if qualification else "execution.json")).write_text(json.dumps(value,indent=2,default=str)+'\n')
    return value


async def qualify(output_dir: Path) -> dict:
    return await execute_native(output_dir, qualification=True)



WORKER_PROTOCOL = "swissknife.native-accelerate-worker.v1"
WORKER_MAX_INPUT = 8192
WORKER_MAX_OUTPUT = 131072
WORKER_SOURCE_PATHS = ("scripts/svf_backends/native_accelerate_backend.py",
    "scripts/svf_backends/native_accelerate_service.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py")


def process_birth(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def worker_sources(root=ROOT):
    result = {}
    for name in WORKER_SOURCE_PATHS:
        path = Path(root) / name
        if any(parent.is_symlink() for parent in [path, *path.parents]):
            raise ValueError("Worker source must be a regular pinned file")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def serve_worker(input_stream, output_stream, *, root=ROOT, engine_factory=None,
                 executor=None, max_requests=256):
    """One owned model instance; each request still executes the actual SDK.

    Explicit factory/executor arguments exist for authored protocol unit tests;
    the CLI always uses OfflineGPT2Backend and execute_native.
    """
    def read_frame():
        raw = input_stream.readline(WORKER_MAX_INPUT + 1)
        if not raw:
            return None
        if len(raw) > WORKER_MAX_INPUT or not raw.endswith(b"\n"):
            raise ValueError("Worker input frame exceeds its bound")
        value = json.loads(raw)
        if type(value) is not dict:
            raise ValueError("Worker frame must be an object")
        return value

    def emit(value):
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode() + b"\n"
        if len(raw) > WORKER_MAX_OUTPUT:
            raise ValueError("Worker output frame exceeds its bound")
        output_stream.write(raw)
        output_stream.flush()

    init = read_frame()
    required = {"protocol", "type", "worker_id", "parent_pid", "parent_birth", "source_sha256"}
    if (type(init) is not dict or set(init) != required or init["protocol"] != WORKER_PROTOCOL
            or init["type"] != "initialize" or str(uuid.UUID(init["worker_id"])) != init["worker_id"]
            or init["parent_pid"] != os.getppid() or process_birth(os.getppid()) != init["parent_birth"]
            or init["source_sha256"] != worker_sources(root)):
        raise ValueError("Worker initialization identity mismatch")
    sources = init["source_sha256"]
    if engine_factory is None:
        sys.path.insert(0, str(Path(root) / "external/ipfs_accelerate"))
        sdk = importlib.import_module("ipfs_accelerate_py.inference_backend_manager")
        if Path(sdk.__file__).resolve() != Path(root) / WORKER_SOURCE_PATHS[2]:
            raise RuntimeError("Worker manager import is not the pinned SDK file")
        engine_factory = OfflineGPT2Backend
    with contextlib.redirect_stdout(sys.stderr):
        engine = engine_factory()
    if engine.model is None or engine.tokenizer is None or worker_sources(root) != sources:
        raise RuntimeError("Worker model/source readiness failed")
    identity = {"protocol": WORKER_PROTOCOL, "worker_id": init["worker_id"],
        "pid": os.getpid(), "pid_birth": process_birth(os.getpid()), "session_id": os.getsid(0),
        "parent_pid": init["parent_pid"], "parent_birth": init["parent_birth"], "source_sha256": sources}
    emit({**identity, "type": "ready", "engine_loaded": True, "model": MODEL_ID, "model_snapshot": SNAPSHOT})
    seen = set()
    for index in range(max_requests):
        frame = read_frame()
        if frame is None:
            return
        expected = {"protocol", "type", "worker_id", "request_id", "source_sha256", "job_dir",
                    "model", "input_data", "max_new_tokens", "correlation_id"}
        if (set(frame) != expected or frame["protocol"] != WORKER_PROTOCOL or frame["type"] != "execute"
                or frame["worker_id"] != identity["worker_id"] or frame["source_sha256"] != sources
                or worker_sources(root) != sources or os.getppid() != init["parent_pid"]
                or process_birth(os.getppid()) != init["parent_birth"]):
            raise ValueError("Worker request source/owner identity mismatch")
        request_id = frame["request_id"]
        if str(uuid.UUID(request_id)) != request_id or request_id in seen:
            raise ValueError("Worker request UUID is invalid or replayed")
        seen.add(request_id)
        validate_request(frame["model"], frame["input_data"], frame["max_new_tokens"])
        if (frame["correlation_id"] is not None and (type(frame["correlation_id"]) is not str
                or len(frame["correlation_id"]) > 256)):
            raise ValueError("Worker correlation is invalid")
        job = Path(frame["job_dir"])
        if not job.is_absolute() or job.name != request_id or not job.is_relative_to(Path(root) / "data/agent_supervisor/swissknife_visual_functional"):
            raise ValueError("Worker job identity escaped campaign namespace")
        context = {**identity, "request_id": request_id, "correlation_id": frame["correlation_id"]}
        with contextlib.redirect_stdout(sys.stderr):
            native = asyncio.run((executor or execute_native)(job, model=frame["model"],
                input_data=frame["input_data"], max_new_tokens=frame["max_new_tokens"],
                backend=engine, worker_context=context))
        if worker_sources(root) != sources or native.get("warm_worker") != context:
            raise RuntimeError("Worker execution source/correlation changed")
        emit({**context, "type": "completed", "native": native, "retiring": index + 1 == max_requests})


def worker_main():
    # SDK Python and native stdout noise goes to the bounded stderr drain.
    # A duplicate of the original stdout pipe is reserved for exact JSONL frames.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "wb", buffering=0)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = sys.stderr
    try:
        serve_worker(sys.stdin.buffer, protocol)
    finally:
        protocol.close()


def main():
    parser=argparse.ArgumentParser(); modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--qualify", action="store_true");modes.add_argument("--execute", action="store_true")
    modes.add_argument("--worker", action="store_true")
    parser.add_argument("--output-dir", type=Path);args=parser.parse_args()
    if args.worker:
        if args.output_dir is not None: raise ValueError("Worker output directories are per request")
        return worker_main()
    if args.output_dir is None: raise ValueError("Output directory is required")
    request = json.loads(sys.stdin.read(4097)) if args.execute else {}
    if type(request) is not dict or set(request) - {"model", "input_data", "max_new_tokens"}:
        raise ValueError("Unsupported native execution request")
    print(json.dumps(asyncio.run(execute_native(args.output_dir, qualification=args.qualify, **request)),default=str))

if __name__ == "__main__":main()
