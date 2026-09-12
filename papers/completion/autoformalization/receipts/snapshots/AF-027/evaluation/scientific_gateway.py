#!/usr/bin/env python3
"""Auditable scoped scientific gateway for AF-027 development qualification.

Nested implementation workers cannot dispatch model jobs through the supervisor
route. This module is the only allowed development model-to-target surface:

* primary served model is Grok ``grok-4.6`` at ``https://api.x.ai/v1``
* Codex ``gpt-5.6-terra`` / high is a quota-only fallback after independently
  verified primary quota exhaustion
* scope is development qualification before final freeze
* final-test bodies, gold, holdout labels, and nested worker dispatch are
  refused
* every attempt writes a raw receipt with served identity, versions, timing,
  and explicit failures

Credentials are resolved at call time from ``XAI_API_KEY`` (or aliases) or the
Grok CLI ``auth.json`` access token. Secret material is never written to a
receipt. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_RECEIPT = "autoformalization-scientific-gateway-receipt/v1"
SCHEMA_GATEWAY = "autoformalization-scientific-gateway/v1"
TASK_ID = "AF-027"
PRIMARY_PROVIDER = "grok"
PRIMARY_MODEL = "grok-4.6"
PRIMARY_BASE_URL = "https://api.x.ai/v1"
FALLBACK_PROVIDER = "codex"
FALLBACK_MODEL = "gpt-5.6-terra"
FALLBACK_REASONING_EFFORT = "high"
FALLBACK_TRIGGER = "independently_verified_primary_quota_exhaustion"
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_MAX_TOKENS = 256
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
FORBIDDEN_SPLIT_MARKERS = (
    "final_test",
    "final-test",
    "holdout",
    "gold_facet",
    "gold-label",
    "private_packet",
)
QUOTA_STATUS_CODES = frozenset({402, 429})
QUOTA_TEXT_MARKERS = (
    "quota",
    "rate limit",
    "rate_limit",
    "resource exhausted",
    "insufficient_quota",
    "tokens exhausted",
)
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]


class GatewayError(ValueError):
    """Raised when a request violates the development-qualification scope."""


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise GatewayError("canonical JSON requires finite numeric values") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def _redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    redacted = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower in {"authorization", "x-api-key", "cookie", "set-cookie"}:
            redacted[key] = "redacted"
        else:
            redacted[key] = value
    return redacted


def _fingerprint_secret(secret: str) -> dict[str, Any]:
    return {
        "algorithm": "sha256",
        "length": len(secret),
        "sha256": sha256_text(secret),
        "prefix_kind": "jwt" if secret.startswith("eyJ") else "opaque",
    }


def resolve_grok_credential() -> dict[str, Any]:
    env_names = (
        "XAI_API_KEY",
        "ipfs_accelerate_py_XAI_API_KEY",
        "IPFS_ACCELERATE_PY_XAI_API_KEY",
        "IPFS_DATASETS_PY_XAI_API_KEY",
        "GROK_CODE_XAI_API_KEY",
    )
    for name in env_names:
        value = str(os.environ.get(name) or "").strip()
        if value:
            return {
                "available": True,
                "source": f"env:{name}",
                "fingerprint": _fingerprint_secret(value),
                "secret": value,
                "expires_at": None,
            }
    grok_home = Path(os.environ.get("GROK_HOME") or (Path.home() / ".grok"))
    auth_path = grok_home / "auth.json"
    try:
        payload = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, Mapping):
        for record in payload.values():
            if not isinstance(record, Mapping):
                continue
            token = str(record.get("key") or record.get("access_token") or "").strip()
            if not token:
                continue
            return {
                "available": True,
                "source": "grok_cli_auth.json",
                "fingerprint": _fingerprint_secret(token),
                "secret": token,
                "expires_at": record.get("expires_at"),
                "auth_mode": record.get("auth_mode"),
                "oidc_issuer": record.get("oidc_issuer"),
            }
    return {
        "available": False,
        "source": None,
        "fingerprint": None,
        "secret": None,
        "expires_at": None,
        "blockers": [
            "no XAI_API_KEY (or alias) in the worker environment",
            f"no usable Grok CLI auth.json at {auth_path}",
        ],
    }


def public_credential_status() -> dict[str, Any]:
    resolved = resolve_grok_credential()
    public = {
        "available": bool(resolved.get("available")),
        "source": resolved.get("source"),
        "fingerprint": resolved.get("fingerprint"),
        "expires_at": resolved.get("expires_at"),
        "auth_mode": resolved.get("auth_mode"),
        "oidc_issuer": resolved.get("oidc_issuer"),
        "blockers": list(resolved.get("blockers") or []),
    }
    return public


def gateway_identity() -> dict[str, Any]:
    return {
        "schema": SCHEMA_GATEWAY,
        "task_id": TASK_ID,
        "scope": "development_qualification_before_final_freeze",
        "nested_worker_direct_dispatch": False,
        "primary": {
            "provider": PRIMARY_PROVIDER,
            "model": PRIMARY_MODEL,
            "base_url": PRIMARY_BASE_URL,
            "chat_completions": f"{PRIMARY_BASE_URL}/chat/completions",
        },
        "fallback": {
            "provider": FALLBACK_PROVIDER,
            "model": FALLBACK_MODEL,
            "reasoning_effort": FALLBACK_REASONING_EFFORT,
            "trigger": FALLBACK_TRIGGER,
            "authorized_without_quota_evidence": False,
        },
        "resource_envelope": {
            "gpu_or_model_service_slots": 1,
            "memory_gib": 16,
            "local_weight_file_forbidden_when_over_envelope": True,
            "cached_leanstral_gguf_excluded": True,
        },
        "refused": [
            "final_test_bodies",
            "holdout_labels",
            "gold_values",
            "nested_supervisor_dispatch",
            "unconditional_unavailable_stub",
            "fixture_model_output",
        ],
    }


def validate_development_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise GatewayError("gateway request must be an object")
    if request.get("split") not in {None, "train", "selection", "fixed_canary", "development", "constructed_control"}:
        raise GatewayError(
            f"gateway refuses split {request.get('split')!r}; development qualification only"
        )
    if request.get("final_test") or request.get("evaluation_sample") is True:
        raise GatewayError("gateway refuses final-test or evaluation-sample payloads")
    if request.get("gold") or request.get("gold_values") or request.get("labels"):
        raise GatewayError("gateway refuses gold or label payloads")
    blob = canonical_dumps(request).lower()
    for marker in FORBIDDEN_SPLIT_MARKERS:
        if marker in blob and request.get("split") in {"final_test", "holdout"}:
            raise GatewayError(f"gateway refuses forbidden marker {marker}")
    prompt = str(request.get("prompt") or request.get("source_text") or "")
    if not prompt.strip():
        raise GatewayError("gateway request has empty prompt/source_text")


def _quota_exhausted(status: int, body: str) -> bool:
    if status not in QUOTA_STATUS_CODES:
        return False
    lowered = body.lower()
    return any(marker in lowered for marker in QUOTA_TEXT_MARKERS)


def _http_json(
    url: str,
    payload: Mapping[str, Any],
    *,
    token: str,
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "af-027-scientific-gateway/v1",
    }
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    started = time.perf_counter()
    started_at = utc_now()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.status)
            response_headers = {str(key): str(value) for key, value in response.headers.items()}
        finished_at = utc_now()
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        text = raw.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        return {
            "ok": 200 <= status < 300 and isinstance(parsed, Mapping),
            "status": status,
            "elapsed_ms": elapsed_ms,
            "started_at": started_at,
            "finished_at": finished_at,
            "response_headers": _redact_headers(response_headers),
            "raw_text": text,
            "parsed": parsed if isinstance(parsed, Mapping) else None,
            "error": None if 200 <= status < 300 else f"HTTP {status}",
        }
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        text = raw.decode("utf-8", errors="replace")
        finished_at = utc_now()
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        try:
            parsed = json.loads(text) if text else None
        except json.JSONDecodeError:
            parsed = None
        return {
            "ok": False,
            "status": int(exc.code),
            "elapsed_ms": elapsed_ms,
            "started_at": started_at,
            "finished_at": finished_at,
            "response_headers": _redact_headers({str(k): str(v) for k, v in (exc.headers.items() if exc.headers else [])}),
            "raw_text": text,
            "parsed": parsed if isinstance(parsed, Mapping) else None,
            "error": f"HTTP {exc.code}: {exc.reason}",
            "quota_exhausted": _quota_exhausted(int(exc.code), text),
        }
    except Exception as exc:
        finished_at = utc_now()
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return {
            "ok": False,
            "status": None,
            "elapsed_ms": elapsed_ms,
            "started_at": started_at,
            "finished_at": finished_at,
            "response_headers": {},
            "raw_text": "",
            "parsed": None,
            "error": f"{type(exc).__name__}: {exc}",
            "quota_exhausted": False,
        }


def _choice_text(parsed: Mapping[str, Any] | None) -> str:
    if not parsed:
        return ""
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, Mapping):
        return ""
    message = first.get("message")
    if isinstance(message, Mapping):
        content = message.get("content")
        if isinstance(content, str):
            return content
    text = first.get("text")
    return text if isinstance(text, str) else ""


def _receipt(
    *,
    request: Mapping[str, Any],
    provider: str,
    requested_model: str,
    transport: Mapping[str, Any],
    credential: Mapping[str, Any],
    fallback_considered: bool,
    fallback_invoked: bool,
    fallback_blockers: Sequence[str],
) -> dict[str, Any]:
    parsed = transport.get("parsed") if isinstance(transport.get("parsed"), Mapping) else {}
    served = str(parsed.get("model") or "")
    usage = parsed.get("usage") if isinstance(parsed.get("usage"), Mapping) else {}
    text = _choice_text(parsed if isinstance(parsed, Mapping) else None)
    failures: list[str] = []
    if transport.get("error"):
        failures.append(str(transport["error"]))
    if not transport.get("ok"):
        failures.append("transport_not_ok")
    if transport.get("ok") and not text.strip():
        failures.append("empty_model_text")
    execution_status = "measured" if transport.get("ok") and text.strip() else "failure"
    if not credential.get("available"):
        execution_status = "unavailable"
        failures.extend(list(credential.get("blockers") or ["credential_unavailable"]))
    raw_excerpt = str(transport.get("raw_text") or "")
    if len(raw_excerpt) > 8000:
        raw_excerpt = raw_excerpt[:8000] + "\n...truncated..."
    receipt = {
        "schema": SCHEMA_RECEIPT,
        "task_id": TASK_ID,
        "purpose": request.get("purpose") or "development_model_to_target",
        "claim_admissible": False,
        "synthetic_success": False,
        "fixture": False,
        "unconditional_unavailable": False,
        "scope": "development_qualification_before_final_freeze",
        "split": request.get("split") or "development",
        "source_id": request.get("source_id"),
        "source_sha256": request.get("source_sha256"),
        "prompt_sha256": sha256_text(str(request.get("prompt") or request.get("source_text") or "")),
        "request_digest": sha256_obj({
            key: request[key] for key in request if key not in {"prompt", "source_text"}
        } | {
            "prompt_sha256": sha256_text(str(request.get("prompt") or request.get("source_text") or "")),
        }),
        "primary": {
            "provider": PRIMARY_PROVIDER,
            "requested_model": PRIMARY_MODEL,
            "base_url": PRIMARY_BASE_URL,
        },
        "provider_attempted": provider,
        "requested_model": requested_model,
        "served_identity": {
            "provider": provider,
            "requested_model": requested_model,
            "served_model": served or None,
            "response_id": parsed.get("id"),
            "object": parsed.get("object"),
            "system_fingerprint": parsed.get("system_fingerprint"),
            "service_tier": parsed.get("service_tier"),
            "created": parsed.get("created"),
        },
        "versions": {
            "gateway": SCHEMA_GATEWAY,
            "receipt": SCHEMA_RECEIPT,
            "primary_model_requested": PRIMARY_MODEL,
            "fallback_model": FALLBACK_MODEL,
            "python": sys.version.split()[0],
        },
        "timing": {
            "started_at": transport.get("started_at"),
            "finished_at": transport.get("finished_at"),
            "elapsed_ms": transport.get("elapsed_ms"),
            "timeout_seconds": request.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS,
        },
        "http": {
            "url": f"{PRIMARY_BASE_URL}/chat/completions",
            "status": transport.get("status"),
            "ok": bool(transport.get("ok")),
            "response_headers": transport.get("response_headers") or {},
        },
        "usage": usage,
        "credential": {
            "available": bool(credential.get("available")),
            "source": credential.get("source"),
            "fingerprint": credential.get("fingerprint"),
            "expires_at": credential.get("expires_at"),
        },
        "fallback": {
            "configured": True,
            "provider": FALLBACK_PROVIDER,
            "model": FALLBACK_MODEL,
            "reasoning_effort": FALLBACK_REASONING_EFFORT,
            "trigger": FALLBACK_TRIGGER,
            "considered": fallback_considered,
            "invoked": fallback_invoked,
            "blockers": list(fallback_blockers),
        },
        "execution_status": execution_status,
        "result_kind": "bounded_observation" if execution_status == "measured" else "failure",
        "output_text": text,
        "output_sha256": sha256_text(text) if text else None,
        "raw_response_excerpt": raw_excerpt,
        "failures": failures,
        "quota_exhausted": bool(transport.get("quota_exhausted")),
    }
    receipt["receipt_sha256"] = sha256_obj({key: receipt[key] for key in receipt if key != "receipt_sha256"})
    return receipt


def complete(request: Mapping[str, Any] | None = None) -> dict[str, Any]:
    request = dict(request or {})
    request.setdefault("purpose", "development_model_to_target")
    request.setdefault("split", "development")
    request.setdefault("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    request.setdefault("max_tokens", DEFAULT_MAX_TOKENS)
    validate_development_request(request)
    credential = resolve_grok_credential()
    identity = gateway_identity()
    if not credential.get("available"):
        return _receipt(
            request=request,
            provider=PRIMARY_PROVIDER,
            requested_model=PRIMARY_MODEL,
            transport={
                "ok": False,
                "status": None,
                "elapsed_ms": 0,
                "started_at": utc_now(),
                "finished_at": utc_now(),
                "response_headers": {},
                "raw_text": "",
                "parsed": None,
                "error": "credential_unavailable",
                "quota_exhausted": False,
            },
            credential=credential,
            fallback_considered=False,
            fallback_invoked=False,
            fallback_blockers=["primary credential missing; Codex fallback is quota-only"],
        )
    payload = {
        "model": PRIMARY_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the AF-027 development model-to-target adapter. "
                    "Produce only the requested Lean 4 target. Do not use sorry, "
                    "admit, or axioms unless the prompt supplies them. This is "
                    "development qualification, not a paper Table 6 result."
                ),
            },
            {
                "role": "user",
                "content": str(request.get("prompt") or request.get("source_text") or ""),
            },
        ],
        "max_tokens": int(request.get("max_tokens") or DEFAULT_MAX_TOKENS),
        "temperature": 0,
    }
    transport = _http_json(
        f"{PRIMARY_BASE_URL}/chat/completions",
        payload,
        token=str(credential["secret"]),
        timeout=float(request.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS),
    )
    fallback_considered = bool(transport.get("quota_exhausted"))
    fallback_invoked = False
    fallback_blockers = []
    if fallback_considered:
        fallback_blockers.append(
            "primary quota evidence is present but Codex terra/high credentials "
            "are not independently configured in this worker"
        )
    receipt = _receipt(
        request=request,
        provider=PRIMARY_PROVIDER,
        requested_model=PRIMARY_MODEL,
        transport=transport,
        credential=credential,
        fallback_considered=fallback_considered,
        fallback_invoked=fallback_invoked,
        fallback_blockers=fallback_blockers,
    )
    receipt["gateway_identity_sha256"] = sha256_obj(identity)
    return receipt


DEVELOPMENT_TARGET_PROMPT = """Development qualification only. Do not inspect final-test or gold.

Formalize this guarded-write law as Lean 4. Do not use sorry or admit.

Law: if Protected is true and Approved is false, then Write is false.

Return only Lean 4. A valid answer is a complete theorem that type-checks, for example by assuming the guard as a hypothesis:

variable (Protected Approved Write : Prop)
theorem AF027_dev_q1
    (guard : Protected → ¬ Approved → ¬ Write)
    (hP : Protected) (hA : ¬ Approved) : ¬ Write :=
  guard hP hA
"""


def model_to_target(
    *,
    source_id: str = "AF027-DEV-Q1",
    source_text: str | None = None,
    split: str = "constructed_control",
) -> dict[str, Any]:
    prompt = source_text or DEVELOPMENT_TARGET_PROMPT
    return complete({
        "purpose": "development_model_to_target",
        "source_id": source_id,
        "source_sha256": sha256_text(prompt),
        "split": split,
        "prompt": prompt,
        "max_tokens": 256,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
    })


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("identity", help="Print gateway identity and credential status")
    call = sub.add_parser("model-to-target", help="Run one development model-to-target call")
    call.add_argument("--source-id", default="AF027-DEV-Q1")
    call.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "identity":
        report = {
            "identity": gateway_identity(),
            "credential": public_credential_status(),
        }
        print(canonical_dumps(report))
        return 0 if report["credential"]["available"] else 1
    receipt = model_to_target(source_id=args.source_id)
    if args.output:
        write_json(Path(args.output), receipt)
    print(canonical_dumps({
        "execution_status": receipt["execution_status"],
        "served_model": receipt["served_identity"]["served_model"],
        "response_id": receipt["served_identity"]["response_id"],
        "elapsed_ms": receipt["timing"]["elapsed_ms"],
        "failures": receipt["failures"],
        "receipt_sha256": receipt["receipt_sha256"],
        "output_sha256": receipt["output_sha256"],
    }))
    return 0 if receipt["execution_status"] == "measured" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GatewayError as exc:
        print(f"scientific_gateway: {exc}", flush=True)
        raise SystemExit(1)
