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
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
KEYFILES = (
    Path.home() / ".config/ipfs_accelerate_py/mistral.env",
    Path.home() / ".config/ipfs_accelerate_py/typesafe.env",
    Path.home() / ".vibe" / ".env",
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import generate_text as lra_gt  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import typesafe_router as lra_ts  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
PR_ID = "PR-12b"
LRAH_ID = "LRAH-011b"
from jevops.catalogs import ACCEL_ROOT as ROOT_ACCEL  # noqa: E402
from jevops.catalogs import CANARY_PRIMARY as CANARY_NAME  # noqa: E402
from jevops.catalogs import TRACK_LABEL  # noqa: E402
from jevops.catalogs import LABS_RETIRE_DATE  # noqa: E402
from jevops.catalogs import PROTOCOL  # noqa: E402
from jevops.catalogs import MISTRAL_ALT_MODELS as ALT_MODELS  # noqa: E402
from jevops.catalogs import MISTRAL_API_HOST as API_HOST  # noqa: E402
from jevops.catalogs import MISTRAL_CHAT_URL as CHAT_URL  # noqa: E402
from jevops.catalogs import MISTRAL_FORBIDDEN_HOSTS as FORBIDDEN_HOSTS  # noqa: E402
from jevops.catalogs import MISTRAL_FORBIDDEN_PROVIDERS as FORBIDDEN_PROVIDERS  # noqa: E402
from jevops.catalogs import MISTRAL_HARDWARE_CLASS as HARDWARE_CLASS  # noqa: E402
from jevops.catalogs import MISTRAL_KEY_ENV_NAMES as KEY_ENV_NAMES  # noqa: E402
from jevops.catalogs import MISTRAL_MAX_NEW_TOKENS as MAX_NEW_TOKENS_DEFAULT  # noqa: E402
from jevops.catalogs import MISTRAL_MODEL as REQUESTED_MODEL  # noqa: E402
from jevops.catalogs import MISTRAL_PROVIDER as REQUESTED_PROVIDER  # noqa: E402
from jevops.catalogs import MISTRAL_TIMEOUT_SECONDS as TIMEOUT_DEFAULT  # noqa: E402
from jevops.catalogs import PROTOTYPE_BASE_URL  # noqa: E402
from jevops.catalogs import PROTOTYPE_HARDWARE_CLASS  # noqa: E402
FORBIDDEN_IMPORT_NAMES = frozenset({"fcntl", "typesafe_sdk", "LeanstralProofProvider"})


class Track1MistralError(RuntimeError):
    """Fail-closed hosted Leanstral error. Never a local GGUF success."""


def load_keyfiles() -> None:
    from jevops.outer import load_env_file

    for path in KEYFILES:
        load_env_file(path, strip_quotes=True)


def pin_paths() -> None:
    from jevops.outer import pin_sys_path

    pin_sys_path(
        ROOT_ACCEL,
        defaults={
            "IPFS_ACCEL_SKIP_CORE": "1",
            "IPFS_AUTO_INSTALL": "false",
            "IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0",
        },
    )
    lra_ts.ACCEL_ROOT = ROOT_ACCEL
    lra_ts.TYPESAFE_INFERENCE_PATH = ROOT_ACCEL / "ipfs_accelerate_py" / "typesafe_inference.py"


def mistral_key_configured(env: Optional[Mapping[str, str]] = None) -> bool:
    from jevops.jev import any_key

    from jevops.outer import env_mapping

    return any_key(env_mapping(env), KEY_ENV_NAMES)


def resolve_mistral_key(env: Optional[Mapping[str, str]] = None) -> str:
    from jevops.outer import env_mapping, first_nonempty, raise_if

    value = first_nonempty(env_mapping(env), *KEY_ENV_NAMES)
    raise_if(not value, Track1MistralError, "MISTRAL_API_KEY is not set")
    return value


def _redact_text(text: str, secret: str) -> str:
    from jevops.outer import redact_secret

    return redact_secret(text, secret)


def assert_hosted_url(url: str) -> None:
    from jevops.outer import require_host

    require_host(
        url,
        API_HOST,
        forbidden=FORBIDDEN_HOSTS,
        error_cls=Track1MistralError,
        prototype_fmt="refusing prototype host {host!r}; Track 1 must use {expected}",
        mismatch_fmt="refusing non-Labs host {host!r}; expected {expected}",
    )


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
    from jevops.outer import chat_request_payload, elapsed_ms, http_json, pack_chat_response

    payload = chat_request_payload(
        prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        n=n,
        stop=stop,
    )
    started = time.perf_counter()
    status, data, final_url = http_json(
        url,
        payload,
        timeout=float(timeout),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        error_cls=Track1MistralError,
        redact_fn=lambda message: _redact_text(message, key),
        http_fmt="Mistral HTTP {status}: {body}",
        json_fmt="Mistral returned invalid JSON: {exc}",
        not_object="Mistral returned a non-object JSON payload",
    )
    from jevops.outer import first_truthy

    resolved = first_truthy(final_url, url)
    assert_hosted_url(resolved)
    return pack_chat_response(
        data,
        status=status,
        url=resolved,
        wall_ms=elapsed_ms(started),
        model=model,
        extra={
            "hardware_class": HARDWARE_CLASS,
            "prototype_base_url": PROTOTYPE_BASE_URL,
            "used_prototype_endpoint": False,
        },
    )


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
    from jevops.outer import ledger_generate

    estimated_in = lra_t1.estimate_tokens(prompt)
    from jevops.outer import first_int

    estimated_out = first_int(max_new_tokens)

    def _identity(*, model: str, fixture: bool, extra: Optional[Mapping[str, Any]] = None, text: str = "") -> dict[str, Any]:
        del text
        from jevops.lean import hosted_identity

        return hosted_identity(
            requested_provider=REQUESTED_PROVIDER,
            requested_model=model,
            fixture=fixture,
            extra=extra,
            api_host=API_HOST,
            hardware_class=HARDWARE_CLASS,
            error_cls=Track1MistralError,
            host_fmt="resolved host is not {host}",
        )

    def _live() -> tuple[str, Mapping[str, Any], tuple[int, int]]:
        payload = chat_completions(
            prompt,
            model=model,
            max_tokens=max_new_tokens,
            timeout=timeout,
        )
        from jevops.outer import first_int, get_str

        inn = first_int(payload.get("input_tokens"), estimated_in)
        out = first_int(payload.get("output_tokens"), lra_t1.estimate_tokens(get_str(payload, "text")))
        return get_str(payload, "text"), payload, (inn, out)

    return ledger_generate(
        ledger,
        "mistral",
        estimated_in=estimated_in,
        estimated_out=estimated_out,
        model=model,
        fixture=fixture,
        fixture_text=fixture_text,
        live_fn=_live,
        identity_fn=_identity,
        error_cls=Track1MistralError,
        estimate_fn=lra_t1.estimate_tokens,
        refuse_fmt="mistral call refused: {reason}",
        after_fmt="mistral spend refused after call: {reason}",
    )


def redact(payload: Any) -> Any:
    from jevops.jev import redact as _fn

    return _fn(payload, exact=("authorization", "bearer"), prefixes=("apikey_", "sk-"))


def run_named(
    name: str,
    *,
    max_new_tokens: int = MAX_NEW_TOKENS_DEFAULT,
    timeout: float = TIMEOUT_DEFAULT,
    official_track2: bool = False,
    fixture: bool = False,
    path: Optional[Path] = None,
) -> dict[str, Any]:
    from jevops.outer import env_copy

    pin_paths()
    from jevops.outer import closed_skip, first_call, first_truthy

    early = first_call(
        (
            first_truthy(official_track2, lra_ts.official_track2_requested()),
            lambda: closed_skip(
                "official_track2_off",
                extra={"called_jev": False, "contaminates_track2": False},
            ),
        ),
        (
            not fixture and not (mistral_key_configured() and lra_t1.jev_key_configured()),
            lambda: closed_skip(
                "no_key",
                extra={
                    "name": name,
                    "mistral_key_configured": mistral_key_configured(),
                    "jev_key_configured": lra_t1.jev_key_configured(),
                },
            ),
        ),
    )
    from jevops.outer import first_not_none

    def _run() -> dict[str, Any]:
        record, records, digest = lra_t1._load_named_record(name, path)
        ledger = lra_t1.ProblemLedger(name=name, official_track2=False)
        from jevops.outer import begin_named_route, fixture_factory, get_str

        neighbors, state, router = begin_named_route(
            record,
            records,
            neighbor_fn=lra_t1._neighbors_for,
            state_fn=lra_ts.problem_state,
            fixture=fixture,
            factory_fn=lambda: fixture_factory(lra_ts.FixtureClient, lra_ts.default_fixture_answers),
            router_cls=lra_ts.TypeSafeLraRouter,
            mode="inloop",
            official_track2=False,
            env=env_copy({"LRA_TYPESAFE": "inloop"}),
            require_key=not fixture,
        )
        from jevops.outer import elapsed_ms, names_of, record_route_usage

        started = time.perf_counter()
        jev_result = router.route(state, neighbor_names=names_of(neighbors))
        record_route_usage(
            ledger,
            jev_result,
            fixture=fixture,
            model=lra_t1.JEV_MODEL_ID,
        )
        prompt = lra_gt.render_prompt(record)
        text, identity, _line = generate_mistral(
            prompt,
            ledger,
            max_new_tokens=max_new_tokens,
            timeout=timeout,
            fixture=fixture,
        )
        from jevops.jev import hosted_run_payload

        return redact(
            hosted_run_payload(
                name=name,
                source=get_str(record, "source"),
                digest=digest,
                identity=identity,
                text=text,
                jev_route=jev_result.as_dict(),
                ledger=ledger.as_dict(),
                wall_ms=elapsed_ms(started),
                requested_provider=REQUESTED_PROVIDER,
                requested_model=REQUESTED_MODEL,
                hardware_class=HARDWARE_CLASS,
                prototype_hardware=PROTOTYPE_HARDWARE_CLASS,
                protocol=PROTOCOL,
                pr=PR_ID,
                track=TRACK_LABEL,
                labs_retire_date=LABS_RETIRE_DATE,
            )
        )

    return first_not_none(early, factory=_run)


def audit_source() -> dict[str, Any]:
    from jevops.outer import read_text
    from jevops.repair import audit_source as _audit

    text = read_text(__file__)
    out = _audit(text, forbidden_imports=FORBIDDEN_IMPORT_NAMES)
    imported = set(out["imported_names"])
    from jevops.repair import pack_call_audit

    return pack_call_audit(
        out,
        extra={
            "uses_lock_ex": out["uses_lock_ex"],
            "mentions_prototype_url": PROTOTYPE_BASE_URL in text,
        },
        extra_ok=(not out["uses_lock_ex"], "typesafe_sdk" not in imported),
    )


def self_check() -> dict[str, Any]:
    audit = audit_source()
    ledger = lra_t1.ProblemLedger(name="fixture")
    text, identity, line = generate_mistral("ping", ledger, fixture=True, fixture_text="simp")
    from jevops.outer import closed_on_error, finalize_ok

    refused = closed_on_error(
        lambda: assert_hosted_url("http://172.17.0.1:8080/v1/chat/completions"),
        Track1MistralError,
    )
    mistral_mode = lra_t1.resolve_track1_mode(env={"LRA_GENERATOR": "mistral_labs"})
    track2 = lra_t1.resolve_track1_mode(
        env={"LRA_GENERATOR": "mistral_labs", "LRA_OFFICIAL_TRACK2": "1"}
    )
    zero = lra_t1.usd_for("mistral", 1_000_000, 1_000_000)
    return finalize_ok(
        {
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
        },
        audit["ok"],
        refused,
        mistral_mode == "track1",
        track2 == "off",
        float(zero) == 0.0,
        text == "simp",
        identity.get("used_prototype_endpoint") is False,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--probe", action="store_true", help="tiny hosted ping; no warmup compile")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--name", default=CANARY_NAME)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.self_check or not (args.probe or args.live):
        report = self_check()
        from jevops.outer import print_ok

        return print_ok(report)
    load_keyfiles()
    pin_paths()
    if args.probe:
        ping = chat_completions(
            "Return exactly the token rfl and nothing else.",
            max_tokens=8,
            timeout=60.0,
        )
        from jevops.outer import get_str, head_chars

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
                "text_head": head_chars(get_str(ping, "text"), 120),
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
    from jevops.outer import write_json_pair

    latest = write_json_pair(
        args.out,
        report,
        prefix="track1-mistral",
        latest="track1-mistral-latest.json",
        refuse=("apikey_", "sk-"),
        refuse_msg="refusing to write a receipt that looks like it contains a secret",
    )
    from jevops.outer import nested_get, print_json, text_or

    print_json({"ok": report.get("ok"), "latest": text_or(latest), "skipped": report.get("skipped"), "reason": report.get("reason"), "host": nested_get(report, "identity", "url_host"), "model": nested_get(report, "identity", "resolved_model"), "used_prototype": report.get("used_prototype_endpoint"), "arena_score": None})
    from jevops.outer import exit_ok

    return exit_ok(report.get("ok"))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
