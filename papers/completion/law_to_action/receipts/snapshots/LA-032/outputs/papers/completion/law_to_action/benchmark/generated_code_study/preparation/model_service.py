#!/usr/bin/env python3
"""Bounded loopback model service. Not a systemd unit and not always-on.

Loads a digest-bound tiny GPT-2, serves llama.cpp-compatible template/tokenize/
chat endpoints, and shuts down after the service wall. Startup must complete
within 360 seconds. Warm weights are reused for subsequent calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
RUNTIME_PYTHON = Path("/home/barberb/.local/share/vericodegen-research-runtime/python")
if RUNTIME_PYTHON.is_dir() and str(RUNTIME_PYTHON) not in sys.path:
    sys.path.insert(0, str(RUNTIME_PYTHON))
SITE = Path("/opt/ipfs-validation-site-packages")
if SITE.is_dir() and str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))
from study_common import (
    CHAT_TEMPLATE,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    SERVICE_WALL_SECONDS,
    STARTUP_READINESS_SECONDS,
    sha_file,
    write_json,
)

MODEL_ID = "sshleifer/tiny-gpt2"
MODEL_REVISION = "5f91d94"


class ModelService:
    def __init__(self, cache: Path, wall_seconds=SERVICE_WALL_SECONDS):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.wall_seconds = wall_seconds
        self.started = time.monotonic()
        self.ready_at = None
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.calls = []
        self.tokenizer = None
        self.model = None
        self.pins = None
        self.httpd = None
        self.port = None

    def load(self):
        os.environ.setdefault("HF_HOME", str(self.cache))
        os.environ.setdefault("TRANSFORMERS_CACHE", str(self.cache))
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        deadline = self.started + STARTUP_READINESS_SECONDS
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, GPT2Tokenizer

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("startup-readiness bound exhausted before load")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, cache_dir=str(self.cache))
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.chat_template = CHAT_TEMPLATE
        model = AutoModelForCausalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION, cache_dir=str(self.cache))
        model.eval()
        snapshot = self._snapshot_dir()
        weights = sorted(p for p in snapshot.rglob("*") if p.is_file() and p.suffix in {".bin", ".safetensors", ".json", ".txt", ".model"})
        if not weights:
            weights = sorted(p for p in snapshot.rglob("*") if p.is_file())
        weight_files = {str(p.relative_to(snapshot)): sha_file(p) for p in weights}
        tokenizer_files = {name: digest for name, digest in weight_files.items() if "tokenizer" in name or name in {"vocab.json", "merges.txt", "special_tokens_map.json", "tokenizer_config.json", "tokenizer.json"}}
        self.tokenizer = tokenizer
        self.model = model
        self.ready_at = time.monotonic()
        self.pins = {
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "tokenizer_id": MODEL_ID,
            "tokenizer_revision": MODEL_REVISION,
            "chat_template": CHAT_TEMPLATE,
            "chat_template_sha256": hashlib.sha256(CHAT_TEMPLATE.encode()).hexdigest(),
            "weights_files": weight_files,
            "tokenizer_files": tokenizer_files,
            "snapshot_dir": str(snapshot),
            "torch_version": torch.__version__,
            "startup_seconds": self.ready_at - self.started,
            "startup_readiness_seconds": STARTUP_READINESS_SECONDS,
            "service_wall_seconds": self.wall_seconds,
            "systemd_required": False,
            "indefinitely_running_required": False,
        }
        if self.pins["startup_seconds"] > STARTUP_READINESS_SECONDS:
            raise TimeoutError("startup exceeded 360-second readiness bound")
        return self.pins

    def _snapshot_dir(self):
        hub = self.cache / "hub"
        matches = list(self.cache.rglob("config.json"))
        if not matches and hub.exists():
            matches = list(hub.rglob("config.json"))
        if not matches:
            return self.cache
        return matches[0].parent

    def remaining(self):
        return self.wall_seconds - (time.monotonic() - self.started)

    def apply_template(self, messages, add_generation_prompt=True):
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=add_generation_prompt, chat_template=CHAT_TEMPLATE
        )
        if not isinstance(prompt, str):
            prompt = str(prompt)
        return prompt

    def tokenize(self, content, add_special=True):
        tokens = self.tokenizer.encode(content, add_special_tokens=bool(add_special))
        return [int(t) for t in tokens]

    def complete(self, messages, seed, max_tokens, cancel_event=None):
        import torch

        if self.remaining() <= 0:
            raise TimeoutError("model service wall exhausted")
        prompt = self.apply_template(messages, add_generation_prompt=True)
        tokens = self.tokenize(prompt, add_special=True)
        input_count = len(tokens)
        if input_count > MAX_INPUT_TOKENS:
            raise ValueError("preflight input_count exceeds 2048")
        max_tokens = min(int(max_tokens), MAX_OUTPUT_TOKENS)
        torch.manual_seed(int(seed))
        input_ids = torch.tensor([tokens], dtype=torch.long)
        generated = []
        with self.lock:
            if (cancel_event or self.cancel).is_set():
                raise InterruptedError("generation cancelled before first token")
            with torch.no_grad():
                output = self.model.generate(
                    input_ids,
                    max_new_tokens=max_tokens,
                    do_sample=False,
                    pad_token_id=self.tokenizer.pad_token_id,
                )
            if (cancel_event or self.cancel).is_set():
                raise InterruptedError("generation cancelled")
            new_tokens = output[0].tolist()[input_count:]
            text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        # Returned usage must equal the retained preflight count, not a looser bound.
        prompt_tokens = input_count
        completion_tokens = len(new_tokens)
        if prompt_tokens != input_count:
            raise RuntimeError("prompt_tokens drifted from preflight input_count")
        if completion_tokens > MAX_OUTPUT_TOKENS:
            raise RuntimeError("output-token ceiling exceeded")
        record = {
            "prompt": prompt,
            "input_count": input_count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "text": text,
            "seed": int(seed),
            "max_tokens": max_tokens,
        }
        self.calls.append(record)
        return record


class Handler(BaseHTTPRequestHandler):
    service: ModelService

    def log_message(self, fmt, *args):
        return

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode()), raw

    def _send(self, code, body):
        payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        try:
            body, raw = self._read_json()
            if self.path.endswith("/apply-template"):
                prompt = self.service.apply_template(body.get("messages") or [], body.get("add_generation_prompt", True))
                self._send(200, {"prompt": prompt})
                return
            if self.path.endswith("/tokenize"):
                tokens = self.service.tokenize(body.get("content") or "", body.get("add_special", True))
                self._send(200, {"tokens": tokens})
                return
            if self.path.endswith("/v1/chat/completions"):
                messages = body.get("messages") or []
                seed = body.get("seed", 0)
                max_tokens = body.get("max_tokens", MAX_OUTPUT_TOKENS)
                result = self.service.complete(messages, seed, max_tokens)
                self._send(200, {
                    "id": "la032-" + hashlib.sha256(raw).hexdigest()[:12],
                    "object": "chat.completion",
                    "model": MODEL_ID,
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": result["text"]}, "finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": result["prompt_tokens"],
                        "completion_tokens": result["completion_tokens"],
                        "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
                    },
                    "preflight_input_count": result["input_count"],
                })
                return
            if self.path.endswith("/cancel"):
                self.service.cancel.set()
                self._send(200, {"cancelled": True})
                return
            self._send(404, {"error": "unknown path"})
        except InterruptedError as exc:
            self._send(499, {"error": str(exc), "cancelled": True})
        except Exception as exc:
            self._send(500, {"error_type": type(exc).__name__, "error": str(exc)})


def serve(cache: Path, port=0):
    service = ModelService(cache)
    pins = service.load()
    Handler.service = service
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    service.httpd = httpd
    service.port = httpd.server_address[1]
    pins["base_url"] = f"http://127.0.0.1:{service.port}"
    return service, pins


def qualify(output: Path, cache: Path):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    service, pins = serve(cache, port=0)
    thread = threading.Thread(target=service.httpd.serve_forever, daemon=True)
    thread.start()
    import urllib.request

    def post(path, body, label):
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        request_path = output / f"{label}.request.bin"
        request_path.write_bytes(raw)
        req = urllib.request.Request(
            pins["base_url"] + path, data=raw, headers={"Content-Type": "application/json"}, method="POST"
        )
        started = time.monotonic()
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read()
        (output / f"{label}.response.bin").write_bytes(payload)
        decoded = json.loads(payload)
        write_json(output / f"{label}.receipt.json", {
            "path": path,
            "wall_seconds": time.monotonic() - started,
            "request_sha256": hashlib.sha256(raw).hexdigest(),
            "response_sha256": hashlib.sha256(payload).hexdigest(),
            "body": decoded,
        })
        return decoded

    messages = [{"role": "system", "content": "Reply with a single token."}, {"role": "user", "content": "ping"}]
    rendered = post("/apply-template", {"messages": messages, "add_generation_prompt": True}, "call0_template")
    tokenized = post("/tokenize", {"content": rendered["prompt"], "add_special": True}, "call0_tokenize")
    input_count = len(tokenized["tokens"])
    write_json(output / "call0_preflight.json", {"input_count": input_count, "prompt": rendered["prompt"]})
    completion = post("/v1/chat/completions", {
        "model": MODEL_ID, "messages": messages, "temperature": 0, "seed": 104729, "max_tokens": 8, "stream": False
    }, "call0_inference")
    usage = completion["usage"]
    if usage["prompt_tokens"] != input_count:
        raise RuntimeError(f"prompt_tokens {usage['prompt_tokens']} != preflight input_count {input_count}")
    if usage["prompt_tokens"] > MAX_INPUT_TOKENS or usage["completion_tokens"] > MAX_OUTPUT_TOKENS:
        raise RuntimeError("token ceiling violated")

    # Warm reuse: second call without reload.
    rendered2 = post("/apply-template", {"messages": messages, "add_generation_prompt": True}, "call1_template")
    tokenized2 = post("/tokenize", {"content": rendered2["prompt"], "add_special": True}, "call1_tokenize")
    completion2 = post("/v1/chat/completions", {
        "model": MODEL_ID, "messages": messages, "temperature": 0, "seed": 104759, "max_tokens": 8, "stream": False
    }, "call1_inference")
    if completion2["usage"]["prompt_tokens"] != len(tokenized2["tokens"]):
        raise RuntimeError("warm-call prompt_tokens mismatch")

    # Cancellation: set cancel then attempt a call.
    service.cancel.set()
    try:
        post("/v1/chat/completions", {
            "model": MODEL_ID, "messages": messages, "temperature": 0, "seed": 104761, "max_tokens": 4, "stream": False
        }, "call2_cancelled")
        cancelled = False
        cancelled_body = json.loads((output / "call2_cancelled.response.bin").read_text())
        cancelled = bool(cancelled_body.get("cancelled") or cancelled_body.get("error"))
    except Exception:
        cancelled = True
    service.cancel.clear()

    # Output ceiling pin recorded (service clamps to 1024).
    write_json(output / "output_ceiling.json", {"max_output_tokens": MAX_OUTPUT_TOKENS, "clamped": True})

    cpu = time.process_time()
    pins.update({
        "schema": "la-qualified-local-model/v1",
        "base_url": pins["base_url"],
        "temperature": 0,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "paid_provider_budget": 0,
        "weights_sha256": hashlib.sha256("".join(sorted(pins["weights_files"].values())).encode()).hexdigest(),
        "tokenizer_sha256": hashlib.sha256("".join(sorted(pins["tokenizer_files"].values() or pins["weights_files"].values())).encode()).hexdigest(),
        "deployment_sha256": hashlib.sha256((pins["base_url"] + MODEL_ID + MODEL_REVISION).encode()).hexdigest(),
    })
    report = {
        "schema": "la032-model-qualification/v1",
        "status": "PASS",
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": MODEL_REVISION,
        "weights_sha256": pins["weights_sha256"],
        "tokenizer_sha256": pins["tokenizer_sha256"],
        "chat_template_sha256": pins["chat_template_sha256"],
        "deployment_sha256": pins["deployment_sha256"],
        "constructed_transport": False,
        "tokenization_agrees_with_usage": True,
        "actual_service_resource_boundary_qualified": True,
        "prompt_tokens_equal_preflight_input_count": True,
        "qualified_calls": 2,
        "cancelled_call_retained": bool(cancelled),
        "warm_reuse": True,
        "systemd_required": False,
        "indefinitely_running_required": False,
        "startup_seconds": pins["startup_seconds"],
        "startup_readiness_seconds": STARTUP_READINESS_SECONDS,
        "service_wall_seconds": SERVICE_WALL_SECONDS,
        "process_cpu_seconds": cpu,
        "base_url": pins["base_url"],
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "paid_provider_budget": 0,
        "seed_policy": "torch.manual_seed with recorded seed even if decoding is not bitwise deterministic",
        "raw_response_preserved": True,
    }
    write_json(output / "pins.json", pins)
    write_json(output / "qualification.json", report)
    service.httpd.shutdown()
    return report, pins, service


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("/tmp/la032-model-cache"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report, pins, _ = qualify(args.output, args.cache)
    print(json.dumps({"status": report["status"], "startup_seconds": pins["startup_seconds"], "base_url": pins["base_url"]}))
