#!/usr/bin/python3.12
"""Bounded local model HTTP service. Not systemd and not indefinitely running."""
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
from typing import Any

import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

CHAT_TEMPLATE = "{% for m in messages %}{{ m.role }}: {{ m.content }}\n{% endfor %}assistant:"
MODEL_DIR = Path("/tmp/la032-cache/tiny-gpt2")
MODEL_ID = "sshleifer/tiny-gpt2"
MODEL_REVISION = "5f91d94bd9cd7190a9f3216ff93cd1dd95f2c7be"


def sha_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Service:
    def __init__(self, model_dir: Path):
        started = time.monotonic()
        self.tokenizer = GPT2TokenizerFast.from_pretrained(str(model_dir), local_files_only=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = GPT2LMHeadModel.from_pretrained(str(model_dir), local_files_only=True)
        self.model.eval()
        self.ready_seconds = time.monotonic() - started
        self.lock = threading.Lock()
        self.calls = 0
        self.cancel = threading.Event()
        self.process_cpu_start = time.process_time()
        self.started_monotonic = started

    def apply_template(self, messages: list[dict[str, str]]) -> str:
        parts = []
        for message in messages:
            parts.append(f"{message['role']}: {message['content']}")
        return "\n".join(parts) + "\nassistant:"

    def tokenize(self, content: str) -> list[int]:
        return self.tokenizer.encode(content, add_special_tokens=True)

    def complete(self, messages: list[dict[str, str]], max_tokens: int, seed: int) -> dict[str, Any]:
        prompt = self.apply_template(messages)
        tokens = self.tokenize(prompt)
        if len(tokens) > 2048:
            raise ValueError("input exceeds 2048")
        if max_tokens > 1024:
            raise ValueError("output ceiling is 1024")
        with self.lock:
            self.calls += 1
            torch.manual_seed(seed)
            input_ids = torch.tensor([tokens])
            with torch.no_grad():
                out = self.model.generate(
                    input_ids,
                    max_new_tokens=min(max_tokens, 32),
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            new_tokens = out[0].tolist()[len(tokens) :]
            text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return {
            "prompt": prompt,
            "prompt_token_ids": tokens,
            "prompt_tokens": len(tokens),
            "completion_tokens": len(new_tokens),
            "text": text,
        }


SERVICE: Service | None = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _write(self, code: int, body: dict[str, Any]) -> None:
        data = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        assert SERVICE is not None
        if SERVICE.cancel.is_set():
            self._write(499, {"error": "cancelled"})
            return
        try:
            body = self._read()
            if self.path == "/apply-template":
                prompt = SERVICE.apply_template(body["messages"])
                self._write(200, {"prompt": prompt})
                return
            if self.path == "/tokenize":
                tokens = SERVICE.tokenize(body["content"])
                self._write(200, {"tokens": tokens})
                return
            if self.path == "/v1/chat/completions":
                result = SERVICE.complete(body["messages"], int(body.get("max_tokens") or 1024), int(body.get("seed") or 0))
                self._write(
                    200,
                    {
                        "id": "cmpl-la032",
                        "choices": [{"index": 0, "message": {"role": "assistant", "content": result["text"]}}],
                        "usage": {
                            "prompt_tokens": result["prompt_tokens"],
                            "completion_tokens": result["completion_tokens"],
                            "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
                        },
                    },
                )
                return
            if self.path == "/cancel":
                SERVICE.cancel.set()
                self._write(200, {"cancelled": True})
                return
            self._write(404, {"error": "unknown"})
        except Exception as exc:
            self._write(500, {"error": type(exc).__name__, "message": str(exc)})


def serve(host: str, port: int, ready_path: Path) -> None:
    global SERVICE
    SERVICE = Service(MODEL_DIR)
    pins = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": MODEL_REVISION,
        "weights_sha256": sha_file(MODEL_DIR / "pytorch_model.bin"),
        "tokenizer_sha256": sha_file(MODEL_DIR / "vocab.json"),
        "merges_sha256": sha_file(MODEL_DIR / "merges.txt"),
        "config_sha256": sha_file(MODEL_DIR / "config.json"),
        "chat_template": CHAT_TEMPLATE,
        "chat_template_sha256": sha_text(CHAT_TEMPLATE),
        "startup_ready_seconds": SERVICE.ready_seconds,
        "pid": os.getpid(),
        "port": port,
    }
    ready_path.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
    server = ThreadingHTTPServer((host, port), Handler)

    def stop(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--ready", type=Path, required=True)
    args = parser.parse_args()
    serve(args.host, args.port, args.ready)


if __name__ == "__main__":
    main()
