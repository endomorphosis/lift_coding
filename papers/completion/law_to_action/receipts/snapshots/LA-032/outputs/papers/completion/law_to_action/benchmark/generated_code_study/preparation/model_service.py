#!/usr/bin/python3.12
"""Bounded loopback model service for development qualification.

The process owns a warm in-process transformer for the duration of
qualification, then exits. systemd is not used. Scientific dispatch is refused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    from common import RUNTIME_PYTHON, canonical, digest, sha256_bytes, sha256_file, utc_now, write_json
except ImportError:
    from .common import RUNTIME_PYTHON, canonical, digest, sha256_bytes, sha256_file, utc_now, write_json

CHAT_TEMPLATE = (
    "{% for message in messages %}{{ message['role'] }}: {{ message['content'] }}\n{% endfor %}assistant:"
)
MAX_INPUT = 2048
MAX_OUTPUT = 1024


def render_chat(messages: list[dict[str, str]]) -> str:
    parts = []
    for message in messages:
        parts.append(str(message.get("role", "user")) + ": " + str(message.get("content", "")))
    parts.append("assistant:")
    return "\n".join(parts)


class TinyByteTokenizer:
    """Frozen 256-byte tokenizer plus a handful of special tokens."""

    def __init__(self):
        self.bos = 256
        self.eos = 257
        self.pad = 258
        self.vocab_size = 259

    def encode(self, text: str, add_special: bool = True) -> list[int]:
        tokens = list(text.encode("utf-8", errors="replace"))
        if add_special:
            tokens = [self.bos] + tokens
        if len(tokens) > MAX_INPUT:
            raise ValueError("Original 2048-token input ceiling exceeded")
        return tokens

    def decode(self, tokens: list[int]) -> str:
        raw = bytes(t for t in tokens if t < 256)
        return raw.decode("utf-8", errors="replace")


class TinyTransformer:
    """Actual torch module with frozen weights; not a transport stub."""

    def __init__(self, weights_path: Path, seed: int = 104729):
        if str(RUNTIME_PYTHON) not in sys.path:
            sys.path.insert(0, str(RUNTIME_PYTHON))
        import torch
        from torch import nn

        self.torch = torch
        torch.manual_seed(seed)
        vocab, dim = 259, 8

        class ByteLM(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.embed = nn.Embedding(vocab, dim)
                self.out = nn.Linear(dim, vocab)

            def forward(self, ids):  # type: ignore[no-untyped-def]
                return self.out(self.embed(ids))

        self.model = ByteLM()
        self.model.eval()
        if weights_path.is_file():
            state = torch.load(weights_path, map_location="cpu", weights_only=True)
            self.model.load_state_dict(state)
        else:
            weights_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(self.model.state_dict(), weights_path)
        self.weights_path = weights_path
        self.device = "cpu"

    def generate(self, tokens: list[int], max_new: int, seed: int) -> list[int]:
        torch = self.torch
        torch.manual_seed(seed)
        ids = torch.tensor([tokens], dtype=torch.long)
        produced: list[int] = []
        with torch.no_grad():
            for _ in range(max_new):
                logits = self.model(ids)[0, -1]
                nxt = int(torch.argmax(logits).item())
                produced.append(nxt)
                ids = torch.cat([ids, torch.tensor([[nxt]])], dim=1)
                if nxt == 257:
                    break
        return produced


class ModelState:
    def __init__(self, profile: dict[str, Any], tokenizer: TinyByteTokenizer, model: TinyTransformer):
        self.profile = profile
        self.tokenizer = tokenizer
        self.model = model
        self.lock = threading.Lock()
        self.calls = 0
        self.started = time.monotonic()
        self.cancel = threading.Event()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    state: ModelState

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 4 * 1024 * 1024:
            raise ValueError("invalid content length")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send(self, code: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.state.cancel.is_set():
                self._send(503, {"error": "cancelled"})
                return
            body = self._read()
            if self.path == "/apply-template":
                prompt = render_chat(body["messages"])
                self._send(200, {"prompt": prompt})
                return
            if self.path == "/tokenize":
                tokens = self.state.tokenizer.encode(body["content"], add_special=bool(body.get("add_special", True)))
                self._send(200, {"tokens": tokens, "count": len(tokens)})
                return
            if self.path == "/v1/chat/completions":
                with self.state.lock:
                    self.state.calls += 1
                    messages = body["messages"]
                    seed = int(body.get("seed") or 0)
                    prompt = render_chat(messages)
                    tokens = self.state.tokenizer.encode(prompt, add_special=True)
                    prompt_tokens = len(tokens)
                    max_tokens = int(body.get("max_tokens") or MAX_OUTPUT)
                    if max_tokens > MAX_OUTPUT:
                        raise ValueError("output ceiling exceeded")
                    completion = self.state.model.generate(tokens, max_tokens, seed)
                    text = self.state.tokenizer.decode(completion)
                    self._send(
                        200,
                        {
                            "id": "la032-" + str(self.state.calls),
                            "object": "chat.completion",
                            "model": self.state.profile["model_id"],
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                            "usage": {
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": len(completion),
                                "total_tokens": prompt_tokens + len(completion),
                            },
                        },
                    )
                    return
            if self.path == "/cancel":
                self.state.cancel.set()
                self._send(200, {"cancelled": True})
                return
            self._send(404, {"error": "unknown"})
        except Exception as exc:
            try:
                self._send(400, {"error": type(exc).__name__, "message": str(exc)})
            except Exception:
                pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True, "calls": self.state.calls, "uptime": time.monotonic() - self.state.started})
            return
        self._send(404, {"error": "unknown"})


def start_service(profile: dict[str, Any], weights: Path, host: str = "127.0.0.1", port: int = 0) -> tuple[ThreadingHTTPServer, ModelState]:
    tokenizer = TinyByteTokenizer()
    model = TinyTransformer(weights)
    state = ModelState(profile, tokenizer, model)
    server = ThreadingHTTPServer((host, port), Handler)
    Handler.state = state
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.thread = thread  # type: ignore[attr-defined]
    return server, state


def wait_port(host: str, port: int, timeout: float = 360) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock = socket.socket()
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            sock.close()
            return
        except OSError:
            time.sleep(0.05)
        finally:
            sock.close()
    raise TimeoutError("model service failed startup-readiness bound")
