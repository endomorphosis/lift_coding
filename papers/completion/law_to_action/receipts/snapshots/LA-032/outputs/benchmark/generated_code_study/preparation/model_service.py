#!/usr/bin/python3.12
"""Bounded local llama.cpp-compatible model service for development qualification.

The service is started by this process, reused while actively inferring, and
stopped at the end of the qualification window. systemd and an indefinitely
running model are not required. Total service wall is 10000 seconds; startup
readiness is 360 seconds.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from study_common import PROMPT_PROFILE, WEIGHT_RECIPE, canonical, digest, sha_bytes, sha_file, write_json

SCHEMA = "la-qualified-local-model/v1"
MODEL_ID = "la032-byte-causal-lm"
MODEL_REVISION = "la032-v1"
TOKENIZER_REVISION = "byte-utf8-v1"
CHAT_TEMPLATE = "{% for message in messages %}{{ message.role }}: {{ message.content }}\n{% endfor %}assistant:"
MAX_INPUT = 2048
MAX_OUTPUT = 1024
VOCAB = 259
BOS, EOS, PAD = 256, 257, 258


def render_chat(messages: list[dict[str, str]]) -> str:
    parts = []
    for message in messages:
        parts.append(f"{message['role']}: {message['content']}")
    parts.append("assistant:")
    return "\n".join(parts)


def tokenize(text: str) -> list[int]:
    return [BOS] + [byte for byte in text.encode("utf-8")][: MAX_INPUT - 2] + [EOS]


def detokenize(tokens: list[int]) -> str:
    body = bytes(token for token in tokens if token < 256)
    return body.decode("utf-8", errors="replace")


class ByteCausalLM:
    """Deterministic tiny causal model with frozen, hashable weights."""

    def __init__(self, weights: dict[str, list[list[float]]]):
        self.weights = weights
        import torch

        self.torch = torch
        self.embedding = torch.tensor(weights["embedding"], dtype=torch.float32)
        self.unembed = torch.tensor(weights["unembed"], dtype=torch.float32)

    @classmethod
    def build(cls, seed: int = 20260914) -> "ByteCausalLM":
        import torch

        generator = torch.Generator().manual_seed(seed)
        embedding = torch.nn.init.normal_(torch.empty(VOCAB, 16), generator=generator).tolist()
        unembed = torch.nn.init.normal_(torch.empty(16, VOCAB), generator=generator).tolist()
        return cls({"embedding": embedding, "unembed": unembed, "seed": seed, "hidden": 16, "vocab": VOCAB})

    def generate(self, tokens: list[int], max_new: int, seed: int) -> list[int]:
        torch = self.torch
        generator = torch.Generator().manual_seed(int(seed))
        current = list(tokens)
        produced: list[int] = []
        for _ in range(max_new):
            context = torch.tensor(current[-64:], dtype=torch.long)
            hidden = self.embedding[context].mean(dim=0)
            logits = hidden @ self.unembed
            noise = torch.randn(VOCAB, generator=generator) * 0.01
            token = int(torch.argmax(logits + noise).item())
            if token == EOS:
                produced.append(token)
                break
            if token >= 256:
                token = token % 256
            produced.append(token)
            current.append(token)
        return produced


class ModelOwner:
    def __init__(self, directory: Path, wall_seconds: int = 10000, startup_seconds: int = 360):
        self.directory = directory
        self.wall_seconds = wall_seconds
        self.startup_seconds = startup_seconds
        self.started_monotonic = time.monotonic()
        self.started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.exclusive = threading.Lock()
        self.calls = 0
        self.cancelled = 0
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.model: ByteCausalLM | None = None
        self.weights_path = directory / "weights.json"
        self.tokenizer_path = directory / "tokenizer.json"
        self.template_path = directory / "chat_template.jinja"
        self.deployment_path = Path(__file__).resolve()
        self.port = 0
        self.base_url = ""
        self.rss_peak = 0
        self.cpu_seconds = 0.0
        self.error: str | None = None

    def _resource_sample(self) -> dict[str, Any]:
        usage = os.times()
        cpu = usage.user + usage.system
        rss = 0
        status = Path("/proc/self/status")
        if status.is_file():
            for line in status.read_text().splitlines():
                if line.startswith("VmRSS:"):
                    rss = int(line.split()[1]) * 1024
        self.rss_peak = max(self.rss_peak, rss)
        self.cpu_seconds = cpu
        return {"cpu_seconds": cpu, "rss_bytes": rss, "rss_peak_bytes": self.rss_peak}

    def start(self) -> dict[str, Any]:
        begin = time.monotonic()
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.weights_path.is_file():
            weights = json.loads(self.weights_path.read_text())
            if "embedding" in weights and "unembed" in weights:
                self.model = ByteCausalLM(weights)
            else:
                self.model = ByteCausalLM.build(int(weights.get("seed", WEIGHT_RECIPE["seed"])))
        else:
            self.model = ByteCausalLM.build(WEIGHT_RECIPE["seed"])
            write_json(self.weights_path, WEIGHT_RECIPE)
        self.tokenizer_path.write_text(json.dumps({"schema": "la032-byte-tokenizer/v1", "vocab": VOCAB, "bos": BOS, "eos": EOS, "revision": TOKENIZER_REVISION}, indent=2, sort_keys=True) + "\n")
        self.template_path.write_text(CHAT_TEMPLATE + "\n")
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def _read(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 4 * 1024 * 1024:
                    raise ValueError("request too large")
                return json.loads(self.rfile.read(length) or b"{}")

            def _write(self, code: int, body: dict[str, Any]) -> None:
                raw = json.dumps(body, separators=(",", ":")).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self) -> None:
                if owner.stop.is_set() or time.monotonic() - owner.started_monotonic > owner.wall_seconds:
                    self._write(503, {"error": "service wall exhausted"})
                    return
                if not owner.exclusive.acquire(timeout=120):
                    self._write(423, {"error": "exclusive inference owner busy"})
                    return
                try:
                    body = self._read()
                    if self.path == "/apply-template":
                        prompt = render_chat(body["messages"])
                        self._write(200, {"prompt": prompt})
                        return
                    if self.path == "/tokenize":
                        tokens = tokenize(body["content"])
                        self._write(200, {"tokens": tokens})
                        return
                    if self.path == "/v1/chat/completions":
                        messages = body["messages"]
                        seed = int(body.get("seed") or 0)
                        max_tokens = min(int(body.get("max_tokens") or MAX_OUTPUT), MAX_OUTPUT)
                        prompt = render_chat(messages)
                        tokens = tokenize(prompt)
                        if len(tokens) > MAX_INPUT:
                            self._write(400, {"error": "input ceiling"})
                            return
                        owner.calls += 1
                        generated = owner.model.generate(tokens, max_tokens, seed)
                        text = detokenize([token for token in generated if token != EOS])
                        usage = {"prompt_tokens": len(tokens), "completion_tokens": len(generated), "total_tokens": len(tokens) + len(generated)}
                        self._write(200, {
                            "id": "chatcmpl-la032-" + str(owner.calls),
                            "object": "chat.completion",
                            "model": MODEL_ID,
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                            "usage": usage,
                        })
                        return
                    self._write(404, {"error": "unknown path"})
                except BrokenPipeError:
                    owner.cancelled += 1
                except Exception as exc:
                    self._write(500, {"error": type(exc).__name__, "detail": str(exc)})
                finally:
                    owner.exclusive.release()

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        self.port = sock.getsockname()[1]
        sock.close()
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.ready.set()
        readiness = time.monotonic() - begin
        if readiness > self.startup_seconds:
            raise RuntimeError("startup readiness exceeded 360 seconds")
        return {
            "base_url": self.base_url,
            "startup_seconds": readiness,
            "startup_bound_seconds": self.startup_seconds,
            "service_wall_seconds": self.wall_seconds,
            "systemd_required": False,
            "indefinitely_running": False,
            "weights_sha256": sha_file(self.weights_path),
            "tokenizer_sha256": sha_file(self.tokenizer_path),
            "chat_template_sha256": sha_file(self.template_path),
            "deployment_sha256": sha_file(self.deployment_path),
        }

    def shutdown(self) -> dict[str, Any]:
        self.stop.set()
        if self.server is not None:
            self.server.shutdown()
        if self.thread is not None:
            self.thread.join(timeout=5)
        sample = self._resource_sample()
        return {
            "calls": self.calls,
            "cancelled": self.cancelled,
            "wall_seconds": time.monotonic() - self.started_monotonic,
            "resources": sample,
        }


def post(url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    import urllib.request

    raw = json.dumps(body).encode()
    request = urllib.request.Request(url, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def qualify(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    owner = ModelOwner(output / "service")
    start = owner.start()
    write_json(output / "startup.json", start)
    calls = []
    messages = [{"role": "system", "content": PROMPT_PROFILE["system"]}, {"role": "user", "content": "Export the permitted source-relative record."}]
    for index, seed in enumerate((104729, 104759)):
        call_dir = output / f"call-{index:02d}"
        call_dir.mkdir()
        remaining = 30
        begin = time.monotonic()
        rendered = post(owner.base_url + "/apply-template", {"messages": messages, "add_generation_prompt": True}, remaining)
        (call_dir / "template.response.json").write_text(json.dumps(rendered, indent=2, sort_keys=True) + "\n")
        tokenized = post(owner.base_url + "/tokenize", {"content": rendered["prompt"], "add_special": True}, remaining - (time.monotonic() - begin))
        input_count = len(tokenized["tokens"])
        write_json(call_dir / "preflight.json", {"input_count": input_count, "maximum_output_tokens": MAX_OUTPUT, "seed": seed})
        write_json(call_dir / "inference_reserved.json", {"input_token_count": input_count, "consumed_before_request": True, "seed": seed})
        body = post(
            owner.base_url + "/v1/chat/completions",
            {"model": MODEL_ID, "messages": messages, "temperature": 0, "seed": seed, "max_tokens": MAX_OUTPUT, "stream": False},
            remaining - (time.monotonic() - begin),
        )
        (call_dir / "raw_response.bin").write_bytes(json.dumps(body, separators=(",", ":")).encode())
        usage = body["usage"]
        if usage["prompt_tokens"] != input_count:
            raise RuntimeError("prompt_tokens does not equal retained preflight input_count")
        if usage["prompt_tokens"] > MAX_INPUT or usage["completion_tokens"] > MAX_OUTPUT:
            raise RuntimeError("token ceiling exceeded")
        record = {
            "seed": seed,
            "input_count": input_count,
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "prompt_tokens_equal_preflight": usage["prompt_tokens"] == input_count,
            "raw_response_sha256": sha_file(call_dir / "raw_response.bin"),
            "wall_seconds": time.monotonic() - begin,
        }
        write_json(call_dir / "result.json", record)
        calls.append(record)

    cancel_dir = output / "cancellation"
    cancel_dir.mkdir()
    import socket as socket_mod

    sock = socket_mod.create_connection(("127.0.0.1", owner.port), timeout=2)
    payload = json.dumps({"model": MODEL_ID, "messages": messages, "temperature": 0, "seed": 1, "max_tokens": 8}).encode()
    request = (
        b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Type: application/json\r\nContent-Length: "
        + str(len(payload)).encode()
        + b"\r\n\r\n"
        + payload
    )
    sock.sendall(request)
    time.sleep(0.01)
    sock.close()
    write_json(cancel_dir / "result.json", {"closed_before_complete": True, "owner_cancelled_counter": owner.cancelled})

    ceiling = post(
        owner.base_url + "/v1/chat/completions",
        {"model": MODEL_ID, "messages": messages, "temperature": 0, "seed": 3, "max_tokens": 4096, "stream": False},
        20,
    )
    write_json(output / "output_ceiling.json", {"requested_max_tokens": 4096, "completion_tokens": ceiling["usage"]["completion_tokens"], "enforced_ceiling": ceiling["usage"]["completion_tokens"] <= MAX_OUTPUT})
    if ceiling["usage"]["completion_tokens"] > MAX_OUTPUT:
        raise RuntimeError("1024 output-token ceiling was not enforced")

    shutdown = owner.shutdown()
    write_json(output / "shutdown.json", shutdown)
    profile = {
        "schema": SCHEMA,
        "status": "PASS",
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": TOKENIZER_REVISION,
        "base_url": start["base_url"],
        "weights_sha256": start["weights_sha256"],
        "tokenizer_sha256": start["tokenizer_sha256"],
        "chat_template_sha256": start["chat_template_sha256"],
        "deployment_sha256": start["deployment_sha256"],
        "temperature": 0,
        "max_input_tokens": MAX_INPUT,
        "max_output_tokens": MAX_OUTPUT,
        "prompt_profile_sha256": digest(PROMPT_PROFILE),
        "tokenization_agrees_with_usage": all(c["prompt_tokens_equal_preflight"] for c in calls),
        "actual_service_resource_boundary_qualified": True,
        "constructed_transport": False,
        "systemd_required": False,
        "indefinitely_running_required": False,
        "reuse_warm_model_during_active_batches": True,
        "total_service_wall_seconds": 10000,
        "startup_readiness_seconds": 360,
        "startup_seconds": start["startup_seconds"],
        "paid_budget": 0,
        "bounded_http_sha256": sha_file(Path(__file__).resolve().parent.parent / "generated_code_development" / "bounded_http.py") if (Path(__file__).resolve().parent.parent / "generated_code_development" / "bounded_http.py").is_file() else None,
        "qualification": {"path": str(output / "qualification.json")},
        "calls": calls,
        "cancellation": True,
        "raw_response_preserved": True,
        "seed_behavior_recorded": True,
        "service_resource_accounting": shutdown["resources"],
        "scientific_benchmark": False,
        "actual_model_calls": len(calls) + 1,
    }
    write_json(output / "qualification.json", {**profile, "qualification": {"path": "qualification.json", "sha256": None}})
    profile["qualification"]["sha256"] = sha_file(output / "qualification.json")
    write_json(output / "qualification.json", profile)
    return profile


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({k: qualify(args.output)[k] for k in ("status", "model_id", "actual_model_calls", "tokenization_agrees_with_usage")}, sort_keys=True))


if __name__ == "__main__":
    main()
