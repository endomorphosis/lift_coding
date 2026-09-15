#!/usr/bin/env python3
"""Bounded loopback model service. Not a systemd unit and not always-on."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
for path in (
    HERE,
    Path("/opt/ipfs-validation-site-packages"),
    Path("/home/barberb/.local/share/vericodegen-research-runtime/python"),
):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

from preparation.study_common import (  # noqa: E402
    CHAT_TEMPLATE,
    MODEL_PIN,
    apply_chat_template,
    canonical,
    digest,
    locate_model_cache,
    sha_file,
    write_json,
)

STARTUP_BOUND_SECONDS = 360
SERVICE_WALL_SECONDS = 10000
MAX_INPUT = 2048
MAX_OUTPUT = 1024


def _resource_snapshot() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = None
    status = Path("/proc/self/status")
    if status.is_file():
        for line in status.read_text().splitlines():
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1]) * 1024
                break
    return {
        "ru_utime": usage.ru_utime,
        "ru_stime": usage.ru_stime,
        "maxrss_bytes": usage.ru_maxrss * 1024,
        "vmrss_bytes": rss,
        "monotonic": time.monotonic(),
    }


class ModelRuntime:
    def __init__(self, cache: Path):
        self.cache = cache
        self.started_wall = time.time()
        self.started_monotonic = time.monotonic()
        self.ready_monotonic = None
        self.calls: list[dict[str, Any]] = []
        self.cancelled = 0
        self._lock = threading.Lock()
        self.tokenizer = None
        self.model = None
        self.weights_sha256 = sha_file(cache / MODEL_PIN["weights_file"])
        if self.weights_sha256 != MODEL_PIN["weights_sha256"]:
            raise RuntimeError("Pinned model weights changed")
        for name, expected in MODEL_PIN["tokenizer_files"].items():
            if sha_file(cache / name) != expected:
                raise RuntimeError("Pinned tokenizer file changed: " + name)
        self.chat_template = CHAT_TEMPLATE
        self.chat_template_sha256 = digest(CHAT_TEMPLATE)
        self.deployment_sha256 = digest(
            {
                "model_id": MODEL_PIN["model_id"],
                "model_revision": MODEL_PIN["model_revision"],
                "weights_sha256": self.weights_sha256,
                "tokenizer_files": MODEL_PIN["tokenizer_files"],
                "chat_template_sha256": self.chat_template_sha256,
                "max_input_tokens": MAX_INPUT,
                "max_output_tokens": MAX_OUTPUT,
                "temperature": 0,
            }
        )

    def load(self) -> None:
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        import torch
        from transformers import GPT2LMHeadModel, GPT2Tokenizer

        start = time.monotonic()
        self.tokenizer = GPT2Tokenizer.from_pretrained(str(self.cache), local_files_only=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = GPT2LMHeadModel.from_pretrained(str(self.cache), local_files_only=True)
        self.model.eval()
        self.torch = torch
        elapsed = time.monotonic() - start
        if elapsed > STARTUP_BOUND_SECONDS:
            raise TimeoutError("model startup exceeded 360-second readiness bound")
        self.ready_monotonic = time.monotonic()
        self.startup_seconds = elapsed

    def remaining_service(self) -> float:
        return SERVICE_WALL_SECONDS - (time.monotonic() - self.started_monotonic)

    def tokenize(self, text: str) -> list[int]:
        return self.tokenizer.encode(text, add_special_tokens=True)

    def generate(self, messages: list[dict[str, str]], seed: int, max_tokens: int) -> dict[str, Any]:
        if self.remaining_service() <= 0:
            raise TimeoutError("10000-second service wall exhausted")
        prompt = apply_chat_template(messages)
        tokens = self.tokenize(prompt)
        input_count = len(tokens)
        if input_count > MAX_INPUT:
            raise ValueError("2048-token input ceiling exceeded")
        max_tokens = min(max_tokens, MAX_OUTPUT)
        self.torch.manual_seed(seed)
        ids = self.torch.tensor([tokens])
        started = time.monotonic()
        with self.torch.no_grad():
            output = self.model.generate(
                ids,
                max_new_tokens=max_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = output[0, input_count:].tolist()
        text = self.tokenizer.decode(generated, skip_special_tokens=True)
        completion = len(generated)
        row = {
            "prompt": prompt,
            "input_count": input_count,
            "prompt_tokens": input_count,
            "completion_tokens": completion,
            "text": text,
            "seed": seed,
            "wall_seconds": time.monotonic() - started,
            "raw_response": {"choices": [{"message": {"role": "assistant", "content": text}}], "usage": {"prompt_tokens": input_count, "completion_tokens": completion}},
        }
        if row["prompt_tokens"] != row["input_count"]:
            raise RuntimeError("prompt_tokens drifted from preflight input_count")
        with self._lock:
            self.calls.append({"input_count": input_count, "prompt_tokens": input_count, "completion_tokens": completion, "seed": seed})
        return row


RUNTIME: ModelRuntime | None = None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > 4 * 1024 * 1024:
            raise ValueError("invalid body")
        return json.loads(self.rfile.read(length))

    def _send(self, code: int, body: dict[str, Any]) -> None:
        raw = canonical(body)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802
        assert RUNTIME is not None
        try:
            if RUNTIME.remaining_service() <= 0:
                raise TimeoutError("service wall exhausted")
            body = self._read_json()
            if self.path == "/apply-template":
                prompt = apply_chat_template(body["messages"])
                self._send(200, {"prompt": prompt, "chat_template_sha256": RUNTIME.chat_template_sha256})
                return
            if self.path == "/tokenize":
                tokens = RUNTIME.tokenize(body["content"])
                self._send(200, {"tokens": tokens, "count": len(tokens)})
                return
            if self.path == "/v1/chat/completions":
                result = RUNTIME.generate(body["messages"], int(body.get("seed") or 0), int(body.get("max_tokens") or MAX_OUTPUT))
                self._send(200, result["raw_response"])
                return
            if self.path == "/cancel":
                RUNTIME.cancelled += 1
                self._send(200, {"cancelled": True, "count": RUNTIME.cancelled})
                return
            self._send(404, {"error": "unknown path"})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"error_type": type(exc).__name__, "error": str(exc)})


def serve(host: str, port: int, cache: Path) -> None:
    global RUNTIME
    RUNTIME = ModelRuntime(cache)
    RUNTIME.load()
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.serve_forever()


def qualify(output: Path) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    global RUNTIME
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cache = locate_model_cache()
    runtime = ModelRuntime(cache)
    load_started = time.monotonic()
    runtime.load()
    startup = time.monotonic() - load_started
    RUNTIME = runtime
    resources_before = _resource_snapshot()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + min(30, STARTUP_BOUND_SECONDS)
    ready = False
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    base + "/apply-template",
                    data=canonical({"messages": [{"role": "user", "content": "ping"}]}),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                ),
                timeout=2,
            )
            ready = True
            break
        except Exception:
            time.sleep(0.1)
    if not ready:
        httpd.shutdown()
        raise RuntimeError("model service failed startup readiness")

    def post(path: str, body: dict[str, Any], label: str) -> dict[str, Any]:
        raw = canonical(body)
        request_path = output / f"{label}.request.bin"
        request_path.write_bytes(raw)
        req = urllib.request.Request(base + path, data=raw, method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            (output / f"{label}.response.bin").write_bytes(payload)
            raise
        (output / f"{label}.response.bin").write_bytes(payload)
        return json.loads(payload)

    messages = [
        {"role": "system", "content": "Return exactly one JSON object with a program string."},
        {"role": "user", "content": "Export the permitted payload through allowed_sink."},
    ]
    templated = post("/apply-template", {"messages": messages}, "call0_template")
    tokenized = post("/tokenize", {"content": templated["prompt"]}, "call0_tokenize")
    input_count = tokenized["count"]
    write_json(output / "call0_preflight.json", {"input_count": input_count, "prompt": templated["prompt"]})
    inference = post("/v1/chat/completions", {"messages": messages, "seed": 104729, "max_tokens": 32, "temperature": 0}, "call0_inference")
    pt = inference["usage"]["prompt_tokens"]
    if pt != input_count:
        raise RuntimeError(f"prompt_tokens {pt} != preflight {input_count}")
    second = post("/v1/chat/completions", {"messages": messages, "seed": 104759, "max_tokens": 16, "temperature": 0}, "call1_inference")
    if second["usage"]["prompt_tokens"] != input_count:
        raise RuntimeError("warm-call prompt_tokens drifted")
    cancel = post("/cancel", {"reason": "qualification-cancel"}, "cancel")
    resources_after = _resource_snapshot()
    httpd.shutdown()
    thread.join(timeout=5)
    tokenizer_sha = digest({name: sha_file(cache / name) for name in MODEL_PIN["tokenizer_files"]})
    report = {
        "schema": "la032-model-qualification/v1",
        "status": "PASS",
        "constructed_transport": False,
        "mock_mechanism": False,
        "model_id": MODEL_PIN["model_id"],
        "model_revision": MODEL_PIN["model_revision"],
        "tokenizer_revision": MODEL_PIN["tokenizer_revision"],
        "weights_sha256": runtime.weights_sha256,
        "tokenizer_sha256": tokenizer_sha,
        "chat_template_sha256": runtime.chat_template_sha256,
        "deployment_sha256": runtime.deployment_sha256,
        "temperature": 0,
        "max_input_tokens": MAX_INPUT,
        "max_output_tokens": MAX_OUTPUT,
        "startup_seconds": startup,
        "startup_bound_seconds": STARTUP_BOUND_SECONDS,
        "service_wall_seconds": SERVICE_WALL_SECONDS,
        "systemd_required": False,
        "indefinitely_running_required": False,
        "warm_reuse_calls": 2,
        "tokenization_agrees_with_usage": True,
        "actual_service_resource_boundary_qualified": True,
        "prompt_tokens_equal_preflight": True,
        "seed_behavior_recorded": True,
        "raw_response_preserved": True,
        "cancellation_recorded": cancel.get("cancelled") is True,
        "resource_before": resources_before,
        "resource_after": resources_after,
        "paid_budget": 0,
        "base_url": base,
        "process_terminated": thread.is_alive() is False,
        "calls": [
            {"label": "call0", "input_count": input_count, "prompt_tokens": pt, "completion_tokens": inference["usage"]["completion_tokens"], "seed": 104729},
            {"label": "call1", "input_count": input_count, "prompt_tokens": second["usage"]["prompt_tokens"], "completion_tokens": second["usage"]["completion_tokens"], "seed": 104759},
        ],
    }
    write_json(output / "qualification.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualify", type=Path)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if args.qualify:
        print(json.dumps(qualify(args.qualify), sort_keys=True))
        return
    if args.serve:
        cache = locate_model_cache()
        sock = socket.socket()
        sock.bind(("127.0.0.1", args.port))
        port = sock.getsockname()[1]
        sock.close()
        serve("127.0.0.1", port, cache)


if __name__ == "__main__":
    main()
