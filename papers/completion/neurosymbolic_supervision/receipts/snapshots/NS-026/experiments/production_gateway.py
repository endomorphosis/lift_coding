#!/usr/bin/env python3
"""Scoped scientific provider gateway for NS-026.

The sealed provider container cannot safely dispatch itself: Docker is
absent, the authoritative validation PATH does not contain Grok/Codex,
and NS-004 Terra HIGH is not admitted. This gateway runs as a separate
principal. It never mounts a Docker socket, host credential trees,
original .git, fixed-commit trees, curator sessions, or scorer-only
payloads into a proposal export.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PAPER_REL = Path("papers/completion/neurosymbolic_supervision")
AMENDMENT_REL = PAPER_REL / "protocol" / "development_provider_amendment.json"
PROFILE_REL = PAPER_REL / "experiments" / "production_profile.json"
HIDDEN_STORE_REL = PAPER_REL / "receipts" / "snapshots" / "NS-005" / "scorer_only"
PROPOSAL_SNAPSHOT_REL = PAPER_REL / "receipts" / "snapshots" / "NS-005" / "proposal_snapshots"
DEFAULT_ENDPOINT = "https://api.x.ai/v1/chat/completions"
DEFAULT_MODEL = "grok-4.6"
GITHUB_TARBALL = "https://codeload.github.com/{slug}/tar.gz/{commit}"
FORBIDDEN_PROPOSAL_MARKERS = (
    "receipts/snapshots/NS-005/scorer_only",
    "scorer_only/oracles",
    "fail_to_pass",
    "reference_patch",
    "/.git/",
    "git/objects",
    "fix_commit",
)
CREDENTIAL_ENV = ("XAI_API_KEY", "GROK_API_KEY")
TERRA_ENV = ("OPENAI_API_KEY", "CODEX_API_KEY")


class GatewayError(Exception):
    def __init__(self, message: str, *, terminal: str = "unavailable") -> None:
        super().__init__(message)
        self.terminal = terminal


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def atomic_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = obj if isinstance(obj, str) else canonical_dumps(obj) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def repo_root(start: Path | None = None) -> Path:
    cur = (start or Path(__file__)).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / AMENDMENT_REL).is_file() or (candidate / PROFILE_REL).is_file():
            return candidate
        marker = candidate / PAPER_REL / "protocol" / "experiment_manifest.json"
        if marker.is_file():
            return candidate
    raise GatewayError("cannot locate neurosymbolic_supervision paper tree")


def paper_dir(root: Path) -> Path:
    return root / PAPER_REL


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_profile(root: Path) -> dict[str, Any]:
    path = root / PROFILE_REL
    if not path.is_file():
        raise GatewayError(f"missing production profile: {path}")
    return load_json(path)


def load_amendment(root: Path) -> dict[str, Any]:
    path = root / AMENDMENT_REL
    if not path.is_file():
        raise GatewayError(
            "development provider amendment is not frozen; refusing development dispatch",
            terminal="unavailable",
        )
    data = load_json(path)
    if data.get("schema") != "paper-ns-development-provider-amendment/v1":
        raise GatewayError("development amendment schema mismatch")
    if data.get("overwrites_original_protocol") is True:
        raise GatewayError("amendment must not overwrite ns-core-v1")
    if data.get("permitted_development_profile", {}).get("admitted_production") is True:
        raise GatewayError("development amendment cannot admit production")
    return data


def credential_fingerprint(token: str) -> str:
    return sha256_text("ns-026-credential|" + token)


def load_runtime_credential() -> dict[str, Any] | None:
    for name in CREDENTIAL_ENV:
        value = (os.environ.get(name) or "").strip()
        if value:
            return {
                "source": f"env:{name}",
                "token": value,
                "expires_at": None,
                "fingerprint": credential_fingerprint(value),
            }
    grok_home = os.environ.get("GROK_HOME") or str(Path.home() / ".grok")
    auth_path = Path(grok_home) / "auth.json"
    try:
        if not auth_path.is_file() or auth_path.stat().st_size <= 0:
            return None
        data = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    records = data.values() if isinstance(data, dict) else []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        token = rec.get("key")
        if isinstance(token, str) and token.strip():
            return {
                "source": "grok_home_auth_json",
                "token": token.strip(),
                "expires_at": rec.get("expires_at"),
                "fingerprint": credential_fingerprint(token.strip()),
                "auth_path": str(auth_path),
            }
    return None


def sealed_validation_path() -> str:
    return os.environ.get("IPFS_ACCELERATE_AGENT_VALIDATION_PATH") or os.environ.get("PATH") or ""


def which_on(name: str, path: str | None = None) -> str | None:
    path = path or os.environ.get("PATH") or ""
    for folder in path.split(os.pathsep):
        if not folder:
            continue
        candidate = Path(folder) / name
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK) and candidate.stat().st_size > 0:
                return str(candidate)
        except OSError:
            continue
    return None


def probe_terra_high() -> dict[str, Any]:
    validation_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
    docker = which_on("docker", validation_path)
    codex = which_on("codex", validation_path)
    keys = [name for name in TERRA_ENV if os.environ.get(name)]
    reasons = []
    if not docker:
        reasons.append("docker_absent_from_authoritative_validation_PATH")
    if not codex:
        reasons.append("codex_absent_from_authoritative_validation_PATH")
    if not keys:
        reasons.append("no_codex_or_openai_key_in_process")
    reasons.append("no_independently_verified_fresh_grok_quota_exhaustion")
    reasons.append("usage_reset_does_not_authorize_terra_high")
    return {
        "admitted": False,
        "requested_provider": "openai",
        "requested_model": "gpt-5.6-terra",
        "reasoning_effort": "high",
        "transport": "existing_native_quota_guarded_Docker_Codex_fallback",
        "docker_available": bool(docker),
        "codex_available": bool(codex),
        "credential_names_present": keys,
        "reasons": reasons,
    }


def probe(root: Path | None = None) -> dict[str, Any]:
    root = repo_root(root)
    profile = load_profile(root)
    configured = (profile.get("host_handoff") or {}).get("grants", [])
    admitted = []
    for item in configured:
        checked = host_handoff_grant(root, item["task_id"], item["arm"], item["cache"], item["repetition"], item["record_kind"])
        if checked is not None:
            admitted.append(item["grant_sha256"])
    if admitted:
        return {"schema": "paper-ns-provider-probe/v1", "probed_at": utcnow(), "profile_id": profile.get("profile_id"), "production": {"admitted": True, "admission_scope": "operator_historical_development_only", "final_admitted": False, "sampling_seed_supported": False, "temperature_supported": False, "served_provider": None, "served_model": None, "served_revision": None, "revision_availability_reason": "Exact development grant available; served identity is established only by its signed result.", "grant_sha256": admitted}, "development": {"admitted": True, "admitted_production": False, "transport": "signed_operator_host_handoff", "credential_present_in_client": False}, "isolation": {"client_loads_hidden_oracle": False, "client_loads_provider_credential": False}}
    amendment = load_amendment(root)
    terra = probe_terra_high()
    cred = load_runtime_credential()
    permitted = amendment["permitted_development_profile"]
    development_ready = bool(cred) and permitted.get("requested_model") == DEFAULT_MODEL
    return {
        "schema": "paper-ns-provider-probe/v1",
        "probed_at": utcnow(),
        "profile_id": profile.get("profile_id"),
        "amendment_id": amendment.get("amendment_id"),
        "amendment_sha256": sha256_file(root / AMENDMENT_REL),
        "profile_sha256": sha256_file(root / PROFILE_REL),
        "production": {
            "admitted": False,
            "served_provider": None,
            "served_model": None,
            "served_revision": None,
            "revision_availability_reason": (
                "Production Terra HIGH is not admitted. "
                + "; ".join(terra["reasons"])
                + ". Development amendment "
                + str(amendment.get("amendment_id"))
                + " does not grant production."
            ),
            "terra": terra,
        },
        "development": {
            "admitted": development_ready,
            "admitted_production": False,
            "simulated": False,
            "requested_provider": permitted.get("provider"),
            "requested_model": permitted.get("requested_model"),
            "transport": permitted.get("transport"),
            "reasoning_effort": permitted.get("reasoning_effort"),
            "credential_present": bool(cred),
            "credential_source": None if not cred else cred.get("source"),
            "credential_fingerprint": None if not cred else cred.get("fingerprint"),
            "credential_expires_at": None if not cred else cred.get("expires_at"),
            "sampling_seed_supported": False,
            "temperature_supported": False,
            "reason": (
                None
                if development_ready
                else "No runtime XAI/GROK credential is bound to this process; development HTTPS dispatch is unavailable."
            ),
        },
        "isolation": {
            "docker_socket": False,
            "proposal_may_read_credentials": False,
            "proposal_may_read_hidden_store": False,
            "hidden_store": str(HIDDEN_STORE_REL),
        },
    }


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    out = {}
    for key, value in headers.items():
        if key.lower() in {"authorization", "x-api-key"}:
            out[key] = "Bearer <redacted>"
        else:
            out[key] = value
    return out


def build_prompt(request: Mapping[str, Any], *, allowed: list[str], files: Mapping[str, str]) -> str:
    issue = request.get("issue") or {}
    blocks = []
    for rel in sorted(files):
        blocks.append(f"--- {rel}\n{files[rel]}")
    return (
        "You are performing a single bounded one-proposal repair.\n"
        "Return ONLY a JSON object with this exact shape:\n"
        '{"files": {"<admitted-path>": "<full replacement file contents>"}}\n'
        "No markdown fences. No commentary.\n\n"
        f"Issue title: {issue.get('title') or ''}\n"
        f"Issue specification: {issue.get('specification') or issue.get('body') or ''}\n"
        f"Admitted paths you may edit: {', '.join(allowed)}\n\n"
        "Current files:\n"
        + "\n\n".join(blocks)
    )


def parse_candidate_text(text: str, *, previous: Mapping[str, str] | None = None) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    files = obj.get("files")
    if not isinstance(files, dict) or not files:
        return None
    cleaned = {str(path).replace("\\", "/").lstrip("./"): str(body) for path, body in files.items()}
    patch_bits = []
    prev = previous or {}
    for path, body in cleaned.items():
        old = prev.get(path, "")
        if old != body:
            patch_bits.append(f"--- a/{path}\n+++ b/{path}\n{body}")
    return {
        "kind": "generated_patch",
        "files": cleaned,
        "patch_text": "\n".join(patch_bits) if patch_bits else canonical_dumps(cleaned),
    }


def https_json(url: str, payload: dict[str, Any], *, token: str, timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ns-026-scientific-gateway/1",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            raw = resp.read()
            elapsed = time.perf_counter() - started
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                return {
                    "ok": False,
                    "http_status": int(getattr(resp, "status", 0) or 0),
                    "elapsed": elapsed,
                    "error": f"JSONDecodeError: {exc}",
                    "raw_preview": raw[:500].decode("utf-8", "replace"),
                    "request_headers": redact_headers(headers),
                }
            return {
                "ok": True,
                "http_status": int(getattr(resp, "status", 200) or 200),
                "elapsed": elapsed,
                "body": parsed,
                "raw_sha256": sha256_bytes(raw),
                "raw_bytes": len(raw),
                "request_headers": redact_headers(headers),
            }
    except urllib.error.HTTPError as exc:
        err = exc.read()[:2000]
        return {
            "ok": False,
            "http_status": int(exc.code),
            "elapsed": time.perf_counter() - started,
            "error": err.decode("utf-8", "replace"),
            "request_headers": redact_headers(headers),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "http_status": None,
            "elapsed": time.perf_counter() - started,
            "error": f"{type(exc).__name__}: {exc}",
            "request_headers": redact_headers(headers),
        }


# Host-owned ID-only handoff. This code holds only public verification metadata.
def _handoff_read(path: Path) -> bytes:
    import stat
    if not path.is_absolute() or path.resolve() != path:
        raise GatewayError("handoff path is not canonical", terminal="rejected")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576:
            raise GatewayError("handoff file exceeds its type/size bound", terminal="rejected")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read(1048577)
    finally:
        os.close(fd)


def host_handoff_grant(root: Path, task_id: str, arm: str, cache: str, repetition: int, record_kind: str) -> dict[str, Any] | None:
    if record_kind != "development":
        return None
    config = load_profile(root).get("host_handoff") or {}
    matches = [item for item in config.get("grants", []) if (item.get("task_id"), item.get("arm"), item.get("cache"), item.get("repetition"), item.get("record_kind")) == (task_id, arm, cache, repetition, record_kind)]
    if len(matches) > 1:
        raise GatewayError("ambiguous host grant", terminal="rejected")
    if not matches:
        return None
    binding = dict(matches[0])
    relative = Path(binding["queue_relative"])
    allowed = PAPER_REL / "qualification/production_provider/host_handoff"
    if relative.is_absolute() or ".." in relative.parts or not relative.is_relative_to(allowed):
        raise GatewayError("host handoff outside declared output scope", terminal="rejected")
    queue = root / relative
    durable = binding.get("evidence_relative")
    if durable:
        evidence = Path(durable)
        if evidence.is_absolute() or ".." in evidence.parts or not evidence.is_relative_to(PAPER_REL / "qualification/production_provider/host_receipts"):
            raise GatewayError("durable host receipt outside evidence scope", terminal="rejected")
        if (root / evidence / "response.json").exists():
            queue = root / evidence
    raw = _handoff_read(queue / "offer.json")
    if sha256_bytes(raw) != binding["offer_sha256"]:
        raise GatewayError("host offer changed", terminal="rejected")
    offer = json.loads(raw)
    request = offer["request"]
    expected_keys = {"schema", "grant_sha256", "grant_id", "request_id", "unit", "arm", "amendment_sha256"}
    if set(request) != expected_keys or request["schema"] != "operator-development-request/v1":
        raise GatewayError("host request schema differs", terminal="rejected")
    if request["unit"] != binding["unit_id"] or request["arm"] != arm or request["grant_sha256"] != binding["grant_sha256"] or request["amendment_sha256"] != binding["amendment_sha256"]:
        raise GatewayError("host request binding differs", terminal="rejected")
    if offer["profile"] != binding["profile"] or offer["source_sha256"] != binding["source_sha256"]:
        raise GatewayError("host proposal profile/source differs", terminal="rejected")
    return {"binding": binding, "offer": offer, "queue": queue}


def verify_host_response(root: Path, binding: Mapping[str, Any]) -> dict[str, Any]:
    import base64
    import subprocess
    selected = host_handoff_grant(root, binding["task_id"], binding["arm"], binding["cache"], binding["repetition"], binding["record_kind"])
    if selected is None or selected["binding"] != dict(binding):
        raise GatewayError("historical grant no longer admitted", terminal="rejected")
    offer, queue = selected["offer"], selected["queue"]
    response_raw = _handoff_read(queue / "response.json")
    response = json.loads(response_raw)
    receipt = response["receipt"]
    verifier = offer["public_verifier"]
    if set(verifier) != {"algorithm", "encoding", "data"} or verifier["algorithm"] != "Ed25519" or verifier["encoding"] != "spki_der_base64":
        raise GatewayError("unapproved public verifier", terminal="rejected")
    key = base64.b64decode(verifier["data"], validate=True)
    if sha256_bytes(key) != offer["public_key_sha256"] or response["public_key_sha256"] != offer["public_key_sha256"]:
        raise GatewayError("public verification key changed", terminal="rejected")
    with tempfile.TemporaryDirectory(prefix="ns-public-receipt-") as directory:
        tmp = Path(directory)
        (tmp / "public.der").write_bytes(key)
        (tmp / "body.json").write_text(canonical_dumps(receipt))
        (tmp / "signature").write_bytes(base64.b64decode(response["signature"], validate=True))
        checked = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-keyform", "DER", "-rawin", "-inkey", str(tmp / "public.der"), "-in", str(tmp / "body.json"), "-sigfile", str(tmp / "signature")], capture_output=True, timeout=15)
        if checked.returncode:
            raise GatewayError("host receipt signature invalid", terminal="rejected")
    request = offer["request"]
    if receipt.get("schema") != "operator-development-receipt/v1" or any(receipt.get(key) != request[key] for key in ("grant_id", "grant_sha256", "unit", "arm", "amendment_sha256")):
        raise GatewayError("receipt belongs to another request", terminal="rejected")
    if receipt.get("request_sha256") != sha256_text(canonical_dumps(request)) or receipt.get("profile") != offer["profile"] or receipt.get("source_sha256") != offer["source_sha256"] or receipt.get("manifest_sha256") != binding["manifest_sha256"]:
        raise GatewayError("receipt source/profile/request binding failed", terminal="rejected")
    if receipt.get("final_scientific_run") is not False or receipt.get("historical_population_admitted") is not False:
        raise GatewayError("development grant attempted final-population admission", terminal="rejected")
    if receipt.get("inert_qualification") is True and not binding.get("synthetic_qualification_only"):
        raise GatewayError("inert fixture cannot satisfy actual historical development", terminal="rejected")
    return {"receipt": receipt, "response_sha256": sha256_bytes(response_raw), "binding": dict(binding), "signature_and_scope_verified": True}


def dispatch_host_handoff(request: Mapping[str, Any], root: Path) -> dict[str, Any]:
    selected = host_handoff_grant(root, str(request["task_id"]), str(request["arm"]), str(request.get("cache", "local_cold")), int(request.get("repetition", 0)), str(request.get("record_kind", "development")))
    if selected is None:
        raise GatewayError("no exact operator historical-development grant for this unit/arm/schedule", terminal="unavailable")
    queue, offer = selected["queue"], selected["offer"]
    expected = canonical_dumps(offer["request"]).encode()
    path = queue / "request.json"
    if (queue / "response.json").exists():
        pass  # Immutable completed evidence requires no queue write.
    elif path.exists():
        if _handoff_read(path) != expected:
            raise GatewayError("different host request already exists", terminal="rejected")
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(expected); stream.flush(); os.fsync(fd)
        finally:
            os.close(fd)
        fd = os.open(queue, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    if not (queue / "response.json").exists():
        return {"schema": "paper-ns-host-handoff-pending/v1", "status": "pending_operator", "grant_binding": selected["binding"], "provider_dispatched_by_client": False, "reason": "Exact request submitted; operator must execute the already-reviewed host grant. Resume the same command after its signed response arrives."}
    verified = verify_host_response(root, selected["binding"])
    receipt = verified["receipt"]
    qualified = receipt.get("historical_development_unit_admitted") is True and receipt.get("served_profile_admitted") is True and receipt.get("error") is None and receipt.get("status") == "completed" and receipt.get("operator_review_kind") == "ai_operator" and receipt.get("trust_scope") == "specific_reviewed_development_candidate_only" and receipt.get("automatic_adversarial_scorer_integrity_qualified") is False and receipt.get("production_final_admitted") is False and receipt.get("operator_review_sha256") and receipt.get("scorer", {}).get("schema") == "ns-historical-cold-host-result/v1"
    return {"schema": "paper-ns-host-historical-development/v1", "status": "completed", "admitted_historical_development": qualified, "admitted_production": False, "admitted_final": False, "dispatched": receipt.get("provider_dispatch_may_have_occurred") is True, "dispatch_confirmed": receipt.get("provider_invoked") is True, "served_provider": "grok", "served_model": (receipt.get("provider_stream_metadata", {}).get("served_models") or [None])[0], "served_revision": None, "possibly_charged": receipt.get("unknown_external_charge") is True, "proposal_effect_count": 1 if receipt.get("provider_dispatch_may_have_occurred") else 0, "host_verified": verified}



def host_oracle(verified: Mapping[str, Any]) -> dict[str, Any]:
    """Interpret scalar signed host evidence; no tests, source or oracle loading."""
    receipt = verified["receipt"]
    scorer = receipt.get("scorer") or {}
    binding = receipt.get("operator_review_binding") or {}
    if not verified.get("signature_and_scope_verified") or receipt.get("status") != "completed" or receipt.get("error") is not None or receipt.get("operator_review_kind") != "ai_operator" or receipt.get("trust_scope") != "specific_reviewed_development_candidate_only" or receipt.get("automatic_adversarial_scorer_integrity_qualified") is not False or receipt.get("production_final_admitted") is not False:
        raise GatewayError("reviewed host scoring evidence incomplete", terminal="unavailable")
    if not receipt.get("operator_review_sha256") or binding.get("grant_sha256") != receipt["grant_sha256"] or binding.get("candidate_sha256") != receipt["candidate_sha256"] or binding.get("source_sha256") != receipt["source_sha256"]:
        raise GatewayError("operator candidate review binding differs", terminal="rejected")
    if scorer.get("schema") != "ns-historical-cold-host-result/v1" or scorer.get("candidate_sha256") != receipt.get("candidate_sha256") or scorer.get("manifest_sha256") != receipt.get("manifest_sha256") or scorer.get("unit_id") != receipt.get("unit") or scorer.get("split") != "development":
        raise GatewayError("signed cold scorer scope differs", terminal="rejected")
    details = scorer.get("scorer") or {}
    passed = scorer.get("success") is True and details.get("success") is True and scorer.get("container_exit_code") == 0 and scorer.get("timed_out") is False
    completed = isinstance(details.get("visible_collected"), int) and details["visible_collected"] > 0 and isinstance(details.get("hidden_collected"), int) and details["hidden_collected"] > 0
    return {"status": "passed" if passed and completed else "failed" if completed else "unavailable", "independent_scorer_id": "operator-cold-scorer-reviewed-development", "receipt_id": "sha256:" + verified["response_sha256"], "cold_full_validation": completed, "candidate_valid": passed if completed else None, "hidden_access_incident": False, "reason": "Signed cold score of the exact AI-operator-reviewed development candidate; adversarial observation integrity and final admission remain unqualified.", "operator_review_sha256": receipt["operator_review_sha256"], "trust_scope": receipt["trust_scope"], "automatic_adversarial_scorer_integrity_qualified": False, "human_annotation": False, "visible_collected": details.get("visible_collected"), "visible_passed": details.get("visible_passed"), "hidden_collected": details.get("hidden_collected"), "hidden_passed": details.get("hidden_passed")}


def dispatch(request: Mapping[str, Any], *, root: Path | None = None, timeout: float | None = None) -> dict[str, Any]:
    root = repo_root(root)
    path_class = str(request.get("path_class") or "development")
    if path_class == "production" and request.get("record_kind") == "development":
        return dispatch_host_handoff(request, root)
    amendment = load_amendment(root)
    permitted = amendment["permitted_development_profile"]
    probe_info = probe(root)
    if path_class == "production":
        production = probe_info["production"]
        return {
            "ok": False,
            "path_class": "production",
            "admitted_production": False,
            "simulated": False,
            "dispatched": False,
            "dispatch_confirmed": False,
            "served_provider": None,
            "served_model": None,
            "served_revision": None,
            "revision_availability_reason": production["revision_availability_reason"],
            "reasoning_effort": None,
            "runtime_receipt_id": None,
            "usage_receipt_id": None,
            "usage": None,
            "possibly_charged": False,
            "sampling_seed_supported": False,
            "temperature_supported": False,
            "proposal_effect_count": 0,
            "provider_cache_observed": None,
            "candidate": None,
            "terminal": "unavailable",
            "reason": production["revision_availability_reason"],
            "http_status": None,
            "stage_failure": "provider",
        }
    if path_class != "development":
        raise GatewayError(f"gateway refuses path_class={path_class}")
    if not probe_info["development"]["admitted"]:
        return {
            "ok": False,
            "path_class": "development",
            "admitted_production": False,
            "simulated": False,
            "dispatched": False,
            "dispatch_confirmed": False,
            "served_provider": None,
            "served_model": None,
            "served_revision": None,
            "revision_availability_reason": probe_info["development"]["reason"],
            "reasoning_effort": permitted.get("reasoning_effort"),
            "runtime_receipt_id": None,
            "usage_receipt_id": None,
            "usage": None,
            "possibly_charged": False,
            "sampling_seed_supported": False,
            "temperature_supported": False,
            "proposal_effect_count": 0,
            "provider_cache_observed": None,
            "candidate": None,
            "terminal": "unavailable",
            "reason": probe_info["development"]["reason"],
            "http_status": None,
            "stage_failure": "provider",
        }
    cred = load_runtime_credential()
    if cred is None:
        raise GatewayError("credential vanished between probe and dispatch")
    files = dict(request.get("files") or {})
    allowed = list(request.get("allowed_paths") or sorted(files))
    prompt = build_prompt(request, allowed=allowed, files=files)
    endpoint = str(permitted.get("transport") or DEFAULT_ENDPOINT)
    model = str(permitted.get("requested_model") or DEFAULT_MODEL)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": int(permitted.get("max_tokens") or 1024),
    }
    effort = permitted.get("reasoning_effort")
    if effort:
        payload["reasoning_effort"] = effort
    wall = float(timeout if timeout is not None else 180)
    http = https_json(endpoint, payload, token=cred["token"], timeout=wall)
    possibly_charged = http.get("http_status") is not None
    body = http.get("body") if http.get("ok") else None
    served_model = None
    served_revision = None
    usage = None
    content = ""
    runtime_id = None
    if isinstance(body, dict):
        served_model = body.get("model")
        served_revision = body.get("system_fingerprint")
        runtime_id = body.get("id")
        usage = body.get("usage")
        choices = body.get("choices") or []
        if choices and isinstance(choices[0], dict):
            content = str(((choices[0].get("message") or {}).get("content")) or "")
    candidate = parse_candidate_text(content, previous=files) if content else None
    usage_receipt = None
    if usage is not None:
        usage_receipt = "sha256:" + sha256_text(canonical_dumps(usage))
    runtime_receipt = None
    if runtime_id:
        runtime_receipt = str(runtime_id)
    elif http.get("raw_sha256"):
        runtime_receipt = "sha256:" + str(http["raw_sha256"])
    cached = None
    if isinstance(usage, dict):
        details = usage.get("prompt_tokens_details") or {}
        cached_tokens = details.get("cached_tokens")
        if cached_tokens:
            cached = "cached_tokens"
    ok = bool(http.get("ok") and candidate)
    reason = None
    terminal = "unsolved"
    stage_failure = None
    if not http.get("ok"):
        reason = f"provider HTTP failure: status={http.get('http_status')} {http.get('error')}"
        terminal = "unavailable"
        stage_failure = "provider"
    elif candidate is None:
        reason = "provider returned no parseable candidate JSON"
        terminal = "abstained"
        stage_failure = "provider"
    else:
        reason = "provider returned a parseable candidate"
        terminal = "unsolved"
    return {
        "ok": ok,
        "path_class": "development",
        "admitted_production": False,
        "simulated": False,
        "dispatched": True,
        "dispatch_confirmed": True,
        "served_provider": "xai",
        "served_model": served_model or model,
        "served_revision": served_revision,
        "revision_availability_reason": None if served_revision else "system_fingerprint not exposed",
        "reasoning_effort": effort,
        "runtime_receipt_id": runtime_receipt,
        "usage_receipt_id": usage_receipt,
        "usage": usage,
        "possibly_charged": bool(possibly_charged),
        "sampling_seed_supported": False,
        "temperature_supported": False,
        "proposal_effect_count": 1,
        "provider_cache_observed": cached,
        "candidate": candidate,
        "terminal": terminal,
        "reason": reason,
        "http_status": http.get("http_status"),
        "provider_wall_seconds": http.get("elapsed"),
        "stage_failure": stage_failure,
        "amendment_id": amendment.get("amendment_id"),
        "requested_model": model,
        "endpoint": endpoint,
        "credential_source": cred.get("source"),
        "credential_fingerprint": cred.get("fingerprint"),
        "raw_sha256": http.get("raw_sha256"),
        "content_preview": content[:1000],
        "prompt_sha256": sha256_text(prompt),
        "prompt_bytes": len(prompt.encode("utf-8")),
    }


def family_slug(task: Mapping[str, Any]) -> str:
    prov = task.get("provenance") or {}
    if prov.get("upstream_slug"):
        return str(prov["upstream_slug"])
    family = str(task.get("family_id") or "")
    if family.startswith("upstream:"):
        return family.split(":", 1)[1]
    snap = task.get("source_snapshot") or {}
    repo = str(snap.get("upstream_repo") or "")
    if "github.com/" in repo:
        return repo.rstrip("/").split("github.com/", 1)[1]
    raise GatewayError(f"cannot derive upstream slug for {task.get('task_id')}")


def fetch_github_tarball(slug: str, commit: str, dest: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        digest = sha256_file(dest)
        if expected_sha256 and digest != expected_sha256:
            dest.unlink()
        else:
            return {"path": dest, "sha256": digest, "bytes": dest.stat().st_size, "reused": True, "url": GITHUB_TARBALL.format(slug=slug, commit=commit)}
    url = GITHUB_TARBALL.format(slug=slug, commit=commit)
    req = urllib.request.Request(url, headers={"User-Agent": "ns-026-upstream-materialize/1"})
    with urllib.request.urlopen(req, timeout=90, context=ssl.create_default_context()) as resp:
        blob = resp.read()
    digest = sha256_bytes(blob)
    if expected_sha256 and digest != expected_sha256:
        raise GatewayError(f"tarball sha256 mismatch for {slug}@{commit}: got {digest}")
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(blob)
    os.replace(tmp, dest)
    return {"path": dest, "sha256": digest, "bytes": len(blob), "reused": False, "url": url}


def extract_tarball(archive: Path, dest: Path, *, allowed: set[str] | None = None) -> dict[str, str]:
    dest.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            parts = path.parts[1:]
            if not parts:
                continue
            if path.is_absolute() or ".." in parts:
                raise GatewayError(f"unsafe tar member {member.name}")
            if parts[0] == ".git" or ".git" in parts:
                continue
            rel = Path(*parts).as_posix()
            if allowed is not None and rel not in allowed:
                continue
            if member.issym() or member.islnk():
                continue
            if not member.isfile():
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            data = handle.read()
            target = dest / rel
            if not str(target.resolve()).startswith(str(dest.resolve())):
                raise GatewayError(f"path escapes sandbox: {rel}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            try:
                written[rel] = data.decode("utf-8")
            except UnicodeDecodeError:
                written[rel] = ""
    return written


def snapshot_recipe_path(root: Path, task_id: str) -> Path:
    return root / PROPOSAL_SNAPSHOT_REL / task_id / "snapshot_recipe.json"


def materialize_pinned_snapshot(
    task: Mapping[str, Any],
    dest: Path,
    *,
    root: Path,
    store: Path,
    mode: str = "proposal",
) -> dict[str, Any]:
    snap = task.get("source_snapshot") or {}
    commit = snap.get("pre_fix_commit")
    files = list(snap.get("files") or [])
    if not commit or not files:
        return {"ok": False, "reason": "live snapshot missing pre_fix_commit or files", "mode": mode}
    slug = family_slug(task)
    expected_archive = None
    qual = ((task.get("baseline_qualification_correction") or {}).get("qualification") or {})
    if qual.get("pre_fix_archive_sha256"):
        expected_archive = str(qual["pre_fix_archive_sha256"])
    recipe_path = snapshot_recipe_path(root, str(task.get("task_id")))
    recipe = load_json(recipe_path) if recipe_path.is_file() else None
    store.mkdir(parents=True, exist_ok=True)
    archive = store / "archives" / f"{commit}.tar.gz"
    try:
        fetched = fetch_github_tarball(slug, str(commit), archive, expected_sha256=expected_archive)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"pinned upstream fetch failed: {type(exc).__name__}: {exc}", "mode": mode}
    dest.mkdir(parents=True, exist_ok=True)
    allowed = None
    if mode == "proposal":
        allowed = {row["path"] for row in files}
        extra = snap.get("admitted_paths") or []
        allowed.update(str(p) for p in extra)
    extracted = extract_tarball(archive, dest, allowed=allowed)
    missing = []
    for row in files:
        rel = row["path"]
        expected = row["sha256"]
        path = dest / rel
        if not path.is_file():
            missing.append(f"{rel}: missing after pinned extract")
            continue
        digest = sha256_file(path)
        if digest != expected:
            missing.append(f"{rel}: sha256 mismatch (got {digest})")
    git_dir = dest / ".git"
    if git_dir.exists():
        return {"ok": False, "reason": "refusing original .git in materialized tree", "mode": mode}
    if missing:
        return {"ok": False, "reason": "; ".join(missing), "mode": mode, "archive_sha256": fetched["sha256"]}
    export = {rel: (dest / rel).read_text(encoding="utf-8") for rel in (allowed or extracted) if (dest / rel).is_file()}
    scan = scan_proposal_export(export, dest)
    return {
        "ok": True,
        "reason": None,
        "mode": mode,
        "commit": commit,
        "slug": slug,
        "archive_sha256": fetched["sha256"],
        "archive_bytes": fetched["bytes"],
        "url": fetched["url"],
        "files": sorted(export),
        "source_preimage_id": snap.get("snapshot_sha256"),
        "recipe_sha256": sha256_file(recipe_path) if recipe_path.is_file() else None,
        "recipe_kind": None if recipe is None else recipe.get("kind"),
        "isolation": scan,
        "used_caller_git": False,
    }


def scan_proposal_export(files: Mapping[str, str], root: Path | None = None) -> dict[str, Any]:
    markers: list[str] = []
    blob = "\n".join(files.values())
    names = "\n".join(files)
    haystack = (blob + "\n" + names).replace("\\", "/")
    for marker in FORBIDDEN_PROPOSAL_MARKERS:
        if marker.lower() in haystack.lower():
            markers.append(marker)
    git_present = False
    if root is not None and (root / ".git").exists():
        git_present = True
        markers.append("original-.git")
    return {
        "forbidden_markers": sorted(set(markers)),
        "git_present": git_present,
        "file_count": len(files),
        "clean": (not markers) and not git_present,
    }


def oracle_path(root: Path, task_id: str) -> Path:
    return root / HIDDEN_STORE_REL / "oracles" / task_id / "oracle.json"


def reconstruct_hidden_oracle(task_id: str, *, root: Path, store: Path) -> dict[str, Any]:
    path = oracle_path(root, task_id)
    if not path.is_file():
        return {"ok": False, "reason": f"missing scorer-only oracle for {task_id}"}
    oracle = load_json(path)
    if oracle.get("proposal_sandbox_may_read") is True:
        return {"ok": False, "reason": "oracle incorrectly marked readable by proposal"}
    slug = str(oracle.get("family_id") or "").split(":", 1)[-1]
    fix = oracle.get("fix_commit")
    if not slug or not fix:
        return {"ok": False, "reason": "oracle missing family or fix_commit"}
    archive = store / "archives" / f"{fix}.tar.gz"
    try:
        fetched = fetch_github_tarball(slug, str(fix), archive)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"fix-commit fetch failed: {type(exc).__name__}: {exc}"}
    work = Path(tempfile.mkdtemp(prefix="ns026-oracle-"))
    extracted = extract_tarball(archive, work, allowed={row["path"] for row in oracle.get("hidden_files") or []})
    hidden: dict[str, str] = {}
    missing = []
    for row in oracle.get("hidden_files") or []:
        rel = row["path"]
        expected = row["sha256"]
        if rel not in extracted:
            missing.append(f"{rel}: not in fix tree")
            continue
        digest = sha256_text(extracted[rel])
        if digest != expected:
            missing.append(f"{rel}: sha256 mismatch")
            continue
        hidden[rel] = extracted[rel]
    import shutil

    shutil.rmtree(work, ignore_errors=True)
    if missing:
        return {"ok": False, "reason": "; ".join(missing), "oracle_id": oracle.get("oracle_id")}
    return {
        "ok": True,
        "oracle": oracle,
        "hidden_files": hidden,
        "fail_to_pass": list(oracle.get("fail_to_pass") or []),
        "fix_commit": fix,
        "pre_fix_commit": oracle.get("pre_fix_commit"),
        "archive_sha256": fetched["sha256"],
        "payload_stored_in_tree": False,
        "oracle_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    probe_cmd = sub.add_parser("probe", help="fail-closed production/development probe; never dispatches")
    probe_cmd.add_argument("--repo", default=None)
    probe_cmd.add_argument("--out", default=None)
    disp = sub.add_parser("dispatch", help="dispatch one admitted development proposal")
    disp.add_argument("--repo", default=None)
    disp.add_argument("--request", required=True)
    disp.add_argument("--out", required=True)
    disp.add_argument("--timeout", type=float, default=None)
    mat = sub.add_parser("materialize", help="materialize a pinned upstream pre-fix snapshot")
    mat.add_argument("--repo", default=None)
    mat.add_argument("--task-id", required=True)
    mat.add_argument("--dest", required=True)
    mat.add_argument("--store", required=True)
    mat.add_argument("--mode", default="proposal", choices=["proposal", "full_pre_fix"])
    mat.add_argument("--out", default=None)
    return parser


def load_task_row(root: Path, task_id: str) -> dict[str, Any]:
    path = paper_dir(root) / "benchmark" / "tasks.jsonl"
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("task_id") == task_id:
                return row
    raise GatewayError(f"unknown task_id {task_id}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root(Path(args.repo).resolve() if getattr(args, "repo", None) else None)
    if args.command == "probe":
        result = probe(root)
        if args.out:
            atomic_write(Path(args.out), result)
        print(canonical_dumps(result))
        return 0
    if args.command == "dispatch":
        request = load_json(Path(args.request))
        result = dispatch(request, root=root, timeout=args.timeout)
        safe = dict(result)
        safe.pop("candidate_raw", None)
        atomic_write(Path(args.out), safe)
        print(canonical_dumps({k: safe.get(k) for k in ("ok", "served_model", "served_revision", "runtime_receipt_id", "terminal", "reason")}))
        return 0 if result.get("dispatched") else 2
    if args.command == "materialize":
        task = load_task_row(root, args.task_id)
        result = materialize_pinned_snapshot(
            task,
            Path(args.dest),
            root=root,
            store=Path(args.store),
            mode=args.mode,
        )
        if args.out:
            atomic_write(Path(args.out), result)
        print(canonical_dumps({k: result.get(k) for k in ("ok", "reason", "archive_sha256", "files")}))
        return 0 if result.get("ok") else 1
    raise GatewayError(f"unknown command {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
