#!/usr/bin/env python3
"""Track 1 scored generator: Mistral Labs hosted Leanstral.

Local docker0 NVFP4 is prototype only. This adapter POSTs to
``https://api.mistral.ai/v1/chat/completions`` with model
``labs-leanstral-1-5``. It never calls ``172.17.0.1:8080``, never
``LOCK_EX``, never starts llama-server, and never falls back to grok or
local GGUF. Official Track 2 stays off. Labs preview pricing is treated
as US$0 and still logged. Jev in-loop cost counts toward the US$3 cap.
Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
ROOT_ACCEL = Path("/home/barberb/lift_coding/external/ipfs_accelerate")
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
KEYFILES = (
    Path.home() / ".config/ipfs_accelerate_py/mistral.env",
    Path.home() / ".config/ipfs_accelerate_py/typesafe.env",
    Path.home() / ".vibe" / ".env",
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import generate_text as lra_gt  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import typesafe_router as lra_ts  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
PROTOCOL = "LRA/v1"
PR_ID = "PR-12b"
LRAH_ID = "LRAH-011b"
TRACK_LABEL = "track1_closed"
REQUESTED_PROVIDER = "mistral"
REQUESTED_MODEL = "labs-leanstral-1-5"
ALT_MODELS = ("labs-leanstral-1-5", "leanstral-1-5")
API_HOST = "api.mistral.ai"
CHAT_URL = f"https://{API_HOST}/v1/chat/completions"
LABS_RETIRE_DATE = "2026-09-30"
HARDWARE_CLASS = "mistral_labs_api"
PROTOTYPE_HARDWARE_CLASS = "spark_gb10"
PROTOTYPE_BASE_URL = "http://172.17.0.1:8080/v1"
MAX_NEW_TOKENS_DEFAULT = 256
TIMEOUT_DEFAULT = 180.0
KEY_ENV_NAMES = (
    "MISTRAL_API_KEY",
    "IPFS_ACCELERATE_MISTRAL_API_KEY",
    "IPFS_ACCELERATE_PY_MISTRAL_API_KEY",
    "ipfs_accelerate_py_MISTRAL_API_KEY",
    "IPFS_DATASETS_PY_MISTRAL_API_KEY",
)
FORBIDDEN_HOSTS = frozenset({"172.17.0.1", "127.0.0.1", "localhost", "0.0.0.0"})
FORBIDDEN_PROVIDERS = frozenset(
    {
        "leanstral_local",
        "llama_cpp",
        "grok",
        "grok_cli",
        "xai",
        "hf_inference_api",
        "openai",
        "openrouter",
    }
)
CANARY_NAME = "CallElimCorrect.substOldPostSubset"
FORBIDDEN_IMPORT_NAMES = frozenset({"fcntl", "typesafe_sdk", "LeanstralProofProvider"})


class Track1MistralError(RuntimeError):
    """Fail-closed hosted Leanstral error. Never a local GGUF success."""


def load_keyfiles() -> None:
    for path in KEYFILES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            os.environ.setdefault(name.strip(), value)


def pin_paths() -> None:
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    text = str(ROOT_ACCEL)
    if text in sys.path:
        sys.path.remove(text)
    sys.path.insert(0, text)
    lra_ts.ACCEL_ROOT = ROOT_ACCEL
    lra_ts.TYPESAFE_INFERENCE_PATH = ROOT_ACCEL / "ipfs_accelerate_py" / "typesafe_inference.py"


def mistral_key_configured(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return any(str(source.get(name) or "").strip() for name in KEY_ENV_NAMES)


def resolve_mistral_key(env: Optional[Mapping[str, str]] = None) -> str:
    source = os.environ if env is None else env
    for name in KEY_ENV_NAMES:
        value = str(source.get(name) or "").strip()
        if value:
            return value
    raise Track1MistralError("MISTRAL_API_KEY is not set")


def _redact_text(text: str, secret: str) -> str:
    if not text:
        return ""
    redacted = text
    if secret:
        redacted = redacted.replace(secret, "[redacted]")
    return redacted


def assert_hosted_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in FORBIDDEN_HOSTS or host.endswith(".local"):
        raise Track1MistralError(f"refusing prototype host {host!r}; Track 1 must use {API_HOST}")
    if host != API_HOST:
        raise Track1MistralError(f"refusing non-Labs host {host!r}; expected {API_HOST}")


def chat_completions(
    prompt: str,
    *,
    model: str = REQUESTED_MODEL,
    max_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    timeout: float = TIMEOUT_DEFAULT,
    url: str = CHAT_URL,
    temperature: float = 0.0,
    n: int = 1,
    stop: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    """POST chat/completions to Mistral Labs. Never docker0."""

    assert_hosted_url(url)
    key = resolve_mistral_key()
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(temperature),
        "top_p": 1,
        "max_tokens": int(max_tokens),
    }
    if int(n) > 1:
        payload["n"] = int(n)
        if float(payload["temperature"]) <= 0.0:
            payload["temperature"] = 0.3
    if stop:
        payload["stop"] = [str(item) for item in stop if str(item)]
    raw_body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=raw_body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=float(timeout)) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = int(getattr(response, "status", 200))
            final_url = str(getattr(response, "geturl", lambda: url)())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise Track1MistralError(
            _redact_text(f"Mistral HTTP {exc.code}: {detail[:400]}", key)
        ) from None
    except Exception as exc:
        raise Track1MistralError(_redact_text(f"{type(exc).__name__}: {exc}", key)) from None
    assert_hosted_url(final_url or url)
    try:
        data = json.loads(raw)
    except Exception as exc:
        raise Track1MistralError(f"Mistral returned invalid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise Track1MistralError("Mistral returned a non-object JSON payload")
    choices = data.get("choices") if isinstance(data.get("choices"), list) else []
    texts: list[str] = []
    for choice in choices:
        if not isinstance(choice, Mapping):
            continue
        message = choice.get("message") if isinstance(choice.get("message"), Mapping) else {}
        content = str(message.get("content") or "")
        if content:
            texts.append(content)
    message = {}
    if choices and isinstance(choices[0], Mapping):
        message = choices[0].get("message") if isinstance(choices[0].get("message"), Mapping) else {}
    text = texts[0] if texts else str(message.get("content") or "")
    usage = data.get("usage") if isinstance(data.get("usage"), Mapping) else {}
    resolved_model = str(data.get("model") or model)
    return {
        "text": text,
        "model": resolved_model,
        "id": str(data.get("id") or ""),
        "object": str(data.get("object") or ""),
        "status": status,
        "url_host": urlparse(final_url or url).hostname,
        "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        "finish_reason": str((choices[0] or {}).get("finish_reason") or "") if choices else "",
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "hardware_class": HARDWARE_CLASS,
        "prototype_base_url": PROTOTYPE_BASE_URL,
        "used_prototype_endpoint": False,
    }


def generate_mistral(
    prompt: str,
    ledger: lra_t1.ProblemLedger,
    *,
    max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    timeout: float = TIMEOUT_DEFAULT,
    model: str = REQUESTED_MODEL,
    fixture: bool = False,
    fixture_text: str = "simp_all",
) -> tuple[str, dict[str, Any], lra_t1.UsageLine]:
    estimated_in = lra_t1.estimate_tokens(prompt)
    estimated_out = int(max_new_tokens)
    allowed, reason, _cost = ledger.authorize("mistral", estimated_in, estimated_out)
    if not allowed:
        line = ledger.record(
            "mistral",
            input_tokens=estimated_in,
            output_tokens=estimated_out,
            fixture=fixture,
            model=model,
        )
        raise Track1MistralError(f"mistral call refused: {reason}")
    if fixture:
        identity = {
            "requested_provider": REQUESTED_PROVIDER,
            "requested_model": model,
            "resolved_provider": REQUESTED_PROVIDER,
            "resolved_model": model,
            "fallback_used": False,
            "url_host": API_HOST,
            "hardware_class": HARDWARE_CLASS,
            "used_prototype_endpoint": False,
            "arena_score": None,
        }
        line = ledger.record(
            "mistral",
            input_tokens=estimated_in,
            output_tokens=lra_t1.estimate_tokens(fixture_text),
            fixture=True,
            model=model,
        )
        return fixture_text, identity, line
    payload = chat_completions(
        prompt,
        model=model,
        max_tokens=max_new_tokens,
        timeout=timeout,
    )
    resolved_provider = REQUESTED_PROVIDER
    if payload.get("url_host") != API_HOST:
        raise Track1MistralError("resolved host is not api.mistral.ai")
    identity = {
        "requested_provider": REQUESTED_PROVIDER,
        "requested_model": model,
        "resolved_provider": resolved_provider,
        "resolved_model": payload.get("model") or model,
        "fallback_used": False,
        "request_id": payload.get("id"),
        "url_host": payload.get("url_host"),
        "hardware_class": HARDWARE_CLASS,
        "used_prototype_endpoint": False,
        "finish_reason": payload.get("finish_reason"),
        "arena_score": None,
    }
    line = ledger.record(
        "mistral",
        input_tokens=int(payload.get("input_tokens") or estimated_in),
        output_tokens=int(payload.get("output_tokens") or lra_t1.estimate_tokens(payload["text"])),
        fixture=False,
        model=str(identity["resolved_model"]),
    )
    if line.skipped:
        raise Track1MistralError(f"mistral spend refused after call: {line.reason}")
    return str(payload["text"]), identity, line


def redact(payload: Any) -> Any:
    if isinstance(payload, Mapping):
        out = {}
        for key, value in payload.items():
            name = str(key).lower()
            if "api_key" in name or name in {"authorization", "bearer"}:
                out[key] = "[redacted]" if value else value
            else:
                out[key] = redact(value)
        return out
    if isinstance(payload, list):
        return [redact(item) for item in payload]
    if isinstance(payload, str) and (payload.startswith("apikey_") or payload.startswith("sk-")):
        return "[redacted]"
    return payload


def run_named(
    name: str,
    *,
    max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    timeout: float = TIMEOUT_DEFAULT,
    official_track2: bool = False,
    fixture: bool = False,
    path: Optional[Path] = None,
) -> dict[str, Any]:
    pin_paths()
    if official_track2 or lra_ts.official_track2_requested():
        return {
            "ok": True,
            "skipped": True,
            "reason": "official_track2_off",
            "called_mistral": False,
            "called_jev": False,
            "arena_score": None,
            "contaminates_track2": False,
        }
    record, records, digest = lra_t1._load_named_record(name, path)
    ledger = lra_t1.ProblemLedger(name=name, official_track2=False)
    if not fixture and not (mistral_key_configured() and lra_t1.jev_key_configured()):
        return {
            "ok": True,
            "skipped": True,
            "reason": "no_key",
            "name": name,
            "mistral_key_configured": mistral_key_configured(),
            "jev_key_configured": lra_t1.jev_key_configured(),
            "called_mistral": False,
            "arena_score": None,
        }
    neighbors = lra_t1._neighbors_for(record, records)
    state = lra_ts.problem_state(record, neighbors=neighbors)
    factory = None
    if fixture:
        factory = lambda **kwargs: lra_ts.FixtureClient(answers=lra_ts.default_fixture_answers(), **kwargs)
    router = lra_ts.TypeSafeLraRouter(
        mode="inloop",
        official_track2=False,
        env={**os.environ, "LRA_TYPESAFE": "inloop"},
        client_factory=factory,
        require_key=not fixture,
    )
    started = time.perf_counter()
    jev_result = router.route(state, neighbor_names=[item["name"] for item in neighbors])
    ledger.record(
        "jev",
        input_tokens=int((jev_result.usage or {}).get("input_tokens") or 0),
        output_tokens=int((jev_result.usage or {}).get("output_tokens") or 0),
        fixture=fixture or bool(jev_result.used_fixture),
        model=jev_result.model or lra_t1.JEV_MODEL_ID,
    )
    prompt = lra_gt.render_prompt(record)
    text, identity, _line = generate_mistral(
        prompt,
        ledger,
        max_new_tokens=max_new_tokens,
        timeout=timeout,
        fixture=fixture,
    )
    payload = {
        "ok": True,
        "skipped": False,
        "schema": "lra-track1-mistral-leanstral/v1",
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "track": TRACK_LABEL,
        "name": name,
        "source": record.get("source"),
        "warmup_jsonl_sha256": digest,
        "requested_provider": REQUESTED_PROVIDER,
        "requested_model": REQUESTED_MODEL,
        "identity": identity,
        "hardware_class": HARDWARE_CLASS,
        "prototype_hardware_class": PROTOTYPE_HARDWARE_CLASS,
        "used_prototype_endpoint": False,
        "labs_retire_date": LABS_RETIRE_DATE,
        "text": text,
        "text_head": text[:400],
        "n_chars": len(text),
        "jev_route": jev_result.as_dict(),
        "ledger": ledger.as_dict(),
        "called_mistral": True,
        "called_jev": True,
        "called_docker0": False,
        "lock_ex": False,
        "llama_server_started": False,
        "official_track2": False,
        "contaminates_track2": False,
        "arena_score": None,
        "api_key_present_in_record": False,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
    }
    return redact(payload)


def audit_source() -> dict[str, Any]:
    text = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    lock_ex = any(isinstance(node, ast.Attribute) and node.attr == "LOCK_EX" for node in ast.walk(tree))
    docker0 = PROTOTYPE_BASE_URL in text
    return {
        "forbidden_imports": sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES),
        "uses_lock_ex": lock_ex,
        "mentions_prototype_url": docker0,
        "ok": not lock_ex and "typesafe_sdk" not in imported,
    }


def self_check() -> dict[str, Any]:
    audit = audit_source()
    ledger = lra_t1.ProblemLedger(name="fixture")
    text, identity, line = generate_mistral("ping", ledger, fixture=True, fixture_text="simp")
    refused = False
    try:
        assert_hosted_url("http://172.17.0.1:8080/v1/chat/completions")
    except Track1MistralError:
        refused = True
    mistral_mode = lra_t1.resolve_track1_mode(env={"LRA_GENERATOR": "mistral_labs"})
    track2 = lra_t1.resolve_track1_mode(
        env={"LRA_GENERATOR": "mistral_labs", "LRA_OFFICIAL_TRACK2": "1"}
    )
    zero = lra_t1.usd_for("mistral", 1_000_000, 1_000_000)
    report = {
        "ok": True,
        "audit": audit,
        "fixture_text": text,
        "fixture_host": identity.get("url_host"),
        "fixture_usd": line.usd,
        "refuses_docker0": refused,
        "mistral_opt_in": mistral_mode == "track1",
        "official_track2_stays_off": track2 == "off",
        "labs_priced_zero": float(zero) == 0.0,
        "requested_provider": REQUESTED_PROVIDER,
        "requested_model": REQUESTED_MODEL,
        "hardware_class": HARDWARE_CLASS,
        "prototype_hardware_class": PROTOTYPE_HARDWARE_CLASS,
        "used_prototype_endpoint": False,
        "arena_score": None,
        "jev_generated_lean": False,
    }
    report["ok"] = (
        audit["ok"]
        and refused
        and mistral_mode == "track1"
        and track2 == "off"
        and float(zero) == 0.0
        and text == "simp"
        and identity.get("used_prototype_endpoint") is False
    )
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--probe", action="store_true", help="tiny hosted ping; no warmup compile")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--name", default=CANARY_NAME)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_check or not (args.probe or args.live):
        report = self_check()
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    load_keyfiles()
    pin_paths()
    if args.probe:
        ping = chat_completions(
            "Return exactly the token rfl and nothing else.",
            max_tokens=8,
            timeout=60.0,
        )
        report = redact(
            {
                "ok": bool(ping.get("text")),
                "probe": True,
                "identity": {
                    "requested_provider": REQUESTED_PROVIDER,
                    "requested_model": REQUESTED_MODEL,
                    "resolved_model": ping.get("model"),
                    "request_id": ping.get("id"),
                    "url_host": ping.get("url_host"),
                    "hardware_class": HARDWARE_CLASS,
                    "used_prototype_endpoint": False,
                },
                "text_head": str(ping.get("text") or "")[:120],
                "finish_reason": ping.get("finish_reason"),
                "input_tokens": ping.get("input_tokens"),
                "output_tokens": ping.get("output_tokens"),
                "wall_ms": ping.get("wall_ms"),
                "labs_retire_date": LABS_RETIRE_DATE,
                "arena_score": None,
            }
        )
    else:
        report = run_named(args.name, max_new_tokens=args.max_new_tokens)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if "apikey_" in text or "sk-" in text:
        raise SystemExit("refusing to write a receipt that looks like it contains a secret")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"track1-mistral-{stamp}.json"
    latest = args.out / "track1-mistral-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": report.get("ok"), "latest": str(latest), "skipped": report.get("skipped"), "reason": report.get("reason"), "host": (report.get("identity") or {}).get("url_host"), "model": (report.get("identity") or {}).get("resolved_model"), "used_prototype": report.get("used_prototype_endpoint"), "arena_score": None}, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
