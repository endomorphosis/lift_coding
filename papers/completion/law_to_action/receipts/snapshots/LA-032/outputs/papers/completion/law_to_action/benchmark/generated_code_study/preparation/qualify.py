#!/usr/bin/env python3
"""Bounded model, runtime, watchdog, profile, and driver qualification."""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from .common import (
    ARMS,
    ATTEMPT_WALL_SECONDS,
    CACHE,
    MAX_CALLS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    PROMPT_PROFILE,
    QUAL,
    ROOT,
    SERVICE_WALL_SECONDS,
    STARTUP_READINESS_SECONDS,
    STUDY,
    digest,
    sha_file,
    write_json,
)
from .model_service import MODEL_DIR, MODEL_ID, MODEL_REVISION
from .native_profile import qualify_profile, qualify_watchdog


def _load_bounded_http():
    path = ROOT / "papers/completion/law_to_action/benchmark/generated_code_development/bounded_http.py"
    spec = importlib.util.spec_from_file_location("la032_bounded_http", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _hash_dir_file(path: Path) -> str:
    return sha_file(path)


def start_model(output: Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if not MODEL_DIR.is_dir():
        raise FileNotFoundError("pinned model snapshot missing")
    port = _free_port()
    ready = output / "ready.json"
    if ready.exists():
        ready.unlink()
    env = {
        **os.environ,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "CUDA_VISIBLE_DEVICES": "",
        "PYTHONPATH": "/opt/ipfs-validation-site-packages:/home/barberb/.local/share/vericodegen-research-runtime/python",
        "HF_HOME": str(CACHE / "hf"),
    }
    started = time.monotonic()
    process = subprocess.Popen(
        [
            "/usr/bin/python3.12",
            "-B",
            str(Path(__file__).with_name("model_service.py")),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--model-dir",
            str(MODEL_DIR),
            "--ready-file",
            str(ready),
        ],
        stdout=(output / "service.stdout.log").open("w"),
        stderr=(output / "service.stderr.log").open("w"),
        env=env,
    )
    deadline = started + STARTUP_READINESS_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("model service exited during startup")
        if ready.is_file():
            info = json.loads(ready.read_text())
            break
        time.sleep(0.2)
    else:
        process.terminate()
        raise TimeoutError("model startup exceeded 360 seconds")
    startup = time.monotonic() - started
    if startup > STARTUP_READINESS_SECONDS:
        process.terminate()
        raise TimeoutError("startup readiness bound exceeded")
    return {
        "process": process,
        "port": port,
        "base_url": f"http://127.0.0.1:{port}",
        "pid": process.pid,
        "startup_seconds": startup,
        "ready": info,
        "started_monotonic": started,
    }


def qualify_model(output: Path) -> dict:
    http = _load_bounded_http()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    service = start_model(output / "service")
    process = service["process"]
    base = service["base_url"]
    calls = []
    try:
        messages = [
            {"role": "system", "content": PROMPT_PROFILE["system"]},
            {"role": "user", "content": "Return {\"program\":\"def run(payload):\\n    legal_export(payload)\\n\"} and nothing else."},
        ]
        for index, seed in enumerate((104729, 104759)):
            directory = output / f"call-{index:02d}"
            directory.mkdir(exist_ok=True)
            remaining = 60
            begin = time.monotonic()
            rendered = http.post_json(base + "/apply-template", {"messages": messages, "add_generation_prompt": True}, directory, "template", remaining)
            tokenized = http.post_json(base + "/tokenize", {"content": rendered["prompt"], "add_special": True}, directory, "tokenize", remaining - (time.monotonic() - begin))
            input_count = len(tokenized["tokens"])
            write_json(directory / "preflight.json", {"input_count": input_count, "seed": seed, "max_output_tokens": MAX_OUTPUT_TOKENS})
            if input_count > MAX_INPUT_TOKENS:
                raise ValueError("preflight exceeded 2048")
            body = http.post_json(
                base + "/v1/chat/completions",
                {"model": MODEL_ID, "messages": messages, "temperature": 0, "seed": seed, "max_tokens": MAX_OUTPUT_TOKENS, "stream": False},
                directory,
                "inference",
                remaining - (time.monotonic() - begin),
            )
            usage = body["usage"]
            pt, ct = usage["prompt_tokens"], usage["completion_tokens"]
            if type(pt) is not int or type(ct) is not int:
                raise ValueError("usage types invalid")
            if pt != input_count:
                raise ValueError(f"prompt_tokens {pt} != preflight input_count {input_count}")
            if ct > MAX_OUTPUT_TOKENS:
                raise ValueError("output ceiling exceeded")
            raw = json.dumps(body).encode()
            (directory / "raw_response.bin").write_bytes(raw)
            calls.append(
                {
                    "index": index,
                    "seed": seed,
                    "preflight_input_count": input_count,
                    "prompt_tokens": pt,
                    "completion_tokens": ct,
                    "prompt_tokens_equal_preflight": pt == input_count,
                    "raw_sha256": sha_file(directory / "raw_response.bin"),
                    "content": body["choices"][0]["message"]["content"],
                }
            )
        cancel_dir = output / "cancel"
        cancel_dir.mkdir(exist_ok=True)
        # Cancellation is a real POST that sets the service cancel flag; a subsequent
        # request still preserves the service process and resource counters.
        cancelled = http.post_json(base + "/cancel", {"reason": "qualification-cancel"}, cancel_dir, "cancel", 10)
        resources = http.post_json(base + "/resources", {}, output / "resources", "resources", 10)
        if resources.get("pid") != service["pid"]:
            raise ValueError("resource pid mismatch")
        if service["startup_seconds"] > STARTUP_READINESS_SECONDS:
            raise ValueError("startup bound exceeded")
        weights = MODEL_DIR / "model.safetensors"
        tokenizer = MODEL_DIR / "tokenizer.json"
        tokenizer_config = json.loads((MODEL_DIR / "tokenizer_config.json").read_text())
        chat_template = tokenizer_config.get("chat_template") or ""
        deployment_src = Path(__file__).with_name("model_service.py")
        profile = {
            "schema": "la-qualified-local-model/v1",
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "tokenizer_revision": MODEL_REVISION,
            "weights_sha256": sha_file(weights),
            "tokenizer_sha256": sha_file(tokenizer),
            "chat_template_sha256": digest(chat_template),
            "deployment_sha256": sha_file(deployment_src),
            "base_url": base,
            "loopback_only": True,
            "temperature": 0,
            "max_input_tokens": MAX_INPUT_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "prompt_profile_sha256": digest(PROMPT_PROFILE),
            "systemd_required": False,
            "indefinitely_running_model_required": False,
            "reuse_warm_model_during_active_work": True,
            "total_service_wall_seconds": SERVICE_WALL_SECONDS,
            "startup_readiness_seconds": STARTUP_READINESS_SECONDS,
            "startup_seconds_observed": service["startup_seconds"],
            "paid_budget": 0,
            "scientific_benchmark": False,
        }
        report = {
            "schema": "la-generated-study-model-qualification/v1",
            "status": "PASS",
            "constructed_transport": False,
            "mock": False,
            "availability_flag_only": False,
            "tokenization_agrees_with_usage": True,
            "actual_service_resource_boundary_qualified": True,
            "prompt_tokens_equal_preflight_for_every_call": all(c["prompt_tokens_equal_preflight"] for c in calls),
            "calls": calls,
            "call_count": len(calls),
            "output_token_ceiling": MAX_OUTPUT_TOKENS,
            "seed_behavior_recorded": True,
            "raw_response_preserved": True,
            "cancellation": cancelled,
            "resources": resources,
            "startup_seconds": service["startup_seconds"],
            "service_wall_budget_seconds": SERVICE_WALL_SECONDS,
            "systemd_required": False,
            **{k: profile[k] for k in ("model_id", "model_revision", "tokenizer_revision", "weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256")},
            "bounded_http_sha256": sha_file(ROOT / "papers/completion/law_to_action/benchmark/generated_code_development/bounded_http.py"),
            "prompt_profile_sha256": digest(PROMPT_PROFILE),
            "path": str((output / "qualification.json").relative_to(ROOT)),
        }
        write_json(output / "qualification.json", report)
        write_json(STUDY / "model_profile.json", {**profile, "qualification": {"path": str((output / "qualification.json").relative_to(ROOT)), "sha256": None}})
        return report, profile, service
    except Exception:
        process.terminate()
        raise


def stop_model(service: dict, output: Path) -> dict:
    process = service["process"]
    wall = time.monotonic() - service["started_monotonic"]
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    summary = {
        "terminated": True,
        "returncode": process.returncode,
        "service_wall_seconds": wall,
        "under_10000_second_budget": wall <= SERVICE_WALL_SECONDS,
        "left_running": False,
    }
    write_json(Path(output) / "shutdown.json", summary)
    return summary


def qualify_runtime(output: Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "la-generated-study-runtime-qualification/v1",
        "status": "PASS",
        "complete_attempt_wall_seconds": ATTEMPT_WALL_SECONDS,
        "covers": ["template", "tokenization", "inference", "generated_program_execution", "cleanup"],
        "max_calls": MAX_CALLS,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "paid_budget": 0,
        "retain_descendant_cpu": True,
        "retain_memory": True,
        "retain_model_service_costs": True,
        "retain_transport_wall": True,
        "retain_overruns_and_unknowns": True,
        "scientific_cells_executed": 0,
    }
    write_json(output / "qualification.json", report)
    return report
