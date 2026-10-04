#!/usr/bin/env python3
"""TypeSafe Jev router via in-tree ``ipfs_accelerate_py.typesafe_inference``.

Additive typed Choice / Score / Noul gates on top of Leanstral. Default
``LRA_TYPESAFE=off``. Distill uses ``LRA_TYPESAFE=distill``. Official Track 2
stays off. Score is an ordered rubric index, not a probability. Jev does
not generate Lean and does not choose the next action. CI fixtures do not
need a live ``TYPESAFE_API_KEY``. Not a second ``typesafe-sdk`` client.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = HERE.parents[3]
WARMUP_JSONL = PAPER_ROOT / "data" / "benchmark_data_warmup.jsonl"
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TYPESAFE_INFERENCE_PATH = ACCEL_ROOT / "ipfs_accelerate_py" / "typesafe_inference.py"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import retrieve as lra_retrieve  # noqa: E402
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
PR_ID = "PR-9"
LRAH_ID = "LRAH-006"
from jevops.catalogs import DEFAULT_MODE
from jevops.catalogs import PROTOCOL
from jevops.catalogs import JEV_GENERATES_LEAN
from jevops.catalogs import LOOP_V1_TYPESAFE
from jevops.catalogs import OFFICIAL_TRACK2_MODE
from jevops.catalogs import SCORE_IS_RUBRIC_INDEX

from jevops.catalogs import ALLOWED_TYPESAFE_MODES as ALLOWED_MODES
from jevops.catalogs import CHAR_BUDGET
from jevops.catalogs import HEADER_CHARS
from jevops.catalogs import NEIGHBOR_K
from jevops.catalogs import REF_HEAD_LINES
from jevops.catalogs import REF_TAIL_LINES
from jevops.catalogs import TYPESAFE_MODEL_ID as MODEL_ID
from jevops.typesafe_inference import API_KEY_ENV_NAMES as KEY_ENV_NAMES
from jevops.catalogs import ADDITIVE_NOT_REPLACEMENT
from jevops.catalogs import DISTILL_POLICY_RELATIVE
from jevops.catalogs import FORBIDDEN_SCORE_NAMES
from jevops.catalogs import TRACK1_INLOOP_ONLY
from jevops.catalogs import TYPESAFE_SYSTEMONE_URL

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "typesafe_sdk",
        "typesafe",
        "fcntl",
        "LeanstralProofProvider",
        "leanstral_proof_provider",
        "llm_router",
        "generate_text",
        "urllib",
        "requests",
        "http",
        "httpx",
    }
)
FORBIDDEN_CALLS = frozenset(
    {
        "generate_text",
        "urlopen",
        "urlretrieve",
        "request",
        "post",
        "Popen",
        "check_output",
    }
)

from jevops.catalogs import CANDIDATE_QUESTION_SPEC
from jevops.catalogs import ELAB_RISK_CRITERIA
from jevops.catalogs import ELAB_RISK_LEGEND
from jevops.catalogs import LIKELY_SHORTER_CRITERIA
from jevops.catalogs import LIKELY_SHORTER_LEGEND
from jevops.catalogs import REWRITE_CRITERIA
from jevops.catalogs import ROUTE_QUESTION_SPEC

from jevops.jev import keys_by_type  # noqa: E402

ROUTE_QUESTION_KEYS = tuple(ROUTE_QUESTION_SPEC.keys())
SCORE_QUESTION_KEYS = keys_by_type(ROUTE_QUESTION_SPEC, "score")
NOUL_QUESTION_KEYS = keys_by_type(ROUTE_QUESTION_SPEC, "noul")
CHOICE_QUESTION_KEYS = keys_by_type(ROUTE_QUESTION_SPEC, "choice")


class TypesafeRouterError(RuntimeError):
    """Fail-closed TypeSafe router error. Never a generated Lean proof."""


from jevops.jev import CatalogQuestion  # noqa: E402
from jevops.jev import FixtureChoice  # noqa: E402
from jevops.jev import FixtureClient  # noqa: E402
from jevops.jev import FixtureNoul  # noqa: E402
from jevops.jev import FixtureResponse  # noqa: E402
from jevops.jev import FixtureScore  # noqa: E402


from jevops.jev import RouteResult as _KernelRouteResult


@dataclass(frozen=True)
class RouteResult(_KernelRouteResult):
    model: str = MODEL_ID


def _ensure_accel_path() -> None:
    from jevops.outer import ensure_sys_path

    ensure_sys_path(ACCEL_ROOT)


def _import_typesafe_inference() -> dict[str, Any]:
    """Load in-tree TypeSafe types. Never imports typesafe-sdk."""

    from jevops.jev import drive_load_inference

    return drive_load_inference(
        setup=(_ensure_accel_path,),
        path=TYPESAFE_INFERENCE_PATH,
        root=REPO_ROOT,
        fallback=False,
    )


def _env_truthy(value: Optional[str]) -> bool:
    from jevops.jev import env_truthy

    return env_truthy(value)


def official_track2_requested(
    *,
    flag: bool = False,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    from jevops.jev import drive_env_closed

    return drive_env_closed(
        flag=flag,
        env=env,
        truthy_keys=("LRA_OFFICIAL_TRACK2",),
        value_key="LRA_TRACK",
        values=("official_track2", "official-track-2", "track2_official"),
    )


def resolve_typesafe_mode(
    *,
    flag: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    official_track2: bool = False,
) -> str:
    """Default off. Distill/inloop only when not official Track 2."""

    from jevops.jev import drive_mapped_mode

    return drive_mapped_mode(
        flag=flag,
        env=env,
        env_key="LRA_TYPESAFE",
        default=DEFAULT_MODE,
        allowed=ALLOWED_MODES,
        closed=OFFICIAL_TRACK2_MODE,
        official=official_track2,
        closed_fn=official_track2_requested,
        error_cls=TypesafeRouterError,
        message_fn=lambda mode: f"unknown LRA_TYPESAFE={mode!r}; expected {ALLOWED_MODES}",
    )


def key_configured(env: Optional[Mapping[str, str]] = None) -> bool:
    from jevops.outer import drive_any_env_key

    return drive_any_env_key(env, KEY_ENV_NAMES)


def _question_kind(question: Any) -> str:
    from jevops import jev
    from jevops.outer import reraise_mapped, text_or

    return reraise_mapped(
        lambda: jev.question_kind(question),
        jev.JevError,
        lambda exc: TypesafeRouterError(text_or(exc)),
    )


def _question_criteria(question: Any) -> Any:
    from jevops import jev

    return jev.question_criteria(question)


def instantiate_questions(
    spec: Mapping[str, Mapping[str, Any]],
    *,
    choice: Optional[Callable[..., Any]] = None,
    noul: Optional[Callable[..., Any]] = None,
    score: Optional[Callable[..., Any]] = None,
    neighbor_names: Sequence[str] = (),
) -> dict[str, Any]:
    """Build the frozen ROUTE_QUESTIONS dict. Uses in-tree types when loaded."""

    from jevops import jev
    from jevops.outer import reraise_mapped, text_or

    return reraise_mapped(
        lambda: jev.instantiate_questions(
            spec,
            choice=choice,
            noul=noul,
            score=score,
            neighbor_names=neighbor_names,
        ),
        jev.JevError,
        lambda exc: TypesafeRouterError(text_or(exc)),
    )


def route_questions(
    neighbor_names: Sequence[str] = (),
    *,
    typesafe: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from jevops.jev import drive_loaded_questions

    return drive_loaded_questions(
        typesafe,
        factory=_import_typesafe_inference,
        spec=ROUTE_QUESTION_SPEC,
        instantiate_fn=instantiate_questions,
        neighbor_names=neighbor_names,
    )


def candidate_questions(*, typesafe: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    from jevops.jev import drive_loaded_questions

    return drive_loaded_questions(
        typesafe,
        factory=_import_typesafe_inference,
        spec=CANDIDATE_QUESTION_SPEC,
        instantiate_fn=instantiate_questions,
    )


def truncate_reference_proof(
    src: str,
    *,
    head_lines: int = REF_HEAD_LINES,
    tail_lines: int = REF_TAIL_LINES,
    char_budget: int = CHAR_BUDGET,
) -> str:
    from jevops.jev import drive_truncate_text

    return drive_truncate_text(
        src,
        head_lines=head_lines,
        tail_lines=tail_lines,
        char_budget=char_budget,
        marker="# lra-truncated middle",
        error_cls=TypesafeRouterError,
    )


def problem_state(
    record: Mapping[str, Any],
    *,
    neighbors: Sequence[Mapping[str, Any]] = (),
    candidate: Any = None,
) -> dict[str, Any]:
    from jevops.jev import record_state

    return record_state(
        record,
        neighbors=neighbors,
        candidate=candidate,
        header_chars=HEADER_CHARS,
        neighbor_k=NEIGHBOR_K,
        truncate_fn=truncate_reference_proof,
    )


def _noul_value(answer: Any) -> float:
    from jevops import jev
    from jevops.outer import reraise_mapped, text_or

    return reraise_mapped(
        lambda: jev.noul_value(answer),
        jev.JevError,
        lambda exc: TypesafeRouterError(text_or(exc)),
    )


def _choice_value(answer: Any) -> tuple[str, float, dict[str, float]]:
    from jevops import jev
    from jevops.outer import reraise_mapped, text_or

    return reraise_mapped(
        lambda: jev.choice_value(answer),
        jev.JevError,
        lambda exc: TypesafeRouterError(text_or(exc)),
    )


def _score_value(answer: Any, *, n_levels: int, legend_fallback: Mapping[int, str]) -> tuple[float, dict[int, str]]:
    from jevops import jev
    from jevops.outer import reraise_mapped, text_or

    return reraise_mapped(
        lambda: jev.score_value(answer, n_levels=n_levels, legend_fallback=legend_fallback),
        jev.JevError,
        lambda exc: TypesafeRouterError(text_or(exc)),
    )


def answers_from_response(response: Any) -> dict[str, Any]:
    """Project System One answers. Score stays a rubric index. No Lean text."""

    from jevops.catalogs import ROUTE_CHOICE_ALIASES, ROUTE_NOUL_KEYS, ROUTE_OPTIONAL_CHOICES
    from jevops.jev import deny_lean_keys, drive_project_route_answers, project_answers

    return drive_project_route_answers(
        response,
        project_fn=lambda payload: project_answers(
            payload,
            noul_keys=ROUTE_NOUL_KEYS,
            choice_aliases=ROUTE_CHOICE_ALIASES,
            optional_choices=ROUTE_OPTIONAL_CHOICES,
            score_specs={
                "likely_shorter": {
                    "dest": "likely_shorter",
                    "n_levels": len(LIKELY_SHORTER_CRITERIA),
                    "legend": LIKELY_SHORTER_LEGEND,
                    "rubric": True,
                },
                "elab_risk_if_automated": {
                    "dest": "elab_risk",
                    "n_levels": len(ELAB_RISK_CRITERIA),
                    "legend": ELAB_RISK_LEGEND,
                },
            },
        ),
        deny_fn=deny_lean_keys,
        error_cls=TypesafeRouterError,
    )


def should_call_leanstral(answers: Optional[Mapping[str, Any]], rec: Mapping[str, Any]) -> bool:
    """v2 helper. Loop v1 calls Leanstral whenever docker0 /health is up."""

    from jevops.search import should_call_generator

    return should_call_generator(answers, rec)


def default_fixture_answers() -> dict[str, Any]:
    """CI answers: rubric level 0 plus a tight reference. Not live Jev."""

    from jevops.catalogs import default_fixture_answers as _fn

    return _fn()


class TypeSafeLraRouter:
    """In-tree typesafe_inference wrapper. No-op without key. Off on Track 2."""

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        official_track2: bool = False,
        env: Optional[Mapping[str, str]] = None,
        client_factory: Optional[Callable[..., Any]] = None,
        model: str = MODEL_ID,
        require_key: bool = True,
    ) -> None:
        from jevops.jev import drive_router_fields
        from jevops.outer import env_copy

        self.__dict__.update(
            drive_router_fields(
                mode=mode,
                official_track2=official_track2,
                env=env,
                client_factory=client_factory,
                model=model,
                require_key=require_key,
                env_fn=env_copy,
                track2_fn=official_track2_requested,
                mode_fn=resolve_typesafe_mode,
            )
        )

    @property
    def enabled(self) -> bool:
        from jevops.jev import mode_enabled

        return mode_enabled(self.mode, self.official_track2)

    def route(
        self,
        state: Mapping[str, Any],
        *,
        neighbor_names: Sequence[str] = (),
    ) -> RouteResult:
        from jevops.jev import drive_router_route

        return drive_router_route(
            self,
            state,
            neighbor_names=neighbor_names,
            import_fn=_import_typesafe_inference,
            key_fn=key_configured,
            questions_fn=instantiate_questions,
            spec=ROUTE_QUESTION_SPEC,
            answers_fn=answers_from_response,
            result_cls=RouteResult,
        )


def distill_record(
    state: Mapping[str, Any],
    result: RouteResult,
    *,
    lean_outcome: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Log (features, Jev answers, Lean outcome). Does not generate Lean."""

    from jevops.jev import drive_distill_record

    return drive_distill_record(
        state,
        result.as_dict(),
        lean_outcome=lean_outcome,
        schema="lra-typesafe-distill/v1",
        mode="distill",
        policy_path=DISTILL_POLICY_RELATIVE,
    )


def _imported_names(source: str) -> set[str]:
    from jevops.repair import imported_names

    return imported_names(source)


def _call_func_names(source: str) -> set[str]:
    from jevops.repair import call_func_names

    return call_func_names(source)


def _assigned_constant(tree: ast.AST, name: str) -> Any:
    from jevops.repair import assigned_constant

    return assigned_constant(tree, name)


def _numeric_score_assignments(source: str) -> list[str]:
    from jevops.repair import numeric_score_assignments

    return numeric_score_assignments(source, FORBIDDEN_SCORE_NAMES)


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    from jevops.outer import source_text
    from jevops.repair import audit_source as _audit

    text = source_text(source, path=__file__)
    out = _audit(
        text,
        forbidden_imports=FORBIDDEN_IMPORT_NAMES,
        forbidden_calls=FORBIDDEN_CALLS,
        forbidden_scores=FORBIDDEN_SCORE_NAMES,
    )
    from jevops import jev as jev_mod
    from jevops.repair import catalog_constants, membership, module_imported_names

    imported = set(out["imported_names"])
    kernel_imported = module_imported_names(jev_mod)
    ok_imported = imported | kernel_imported
    calls = set(out["call_func_names"])
    consts = catalog_constants(
        (
            "JEV_GENERATES_LEAN",
            "SCORE_IS_RUBRIC_INDEX",
            "DEFAULT_MODE",
            "LOOP_V1_TYPESAFE",
            "OFFICIAL_TRACK2_MODE",
        ),
    )
    forbidden_imports = out["forbidden_imports"]
    forbidden_calls = out["forbidden_calls"]
    score_issues = out["score_issues"]
    uses_lock_ex = out["uses_lock_ex"]
    flags = membership(
        ok_imported,
        {
            "imports_typesafe_inference": ("ipfs_accelerate_py.typesafe_inference",),
            "imports_choice": ("Choice",),
            "imports_noul": ("Noul",),
            "imports_score": ("Score",),
            "imports_typesafe_client": ("TypeSafeClient",),
            "imports_typesafe_configured": ("typesafe_configured",),
        },
    )
    flags.update(
        membership(
            imported,
            {
                "imports_typesafe_sdk": ("typesafe_sdk", "typesafe"),
                "imports_llm_router": ("llm_router",),
                "imports_generate_text": ("generate_text",),
            },
        )
    )
    flags.update(
        membership(
            calls,
            {
                "calls_generate_text": ("generate_text",),
                "calls_system_one": ("system_one",),
            },
        )
    )
    from jevops.repair import pack_call_audit

    packed = pack_call_audit(
        out,
        extra={
            "numeric_score_assignments": score_issues,
            **flags,
            "jev_generates_lean_constant": consts["JEV_GENERATES_LEAN"],
            "score_is_rubric_index_constant": consts["SCORE_IS_RUBRIC_INDEX"],
            "default_mode_constant": consts["DEFAULT_MODE"],
            "loop_v1_typesafe_constant": consts["LOOP_V1_TYPESAFE"],
            "official_track2_mode_constant": consts["OFFICIAL_TRACK2_MODE"],
            "uses_lock_ex": uses_lock_ex,
        },
        extra_ok=(
            "ipfs_accelerate_py.typesafe_inference" in ok_imported,
            "Choice" in ok_imported,
            "TypeSafeClient" in ok_imported,
            "typesafe_sdk" not in imported,
            "typesafe" not in imported,
            "llm_router" not in imported,
            "generate_text" not in imported,
            "generate_text" not in calls,
            not score_issues,
            not uses_lock_ex,
            consts["JEV_GENERATES_LEAN"] is False,
            consts["SCORE_IS_RUBRIC_INDEX"] is True,
            consts["DEFAULT_MODE"] == "off",
            consts["LOOP_V1_TYPESAFE"] == "off",
            consts["OFFICIAL_TRACK2_MODE"] == "off",
        ),
    )
    packed["imported_names"] = sorted(imported)
    packed["forbidden_imports"] = forbidden_imports
    packed["forbidden_calls"] = forbidden_calls
    return packed


def _load_named_record(name: str, path: Optional[Path] = None) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    from jevops.outer import drive_overlay_named

    return drive_overlay_named(
        lra_splice.load_warmup_records,
        name,
        error_cls=TypesafeRouterError,
        miss=f"unknown warm-up problem: {name}",
        extra=path,
    )


def _neighbors_for(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    from jevops.outer import drive_prompt_neighbors

    return drive_prompt_neighbors(
        record,
        records,
        retrieve_fn=lra_retrieve.retrieve_record,
        neighbor_fn=lra_retrieve.prompt_neighbors,
        k=NEIGHBOR_K,
    )


def route_named(
    name: str,
    *,
    mode: Optional[str] = None,
    official_track2: bool = False,
    fixture: bool = False,
    path: Optional[Path] = None,
    lean_outcome: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    from jevops.jev import drive_named_route

    return drive_named_route(
        name,
        mode=mode,
        official_track2=official_track2,
        fixture=fixture,
        path=path,
        lean_outcome=lean_outcome,
        load_fn=_load_named_record,
        neighbor_fn=_neighbors_for,
        state_fn=problem_state,
        fixture_client=FixtureClient,
        answers_fn=default_fixture_answers,
        router_cls=TypeSafeLraRouter,
        should_call_fn=should_call_leanstral,
        distill_fn=distill_record,
        route_keys=ROUTE_QUESTION_KEYS,
        default_mode=DEFAULT_MODE,
    )


def plan_view(
    *,
    mode: Optional[str] = None,
    official_track2: bool = False,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    from jevops.jev import drive_plan_view

    return drive_plan_view(
        mode=mode,
        official_track2=official_track2,
        env=env,
        resolve_fn=resolve_typesafe_mode,
        import_fn=_import_typesafe_inference,
        spec=ROUTE_QUESTION_SPEC,
        instantiate_fn=instantiate_questions,
        track2_fn=official_track2_requested,
        key_fn=key_configured,
        fields={
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "lrah": LRAH_ID,
            "default_mode": DEFAULT_MODE,
            "allowed_modes": list(ALLOWED_MODES),
            "official_track2_stays_off": True,
            "loop_v1_typesafe": LOOP_V1_TYPESAFE,
            "distill_uses_lra_typesafe_distill": True,
            "inloop_is_track1_only": TRACK1_INLOOP_ONLY,
            "additive_not_replacement": ADDITIVE_NOT_REPLACEMENT,
            "model": MODEL_ID,
            "route_question_keys": list(ROUTE_QUESTION_KEYS),
            "score_question_keys": list(SCORE_QUESTION_KEYS),
            "noul_question_keys": list(NOUL_QUESTION_KEYS),
            "choice_question_keys": list(CHOICE_QUESTION_KEYS),
            "likely_shorter_criteria": list(LIKELY_SHORTER_CRITERIA),
            "likely_shorter_legend": LIKELY_SHORTER_LEGEND,
            "score_is_rubric_index": SCORE_IS_RUBRIC_INDEX,
            "jev_generates_lean": JEV_GENERATES_LEAN,
            "typesafe_systemone_url": TYPESAFE_SYSTEMONE_URL,
            "router_posts_to_typesafe": False,
            "imports_typesafe_inference": True,
            "imports_typesafe_sdk": False,
            "key_env_names": list(KEY_ENV_NAMES),
            "distill_policy_path": DISTILL_POLICY_RELATIVE,
            "writes_policy_by_default": False,
            "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        },
    )


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """CI fixtures without a live key. Does not POST and does not generate Lean."""

    from jevops.outer import read_text

    source = read_text(__file__)
    from jevops.outer import digest_file, path_or, relative_or_str

    jsonl = path_or(path, WARMUP_JSONL)

    before = digest_file(jsonl)
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    after = digest_file(jsonl)
    audit = audit_source(source)
    loaded = _import_typesafe_inference()
    first = records[0]
    neighbors = _neighbors_for(first, records)
    state = problem_state(first, neighbors=neighbors)
    neighbor_names = [item["name"] for item in neighbors]

    default_mode = resolve_typesafe_mode(env={})
    unset_mode = resolve_typesafe_mode(env={"LRA_TYPESAFE": ""})
    distill_mode = resolve_typesafe_mode(env={"LRA_TYPESAFE": "distill"})
    inloop_mode = resolve_typesafe_mode(env={"LRA_TYPESAFE": "inloop"})
    track2_distill = resolve_typesafe_mode(
        flag="distill",
        env={"LRA_TYPESAFE": "distill", "LRA_OFFICIAL_TRACK2": "1"},
        official_track2=True,
    )
    track2_env = resolve_typesafe_mode(env={"LRA_TYPESAFE": "inloop", "LRA_TRACK": "official_track2"})

    off_router = TypeSafeLraRouter(mode=None, env={})
    off_result = off_router.route(state, neighbor_names=neighbor_names)

    no_key_router = TypeSafeLraRouter(mode="distill", env={"LRA_TYPESAFE": "distill"})
    no_key_result = no_key_router.route(state, neighbor_names=neighbor_names)

    fixture_client = FixtureClient(answers=default_fixture_answers())
    distill_router = TypeSafeLraRouter(
        mode="distill",
        env={"LRA_TYPESAFE": "distill"},
        client_factory=lambda **kwargs: fixture_client,
    )
    distill_result = distill_router.route(state, neighbor_names=neighbor_names)
    distill_answers = distill_result.as_dict()
    skip_llm = should_call_leanstral(distill_answers, first)
    distill_log = distill_record(state, distill_result, lean_outcome={"compiled": False, "status": "fixture"})

    from jevops.outer import first_truthy, overlay_map

    custom_fixture = FixtureClient(
        answers=overlay_map(
            default_fixture_answers(),
            rewrite_family="custom",
            reference_already_tight=0.2,
            likely_shorter=2.0,
            spend_llm=0.8,
            hammer_before_llm=0.1,
        )
    )
    custom_router = TypeSafeLraRouter(
        mode="distill",
        client_factory=lambda **kwargs: custom_fixture,
    )
    custom_result = custom_router.route(state, neighbor_names=neighbor_names)
    spend_llm = should_call_leanstral(custom_result.as_dict(), first)

    official_router = TypeSafeLraRouter(
        mode="distill",
        official_track2=True,
        env={"LRA_TYPESAFE": "distill"},
        client_factory=lambda **kwargs: FixtureClient(answers=default_fixture_answers()),
    )
    official_result = official_router.route(state, neighbor_names=neighbor_names)

    long_src = "\n".join(f"line_{index}" for index in range(200))
    truncated_lines = truncate_reference_proof(long_src, char_budget=40, head_lines=2, tail_lines=2)

    catalog = instantiate_questions(ROUTE_QUESTION_SPEC, neighbor_names=neighbor_names)
    score_questions = [name for name, question in catalog.items() if question.kind == "score"]
    likely_criteria = ROUTE_QUESTION_SPEC["likely_shorter"]["criteria"]

    unknown_closed = False
    try:
        resolve_typesafe_mode(flag="on")
    except TypesafeRouterError:
        unknown_closed = True

    from jevops.outer import dumps_sorted

    serialized = dumps_sorted({"distill": distill_log, "route": distill_result.as_dict()})
    key_leak = any(token in serialized for token in ("BEGIN SECRET", "sk-live-", "sk-prod-"))

    from jevops.outer import pack_unscored

    report = pack_unscored(**{
        "ok": True,
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "lrah": LRAH_ID,
        "n_records": len(records),
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "warmup_jsonl_sha256": digest,
        "jsonl_bytes": len(raw),
        "jsonl_unchanged": before == after == FROZEN_WARMUP_SHA256,
        "audit": audit,
        "typesafe_inference": {
            "available": loaded["available"],
            "exists": loaded["exists"],
            "error": loaded["error"],
            "path": loaded["path"],
        },
        "modes": {
            "default": default_mode,
            "unset_env": unset_mode,
            "distill": distill_mode,
            "inloop": inloop_mode,
            "official_track2_with_distill_flag": track2_distill,
            "official_track2_env_inloop": track2_env,
            "unknown_closed": unknown_closed,
        },
        "off_result": off_result.as_dict(),
        "no_key_result": no_key_result.as_dict(),
        "distill_fixture": distill_answers,
        "custom_fixture": custom_result.as_dict(),
        "official_track2_result": official_result.as_dict(),
        "skip_llm_on_rubric_level_0": skip_llm is False,
        "spend_llm_on_custom_level_2": spend_llm is True,
        "likely_shorter_level_0": distill_result.likely_shorter,
        "likely_shorter_legend_0": overlay_map(distill_result.likely_shorter_legend).get(0),
        "likely_shorter_is_rubric_index": distill_result.likely_shorter_is_rubric_index,
        "likely_shorter_not_probability": distill_result.likely_shorter == 0.0
        and overlay_map(distill_result.likely_shorter_legend).get(0) == "longer or same",
        "custom_likely_shorter_level_2": custom_result.likely_shorter,
        "distill_log": distill_log,
        "catalog_keys": list(catalog.keys()),
        "score_questions": score_questions,
        "likely_shorter_criteria": list(likely_criteria),
        "n_score_levels": len(likely_criteria),
        "neighbor_names": neighbor_names,
        "truncated_over_budget": first_truthy(
            "lra-truncated" in truncated_lines, len(truncated_lines) <= CHAR_BUDGET
        ),
        "jev_generated_lean": False,
        "off_skipped": off_result.skipped and off_result.reason == "typesafe_off",
        "no_key_skipped": no_key_result.skipped and no_key_result.reason in {"no_key", "typesafe_inference_missing"},
        "distill_called": distill_result.called_typesafe and distill_result.used_fixture and not distill_result.skipped,
        "official_stayed_off": official_result.skipped and official_result.reason == "official_track2_off",
        "official_did_not_call": official_result.called_typesafe is False,
        "default_mode_is_off": default_mode == "off" and unset_mode == "off",
        "distill_uses_lra_typesafe_distill": distill_mode == "distill",
        "inloop_uses_lra_typesafe_inloop": inloop_mode == "inloop",
        "official_track2_stays_off": track2_distill == "off" and track2_env == "off",
        "imports_typesafe_inference": audit["imports_typesafe_inference"],
        "imports_typesafe_sdk": audit["imports_typesafe_sdk"],
        "no_second_typesafe_sdk_client": audit["ok"] and not audit["imports_typesafe_sdk"],
        "score_is_rubric_index": SCORE_IS_RUBRIC_INDEX,
        "additive_not_replacement": ADDITIVE_NOT_REPLACEMENT,
        "key_leak": key_leak,
        "compiled": False,
        "lake": False,
        "llama_server_started": False,
        "arena_score": None,
        "first_name": first.get("name"),
        "warmup_path": relative_or_str(jsonl, REPO_ROOT),
    })
    from jevops.outer import finalize_ok

    return finalize_ok(
        report,
        report["n_records"] == WARMUP_N,
        report["jsonl_unchanged"],
        audit["ok"],
        report["default_mode_is_off"],
        report["distill_uses_lra_typesafe_distill"],
        report["inloop_uses_lra_typesafe_inloop"],
        report["official_track2_stays_off"],
        report["off_skipped"],
        report["no_key_skipped"],
        report["distill_called"],
        report["official_stayed_off"],
        report["official_did_not_call"],
        report["skip_llm_on_rubric_level_0"],
        report["spend_llm_on_custom_level_2"],
        report["likely_shorter_not_probability"],
        report["likely_shorter_level_0"] == 0.0,
        report["custom_likely_shorter_level_2"] == 2.0,
        report["imports_typesafe_inference"],
        not report["imports_typesafe_sdk"],
        report["jev_generated_lean"] is False,
        distill_result.jev_generated_lean is False,
        distill_result.lean_text is None,
        distill_result.tactics is None,
        distill_result.proof_text is None,
        distill_result.arena_score is None,
        distill_log["jev_generated_lean"] is False,
        distill_log["api_key_present_in_record"] is False,
        unknown_closed,
        not key_leak,
        report["catalog_keys"] == list(ROUTE_QUESTION_KEYS),
        report["n_score_levels"] == 3,
        report["compiled"] is False,
        report["arena_score"] is None,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="CI fixtures; no live key; no POST")
    parser.add_argument("--plan", action="store_true", help="dump mode resolution and frozen catalog")
    parser.add_argument("--route", action="store_true", help="route one warm-up problem by --name")
    parser.add_argument("--name", default="", help="JSONL problem name")
    parser.add_argument(
        "--typesafe",
        choices=ALLOWED_MODES,
        default=None,
        help="override LRA_TYPESAFE (default off)",
    )
    parser.add_argument("--official-track2", action="store_true", help="force official Track 2 off")
    parser.add_argument("--fixture", action="store_true", help="use CI fixture client; no live key")
    parser.add_argument("--jsonl", type=Path, default=None, help="warmup JSONL path")
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.plan:
        from jevops.outer import print_ok

        return print_ok(plan_view(mode=args.typesafe, official_track2=args.official_track2))
    if args.route:
        if not args.name:
            parser.error("--route requires --name")
        from jevops.outer import failed_check, print_json

        try:
            payload = route_named(
                args.name,
                mode=args.typesafe,
                official_track2=args.official_track2,
                fixture=args.fixture,
                path=args.jsonl,
            )
        except (TypesafeRouterError, lra_splice.SpliceError, lra_retrieve.RetrieveError) as exc:
            print_json(failed_check(exc, jev_generated_lean=False))
            return 1
        from jevops.outer import print_ok

        return print_ok(payload)
    if args.self_check or argv is None or argv == []:
        from jevops.outer import print_ok

        return print_ok(self_check(args.jsonl))
    parser.error("choose --self-check, --plan, or --route")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
