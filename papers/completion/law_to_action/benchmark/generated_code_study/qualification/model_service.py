#!/usr/bin/python3.12
"""Bounded llama.cpp-compatible local model service.

Started by the scientific driver for the duration of active inference. Not a
systemd unit and not an indefinitely running daemon. Total service wall is
enforced by the parent; startup readiness is a separate bound.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

VOCAB = 256
DIM = 8
CHAT_TEMPLATE = (
    "{% for message in messages %}{{ message.role }}: {{ message.content }}\n{% endfor %}assistant:"
)


def sha_file(path: Path) -> str:
    import hashlib

    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def render_chat(messages: list[dict]) -> str:
    parts = []
    for message in messages:
        parts.append(f"{message['role']}: {message['content']}")
    return "\n".join(parts) + "\nassistant:"


def tokenize_bytes(text: str) -> list[int]:
    return list(text.encode("utf-8"))


def generate(weights: dict, prompt_ids: list[int], max_tokens: int, seed: int, temperature: float) -> list[int]:
    emb = np.asarray(weights["embedding"], dtype=np.float32)
    head = np.asarray(weights["head"], dtype=np.float32)
    rng = np.random.RandomState(seed)
    ids = list(prompt_ids)
    hidden = np.zeros(DIM, dtype=np.float32)
    for token in ids[-256:]:
        hidden = 0.9 * hidden + emb[token % VOCAB]
    out = []
    for _ in range(max_tokens):
        logits = hidden @ head
        if temperature == 0:
            nxt = int(np.argmax(logits))
        else:
            scaled = logits / max(temperature, 1e-6)
            scaled = scaled - scaled.max()
            probs = np.exp(scaled)
            probs = probs / probs.sum()
            nxt = int(rng.choice(VOCAB, p=probs))
        out.append(nxt)
        hidden = 0.9 * hidden + emb[nxt]
        if nxt == 10 and len(out) > 8:
            break
    return out


def make_weights(seed: int = 104729) -> dict:
    rng = np.random.RandomState(seed)
    return {
        "schema": "la032-byte-lm-weights/v1",
        "model_id": "la032-byte-lm-v1",
        "model_revision": "la032-byte-lm-v1-r1",
        "tokenizer_revision": "byte-utf8-v1",
        "vocab": VOCAB,
        "dim": DIM,
        "embedding": rng.randn(VOCAB, DIM).astype(np.float32).tolist(),
        "head": rng.randn(DIM, VOCAB).astype(np.float32).tolist(),
        "seed": seed,
    }


class ModelState:
    def __init__(self, weights: dict, started: float, max_wall: float):
        self.weights = weights
        self.started = started
        self.max_wall = max_wall
        self.lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cancelled = 0
        self.stop = threading.Event()


class Handler(BaseHTTPRequestHandler):
    server_version = "la032-bounded-model/1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 4 * 1024 * 1024:
            raise ValueError("invalid content length")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            state: ModelState = self.server.state
            self._send(
                200,
                {
                    "status": "ok",
                    "uptime_seconds": time.monotonic() - state.started,
                    "calls": state.calls,
                },
            )
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        state: ModelState = self.server.state
        if state.stop.is_set() or time.monotonic() - state.started >= state.max_wall:
            self._send(503, {"error": "service wall exhausted"})
            return
        path = urlparse(self.path).path
        try:
            body = self._read_json()
        except Exception as exc:
            self._send(400, {"error": type(exc).__name__, "detail": str(exc)})
            return
        if path == "/apply-template":
            prompt = render_chat(body["messages"])
            self._send(200, {"prompt": prompt, "add_generation_prompt": body.get("add_generation_prompt", True)})
            return
        if path == "/tokenize":
            tokens = tokenize_bytes(body["content"])
            self._send(200, {"tokens": tokens, "add_special": body.get("add_special", True)})
            return
        if path == "/v1/chat/completions":
            messages = body["messages"]
            prompt = render_chat(messages)
            prompt_ids = tokenize_bytes(prompt)
            max_tokens = int(body.get("max_tokens", 1024))
            if max_tokens > 1024:
                self._send(400, {"error": "max_tokens exceeds 1024"})
                return
            seed = int(body.get("seed", 0))
            temperature = float(body.get("temperature", 0))
            cancel_after = body.get("la032_cancel_after_seconds")
            if cancel_after is not None:
                time.sleep(float(cancel_after))
                state.cancelled += 1
                self._send(499, {"error": "cancelled", "cancelled": True})
                return
            completion_ids = generate(state.weights, prompt_ids, max_tokens, seed, temperature)
            text = bytes(completion_ids).decode("utf-8", errors="replace")
            with state.lock:
                state.calls += 1
                state.prompt_tokens += len(prompt_ids)
                state.completion_tokens += len(completion_ids)
            self._send(
                200,
                {
                    "id": f"la032-{state.calls}",
                    "object": "chat.completion",
                    "model": state.weights["model_id"],
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": len(prompt_ids),
                        "completion_tokens": len(completion_ids),
                        "total_tokens": len(prompt_ids) + len(completion_ids),
                    },
                },
            )
            return
        if path == "/shutdown":
            state.stop.set()
            self._send(200, {"shutdown": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self._send(404, {"error": "not found"})


def serve(weights_path: Path, host: str, port: int, max_wall: float) -> ThreadingHTTPServer:
    weights = json.loads(Path(weights_path).read_text(encoding="utf-8"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.state = ModelState(weights, time.monotonic(), max_wall)
    return httpd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--max-wall-seconds", type=float, default=10000)
    parser.add_argument("--ready-file", type=Path)
    args = parser.parse_args()
    httpd = serve(args.weights, args.host, args.port, args.max_wall_seconds)
    bound_host, bound_port = httpd.server_address[:2]
    if args.ready_file:
        args.ready_file.write_text(json.dumps({"host": bound_host, "port": bound_port}) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ready", "host": bound_host, "port": bound_port}), flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
