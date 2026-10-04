#!/usr/bin/env python3
"""Thin fail-closed Leanstral generate_text client for Lean Refactor Arena.

HTTP client of the live docker0 owner at 172.17.0.1:8080. Probe /health, then
call ipfs_accelerate_py.llm_router.generate_text with fail-closed kwargs.
Never flocks the owner GPU lock. Never starts llama-server. Does not compile.
Does not claim Arena scores. Does not import LeanstralProofProvider.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
PROMPT_PATH = HERE / "lra_prompt.txt"
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "fcntl",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
    }
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
from jevops.catalogs import ALLOWED_LEANSTRAL_PROVIDERS as ALLOWED_RESOLVED_PROVIDERS  # noqa: E402
from jevops.catalogs import FROZEN_WARMUP_SHA256  # noqa: E402
from jevops.catalogs import LEANSTRAL_LOCAL_MODEL as REQUESTED_MODEL  # noqa: E402
from jevops.catalogs import LEANSTRAL_LOCAL_PROVIDER as REQUESTED_PROVIDER  # noqa: E402
from jevops.catalogs import DEFAULT_MAX_NEW_TOKENS  # noqa: E402
from jevops.catalogs import DEFAULT_TIMEOUT_SECONDS  # noqa: E402
from jevops.catalogs import DOCKER0_HEALTH_ALIAS_URL  # noqa: E402
from jevops.catalogs import DOCKER0_HEALTH_URL  # noqa: E402
from jevops.catalogs import DOCKER0_HOST  # noqa: E402
from jevops.catalogs import DOCKER0_OPENAI_BASE_URL  # noqa: E402
from jevops.catalogs import DOCKER0_PORT  # noqa: E402
from jevops.catalogs import FAIL_CLOSED_LEANSTRAL_KWARGS as FAIL_CLOSED_KWARGS  # noqa: E402
from jevops.catalogs import FORBIDDEN_LEANSTRAL_FALLBACKS as FORBIDDEN_FALLBACK_PROVIDERS  # noqa: E402
from jevops.catalogs import HEALTH_TIMEOUT_SECONDS  # noqa: E402
from jevops.catalogs import PUTNAM_MAX_NEW_TOKENS  # noqa: E402
from jevops.catalogs import PUTNAM_TIMEOUT_SECONDS  # noqa: E402
from jevops.catalogs import UNREACHABLE_DOCKER0_OPENAI_BASE_URL  # noqa: E402

_GENERATE_LOCK = threading.Lock()
_CLIENT_ENV_PINNED = False


class LraGenerateError(RuntimeError):
    """Fail-closed Leanstral generation failure. Never a fallback success."""


class Docker0Unreachable(LraGenerateError):
    """docker0 Leanstral is not reachable; generation must not complete via Grok/HF."""


from jevops.lean import Generation as LraGeneration
from jevops.lean import HealthProbe
from jevops.lean import ProviderIdentity


def _pin_client_env(*, base_url: Optional[str] = None) -> str:
    """Bind llama.cpp to docker0 as a client. Never enable autostart."""

    from jevops.outer import drive_pin_docker0_client, drive_then_mark

    def _mark() -> None:
        global _CLIENT_ENV_PINNED
        _CLIENT_ENV_PINNED = True

    return drive_then_mark(
        lambda: drive_pin_docker0_client(
            base_url=base_url,
            default_url=DOCKER0_OPENAI_BASE_URL,
            host=DOCKER0_HOST,
            port=DOCKER0_PORT,
        ),
        _mark,
    )


def _ensure_accel_path() -> None:
    from jevops.outer import ensure_sys_path

    ensure_sys_path(ACCEL_ROOT)


def _http_get(url: str, *, timeout: float) -> tuple[Optional[int], str]:
    from jevops.outer import http_get

    return http_get(url, timeout=timeout)


def probe_docker0_health(*, timeout: float = HEALTH_TIMEOUT_SECONDS) -> HealthProbe:
    """GET docker0 /health, then the loopback alias. Does not start a server."""

    from jevops.lean import drive_health_probe

    return drive_health_probe(
        pin_fn=_pin_client_env,
        get_fn=_http_get,
        health_url=DOCKER0_HEALTH_URL,
        alias_url=DOCKER0_HEALTH_ALIAS_URL,
        timeout=timeout,
        probe_cls=HealthProbe,
    )


def token_limits_for_source(source: str) -> tuple[int, int]:
    from jevops.outer import drive_token_limits

    return drive_token_limits(
        source,
        {"putnambench": (PUTNAM_MAX_NEW_TOKENS, PUTNAM_TIMEOUT_SECONDS)},
        (DEFAULT_MAX_NEW_TOKENS, DEFAULT_TIMEOUT_SECONDS),
    )


def render_prompt(
    record: Optional[Mapping[str, Any]] = None,
    **fields: Any,
) -> str:
    """Fill the LRA prompt. Returns a tactic-block-only instruction, not PROOF_PROMPT."""

    from jevops.outer import drive_fill_prompt

    return drive_fill_prompt(
        PROMPT_PATH,
        record,
        fields,
        blanks={"name": "", "source": "", "header": "", "statement": "", "src": ""},
    )


def _load_router():
    from jevops.llm_router import load_accelerate_router

    return load_accelerate_router(setup=(_ensure_accel_path,))


def _identity_from_trace(
    trace: Mapping[str, Any],
    *,
    generated: bool,
) -> ProviderIdentity:
    from jevops.lean import identity_from_trace as _fn

    return _fn(
        trace,
        generated=generated,
        requested_provider=REQUESTED_PROVIDER,
        requested_model=REQUESTED_MODEL,
        allowed=ALLOWED_RESOLVED_PROVIDERS,
        forbidden=FORBIDDEN_FALLBACK_PROVIDERS,
        identity_cls=ProviderIdentity,
    )


def generate_text(
    prompt: str,
    *,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    source: str = "",
    require_health: bool = True,
    generate: Optional[Callable[..., str]] = None,
    get_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
    base_url: Optional[str] = None,
) -> str:
    """Generate a tactic block via docker0 Leanstral. Fail closed; no Grok/HF fallback."""

    return generate_lra(
        prompt,
        max_new_tokens=max_new_tokens,
        timeout=timeout,
        source=source,
        require_health=require_health,
        generate=generate,
        get_trace=get_trace,
        base_url=base_url,
    ).text


def generate_lra(
    prompt: str,
    *,
    max_new_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    source: str = "",
    require_health: bool = True,
    generate: Optional[Callable[..., str]] = None,
    get_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
    stop: Optional[list[str]] = None,
) -> LraGeneration:
    """Probe docker0, then call the router with fail-closed kwargs. Record resolved identity."""

    from jevops.catalogs import DOCKER0_UNREACHABLE_FMT, LEANSTRAL_RERAISE_FMT
    from jevops.lean import drive_docker0_generate

    return drive_docker0_generate(
        prompt,
        max_new_tokens=max_new_tokens,
        timeout=timeout,
        source=source,
        require_health=require_health,
        generate=generate,
        get_trace=get_trace,
        base_url=base_url,
        temperature=temperature,
        stop=stop,
        lock=_GENERATE_LOCK,
        lookup_fn=token_limits_for_source,
        default_new=DEFAULT_MAX_NEW_TOKENS,
        default_timeout=DEFAULT_TIMEOUT_SECONDS,
        pin_fn=_pin_client_env,
        probe_fn=probe_docker0_health,
        health_cls=HealthProbe,
        health_url=DOCKER0_HEALTH_URL,
        alias_url=DOCKER0_HEALTH_ALIAS_URL,
        autostart_key="IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART",
        requested_provider=REQUESTED_PROVIDER,
        requested_model=REQUESTED_MODEL,
        identity_cls=ProviderIdentity,
        unreachable_fmt=DOCKER0_UNREACHABLE_FMT,
        reraise_fmt=LEANSTRAL_RERAISE_FMT,
        openai_base=DOCKER0_OPENAI_BASE_URL,
        base_env_key="IPFS_ACCELERATE_LLAMA_CPP_BASE_URL",
        fail_closed=FAIL_CLOSED_KWARGS,
        load_router_fn=_load_router,
        identity_from_trace_fn=_identity_from_trace,
        generation_cls=LraGeneration,
        generate_cls=LraGenerateError,
        unreachable_cls=Docker0Unreachable,
    )


def _fail_closed_kwargs_from_source(source: str) -> dict[str, Any]:
    from jevops.repair import catalog_literal

    return catalog_literal(
        "FAIL_CLOSED_LEANSTRAL_KWARGS",
        error_cls=LraGenerateError,
        miss="FAIL_CLOSED_KWARGS assignment not found",
        not_dict="FAIL_CLOSED_KWARGS must be a dict",
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _prompt_contract(prompt_text: str) -> dict[str, bool]:
    from jevops.outer import contains_flags

    return contains_flags(
        prompt_text,
        {
            "tactic_block_only": "only the tactic block",
            "no_repeat_statement": "do not repeat the theorem",
            "no_imports": "do not add imports",
            "no_axioms": "do not invent axioms",
            "aesop_allowed": "aesop",
            "nlinarith_allowed": "nlinarith",
            "forbids_theorem_lemma_import_open": ("theorem", "lemma", "import", "open"),
            "not_proof_prompt": {"absent": ("prove the fixed theorem",)},
        },
    )


def self_check() -> dict[str, Any]:
    """Exercise fail-closed kwargs, health probe, and unreachable docker0. No compile."""

    from jevops.outer import env_str, read_text, relative_or_str, text_or

    source = read_text(__file__)
    prompt_text = read_text(PROMPT_PATH)
    kwargs = _fail_closed_kwargs_from_source(source)
    expected = {
        "provider": "leanstral_local",
        "model_name": "Leanstral",
        "temperature": 0.0,
        "allow_local_fallback": False,
        "allow_cross_provider_fallback": False,
        "disable_model_retry": True,
    }
    imported = _imported_names(source)
    forbidden_imports = sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES)
    uses_fcntl = "fcntl" in imported
    from jevops.repair import uses_attr

    uses_lock_ex = uses_attr(source, "LOCK_EX")
    prompt_ok = _prompt_contract(prompt_text)
    health = probe_docker0_health()

    captured: dict[str, Any] = {}

    def fake_generate(prompt: str, **call_kwargs: Any) -> str:
        captured["prompt"] = prompt
        captured["kwargs"] = dict(call_kwargs)
        return "simp"

    def fake_trace() -> dict[str, str]:
        return {
            "effective_provider_name": "leanstral_local",
            "effective_model_name": "Leanstral",
        }

    mock_generation = generate_lra(
        "simp the goal",
        require_health=False,
        generate=fake_generate,
        get_trace=fake_trace,
    )
    from jevops.outer import kwargs_match_all, overlay_map

    mock_kwargs = overlay_map(captured.get("kwargs"))

    mock_kwargs_ok = kwargs_match_all([{"kwargs": mock_kwargs}], expected)

    unreachable_error = ""
    unreachable_fallback = False
    unreachable_resolved = {"requested_provider": REQUESTED_PROVIDER, "requested_model": REQUESTED_MODEL}
    from jevops.outer import exc_name, exc_text

    try:
        generate_lra(
            "unreachable docker0 must fail closed",
            require_health=False,
            base_url=UNREACHABLE_DOCKER0_OPENAI_BASE_URL,
        )
        unreachable_fallback = True
        unreachable_error = "generate_text returned success against unreachable docker0"
    except Docker0Unreachable as exc:
        unreachable_error = text_or(exc)
        lowered = unreachable_error.lower()
        unreachable_fallback = any(name in lowered for name in ("grok", "huggingface", "hf_inference"))
        unreachable_resolved["error_type"] = exc_name(exc)
        unreachable_resolved["resolved_provider"] = ""
        unreachable_resolved["resolved_model"] = ""
    except Exception as exc:  # noqa: BLE001 — self-check must classify unexpected success paths
        unreachable_error = exc_text(exc)
        lowered = unreachable_error.lower()
        unreachable_fallback = any(
            name in lowered for name in FORBIDDEN_FALLBACK_PROVIDERS
        ) and "fail closed" not in lowered

    report = {
        "ok": True,
        "fail_closed_kwargs": kwargs,
        "fail_closed_kwargs_match": kwargs == expected,
        "mock_call_kwargs": {key: mock_kwargs.get(key) for key in expected},
        "mock_call_kwargs_match": mock_kwargs_ok,
        "mock_resolved": asdict(mock_generation.identity),
        "imported_names": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "uses_fcntl": uses_fcntl,
        "uses_lock_ex": uses_lock_ex,
        "prompt_contract": prompt_ok,
        "health": asdict(health),
        "unreachable_docker0": {
            "base_url": UNREACHABLE_DOCKER0_OPENAI_BASE_URL,
            "failed_closed": bool(unreachable_error) and not unreachable_fallback,
            "fallback_used": unreachable_fallback,
            "error": unreachable_error,
            "identity": unreachable_resolved,
        },
        "autostart": env_str("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART"),
        "llama_server_started": False,
        "compiled": False,
        "arena_score": None,
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "prompt_path": relative_or_str(PROMPT_PATH, REPO_ROOT),
    }
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        report["fail_closed_kwargs_match"],
        report["mock_call_kwargs_match"],
        mock_generation.identity.resolved_provider == REQUESTED_PROVIDER,
        mock_generation.identity.resolved_model == REQUESTED_MODEL,
        not mock_generation.identity.fallback_used,
        mock_generation.identity.arena_score is None,
        not forbidden_imports,
        not uses_fcntl,
        not uses_lock_ex,
        all(prompt_ok.values()),
        report["unreachable_docker0"]["failed_closed"],
        report["autostart"] == "0",
        report["llama_server_started"] is False,
        report["compiled"] is False,
        report["arena_score"] is None,
        "fcntl" not in imported,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="fail-closed unit probe; no compile")
    parser.add_argument("--probe-health", action="store_true", help="GET docker0 /health only")
    parser.add_argument("--render-prompt", action="store_true", help="print the filled LRA prompt")
    parser.add_argument("--name", default="")
    parser.add_argument("--source", default="")
    parser.add_argument("--statement", default="")
    parser.add_argument("--src", default="")
    parser.add_argument("--header", default="")
    args = parser.parse_args(argv)
    if args.probe_health:
        from jevops.outer import print_json

        probe = probe_docker0_health()
        print_json(asdict(probe))
        from jevops.outer import exit_ok

        return exit_ok(probe.ok, bad=2)
    if args.render_prompt:
        sys.stdout.write(
            render_prompt(
                name=args.name,
                source=args.source,
                statement=args.statement,
                src=args.src,
                header=args.header,
            )
        )
        if not args.statement and not args.src:
            sys.stdout.write("\n")
        return 0
    if args.self_check or argv is None or argv == []:
        from jevops.outer import print_ok

        return print_ok(self_check())
    parser.error("choose --self-check, --probe-health, or --render-prompt")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
