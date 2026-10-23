"""Bounded development-only xAI chat transport with durable per-effect accounting.

No inference occurs on import. Callers freeze a JSON profile and explicit call IDs
before effects. This is an experimental transport, not production admission.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import time
import urllib.error
import urllib.request


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, value):
    path = Path(path)
    with path.open("xb") as handle:
        handle.write(canonical(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def _credential():
    for name in ("XAI_API_KEY", "GROK_API_KEY"):
        if os.environ.get(name, "").strip():
            return os.environ[name].strip(), {"source": "env:" + name, "expires_at": None}
    auth = Path(os.environ.get("GROK_HOME", str(Path.home() / ".grok"))) / "auth.json"
    try:
        records = json.loads(auth.read_text())
    except (OSError, ValueError):
        return None, {"source": None, "expires_at": None}
    for rec in records.values() if isinstance(records, dict) else ():
        if isinstance(rec, dict) and isinstance(rec.get("key"), str) and rec["key"].strip():
            return rec["key"].strip(), {"source": "grok_auth", "expires_at": rec.get("expires_at")}
    return None, {"source": None, "expires_at": None}


def credential_metadata():
    key, metadata = _credential()
    return {**metadata, "present": bool(key)}


def normalize_usage(usage):
    """Keep API total authoritative; never add overlapping component fields."""
    usage = usage if isinstance(usage, dict) else {}
    def count(value):
        return value if type(value) is int and value >= 0 else None
    prompt_detail = usage.get("prompt_tokens_details") or {}
    output_detail = usage.get("completion_tokens_details") or {}
    prompt_detail = prompt_detail if isinstance(prompt_detail, dict) else {}
    output_detail = output_detail if isinstance(output_detail, dict) else {}
    ticks = count(usage.get("cost_in_usd_ticks"))
    return {
        "input_tokens": count(usage.get("prompt_tokens")),
        "output_tokens": count(usage.get("completion_tokens")),
        "total_tokens": count(usage.get("total_tokens")),
        "cached_input_tokens": count(prompt_detail.get("cached_tokens")),
        "reasoning_tokens": count(output_detail.get("reasoning_tokens", usage.get("reasoning_tokens"))),
        "api_reported_cost_ticks": ticks,
        "cost_usd_decimal": None if ticks is None else f"{ticks // 10**10}.{ticks % 10**10:010d}",
        "total_semantics": "provider total; components preserved without assuming disjointness",
        "billing_scope": "API-reported per-request charge; separate from account settlement",
    }


def _expiry_seconds(value):
    if value is None:
        return None
    if type(value) in (int, float):
        return float(value) / 1000 if value > 10**12 else float(value)
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def call(profile_path, output_root, call_id, messages):
    """Return final text and metering; never retry an existing call identity.

    Profile fields: schema=ns-development-provider/v1, model=grok-4.6,
    call_ids (unique strings), max_output_tokens <= 4096, timeout_seconds <= 600,
    reasoning_effort, max_request_bytes <= 131072. Optional response_format.
    """
    profile_path, output_root = Path(profile_path), Path(output_root)
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    assert profile["schema"] == "ns-development-provider/v1"
    assert profile["model"] == "grok-4.6"
    assert len(set(profile["call_ids"])) == len(profile["call_ids"])
    assert call_id in profile["call_ids"] and call_id.replace("-", "").replace("_", "").isalnum()
    assert 1 <= profile["max_output_tokens"] <= 4096
    assert 1 <= profile["timeout_seconds"] <= 600
    assert 1 <= profile["max_request_bytes"] <= 131072
    assert profile["reasoning_effort"] in ("low", "medium", "high", "xhigh")
    assert isinstance(messages, list) and messages
    assert all(isinstance(m, dict) and set(m) == {"role", "content"}
               and m["role"] in ("system", "user", "assistant")
               and isinstance(m["content"], str) for m in messages)
    request = {"model": profile["model"], "messages": messages,
               "max_tokens": profile["max_output_tokens"],
               "reasoning_effort": profile["reasoning_effort"], "stream": False}
    if profile.get("response_format"):
        request["response_format"] = profile["response_format"]
    body = canonical(request)
    assert len(body) <= profile["max_request_bytes"]
    output_root.mkdir(parents=True, exist_ok=True)
    binding_path = output_root / "profile_binding.json"
    binding = {"profile_sha256": digest(profile_bytes), "transport_sha256": digest(Path(__file__).read_bytes())}
    try:
        write_new(binding_path, binding)
    except FileExistsError:
        assert json.loads(binding_path.read_bytes()) == binding, "new source/profile requires new output root"
    run = output_root / call_id
    run.mkdir()  # Existing started/unknown effects are retained, never silently repeated.
    write_new(run / "request.json", request)
    record = {"schema": "ns-development-call/v1", "call_id": call_id,
              **binding, "request_sha256": digest(body), "request_bytes": len(body),
              "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "attempted_posts": 0, "status": "not_dispatched", "usage": None,
              "normalized_usage": normalize_usage(None), "text": None,
              "workflow_scope": profile.get("workflow_scope", "development proposal")}
    key, metadata = _credential()
    record["credential_metadata"] = metadata
    expiry = _expiry_seconds(metadata["expires_at"])
    if not key or (expiry is not None and expiry - time.time() < profile["timeout_seconds"] + 30):
        record["status"] = "unavailable_credential"
        write_new(run / "result.json", record)
        return record
    write_new(run / "dispatch_intent.json", record)
    started = time.monotonic()
    def deadline(signum, frame):
        raise TimeoutError("absolute development call deadline")
    prior = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, profile["timeout_seconds"])
    try:
        record["attempted_posts"] = 1
        req = urllib.request.Request("https://api.x.ai/v1/chat/completions", data=body,
              headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
        # No redirects: credentials and original effects must stay at the named endpoint.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=profile["timeout_seconds"]) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
            record["http_status"] = response.status
            record["response_sha256"] = digest(raw)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("oversized response")
        value = json.loads(raw)
        record["usage"] = value.get("usage")
        record["normalized_usage"] = normalize_usage(value.get("usage"))
        record["served_model"] = value.get("model")
        record["served_revision"] = value.get("system_fingerprint")
        record["provider_request_id"] = value.get("id")
        choice = value["choices"][0]
        record["finish_reason"] = choice.get("finish_reason")
        record["text"] = choice["message"].get("content")
        record["status"] = "response"
    except urllib.error.HTTPError as exc:
        record.update(status="http_error", http_status=exc.code, error_type=type(exc).__name__)
    except Exception as exc:
        # Do not serialize arbitrary error strings that may contain credentials.
        record.update(status="transport_or_response_error", error_type=type(exc).__name__)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior)
    record["elapsed_seconds"] = time.monotonic() - started
    record["remote_usage_known"] = record["normalized_usage"]["total_tokens"] is not None
    write_new(run / "result.json", record)
    return record
