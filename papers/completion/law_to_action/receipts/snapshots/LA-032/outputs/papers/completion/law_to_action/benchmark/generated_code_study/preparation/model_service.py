#!/usr/bin/python3.12
"""Bounded local HuggingFace model service. Not systemd. Exclusive inference owner."""
from __future__ import annotations

import argparse
import json
import os
import resource
import signal
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import urlparse


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class ModelOwner:
    def __init__(self, args):
        self.args = args
        self.started = time.monotonic()
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.in_flight = None
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.model = None
        self.tokenizer = None
        self.ready = threading.Event()
        self.failed = None
        self.shutdown = threading.Event()

    def load(self) -> None:
        try:
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            root = Path(self.args.model_dir)
            self.tokenizer = AutoTokenizer.from_pretrained(str(root), local_files_only=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                str(root),
                local_files_only=True,
                torch_dtype=torch.float32,
            )
            self.model.eval()
            self.device = torch.device("cpu")
            self.model.to(self.device)
            self.torch = torch
            self.ready.set()
        except BaseException as exc:
            self.failed = type(exc).__name__ + ": " + str(exc) + "\n" + traceback.format_exc()
            self.ready.set()
            raise

    def apply_template(self, messages, add_generation_prompt=True) -> str:
        return self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=bool(add_generation_prompt)
        )

    def tokenize(self, content: str) -> list[int]:
        return self.tokenizer.encode(content, add_special_tokens=False)

    def complete(self, messages, seed: int, max_tokens: int) -> dict:
        if max_tokens > 1024:
            raise ValueError("max_tokens exceeds 1024")
        prompt = self.apply_template(messages, True)
        token_ids = self.tokenize(prompt)
        if len(token_ids) > 2048:
            raise ValueError("input exceeds 2048")
        self.torch.manual_seed(int(seed))
        self.cancel.clear()
        inputs = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        prompt_tokens = int(inputs["input_ids"].shape[1])
        if prompt_tokens != len(token_ids):
            raise ValueError("preflight tokenize/generate input split")
        generated = []

        def hook():
            if self.cancel.is_set():
                raise self.torch.xla if False else RuntimeError("cancelled")

        with self.torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=int(max_tokens),
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        if self.cancel.is_set():
            raise RuntimeError("cancelled")
        new_tokens = output[0][prompt_tokens:]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        completion_tokens = int(new_tokens.shape[0])
        self.calls += 1
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "id": f"la032-{self.calls}",
            "object": "chat.completion",
            "model": self.args.model_id,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "seed": int(seed),
            "preflight_input_count": prompt_tokens,
            "resource": {
                "ru_utime": usage.ru_utime,
                "ru_stime": usage.ru_stime,
                "ru_maxrss_kb": usage.ru_maxrss,
                "service_wall_seconds": time.monotonic() - self.started,
            },
        }

    def resources(self) -> dict:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "ru_utime": usage.ru_utime,
            "ru_stime": usage.ru_stime,
            "ru_maxrss_kb": usage.ru_maxrss,
            "service_wall_seconds": time.monotonic() - self.started,
            "ready": self.ready.is_set() and self.failed is None,
            "exclusive_owner": True,
        }


OWNER = None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 4 * 1024 * 1024:
            raise ValueError("request too large")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode()), raw

    def _send(self, code, body):
        data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, {"status": "ok" if OWNER.ready.is_set() and not OWNER.failed else "loading", "failed": OWNER.failed})
            return
        if path == "/resources":
            self._send(200, OWNER.resources())
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body, raw = self._read_json()
        except BaseException as exc:
            self._send(400, {"error": type(exc).__name__ + ": " + str(exc)})
            return
        if not OWNER.ready.is_set() or OWNER.failed:
            self._send(503, {"error": OWNER.failed or "not ready"})
            return
        if time.monotonic() - OWNER.started > OWNER.args.max_wall:
            self._send(503, {"error": "service wall exhausted"})
            return
        try:
            if path == "/apply-template":
                prompt = OWNER.apply_template(body["messages"], body.get("add_generation_prompt", True))
                self._send(200, {"prompt": prompt})
                return
            if path == "/tokenize":
                tokens = OWNER.tokenize(body["content"])
                self._send(200, {"tokens": tokens, "count": len(tokens)})
                return
            if path == "/v1/cancel":
                OWNER.cancel.set()
                self._send(200, {"cancelled": True, "in_flight": OWNER.in_flight})
                return
            if path == "/v1/chat/completions":
                if not OWNER.lock.acquire(blocking=False):
                    self._send(409, {"error": "exclusive inference owner busy"})
                    return
                try:
                    OWNER.in_flight = body.get("seed")
                    result = OWNER.complete(body["messages"], body.get("seed", 0), body.get("max_tokens", 1024))
                    self._send(200, result)
                    return
                finally:
                    OWNER.in_flight = None
                    OWNER.lock.release()
            self._send(404, {"error": "not found"})
        except BaseException as exc:
            self._send(500, {"error": type(exc).__name__ + ": " + str(exc), "traceback": traceback.format_exc()})


def serve(args) -> None:
    global OWNER
    OWNER = ModelOwner(args)
    loader = threading.Thread(target=OWNER.load, daemon=True)
    loader.start()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    ready_path = Path(args.ready_file)
    deadline = time.monotonic() + args.startup_seconds

    def wait_ready():
        while time.monotonic() < deadline and not OWNER.ready.is_set():
            time.sleep(0.05)
        status = {
            "ready": OWNER.ready.is_set() and OWNER.failed is None,
            "failed": OWNER.failed,
            "startup_seconds": time.monotonic() - OWNER.started,
            "port": args.port,
            "pid": os.getpid(),
            "model_id": args.model_id,
            "model_revision": args.model_revision,
        }
        write_json(ready_path, status)

    threading.Thread(target=wait_ready, daemon=True).start()

    def stop(*_):
        OWNER.shutdown.set()
        server.shutdown()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def wall_guard():
        remaining = args.max_wall - (time.monotonic() - OWNER.started)
        if remaining > 0:
            OWNER.shutdown.wait(remaining)
        if not OWNER.shutdown.is_set():
            stop()

    threading.Thread(target=wall_guard, daemon=True).start()
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--ready-file", required=True)
    parser.add_argument("--max-wall", type=float, default=10000)
    parser.add_argument("--startup-seconds", type=float, default=360)
    args = parser.parse_args()
    serve(args)


if __name__ == "__main__":
    main()
