#!/usr/bin/env python3
"""Bounded local byte-level language model service.

This process loads pinned weights, serves llama.cpp-compatible loopback HTTP,
and exits at the service wall. It is not a systemd unit and does not remain
running after the owner releases it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import torch
import torch.nn as nn

BOS = 256
EOS = 257
PAD = 258
VOCAB = 260
BLOCK = 128
N_EMBD = 32
N_HEAD = 2
N_LAYER = 1
TEMPLATE = (
    "<|im_start|>system\n{system}<|im_end|>\n"
    "<|im_start|>user\n{user}<|im_end|>\n"
    "<|im_start|>assistant\n"
)


class TinyByteLM(nn.Module):
    def __init__(self):
        super().__init__()
        self.tok = nn.Embedding(VOCAB, N_EMBD)
        self.pos = nn.Embedding(BLOCK, N_EMBD)
        layer = nn.TransformerEncoderLayer(
            d_model=N_EMBD,
            nhead=N_HEAD,
            dim_feedforward=64,
            dropout=0.0,
            batch_first=True,
            activation="gelu",
        )
        self.core = nn.TransformerEncoder(layer, num_layers=N_LAYER)
        self.ln = nn.LayerNorm(N_EMBD)
        self.head = nn.Linear(N_EMBD, VOCAB)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        if tokens.size(-1) > BLOCK:
            tokens = tokens[:, -BLOCK:]
        positions = torch.arange(tokens.size(1), device=tokens.device).unsqueeze(0)
        hidden = self.tok(tokens) + self.pos(positions)
        mask = nn.Transformer.generate_square_subsequent_mask(tokens.size(1), device=tokens.device)
        hidden = self.core(hidden, mask=mask, is_causal=True)
        return self.head(self.ln(hidden))


def encode(text: str, add_special: bool = True) -> list[int]:
    tokens = list(text.encode("utf-8"))
    if add_special:
        tokens = [BOS] + tokens
    return tokens


def decode(tokens: list[int]) -> str:
    data = bytes(t for t in tokens if 0 <= t < 256)
    return data.decode("utf-8", errors="replace")


def apply_template(messages, add_generation_prompt: bool = True) -> str:
    system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    users = []
    for message in messages:
        role = message.get("role")
        if role == "user":
            users.append(message.get("content") or "")
        elif role == "assistant":
            users.append("ASSISTANT:" + (message.get("content") or ""))
    user = "\n".join(users)
    text = TEMPLATE.format(system=system, user=user)
    if not add_generation_prompt and text.endswith("<|im_start|>assistant\n"):
        text = text[: -len("<|im_start|>assistant\n")]
    return text


def init_weights(path: Path) -> dict:
    torch.manual_seed(104729)
    model = TinyByteLM()
    payload = {
        "architecture": {
            "vocab": VOCAB,
            "block": BLOCK,
            "n_embd": N_EMBD,
            "n_head": N_HEAD,
            "n_layer": N_LAYER,
            "bos": BOS,
            "eos": EOS,
        },
        "state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)
    return payload


def load_weights(path: Path) -> TinyByteLM:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = TinyByteLM()
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model


def generate(model: TinyByteLM, tokens: list[int], max_tokens: int, seed: int, cancel: threading.Event) -> list[int]:
    torch.manual_seed(seed)
    output = []
    context = tokens[:]
    for _ in range(max_tokens):
        if cancel.is_set():
            break
        with torch.no_grad():
            logits = model(torch.tensor([context[-BLOCK:]], dtype=torch.long))
            nxt = int(torch.argmax(logits[0, -1]))
        output.append(nxt)
        context.append(nxt)
        if nxt == EOS:
            break
    return output


class ServiceState:
    def __init__(self, model, wall, started):
        self.model = model
        self.wall = wall
        self.started = started
        self.cancel = threading.Event()
        self.lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.shutdown = threading.Event()


def handler_for(state: ServiceState, ready_at: float):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *args):
            return

        def _read_json(self):
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 4 * 1024 * 1024:
                raise ValueError("invalid content length")
            return json.loads(self.rfile.read(length))

        def _send(self, code, body):
            raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == "/health":
                self._send(
                    200,
                    {
                        "status": "ready",
                        "uptime_seconds": time.monotonic() - state.started,
                        "ready_seconds": ready_at - state.started,
                        "remaining_service_wall_seconds": state.wall - (time.monotonic() - state.started),
                    },
                )
                return
            self._send(404, {"error": "not found"})

        def do_POST(self):
            remaining = state.wall - (time.monotonic() - state.started)
            if remaining <= 0:
                self._send(503, {"error": "service wall exhausted"})
                return
            try:
                body = self._read_json()
            except Exception as exc:
                self._send(400, {"error": type(exc).__name__, "detail": str(exc)})
                return
            if self.path == "/apply-template":
                prompt = apply_template(body.get("messages") or [], bool(body.get("add_generation_prompt", True)))
                self._send(200, {"prompt": prompt})
                return
            if self.path == "/tokenize":
                tokens = encode(body.get("content") or "", bool(body.get("add_special", True)))
                self._send(200, {"tokens": tokens, "count": len(tokens)})
                return
            if self.path == "/v1/chat/completions":
                messages = body.get("messages") or []
                seed = int(body.get("seed") or 0)
                requested = int(body.get("max_tokens") or 16)
                if requested > 1024:
                    self._send(400, {"error": "max_tokens exceeds 1024 output ceiling"})
                    return
                prompt = apply_template(messages, True)
                prompt_tokens = encode(prompt, True)
                if len(prompt_tokens) > 2048:
                    self._send(400, {"error": "prompt exceeds 2048 input ceiling"})
                    return
                with state.lock:
                    state.calls += 1
                    state.prompt_tokens += len(prompt_tokens)
                completion = generate(state.model, prompt_tokens, min(requested, 1024), seed, state.cancel)
                with state.lock:
                    state.completion_tokens += len(completion)
                text = decode(completion)
                self._send(
                    200,
                    {
                        "id": "la032-local-" + str(state.calls),
                        "object": "chat.completion",
                        "model": body.get("model") or "vericodegen-la032-byte-lm",
                        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                        "usage": {
                            "prompt_tokens": len(prompt_tokens),
                            "completion_tokens": len(completion),
                            "total_tokens": len(prompt_tokens) + len(completion),
                        },
                    },
                )
                return
            if self.path == "/shutdown":
                state.shutdown.set()
                self._send(200, {"status": "shutting_down"})
                return
            self._send(404, {"error": "not found"})

    return Handler


def serve(weights: Path, host: str, port: int, wall: int, ready_file: Path | None):
    started = time.monotonic()
    model = load_weights(weights)
    state = ServiceState(model, wall, started)
    httpd = ThreadingHTTPServer((host, port), handler_for(state, time.monotonic()))
    bound = httpd.server_address
    ready = {
        "host": bound[0],
        "port": bound[1],
        "base_url": f"http://127.0.0.1:{bound[1]}",
        "pid": os.getpid(),
        "startup_seconds": time.monotonic() - started,
        "service_wall_seconds": wall,
    }
    if ready_file:
        ready_file.write_text(json.dumps(ready, indent=2, sort_keys=True) + "\n")
    def expire():
        time.sleep(max(0.0, wall - (time.monotonic() - started)))
        state.shutdown.set()
    threading.Thread(target=expire, daemon=True).start()

    def stop(*_args):
        state.cancel.set()
        state.shutdown.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not state.shutdown.is_set():
        httpd.timeout = 0.2
        httpd.handle_request()
    httpd.server_close()
    return ready


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--wall-seconds", type=int, default=10000)
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--init-weights", action="store_true")
    args = parser.parse_args()
    if args.init_weights:
        init_weights(args.weights)
        print(json.dumps({"weights": str(args.weights), "sha256": hashlib.sha256(args.weights.read_bytes()).hexdigest()}))
        return
    serve(args.weights, args.host, args.port, args.wall_seconds, args.ready_file)


if __name__ == "__main__":
    main()
