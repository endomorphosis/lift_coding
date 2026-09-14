#!/usr/bin/env python3
"""Bounded loopback HuggingFace transformers service. Not a systemd unit."""
from __future__ import annotations

import argparse
import json
import os
import resource
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
MODEL_REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
MODEL_DIR = Path(
    "/tmp/la-032-cache/hf/hub/models--HuggingFaceTB--SmolLM2-135M-Instruct/snapshots/12fd25f77366fa6b3b4b768ec3050bf629380bac"
)


class ModelService:
    def __init__(self, model_dir: Path):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        sys.path[:0] = [
            "/opt/ipfs-validation-site-packages",
            "/home/barberb/.local/share/vericodegen-research-runtime/python",
        ]
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        started = time.monotonic()
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(str(model_dir), local_files_only=True, torch_dtype=torch.float32)
        self.model.eval()
        self.torch = torch
        self.ready_seconds = time.monotonic() - started
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.calls = 0
        self.started_monotonic = time.monotonic()
        self.pid = os.getpid()

    def apply_template(self, messages, add_generation_prompt=True) -> str:
        return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=add_generation_prompt)

    def tokenize(self, content: str, add_special=True):
        tokens = self.tokenizer.encode(content, add_special_tokens=bool(add_special))
        return [int(x) for x in tokens]

    def complete(self, messages, max_tokens=1024, seed=None, temperature=0):
        self.cancel.clear()
        prompt = self.apply_template(messages, True)
        token_ids = self.tokenize(prompt, True)
        input_count = len(token_ids)
        if input_count > 2048:
            raise ValueError("input exceeds 2048")
        max_tokens = min(int(max_tokens), 1024)
        import torch

        with self.lock:
            self.calls += 1
            if seed is not None:
                torch.manual_seed(int(seed))
            inputs = torch.tensor([token_ids], dtype=torch.long)
            generated = self.model.generate(
                inputs,
                max_new_tokens=max_tokens,
                do_sample=False if temperature == 0 else True,
                temperature=None if temperature == 0 else float(temperature),
                pad_token_id=self.tokenizer.eos_token_id,
            )
            if self.cancel.is_set():
                raise TimeoutError("generation cancelled")
            output_ids = generated[0].tolist()[input_count:]
            text = self.tokenizer.decode(output_ids, skip_special_tokens=True)
            return {
                "prompt": prompt,
                "prompt_tokens": input_count,
                "completion_tokens": len(output_ids),
                "content": text,
            }

    def resources(self) -> dict:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        status = {}
        try:
            for line in Path("/proc/self/status").read_text().splitlines():
                if line.startswith(("VmRSS:", "VmHWM:", "Threads:")):
                    status[line.split(":")[0]] = line.split(":", 1)[1].strip()
        except OSError as exc:
            status["error"] = {"type": type(exc).__name__, "errno": exc.errno}
        return {
            "pid": self.pid,
            "cpu_user_seconds": usage.ru_utime,
            "cpu_system_seconds": usage.ru_stime,
            "child_cpu_user_seconds": children.ru_utime,
            "child_cpu_system_seconds": children.ru_stime,
            "maxrss_kb": usage.ru_maxrss,
            "wall_seconds": time.monotonic() - self.started_monotonic,
            "status": status,
            "calls": self.calls,
        }


def make_handler(service: ModelService):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _read(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4 * 1024 * 1024:
                raise ValueError("request too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def _send(self, code, body):
            raw = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            try:
                body = self._read()
                if self.path == "/apply-template":
                    prompt = service.apply_template(body["messages"], body.get("add_generation_prompt", True))
                    self._send(200, {"prompt": prompt})
                    return
                if self.path == "/tokenize":
                    tokens = service.tokenize(body["content"], body.get("add_special", True))
                    self._send(200, {"tokens": tokens, "count": len(tokens)})
                    return
                if self.path == "/v1/chat/completions":
                    result = service.complete(
                        body["messages"],
                        max_tokens=body.get("max_tokens", 1024),
                        seed=body.get("seed"),
                        temperature=body.get("temperature", 0),
                    )
                    self._send(
                        200,
                        {
                            "id": "la032-" + str(service.calls),
                            "object": "chat.completion",
                            "model": MODEL_ID,
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": result["content"]}, "finish_reason": "stop"}],
                            "usage": {
                                "prompt_tokens": result["prompt_tokens"],
                                "completion_tokens": result["completion_tokens"],
                                "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
                            },
                        },
                    )
                    return
                if self.path == "/cancel":
                    service.cancel.set()
                    self._send(200, {"cancelled": True})
                    return
                if self.path == "/resources":
                    self._send(200, service.resources())
                    return
                self._send(404, {"error": "unknown"})
            except Exception as exc:
                self._send(500, {"error": type(exc).__name__, "message": str(exc)})

        def do_GET(self):
            if self.path in ("/health", "/ready"):
                self._send(200, {"ready": True, "model": MODEL_ID, "revision": MODEL_REVISION, "pid": service.pid})
                return
            self._send(404, {"error": "unknown"})

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--model-dir", default=str(MODEL_DIR))
    parser.add_argument("--ready-file", type=Path)
    args = parser.parse_args()
    service = ModelService(Path(args.model_dir))
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(service))
    if args.ready_file:
        args.ready_file.write_text(json.dumps({"pid": os.getpid(), "port": args.port, "ready_seconds": service.ready_seconds}) + "\n")
    def stop(*_):
        threading.Thread(target=httpd.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
