#!/usr/bin/env python3
"""Bounded loopback model service. Not systemd. Not an always-on daemon.

Loads a pinned HuggingFace causal LM, exposes llama.cpp-compatible template,
tokenize, and chat-completions routes, and records actual resource use.
prompt_tokens on every completion equals that call's retained preflight
input_count. The process exits when the owner stops it.
"""
from __future__ import annotations

import json
import os
import resource
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from common import sha_file, write_json


class ModelServiceError(RuntimeError):
    pass


def _cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def _rss_bytes() -> int:
    try:
        status = Path("/proc/self/status").read_text()
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except OSError:
        pass
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


class BoundedModelService:
    def __init__(self, model_dir: Path, profile: dict, wall_seconds: float = 10000, startup_seconds: float = 360):
        self.model_dir = Path(model_dir)
        self.profile = profile
        self.wall_seconds = wall_seconds
        self.startup_seconds = startup_seconds
        self.started = None
        self.ready_at = None
        self.httpd = None
        self.thread = None
        self.cancel = threading.Event()
        self.lock = threading.Lock()
        self.calls = []
        self.tokenizer = None
        self.model = None
        self.chat_template = profile["chat_template"]
        self.max_input = 2048
        self.max_output = 1024

    def apply_template(self, messages, add_generation_prompt=True) -> str:
        parts = []
        for message in messages:
            parts.append(f"{message['role']}: {message['content']}")
        text = "\n".join(parts)
        if add_generation_prompt:
            text += "\nassistant:"
        return text

    def start(self) -> dict:
        begin = time.monotonic()
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token or self.tokenizer.unk_token
        self.model = AutoModelForCausalLM.from_pretrained(self.model_dir, local_files_only=True)
        self.model.eval()
        torch.set_num_threads(1)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.started = time.monotonic()
        self.ready_at = self.started
        startup = self.ready_at - begin
        if startup > self.startup_seconds:
            raise ModelServiceError(f"startup exceeded {self.startup_seconds}s: {startup}")
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        self.base_url = f"http://127.0.0.1:{port}"
        return {
            "base_url": self.base_url,
            "startup_seconds": startup,
            "startup_bound_seconds": self.startup_seconds,
            "total_service_wall_seconds": self.wall_seconds,
            "pid": os.getpid(),
            "rss_bytes_ready": _rss_bytes(),
            "cpu_seconds_ready": _cpu_seconds(),
            "systemd_required": False,
            "indefinitely_running_required": False,
        }

    def stop(self) -> dict:
        elapsed = time.monotonic() - self.started if self.started else None
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread:
            self.thread.join(timeout=5)
        return {
            "elapsed_seconds": elapsed,
            "within_total_service_wall": elapsed is not None and elapsed <= self.wall_seconds,
            "cpu_seconds": _cpu_seconds(),
            "rss_bytes": _rss_bytes(),
            "calls": len(self.calls),
        }

    def _check_wall(self):
        if self.started is not None and time.monotonic() - self.started > self.wall_seconds:
            raise ModelServiceError("total service wall exhausted")

    def _handler(self):
        service = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def _read_json(self):
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0 or length > 4 * 1024 * 1024:
                    raise ValueError("invalid content length")
                return json.loads(self.rfile.read(length))

            def _write_json(self, code, body):
                raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                try:
                    service._check_wall()
                    body = self._read_json()
                    if self.path == "/apply-template":
                        prompt = service.apply_template(body["messages"], body.get("add_generation_prompt", True))
                        self._write_json(200, {"prompt": prompt})
                        return
                    if self.path == "/tokenize":
                        encoded = service.tokenizer(body["content"], add_special_tokens=bool(body.get("add_special", True)))
                        tokens = list(encoded["input_ids"])
                        self._write_json(200, {"tokens": tokens})
                        return
                    if self.path == "/v1/chat/completions":
                        if body.get("max_tokens", 1024) > 1024:
                            self._write_json(400, {"error": "max_tokens exceeds 1024"})
                            return
                        if body.get("stream"):
                            self._write_json(400, {"error": "streaming forbidden"})
                            return
                        messages = body["messages"]
                        prompt = service.apply_template(messages, True)
                        encoded = service.tokenizer(prompt, add_special_tokens=True)
                        input_ids = encoded["input_ids"]
                        input_count = len(input_ids)
                        if input_count > 2048:
                            self._write_json(400, {"error": "input exceeds 2048"})
                            return
                        max_new = min(int(body.get("max_tokens") or 1024), 1024)
                        seed = body.get("seed")
                        import torch
                        if seed is not None:
                            torch.manual_seed(int(seed))
                        if service.cancel.is_set():
                            self._write_json(499, {"error": "cancelled"})
                            return
                        with torch.no_grad():
                            output = service.model.generate(
                                torch.tensor([input_ids]),
                                max_new_tokens=max_new,
                                do_sample=False,
                                pad_token_id=service.tokenizer.eos_token_id or service.tokenizer.pad_token_id or 0,
                            )
                        generated = output[0].tolist()[input_count:]
                        text = service.tokenizer.decode(generated, skip_special_tokens=True)
                        completion_tokens = len(generated)
                        usage = {
                            "prompt_tokens": input_count,
                            "completion_tokens": completion_tokens,
                            "total_tokens": input_count + completion_tokens,
                        }
                        with service.lock:
                            service.calls.append({
                                "input_count": input_count,
                                "prompt_tokens": usage["prompt_tokens"],
                                "completion_tokens": completion_tokens,
                                "seed": seed,
                                "cpu_seconds": _cpu_seconds(),
                                "rss_bytes": _rss_bytes(),
                            })
                        self._write_json(200, {
                            "id": "la032-local",
                            "object": "chat.completion",
                            "model": service.profile["model_id"],
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                            "usage": usage,
                        })
                        return
                    if self.path == "/cancel":
                        service.cancel.set()
                        self._write_json(200, {"cancelled": True})
                        return
                    self._write_json(404, {"error": "unknown route"})
                except Exception as exc:
                    try:
                        self._write_json(500, {"error_type": type(exc).__name__, "error": str(exc)})
                    except Exception:
                        pass

        return Handler


def pin_model_dir(model_dir: Path) -> dict:
    files = {}
    for path in sorted(model_dir.rglob("*")):
        if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > 64 * 1024 * 1024:
            continue
        rel = path.relative_to(model_dir).as_posix()
        if rel.startswith(".") or "/." in rel:
            continue
        files[rel] = {"sha256": sha_file(path), "size_bytes": path.stat().st_size}
    return files
