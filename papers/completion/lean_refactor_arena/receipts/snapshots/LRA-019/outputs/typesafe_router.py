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
import hashlib
import json
import os
import sys
import time
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
import retrieve as lra_retrieve  # noqa: E402
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
WARMUP_N = lra_splice.WARMUP_N
PROTOCOL = "LRA/v1"
PR_ID = "PR-9"
LRAH_ID = "LRAH-006"
LOOP_V1_TYPESAFE = "off"
DEFAULT_MODE = "off"
ALLOWED_MODES = ("off", "distill", "inloop")
OFFICIAL_TRACK2_MODE = "off"
MODEL_ID = "jev-latest"
JEV_GENERATES_LEAN = False
SCORE_IS_RUBRIC_INDEX = True
ADDITIVE_NOT_REPLACEMENT = True
TRACK1_INLOOP_ONLY = True
TYPESAFE_SYSTEMONE_URL = "https://api.typesafe.ai/v1/systemone"
DISTILL_POLICY_RELATIVE = "papers/completion/lean_refactor_arena/policy/open_policy_v1.json"
HEADER_CHARS = 500
NEIGHBOR_K = 4
REF_HEAD_LINES = 80
REF_TAIL_LINES = 80
CHAR_BUDGET = 150_000
KEY_ENV_NAMES = (
    "TYPESAFE_API_KEY",
    "ipfs_accelerate_py_TYPESAFE_API_KEY",
    "IPFS_ACCELERATE_PY_TYPESAFE_API_KEY",
    "IPFS_DATASETS_PY_TYPESAFE_API_KEY",
)
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
FORBIDDEN_SCORE_NAMES = frozenset(
    {
        "arena_score",
        "arena_score_tokens",
        "arena_score_elab",
        "official_track2_score",
        "token_savings",
        "official_score",
        "relevance_score",
    }
)

REWRITE_CRITERIA: dict[str, Any] = {
    "native_hammer": {
        "what": "Goal looks like rfl/decide/omega/simp_all/assumption",
        "not_for": "Long calc, domain-specific lemmas, or large induction",
    },
    "simp_set": {"what": "Unfolding + rewrite lemmas should close or shrink it"},
    "aesop": {"what": "Aesop/auto would likely close"},
    "omega_decide": {"what": "Linear arithmetic or decidable predicates"},
    "calc": {"what": "Keep calc/conv structure; drop noise"},
    "have_chain": {"what": "Merge redundant have/show steps"},
    "custom": {"what": "Needs a model-written tactic script"},
}

LIKELY_SHORTER_CRITERIA = (
    "longer or same",
    "modest cut around 10 percent",
    "large cut of 30 percent or more",
)
ELAB_RISK_CRITERIA = (
    "elab likely better or same",
    "elab unclear",
    "elab likely worse",
)
LIKELY_SHORTER_LEGEND = {index: label for index, label in enumerate(LIKELY_SHORTER_CRITERIA)}
ELAB_RISK_LEGEND = {index: label for index, label in enumerate(ELAB_RISK_CRITERIA)}

ROUTE_QUESTION_SPEC: dict[str, dict[str, Any]] = {
    "rewrite_family": {
        "type": "choice",
        "instructions": "Which rewrite family should code try first on `reference_proof`?",
        "criteria": REWRITE_CRITERIA,
    },
    "hammer_before_llm": {
        "type": "noul",
        "instructions": (
            "Would Lean built-in tactics (rfl, decide, omega, simp_all, aesop if imported) "
            "plausibly close `statement` without a custom script?"
        ),
    },
    "reference_already_tight": {
        "type": "noul",
        "instructions": "Is `reference_proof` already compact relative to `statement`?",
    },
    "likely_shorter": {
        "type": "score",
        "instructions": "How large a source-token cut is plausible versus `problem.proof_length`?",
        "criteria": list(LIKELY_SHORTER_CRITERIA),
    },
    "elab_risk_if_automated": {
        "type": "score",
        "instructions": "If replaced by simp_all/aesop/omega, how likely is elaboration to get worse?",
        "criteria": list(ELAB_RISK_CRITERIA),
    },
    "version_fragile": {
        "type": "noul",
        "instructions": (
            "Does `reference_proof` rely on tactic or API details likely to break "
            "across Lean 4.25 through 4.33?"
        ),
    },
    "putnam_aesop_plausible": {
        "type": "noul",
        "instructions": "Given `header` and `statement`, is a short aesop/simp proof plausible?",
    },
    "calc_structure_worth_keeping": {
        "type": "noul",
        "instructions": "Is `reference_proof` a calc/conv chain whose structure should be kept?",
    },
    "statement_in_proof_duplicated": {
        "type": "noul",
        "instructions": "Does `reference_proof` repeat `statement` or contain a second theorem/lemma?",
    },
    "uses_sorry_or_admit": {
        "type": "noul",
        "instructions": "Does `reference_proof` contain sorry, admit, or an axiom?",
    },
    "neighbor_style_match": {
        "type": "choice",
        "instructions": "Which neighbor's proof style should the generator imitate?",
        "criteria": {"none": "Do not imitate a neighbor"},
    },
    "spend_llm": {
        "type": "noul",
        "instructions": "Should code spend an LLM generation rather than only hammers?",
    },
}

CANDIDATE_QUESTION_SPEC: dict[str, dict[str, Any]] = {
    "candidate_changes_statement": {
        "type": "noul",
        "instructions": "Does the candidate change the theorem statement versus `statement`?",
    },
    "likely_shorter_than_reference": {
        "type": "score",
        "instructions": "How large a source-token cut is this candidate versus the reference?",
        "criteria": list(LIKELY_SHORTER_CRITERIA),
    },
    "likely_compiles": {
        "type": "noul",
        "instructions": "Is the candidate likely to compile on every version_info tag?",
    },
    "likely_worse_elab": {
        "type": "noul",
        "instructions": "Is the candidate likely worse on elaboration effort than the reference?",
    },
    "introduces_sorry": {
        "type": "noul",
        "instructions": "Does the candidate introduce sorry, admit, or a new axiom?",
    },
}

ROUTE_QUESTION_KEYS = tuple(ROUTE_QUESTION_SPEC.keys())
SCORE_QUESTION_KEYS = tuple(name for name, spec in ROUTE_QUESTION_SPEC.items() if spec["type"] == "score")
NOUL_QUESTION_KEYS = tuple(name for name, spec in ROUTE_QUESTION_SPEC.items() if spec["type"] == "noul")
CHOICE_QUESTION_KEYS = tuple(name for name, spec in ROUTE_QUESTION_SPEC.items() if spec["type"] == "choice")


class TypesafeRouterError(RuntimeError):
    """Fail-closed TypeSafe router error. Never a generated Lean proof."""


@dataclass(frozen=True)
class CatalogQuestion:
    """Frozen question descriptor. Not an HTTP client and not typesafe-sdk."""

    kind: str
    instructions: str
    criteria: Any = None


@dataclass(frozen=True)
class FixtureChoice:
    choice: str
    confidence: float
    probabilities: Mapping[str, float]


@dataclass(frozen=True)
class FixtureNoul:
    noul: float


@dataclass(frozen=True)
class FixtureScore:
    score: float
    legend: Mapping[int, str]


@dataclass(frozen=True)
class FixtureResponse:
    choices: Mapping[str, FixtureChoice]
    nouls: Mapping[str, FixtureNoul]
    scores: Mapping[str, FixtureScore]
    usage: Mapping[str, Any]


@dataclass
class FixtureClient:
    """CI fixture System One stand-in. Never POSTs. Not typesafe-sdk."""

    model: str = MODEL_ID
    answers: Mapping[str, Any] = field(default_factory=dict)

    def __enter__(self) -> "FixtureClient":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def system_one(self, state: Mapping[str, Any], questions: Mapping[str, Any]) -> FixtureResponse:
        del state
        choices: dict[str, FixtureChoice] = {}
        nouls: dict[str, FixtureNoul] = {}
        scores: dict[str, FixtureScore] = {}
        for name, question in questions.items():
            kind = _question_kind(question)
            override = self.answers.get(name)
            if kind == "choice":
                criteria = _question_criteria(question)
                keys = list(criteria.keys()) if isinstance(criteria, Mapping) else ["none"]
                picked = str(override if override is not None else (keys[0] if keys else "none"))
                if picked not in keys:
                    picked = keys[0] if keys else "none"
                conf = 0.72 if picked != "none" else 0.64
                mass = (1.0 - conf) / max(len(keys) - 1, 1)
                probs = {key: (conf if key == picked else mass) for key in keys}
                choices[name] = FixtureChoice(choice=picked, confidence=conf, probabilities=probs)
            elif kind == "noul":
                value = 0.25 if override is None else float(override)
                nouls[name] = FixtureNoul(noul=value)
            elif kind == "score":
                criteria = _question_criteria(question)
                n_levels = len(criteria) if isinstance(criteria, (list, tuple)) else 3
                legend = {index: str(item) for index, item in enumerate(criteria)} if isinstance(
                    criteria, (list, tuple)
                ) else dict(LIKELY_SHORTER_LEGEND)
                value = 0.0 if override is None else float(override)
                scores[name] = FixtureScore(score=value, legend=legend)
                if value < 0 or value > max(n_levels - 1, 0):
                    raise TypesafeRouterError(f"{name}: rubric index {value} outside [0, {n_levels - 1}]")
            else:
                raise TypesafeRouterError(f"unknown question kind for {name}")
        return FixtureResponse(
            choices=choices,
            nouls=nouls,
            scores=scores,
            usage={"input_tokens": 0, "output_tokens": 0, "fixture": True, "model": self.model},
        )


@dataclass(frozen=True)
class RouteResult:
    skipped: bool
    reason: str
    mode: str
    official_track2: bool
    family: Optional[str] = None
    family_confidence: Optional[float] = None
    family_probs: Optional[dict[str, float]] = None
    hammer_before_llm: Optional[float] = None
    reference_already_tight: Optional[float] = None
    likely_shorter: Optional[float] = None
    likely_shorter_legend: Optional[dict[int, str]] = None
    likely_shorter_is_rubric_index: bool = True
    elab_risk: Optional[float] = None
    elab_risk_legend: Optional[dict[int, str]] = None
    version_fragile: Optional[float] = None
    putnam_aesop_plausible: Optional[float] = None
    calc_structure_worth_keeping: Optional[float] = None
    statement_in_proof_duplicated: Optional[float] = None
    uses_sorry_or_admit: Optional[float] = None
    neighbor_style_match: Optional[str] = None
    spend_llm: Optional[float] = None
    usage: Optional[dict[str, Any]] = None
    wall_ms: Optional[float] = None
    called_typesafe: bool = False
    used_fixture: bool = False
    model: str = MODEL_ID
    jev_generated_lean: bool = False
    lean_text: None = None
    tactics: None = None
    proof_text: None = None
    arena_score: None = None
    api_key_redacted: bool = True
    score_is_rubric_index: bool = True
    additive_not_replacement: bool = True

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        legend = payload.get("likely_shorter_legend")
        if isinstance(legend, dict):
            payload["likely_shorter_legend"] = {str(key): value for key, value in legend.items()}
        elab_legend = payload.get("elab_risk_legend")
        if isinstance(elab_legend, dict):
            payload["elab_risk_legend"] = {str(key): value for key, value in elab_legend.items()}
        return payload


def _ensure_accel_path() -> None:
    accel = str(ACCEL_ROOT)
    if accel not in sys.path:
        sys.path.insert(0, accel)


def _import_typesafe_inference() -> dict[str, Any]:
    """Load in-tree TypeSafe types. Never imports typesafe-sdk."""

    _ensure_accel_path()
    try:
        from ipfs_accelerate_py.typesafe_inference import (  # type: ignore[import-not-found]
            Choice,
            Noul,
            Score,
            TypeSafeClient,
            typesafe_configured,
        )
    except ImportError as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "path": str(TYPESAFE_INFERENCE_PATH.relative_to(REPO_ROOT)),
            "exists": TYPESAFE_INFERENCE_PATH.is_file(),
            "Choice": None,
            "Noul": None,
            "Score": None,
            "TypeSafeClient": None,
            "typesafe_configured": None,
        }
    return {
        "available": True,
        "error": "",
        "path": str(TYPESAFE_INFERENCE_PATH.relative_to(REPO_ROOT)),
        "exists": True,
        "Choice": Choice,
        "Noul": Noul,
        "Score": Score,
        "TypeSafeClient": TypeSafeClient,
        "typesafe_configured": typesafe_configured,
    }


def _env_truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def official_track2_requested(
    *,
    flag: bool = False,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    if flag:
        return True
    source = os.environ if env is None else env
    if _env_truthy(source.get("LRA_OFFICIAL_TRACK2")):
        return True
    track = str(source.get("LRA_TRACK", "")).strip().lower()
    return track in {"official_track2", "official-track-2", "track2_official"}


def resolve_typesafe_mode(
    *,
    flag: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    official_track2: bool = False,
) -> str:
    """Default off. Distill/inloop only when not official Track 2."""

    source = os.environ if env is None else env
    if official_track2_requested(flag=official_track2, env=source):
        return OFFICIAL_TRACK2_MODE
    raw = DEFAULT_MODE if flag is None else flag
    if flag is None:
        raw = source.get("LRA_TYPESAFE", DEFAULT_MODE)
    if raw is None or str(raw).strip() == "":
        raw = DEFAULT_MODE
    mode = str(raw).strip().lower()
    if mode not in ALLOWED_MODES:
        raise TypesafeRouterError(f"unknown LRA_TYPESAFE={mode!r}; expected {ALLOWED_MODES}")
    return mode


def key_configured(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return any(str(source.get(name) or "").strip() for name in KEY_ENV_NAMES)


def _question_kind(question: Any) -> str:
    if isinstance(question, CatalogQuestion):
        return question.kind
    kind = getattr(question, "kind", None) or getattr(question, "type", None)
    if isinstance(kind, str) and kind:
        return kind.lower()
    name = type(question).__name__.lower()
    if "choice" in name:
        return "choice"
    if "noul" in name:
        return "noul"
    if "score" in name:
        return "score"
    if isinstance(question, Mapping):
        return str(question.get("type") or question.get("kind") or "")
    raise TypesafeRouterError(f"cannot classify question {type(question).__name__}")


def _question_criteria(question: Any) -> Any:
    if isinstance(question, CatalogQuestion):
        return question.criteria
    criteria = getattr(question, "criteria", None)
    if criteria is not None:
        return criteria
    if isinstance(question, Mapping):
        return question.get("criteria")
    return None


def instantiate_questions(
    spec: Mapping[str, Mapping[str, Any]],
    *,
    choice: Optional[Callable[..., Any]] = None,
    noul: Optional[Callable[..., Any]] = None,
    score: Optional[Callable[..., Any]] = None,
    neighbor_names: Sequence[str] = (),
) -> dict[str, Any]:
    """Build the frozen ROUTE_QUESTIONS dict. Uses in-tree types when loaded."""

    choice_ctor = choice or (lambda **kwargs: CatalogQuestion(kind="choice", **kwargs))
    noul_ctor = noul or (lambda **kwargs: CatalogQuestion(kind="noul", **kwargs))
    score_ctor = score or (lambda **kwargs: CatalogQuestion(kind="score", **kwargs))
    questions: dict[str, Any] = {}
    for name, item in spec.items():
        kind = str(item["type"])
        instructions = str(item["instructions"])
        criteria = item.get("criteria")
        if name == "neighbor_style_match":
            neighbor_criteria = {"none": "Do not imitate a neighbor"}
            for neighbor in neighbor_names:
                neighbor_criteria[str(neighbor)] = f"Imitate neighbor {neighbor}"
            criteria = neighbor_criteria
        if kind == "choice":
            questions[name] = choice_ctor(instructions=instructions, criteria=criteria)
        elif kind == "noul":
            questions[name] = noul_ctor(instructions=instructions)
        elif kind == "score":
            questions[name] = score_ctor(instructions=instructions, criteria=list(criteria or []))
        else:
            raise TypesafeRouterError(f"unknown question type {kind} for {name}")
    return questions


def route_questions(
    neighbor_names: Sequence[str] = (),
    *,
    typesafe: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    loaded = typesafe if typesafe is not None else _import_typesafe_inference()
    return instantiate_questions(
        ROUTE_QUESTION_SPEC,
        choice=loaded.get("Choice"),
        noul=loaded.get("Noul"),
        score=loaded.get("Score"),
        neighbor_names=neighbor_names,
    )


def candidate_questions(*, typesafe: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    loaded = typesafe if typesafe is not None else _import_typesafe_inference()
    return instantiate_questions(
        CANDIDATE_QUESTION_SPEC,
        choice=loaded.get("Choice"),
        noul=loaded.get("Noul"),
        score=loaded.get("Score"),
    )


def truncate_reference_proof(
    src: str,
    *,
    head_lines: int = REF_HEAD_LINES,
    tail_lines: int = REF_TAIL_LINES,
    char_budget: int = CHAR_BUDGET,
) -> str:
    if not isinstance(src, str):
        raise TypesafeRouterError("reference_proof must be a string")
    if len(src) <= char_budget:
        return src
    lines = src.splitlines()
    if len(lines) <= head_lines + tail_lines:
        return src[:char_budget]
    head = "\n".join(lines[:head_lines])
    tail = "\n".join(lines[-tail_lines:])
    middle = "\n".join(lines[head_lines:-tail_lines]).encode("utf-8")
    digest = hashlib.sha256(middle).hexdigest()
    skipped = len(lines) - head_lines - tail_lines
    return f"{head}\n\n# lra-truncated middle sha256:{digest} lines={skipped}\n\n{tail}"


def problem_state(
    record: Mapping[str, Any],
    *,
    neighbors: Sequence[Mapping[str, Any]] = (),
    candidate: Any = None,
) -> dict[str, Any]:
    header = record.get("header") if isinstance(record.get("header"), str) else ""
    version_info = record.get("version_info") if isinstance(record.get("version_info"), list) else []
    return {
        "problem": {
            "name": record.get("name"),
            "source": record.get("source"),
            "n_toolchains": len(version_info),
            "proof_length": record.get("proof_length"),
            "num_lines": record.get("num_lines"),
            "has_repo": bool(record.get("url")),
            "header": header[:HEADER_CHARS],
        },
        "statement": record.get("statement"),
        "reference_proof": truncate_reference_proof(str(record.get("src") or "")),
        "neighbors": list(neighbors)[:NEIGHBOR_K],
        "candidate": candidate,
    }


def _noul_value(answer: Any) -> float:
    if hasattr(answer, "noul"):
        return float(answer.noul)
    if isinstance(answer, Mapping) and "noul" in answer:
        return float(answer["noul"])
    raise TypesafeRouterError("noul answer missing .noul")


def _choice_value(answer: Any) -> tuple[str, float, dict[str, float]]:
    choice = getattr(answer, "choice", None)
    confidence = getattr(answer, "confidence", None)
    probabilities = getattr(answer, "probabilities", None)
    if isinstance(answer, Mapping):
        choice = answer.get("choice") if choice is None else choice
        confidence = answer.get("confidence") if confidence is None else confidence
        probabilities = answer.get("probabilities") if probabilities is None else probabilities
    if choice is None:
        raise TypesafeRouterError("choice answer missing .choice")
    return str(choice), float(confidence or 0.0), dict(probabilities or {})


def _score_value(answer: Any, *, n_levels: int, legend_fallback: Mapping[int, str]) -> tuple[float, dict[int, str]]:
    score = getattr(answer, "score", None)
    legend = getattr(answer, "legend", None)
    if isinstance(answer, Mapping):
        score = answer.get("score") if score is None else score
        legend = answer.get("legend") if legend is None else legend
    if score is None:
        raise TypesafeRouterError("score answer missing .score")
    value = float(score)
    if value < 0 or value > max(n_levels - 1, 0):
        raise TypesafeRouterError(f"score rubric index {value} outside [0, {n_levels - 1}]")
    if isinstance(legend, Mapping):
        parsed = {int(key): str(item) for key, item in legend.items()}
    else:
        parsed = dict(legend_fallback)
    return value, parsed


def answers_from_response(response: Any) -> dict[str, Any]:
    """Project System One answers. Score stays a rubric index. No Lean text."""

    choices = getattr(response, "choices", None) or {}
    nouls = getattr(response, "nouls", None) or {}
    scores = getattr(response, "scores", None) or {}
    usage = dict(getattr(response, "usage", None) or {})
    family, family_confidence, family_probs = _choice_value(choices["rewrite_family"])
    neighbor = None
    if "neighbor_style_match" in choices:
        neighbor, _, _ = _choice_value(choices["neighbor_style_match"])
    likely_shorter, likely_legend = _score_value(
        scores["likely_shorter"],
        n_levels=len(LIKELY_SHORTER_CRITERIA),
        legend_fallback=LIKELY_SHORTER_LEGEND,
    )
    elab_risk, elab_legend = _score_value(
        scores["elab_risk_if_automated"],
        n_levels=len(ELAB_RISK_CRITERIA),
        legend_fallback=ELAB_RISK_LEGEND,
    )
    return {
        "family": family,
        "family_confidence": family_confidence,
        "family_probs": family_probs,
        "hammer_before_llm": _noul_value(nouls["hammer_before_llm"]),
        "reference_already_tight": _noul_value(nouls["reference_already_tight"]),
        "likely_shorter": likely_shorter,
        "likely_shorter_legend": likely_legend,
        "likely_shorter_is_rubric_index": True,
        "elab_risk": elab_risk,
        "elab_risk_legend": elab_legend,
        "version_fragile": _noul_value(nouls["version_fragile"]),
        "putnam_aesop_plausible": _noul_value(nouls["putnam_aesop_plausible"]),
        "calc_structure_worth_keeping": _noul_value(nouls["calc_structure_worth_keeping"]),
        "statement_in_proof_duplicated": _noul_value(nouls["statement_in_proof_duplicated"]),
        "uses_sorry_or_admit": _noul_value(nouls["uses_sorry_or_admit"]),
        "neighbor_style_match": neighbor,
        "spend_llm": _noul_value(nouls["spend_llm"]),
        "usage": usage,
        "jev_generated_lean": False,
        "lean_text": None,
        "tactics": None,
        "proof_text": None,
        "arena_score": None,
    }


def should_call_leanstral(answers: Optional[Mapping[str, Any]], rec: Mapping[str, Any]) -> bool:
    """v2 helper. Loop v1 calls Leanstral whenever docker0 /health is up."""

    if answers is None:
        return int(rec.get("proof_length") or 0) >= 400
    if float(answers["family_confidence"]) < 0.5:
        return int(rec.get("proof_length") or 0) >= 800
    if float(answers["reference_already_tight"]) >= 0.8 and float(answers["likely_shorter"]) < 1.0:
        return False
    if float(answers["hammer_before_llm"]) >= 0.7 and float(answers["spend_llm"]) < 0.4:
        return False
    if rec.get("source") == "physlib" and float(answers["calc_structure_worth_keeping"]) >= 0.6:
        return True
    if rec.get("source") == "putnambench" and float(answers["putnam_aesop_plausible"]) >= 0.6:
        return float(answers["spend_llm"]) >= 0.45
    return float(answers["spend_llm"]) >= 0.45 or answers["family"] == "custom"


def default_fixture_answers() -> dict[str, Any]:
    """CI answers: rubric level 0 plus a tight reference. Not live Jev."""

    return {
        "rewrite_family": "have_chain",
        "hammer_before_llm": 0.31,
        "reference_already_tight": 0.91,
        "likely_shorter": 0.0,
        "elab_risk_if_automated": 1.0,
        "version_fragile": 0.22,
        "putnam_aesop_plausible": 0.18,
        "calc_structure_worth_keeping": 0.12,
        "statement_in_proof_duplicated": 0.05,
        "uses_sorry_or_admit": 0.02,
        "neighbor_style_match": "none",
        "spend_llm": 0.21,
    }


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
        self.env = dict(os.environ if env is None else env)
        self.official_track2 = official_track2_requested(flag=official_track2, env=self.env)
        self.mode = resolve_typesafe_mode(flag=mode, env=self.env, official_track2=self.official_track2)
        self.client_factory = client_factory
        self.model = model
        self.require_key = require_key and client_factory is None

    @property
    def enabled(self) -> bool:
        return self.mode in {"distill", "inloop"} and not self.official_track2

    def route(
        self,
        state: Mapping[str, Any],
        *,
        neighbor_names: Sequence[str] = (),
    ) -> RouteResult:
        if not self.enabled:
            reason = "official_track2_off" if self.official_track2 else "typesafe_off"
            return RouteResult(
                skipped=True,
                reason=reason,
                mode=self.mode,
                official_track2=self.official_track2,
                model=self.model,
            )
        loaded = _import_typesafe_inference()
        configured = key_configured(self.env)
        using_fixture = self.client_factory is not None
        if self.require_key and not configured and not using_fixture:
            return RouteResult(
                skipped=True,
                reason="no_key",
                mode=self.mode,
                official_track2=self.official_track2,
                model=self.model,
            )
        if not using_fixture and not loaded["available"]:
            return RouteResult(
                skipped=True,
                reason="typesafe_inference_missing",
                mode=self.mode,
                official_track2=self.official_track2,
                model=self.model,
            )
        questions = instantiate_questions(
            ROUTE_QUESTION_SPEC,
            choice=loaded.get("Choice") if not using_fixture else None,
            noul=loaded.get("Noul") if not using_fixture else None,
            score=loaded.get("Score") if not using_fixture else None,
            neighbor_names=neighbor_names,
        )
        factory = self.client_factory or loaded["TypeSafeClient"]
        started = time.perf_counter()
        client = factory(model=self.model)
        if hasattr(client, "__enter__"):
            with client as opened:
                response = opened.system_one(state, questions)
        else:
            response = client.system_one(state, questions)
        wall_ms = (time.perf_counter() - started) * 1000.0
        extracted = answers_from_response(response)
        return RouteResult(
            skipped=False,
            reason="routed",
            mode=self.mode,
            official_track2=self.official_track2,
            family=extracted["family"],
            family_confidence=extracted["family_confidence"],
            family_probs=extracted["family_probs"],
            hammer_before_llm=extracted["hammer_before_llm"],
            reference_already_tight=extracted["reference_already_tight"],
            likely_shorter=extracted["likely_shorter"],
            likely_shorter_legend=extracted["likely_shorter_legend"],
            elab_risk=extracted["elab_risk"],
            elab_risk_legend=extracted["elab_risk_legend"],
            version_fragile=extracted["version_fragile"],
            putnam_aesop_plausible=extracted["putnam_aesop_plausible"],
            calc_structure_worth_keeping=extracted["calc_structure_worth_keeping"],
            statement_in_proof_duplicated=extracted["statement_in_proof_duplicated"],
            uses_sorry_or_admit=extracted["uses_sorry_or_admit"],
            neighbor_style_match=extracted["neighbor_style_match"],
            spend_llm=extracted["spend_llm"],
            usage=extracted["usage"],
            wall_ms=wall_ms,
            called_typesafe=True,
            used_fixture=using_fixture,
            model=self.model,
            jev_generated_lean=False,
        )


def distill_record(
    state: Mapping[str, Any],
    result: RouteResult,
    *,
    lean_outcome: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Log (features, Jev answers, Lean outcome). Does not generate Lean."""

    problem = state.get("problem") if isinstance(state.get("problem"), Mapping) else {}
    return {
        "schema": "lra-typesafe-distill/v1",
        "mode": "distill",
        "features": {
            "name": problem.get("name"),
            "source": problem.get("source"),
            "n_toolchains": problem.get("n_toolchains"),
            "proof_length": problem.get("proof_length"),
            "num_lines": problem.get("num_lines"),
            "has_repo": problem.get("has_repo"),
        },
        "answers": result.as_dict(),
        "lean_outcome": lean_outcome,
        "jev_generated_lean": False,
        "score_is_rubric_index": True,
        "official_track2": False,
        "api_key_present_in_record": False,
        "policy_path": DISTILL_POLICY_RELATIVE,
        "writes_policy_by_default": False,
        "arena_score": None,
    }


def _imported_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".", 1)[0])
                names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
    return names


def _call_func_names(source: str) -> set[str]:
    names: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _assigned_constant(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = node.value
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value = node.value
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                if isinstance(value, ast.Constant):
                    return value.value
    return None


def _numeric_score_assignments(source: str) -> list[str]:
    tree = ast.parse(source)
    issues: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in FORBIDDEN_SCORE_NAMES:
            value = node.value
            if isinstance(value, ast.Constant) and value.value is None:
                continue
            issues.append(f"keyword {node.arg} at line {getattr(node, 'lineno', 0)}")
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in FORBIDDEN_SCORE_NAMES:
                value = node.value
                if isinstance(value, ast.Constant) and value.value is None:
                    continue
                issues.append(f"ann {node.target.id} at line {getattr(node, 'lineno', 0)}")
    return issues


def audit_source(source: Optional[str] = None) -> dict[str, Any]:
    text = Path(__file__).read_text(encoding="utf-8") if source is None else source
    tree = ast.parse(text)
    imported = _imported_names(text)
    calls = _call_func_names(text)
    forbidden_imports = sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES)
    forbidden_calls = sorted(name for name in calls if name in FORBIDDEN_CALLS)
    score_issues = _numeric_score_assignments(text)
    uses_lock_ex = any(
        isinstance(node, ast.Attribute) and node.attr == "LOCK_EX" for node in ast.walk(tree)
    )
    return {
        "imported_names": sorted(imported),
        "forbidden_imports": forbidden_imports,
        "forbidden_calls": forbidden_calls,
        "numeric_score_assignments": score_issues,
        "imports_typesafe_inference": "ipfs_accelerate_py.typesafe_inference" in imported,
        "imports_choice": "Choice" in imported,
        "imports_noul": "Noul" in imported,
        "imports_score": "Score" in imported,
        "imports_typesafe_client": "TypeSafeClient" in imported,
        "imports_typesafe_configured": "typesafe_configured" in imported,
        "imports_typesafe_sdk": "typesafe_sdk" in imported or "typesafe" in imported,
        "imports_llm_router": "llm_router" in imported,
        "imports_generate_text": "generate_text" in imported,
        "calls_generate_text": "generate_text" in calls,
        "calls_system_one": "system_one" in calls,
        "jev_generates_lean_constant": _assigned_constant(tree, "JEV_GENERATES_LEAN"),
        "score_is_rubric_index_constant": _assigned_constant(tree, "SCORE_IS_RUBRIC_INDEX"),
        "default_mode_constant": _assigned_constant(tree, "DEFAULT_MODE"),
        "loop_v1_typesafe_constant": _assigned_constant(tree, "LOOP_V1_TYPESAFE"),
        "official_track2_mode_constant": _assigned_constant(tree, "OFFICIAL_TRACK2_MODE"),
        "uses_lock_ex": uses_lock_ex,
        "ok": (
            "ipfs_accelerate_py.typesafe_inference" in imported
            and "Choice" in imported
            and "TypeSafeClient" in imported
            and "typesafe_sdk" not in imported
            and "typesafe" not in imported
            and "llm_router" not in imported
            and "generate_text" not in imported
            and "generate_text" not in calls
            and not forbidden_imports
            and not forbidden_calls
            and not score_issues
            and not uses_lock_ex
            and _assigned_constant(tree, "JEV_GENERATES_LEAN") is False
            and _assigned_constant(tree, "SCORE_IS_RUBRIC_INDEX") is True
            and _assigned_constant(tree, "DEFAULT_MODE") == "off"
            and _assigned_constant(tree, "LOOP_V1_TYPESAFE") == "off"
            and _assigned_constant(tree, "OFFICIAL_TRACK2_MODE") == "off"
        ),
    }


def _load_named_record(name: str, path: Optional[Path] = None) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    raw, digest, records = lra_splice.load_warmup_records(path)
    del raw
    for record in records:
        if record.get("name") == name:
            return record, records, digest
    raise TypesafeRouterError(f"unknown warm-up problem: {name}")


def _neighbors_for(record: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    retrieval = lra_retrieve.retrieve_record(record, records)
    return lra_retrieve.prompt_neighbors(retrieval, k=NEIGHBOR_K)


def route_named(
    name: str,
    *,
    mode: Optional[str] = None,
    official_track2: bool = False,
    fixture: bool = False,
    path: Optional[Path] = None,
    lean_outcome: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    record, records, digest = _load_named_record(name, path)
    neighbors = _neighbors_for(record, records)
    state = problem_state(record, neighbors=neighbors)
    factory = None
    if fixture:
        factory = lambda **kwargs: FixtureClient(answers=default_fixture_answers(), **kwargs)
    router = TypeSafeLraRouter(mode=mode, official_track2=official_track2, client_factory=factory)
    result = router.route(state, neighbor_names=[item["name"] for item in neighbors])
    payload = result.as_dict()
    payload["ok"] = True
    payload["name"] = name
    payload["source"] = record.get("source")
    payload["warmup_jsonl_sha256"] = digest
    payload["n_neighbors"] = len(neighbors)
    payload["route_question_keys"] = list(ROUTE_QUESTION_KEYS)
    payload["should_call_leanstral_v2"] = (
        None if result.skipped else should_call_leanstral(payload, record)
    )
    if router.mode == "distill" and not result.skipped:
        payload["distill"] = distill_record(state, result, lean_outcome=lean_outcome)
    payload["imports_typesafe_inference"] = True
    payload["imports_typesafe_sdk"] = False
    payload["jev_generates_lean"] = False
    payload["score_is_rubric_index"] = True
    payload["official_track2_stays_off"] = True
    payload["default_mode"] = DEFAULT_MODE
    return payload


def plan_view(
    *,
    mode: Optional[str] = None,
    official_track2: bool = False,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    resolved = resolve_typesafe_mode(flag=mode, env=env, official_track2=official_track2)
    loaded = _import_typesafe_inference()
    catalog = instantiate_questions(ROUTE_QUESTION_SPEC)
    score_levels = {
        name: list(spec["criteria"])
        for name, spec in ROUTE_QUESTION_SPEC.items()
        if spec["type"] == "score"
    }
    return {
        "ok": True,
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "lrah": LRAH_ID,
        "default_mode": DEFAULT_MODE,
        "resolved_mode": resolved,
        "allowed_modes": list(ALLOWED_MODES),
        "official_track2": official_track2_requested(flag=official_track2, env=env),
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
        "likely_shorter_legend": {str(key): value for key, value in LIKELY_SHORTER_LEGEND.items()},
        "score_is_rubric_index": SCORE_IS_RUBRIC_INDEX,
        "score_levels": score_levels,
        "jev_generates_lean": JEV_GENERATES_LEAN,
        "typesafe_systemone_url": TYPESAFE_SYSTEMONE_URL,
        "router_posts_to_typesafe": False,
        "imports_typesafe_inference": True,
        "imports_typesafe_sdk": False,
        "typesafe_inference_available": loaded["available"],
        "typesafe_inference_exists": loaded["exists"],
        "typesafe_inference_error": loaded["error"],
        "typesafe_inference_path": loaded["path"],
        "key_configured": key_configured(env),
        "key_env_names": list(KEY_ENV_NAMES),
        "catalog_kinds": {name: question.kind for name, question in catalog.items()},
        "n_catalog": len(catalog),
        "distill_policy_path": DISTILL_POLICY_RELATIVE,
        "writes_policy_by_default": False,
        "frozen_warmup_sha256": FROZEN_WARMUP_SHA256,
        "arena_score": None,
        "compiled": False,
        "llama_server_started": False,
    }


def self_check(path: Optional[Path] = None) -> dict[str, Any]:
    """CI fixtures without a live key. Does not POST and does not generate Lean."""

    source = Path(__file__).read_text(encoding="utf-8")
    jsonl = Path(path) if path is not None else WARMUP_JSONL
    before = hashlib.sha256(jsonl.read_bytes()).hexdigest()
    raw, digest, records = lra_splice.load_warmup_records(jsonl)
    after = hashlib.sha256(jsonl.read_bytes()).hexdigest()
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

    custom_fixture = FixtureClient(
        answers={
            **default_fixture_answers(),
            "rewrite_family": "custom",
            "reference_already_tight": 0.2,
            "likely_shorter": 2.0,
            "spend_llm": 0.8,
            "hammer_before_llm": 0.1,
        }
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

    serialized = json.dumps({"distill": distill_log, "route": distill_result.as_dict()}, sort_keys=True)
    key_leak = any(token in serialized for token in ("BEGIN SECRET", "sk-live-", "sk-prod-"))

    report = {
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
        "likely_shorter_legend_0": (distill_result.likely_shorter_legend or {}).get(0),
        "likely_shorter_is_rubric_index": distill_result.likely_shorter_is_rubric_index,
        "likely_shorter_not_probability": distill_result.likely_shorter == 0.0
        and (distill_result.likely_shorter_legend or {}).get(0) == "longer or same",
        "custom_likely_shorter_level_2": custom_result.likely_shorter,
        "distill_log": distill_log,
        "catalog_keys": list(catalog.keys()),
        "score_questions": score_questions,
        "likely_shorter_criteria": list(likely_criteria),
        "n_score_levels": len(likely_criteria),
        "neighbor_names": neighbor_names,
        "truncated_over_budget": "lra-truncated" in truncated_lines or len(truncated) <= CHAR_BUDGET,
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
        "warmup_path": str(jsonl.relative_to(REPO_ROOT)),
    }
    report["ok"] = bool(
        report["n_records"] == WARMUP_N
        and report["jsonl_unchanged"]
        and audit["ok"]
        and report["default_mode_is_off"]
        and report["distill_uses_lra_typesafe_distill"]
        and report["inloop_uses_lra_typesafe_inloop"]
        and report["official_track2_stays_off"]
        and report["off_skipped"]
        and report["no_key_skipped"]
        and report["distill_called"]
        and report["official_stayed_off"]
        and report["official_did_not_call"]
        and report["skip_llm_on_rubric_level_0"]
        and report["spend_llm_on_custom_level_2"]
        and report["likely_shorter_not_probability"]
        and report["likely_shorter_level_0"] == 0.0
        and report["custom_likely_shorter_level_2"] == 2.0
        and report["imports_typesafe_inference"]
        and not report["imports_typesafe_sdk"]
        and report["jev_generated_lean"] is False
        and distill_result.jev_generated_lean is False
        and distill_result.lean_text is None
        and distill_result.tactics is None
        and distill_result.proof_text is None
        and distill_result.arena_score is None
        and distill_log["jev_generated_lean"] is False
        and distill_log["api_key_present_in_record"] is False
        and unknown_closed
        and not key_leak
        and report["catalog_keys"] == list(ROUTE_QUESTION_KEYS)
        and report["n_score_levels"] == 3
        and report["compiled"] is False
        and report["arena_score"] is None
    )
    return report


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
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.plan:
        payload = plan_view(mode=args.typesafe, official_track2=args.official_track2)
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if payload.get("ok") else 1
    if args.route:
        if not args.name:
            parser.error("--route requires --name")
        try:
            payload = route_named(
                args.name,
                mode=args.typesafe,
                official_track2=args.official_track2,
                fixture=args.fixture,
                path=args.jsonl,
            )
        except (TypesafeRouterError, lra_splice.SpliceError, lra_retrieve.RetrieveError) as exc:
            json.dump(
                {
                    "ok": False,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "arena_score": None,
                    "jev_generated_lean": False,
                },
                sys.stdout,
                indent=2,
                sort_keys=True,
            )
            sys.stdout.write("\n")
            return 1
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if payload.get("ok") else 1
    if args.self_check or argv is None or argv == []:
        report = self_check(args.jsonl)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    parser.error("choose --self-check, --plan, or --route")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
