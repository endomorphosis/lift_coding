#!/usr/bin/env python3
"""PCA/MCA-guided TypeSafe fan-out of AST refactor drafts.

Principal components = dominant proof style (keep). Minor components =
residual/idiosyncratic variance (candidates for simplification). Those
directions are labeled as classical compiler families:

- dead_code: unused have/obtain/rename_i, simp-at before simp_all
- search_space: extra search tactics; never drop case arms
- loop_invariant: have-facts after induction
- strength_reduction: simp-at runs → simp_all
- algebraic_simplification: rw/calc/ring/omega chains → simp/omega

TypeSafe ranks the drafts. Lake is the oracle. Jev does not write Lean.
Not official Track 2. Not an Arena ranking. Never LOCK_EX.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
ROOT_ACCEL = Path("/home/barberb/lift_coding/external/ipfs_accelerate")
KEYFILE = Path.home() / ".config/ipfs_accelerate_py/typesafe.env"
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
LAKE_READY = (
    "CallElimCorrect.substOldPostSubset",
    "CallElimCorrect.extractedOldExprInVars",
    "Core.InitsUpdatesComm",
    "Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress",
    "Cslib.SKI.parallelReduction_diamond",
    "Cslib.CCS.bisimilarity_congr_choice",
    "putnam_1964_a4",
    "putnam_1964_b2",
    "putnam_1995_a3",
    "fundamental_theorem_of_variational_calculus'",
    "Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema",
    "FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time",
    "Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius",
    "Binius.BinaryBasefold.fold_advances_evaluation_poly",
    "interleaved_affine_gaps_imply_tensor_gaps",
)

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import draft_fanout as lra_fan  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402

FROZEN_WARMUP_SHA256 = lra_splice.FROZEN_WARMUP_SHA256
PROTOCOL = "LRA/v1"
PR_ID = "PR-9c"
FEATURE_NAMES = (
    "n_cases",
    "n_simp_at",
    "n_simp_all",
    "n_have",
    "n_obtain",
    "n_rename_i",
    "n_induction",
    "n_calc",
    "n_exact",
    "n_apply",
    "n_rw",
    "n_intro",
    "n_ring",
    "n_omega",
    "n_linarith",
    "n_tokens",
    "n_lines",
    "max_indent",
    "n_blank",
)
FAMILY_FEATURES = {
    "dead_code": ("n_have", "n_obtain", "n_rename_i", "n_simp_at"),
    "search_space": ("n_apply", "n_intro", "n_cases"),
    "loop_invariant": ("n_have", "n_induction"),
    "strength_reduction": ("n_simp_at", "n_simp_all", "n_rw"),
    "algebraic_simplification": ("n_rw", "n_calc", "n_ring", "n_omega", "n_linarith", "n_simp_all"),
}
_RENAME = re.compile(r"^( *)rename_i ")
_HAVE = re.compile(r"^( *)have ")
_RW_BRACKET = re.compile(r"^(?P<indent> *)rw \[([^\]]+)\]\s*$")
FORBIDDEN_IMPORT_NAMES = frozenset({"fcntl", "generate_text", "typesafe_sdk"})


@dataclass(frozen=True)
class FeatureRow:
    name: str
    source: str
    vector: tuple[float, ...]
    counts: dict[str, float]


def load_keyfile() -> None:
    if not KEYFILE.is_file():
        return
    for line in KEYFILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip())


def pin_typesafe_path() -> None:
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    text = str(ROOT_ACCEL)
    if text in sys.path:
        sys.path.remove(text)
    sys.path.insert(0, text)
    lra_fan.pin_typesafe_path()
    lra_fan.ACCEL_ROOT = ROOT_ACCEL
    lra_fan.TYPESAFE_INFERENCE_PATH = ROOT_ACCEL / "ipfs_accelerate_py" / "typesafe_inference.py"


def count_tactics(tactics: str) -> dict[str, float]:
    lines = tactics.splitlines()
    counts = {name: 0.0 for name in FEATURE_NAMES}
    counts["n_cases"] = float(len(lra_fan.case_spans(tactics)))
    counts["n_lines"] = float(len(lines))
    counts["n_tokens"] = float(lra_loop.token_count(tactics))
    counts["n_blank"] = float(sum(1 for line in lines if not line.strip()))
    counts["max_indent"] = float(max((len(line) - len(line.lstrip()) for line in lines), default=0))
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("simp at "):
            counts["n_simp_at"] += 1
        if stripped.startswith("simp_all") or stripped == "simp" or stripped.startswith("simp ["):
            counts["n_simp_all"] += 1
        if stripped.startswith("have "):
            counts["n_have"] += 1
        if stripped.startswith("obtain "):
            counts["n_obtain"] += 1
        if stripped.startswith("rename_i "):
            counts["n_rename_i"] += 1
        if stripped.startswith("induction ") or stripped.startswith("induction\n"):
            counts["n_induction"] += 1
        if stripped.startswith("calc"):
            counts["n_calc"] += 1
        if stripped.startswith("exact "):
            counts["n_exact"] += 1
        if stripped.startswith("apply "):
            counts["n_apply"] += 1
        if stripped.startswith("rw ") or stripped.startswith("rw["):
            counts["n_rw"] += 1
        if stripped.startswith("intro") or stripped.startswith("intros "):
            counts["n_intro"] += 1
        if stripped == "ring" or stripped.startswith("ring "):
            counts["n_ring"] += 1
        if stripped == "omega" or stripped.startswith("omega "):
            counts["n_omega"] += 1
        if stripped.startswith("linarith") or stripped.startswith("nlinarith"):
            counts["n_linarith"] += 1
    return counts


def feature_row(record: Mapping[str, Any]) -> FeatureRow:
    tactics = lra_fan.tactic_block(record)
    counts = count_tactics(tactics)
    vector = tuple(float(counts[name]) for name in FEATURE_NAMES)
    return FeatureRow(
        name=str(record.get("name") or ""),
        source=str(record.get("source") or ""),
        vector=vector,
        counts=counts,
    )


def fit_pca_mca(rows: Sequence[FeatureRow], *, n_principal: int = 3, n_minor: int = 3) -> dict[str, Any]:
    matrix = np.asarray([row.vector for row in rows], dtype=float)
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std[std == 0] = 1.0
    zscore = (matrix - mean) / std
    _, singular, vt = np.linalg.svd(zscore, full_matrices=False)
    n_comp = int(vt.shape[0])
    n_principal = max(1, min(int(n_principal), n_comp))
    n_minor = max(1, min(int(n_minor), n_comp))
    principal = vt[:n_principal]
    minor = vt[-n_minor:]
    explained = (singular ** 2)
    explained = explained / float(explained.sum()) if float(explained.sum()) else explained
    return {
        "n_rows": int(matrix.shape[0]),
        "n_features": int(matrix.shape[1]),
        "feature_names": list(FEATURE_NAMES),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "singular_values": singular.tolist(),
        "explained_ratio": explained.tolist(),
        "principal": [
            {"index": index, "explained": float(explained[index]), "loadings": dict(zip(FEATURE_NAMES, component.tolist()))}
            for index, component in enumerate(principal)
        ],
        "minor": [
            {
                "index": n_comp - n_minor + index,
                "explained": float(explained[n_comp - n_minor + index]),
                "loadings": dict(zip(FEATURE_NAMES, component.tolist())),
            }
            for index, component in enumerate(minor)
        ],
        "zscore": zscore,
        "vt": vt,
    }


def amenable_families(counts: Mapping[str, float], model: Mapping[str, Any], *, top_k: int = 5) -> list[dict[str, Any]]:
    """Features that load on minor components *and* are present in this proof."""

    std = np.asarray(model["std"], dtype=float)
    mean = np.asarray(model["mean"], dtype=float)
    vector = np.asarray([float(counts[name]) for name in FEATURE_NAMES], dtype=float)
    zscore = (vector - mean) / std
    scores: dict[str, float] = {name: 0.0 for name in FEATURE_NAMES}
    for component in model["minor"]:
        loadings = component["loadings"]
        for name in FEATURE_NAMES:
            scores[name] += abs(float(loadings[name]) * float(zscore[FEATURE_NAMES.index(name)]))
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    families: list[dict[str, Any]] = []
    for family, features in FAMILY_FEATURES.items():
        hit = [name for name in features if counts.get(name, 0) > 0]
        if not hit:
            continue
        families.append(
            {
                "family": family,
                "features": hit,
                "mca_score": float(sum(scores[name] for name in hit)),
                "present": {name: counts[name] for name in hit},
            }
        )
    families.sort(key=lambda item: item["mca_score"], reverse=True)
    return families[:top_k]


def drop_rename_i(text: str) -> str:
    """Drop rename_i lines whose binders are not referenced later."""

    import binder_use as lra_bind

    return lra_bind.drop_unused_binders(text, kinds=("rename_i",))


def drop_have_after_induction(text: str) -> str:
    import binder_use as lra_bind

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    after_induction = False
    offset = 0
    for line in lines:
        start, end = offset, offset + len(line)
        stripped = line.strip()
        if stripped.startswith("induction "):
            after_induction = True
            out.append(line)
            offset = end
            continue
        if after_induction and _HAVE.match(line.rstrip("\n")):
            if not lra_bind.safe_to_drop_span(text, start, end, line.rstrip("\n")):
                out.append(line)
            offset = end
            continue
        out.append(line)
        offset = end
    return "".join(out).strip("\n")


def collapse_rw_to_simp(text: str) -> str:
    """Strength-reduce consecutive ``rw [lemmas]`` into one ``simp [lemmas]``."""

    lines = text.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        match = _RW_BRACKET.match(lines[index])
        if not match:
            out.append(lines[index])
            index += 1
            continue
        indent = match.group("indent")
        lemmas: list[str] = []
        while index < len(lines):
            nxt = _RW_BRACKET.match(lines[index])
            if not nxt or nxt.group("indent") != indent:
                break
            lemmas.extend(part.strip() for part in nxt.group(2).split(",") if part.strip())
            index += 1
        if len(lemmas) >= 2:
            out.append(f"{indent}simp [{', '.join(lemmas)}]")
        else:
            out.append(f"{indent}rw [{lemmas[0]}]" if lemmas else lines[index - 1])
    return "\n".join(out)


def keep_calc_only(text: str) -> str:
    if not lra_fan._CALC.search(text):
        return text
    kept = [line for line in text.splitlines() if line.strip().startswith("calc") or line.startswith("  ")]
    return "\n".join(kept[:40]) if kept else text


def guided_drafts(
    tactics: str,
    families: Sequence[Mapping[str, Any]],
    counts: Optional[Mapping[str, float]] = None,
) -> list[lra_fan.Draft]:
    drafts: list[lra_fan.Draft] = []
    seen: set[str] = set()
    names = {item["family"] for item in families}
    counts = dict(counts or {})
    if counts.get("n_rw") or counts.get("n_calc") or counts.get("n_omega") or counts.get("n_ring") or counts.get("n_induction"):
        names.add("algebraic_simplification")
    lra_fan._push(drafts, seen, "reference", tactics, ("identity", "pca_keep"))
    import portable_rewrites as lra_port

    for item in lra_port.portable_drafts(tactics):
        lra_fan._push(
            drafts,
            seen,
            str(item.get("family") or "search_space"),
            str(item["tactics"]),
            ("portable", str(item.get("kind") or "")),
        )
    import inits_updates_shorten as lra_ius

    for family, body, ops in lra_ius.pca_mca_ops(tactics):
        lra_fan._push(drafts, seen, family, body, ops)
    import symbol_diffuse as lra_sym

    for family, body, ops in lra_sym.pca_mca_ops(tactics):
        lra_fan._push(drafts, seen, family, body, ops)
    if "strength_reduction" in names or "dead_code" in names:
        lra_fan._push(
            drafts,
            seen,
            "strength_reduction",
            lra_fan.drop_redundant_simp_at(tactics),
            ("drop_redundant_simp_at", "mca"),
        )
        for span_draft in lra_fan.span_preserving_drafts(tactics):
            lra_fan._push(drafts, seen, span_draft.family, span_draft.tactics, span_draft.ops + ("mca_span",))
    if "dead_code" in names:
        import binder_use as lra_bind

        lra_fan._push(
            drafts,
            seen,
            "dead_code",
            lra_bind.drop_unused_binders(tactics),
            ("drop_unused_binders", "mca"),
        )
        lra_fan._push(drafts, seen, "dead_code", drop_rename_i(tactics), ("drop_rename_i", "mca"))
        lra_fan._push(
            drafts,
            seen,
            "dead_code",
            lra_fan.drop_have_obtain(tactics),
            ("drop_have_obtain", "mca"),
        )
    if "loop_invariant" in names:
        lra_fan._push(
            drafts,
            seen,
            "loop_invariant",
            drop_have_after_induction(tactics),
            ("drop_have_after_induction", "mca"),
        )
    if "search_space" in names:
        # Keep every case arm; only drop intros that duplicate the telescope.
        stripped_intros = "\n".join(
            line for line in tactics.splitlines() if not line.strip().startswith("intros ") or "Hin" not in line
        )
        lra_fan._push(drafts, seen, "search_space", stripped_intros, ("drop_intros_hin", "mca"))
    if "algebraic_simplification" in names:
        lra_fan._push(
            drafts,
            seen,
            "algebraic_simplification",
            collapse_rw_to_simp(tactics),
            ("collapse_rw_to_simp", "mca"),
        )
        calc = keep_calc_only(tactics)
        lra_fan._push(drafts, seen, "algebraic_simplification", calc, ("keep_calc", "mca"))
        match = re.search(r"induction (\S+)", tactics)
        if match:
            lra_fan._push(
                drafts,
                seen,
                "algebraic_simplification",
                f"induction {match.group(1)} <;> simp",
                ("induction_simp", "mca"),
            )
    return drafts


def fanout_state(
    record: Mapping[str, Any],
    *,
    features: Mapping[str, float],
    families: Sequence[Mapping[str, Any]],
    drafts: Sequence[lra_fan.Draft],
    pca: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "problem": {"name": record.get("name"), "source": record.get("source")},
        "statement": str(record.get("statement") or "")[:480],
        "ast_features": dict(features),
        "pca_principal": pca["principal"][:2],
        "mca_minor": pca["minor"],
        "amenable": list(families),
        "drafts": lra_fan.draft_catalog(drafts),
        "compiler_families": list(FAMILY_FEATURES),
    }


def fanout_questions(drafts: Sequence[lra_fan.Draft], *, Choice: Any, Noul: Any, Score: Any) -> dict[str, Any]:
    criteria = {
        item.draft_id: f"{item.family}; ops={','.join(item.ops)}; {item.n_chars} chars"
        for item in drafts
    }
    family_criteria = {
        "dead_code": "Drop unused have/obtain/rename_i or simp-at-before-simp_all",
        "search_space": "Shrink intros/apply search; never delete a case arm",
        "loop_invariant": "Drop have-facts after induction",
        "strength_reduction": "Replace simp-at runs with simp_all",
        "algebraic_simplification": "Collapse rw/calc/ring/omega into simp or omega",
        "pca_keep": "Keep the reference; PCA says it is already the dominant style",
        "inits_replay": (
            "Apply the closed Core.InitsUpdatesComm 268→139 kernel sequence. "
            "No LLM. Lake is the oracle."
        ),
        "drop": "Drop a residual binder, named arg, or unused intro",
        "rewrite": "Apply one InitsUpdatesComm shorten kernel (MCA residual)",
        "symbol_diffuse": (
            "Fill a masked Lean operator/symbol from the closed language "
            "($, constructor, intro, all_goals, .update_some) or Leanstral"
        ),
    }
    return {
        "best_compiler_family": Choice(
            instructions=(
                "Which compiler family should lake try first on this AST given PCA/MCA? "
                "Do not write Lean."
            ),
            criteria=family_criteria,
        ),
        "best_first_draft": Choice(
            instructions=(
                "Which draft id should lake-compile first as a refactor of the reference? "
                "Prefer MCA-guided dead_code, strength_reduction, or algebraic_simplification "
                "if they preserve every case arm. Do not write Lean."
            ),
            criteria=criteria,
        ),
        "dead_code_safe": Noul(
            instructions="Is dropping have/obtain/rename_i/simp-at-before-simp_all likely to preserve meaning?"
        ),
        "strength_reduction_safe": Noul(
            instructions="Is replacing simp-at runs with simp_all likely to compile?"
        ),
        "loop_invariant_safe": Noul(
            instructions="Are have-facts after induction redundant loop invariants that can be dropped?"
        ),
        "search_space_safe": Noul(
            instructions="Can intros/search tactics shrink without deleting a case arm?"
        ),
        "algebraic_simplification_safe": Noul(
            instructions="Can rw/calc/ring/omega chains be replaced by simp or omega without changing the theorem?"
        ),
        "likely_token_cut": Score(
            instructions="How large a source-token cut is plausible if the best MCA draft replaces the reference?",
            criteria=list(lra_fan.LIKELY_SHORTER_CRITERIA),
        ),
    }


def redact(payload: Any) -> Any:
    return lra_fan.redact(payload)


def rank_problem(
    record: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    model: Mapping[str, Any],
    *,
    live: bool,
) -> dict[str, Any]:
    tactics = lra_fan.tactic_block(record)
    features = count_tactics(tactics)
    families = amenable_families(features, model)
    drafts = guided_drafts(tactics, families, features)
    state = fanout_state(record, features=features, families=families, drafts=drafts, pca=model)
    payload = {
        "name": record.get("name"),
        "source": record.get("source"),
        "n_drafts": len(drafts),
        "families": [item["family"] for item in families],
        "amenable": families,
        "features": features,
        "draft_ids": [item.draft_id for item in drafts],
        "jev_generated_lean": False,
        "arena_score": None,
    }
    if not live:
        payload["live"] = False
        payload["catalog"] = lra_fan.draft_catalog(drafts)
        return payload
    pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        payload["live"] = False
        payload["error"] = "TYPESAFE_API_KEY is not set"
        payload["catalog"] = lra_fan.draft_catalog(drafts)
        return payload
    client = TypeSafeClient(timeout=60.0)
    started = time.perf_counter()
    result = client.system_one(state, fanout_questions(drafts, Choice=Choice, Noul=Noul, Score=Score))
    best = (getattr(result, "choices", None) or {}).get("best_first_draft")
    nouls = getattr(result, "nouls", None) or {}
    scores = getattr(result, "scores", None) or {}
    probabilities = dict(getattr(best, "probabilities", None) or {})
    payload.update(
        {
            "live": True,
            "model": getattr(result, "model", None),
            "usage": dict(getattr(result, "usage", None) or {}),
            "wall_ms": (time.perf_counter() - started) * 1000.0,
            "best_compiler_family": getattr(
                (getattr(result, "choices", None) or {}).get("best_compiler_family"), "choice", None
            ),
            "best_first_draft": getattr(best, "choice", None),
            "best_confidence": getattr(best, "confidence", None),
            "dead_code_safe": getattr(nouls.get("dead_code_safe"), "noul", None),
            "strength_reduction_safe": getattr(nouls.get("strength_reduction_safe"), "noul", None),
            "loop_invariant_safe": getattr(nouls.get("loop_invariant_safe"), "noul", None),
            "search_space_safe": getattr(nouls.get("search_space_safe"), "noul", None),
            "algebraic_simplification_safe": getattr(nouls.get("algebraic_simplification_safe"), "noul", None),
            "likely_token_cut": getattr(scores.get("likely_token_cut"), "score", None),
            "top": lra_fan.rank_choice(probabilities, drafts),
        }
    )
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
    return {
        "forbidden_imports": sorted(name for name in imported if name in FORBIDDEN_IMPORT_NAMES),
        "uses_lock_ex": lock_ex,
        "ok": not lock_ex and "generate_text" not in imported,
    }


def self_check() -> dict[str, Any]:
    _raw, digest, records = lra_splice.load_warmup_records()
    rows = [feature_row(record) for record in records]
    model = fit_pca_mca(rows)
    audit = audit_source()
    sample = next(record for record in records if record.get("name") == LAKE_READY[0])
    ranked = rank_problem(sample, records, {k: v for k, v in model.items() if k not in {"zscore", "vt"}}, live=False)
    ok = (
        audit["ok"]
        and digest == FROZEN_WARMUP_SHA256
        and len(rows) == 15
        and ranked["n_drafts"] >= 2
        and "dead_code" in FAMILY_FEATURES
        and "strength_reduction" in FAMILY_FEATURES
        and "algebraic_simplification" in FAMILY_FEATURES
    )
    public_model = {key: value for key, value in model.items() if key not in {"zscore", "vt"}}
    return {
        "ok": ok,
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "warmup_jsonl_sha256": digest,
        "audit": audit,
        "pca": public_model,
        "sample": ranked,
        "jev_generated_lean": False,
        "arena_score": None,
    }


def live_rank(names: Sequence[str]) -> dict[str, Any]:
    load_keyfile()
    pin_typesafe_path()
    _raw, digest, records = lra_splice.load_warmup_records()
    rows = [feature_row(record) for record in records]
    model = fit_pca_mca(rows)
    public_model = {key: value for key, value in model.items() if key not in {"zscore", "vt"}}
    started = time.perf_counter()
    canaries = []
    for name in names:
        record = next((item for item in records if item.get("name") == name), None)
        if record is None:
            canaries.append({"name": name, "error": "unknown warm-up problem", "arena_score": None})
            continue
        canaries.append(rank_problem(record, records, public_model, live=True))
    return redact(
        {
            "schema": "lra-pca-mca-fanout/v1",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "warmup_jsonl_sha256": digest,
            "pca": public_model,
            "jev_generated_lean": False,
            "typesafe_key_in_receipt": False,
            "lock_ex": False,
            "official_track2": False,
            "arena_score": None,
            "wall_ms": (time.perf_counter() - started) * 1000.0,
            "canaries": canaries,
        }
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--lake", action="store_true", help="lake-compile TypeSafe top drafts on baked clones")
    parser.add_argument("--names", default=",".join(LAKE_READY))
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--state-root", type=Path, default=Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_check or not args.live:
        report = self_check()
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    names = [item.strip() for item in str(args.names).split(",") if item.strip()]
    report = live_rank(names)
    if args.lake:
        import track1_keepbest as lra_kb

        _raw, _digest, records = lra_splice.load_warmup_records()
        for row in report.get("canaries") or []:
            if not row.get("live") or row.get("name") not in LAKE_READY:
                continue
            record = next(item for item in records if item.get("name") == row["name"])
            tactics = lra_fan.tactic_block(record)
            if str(record.get("source") or "") == "putnambench":
                restore = b""
            else:
                clone = lra_kb.lra_cw.clone_dir(str(record["url"]), args.state_root)
                dest = clone / lra_kb.lra_cw.source_relpath(record)
                if not dest.is_file():
                    row["lake"] = {"error": "missing_clone_file"}
                    continue
                restore = dest.read_bytes()
            catalog = {item["id"]: item for item in (row.get("catalog") or [])}
            # Reconstruct tactics for top picks from guided_drafts.
            families = row.get("amenable") or []
            drafts = guided_drafts(tactics, families, row.get("features") or {})
            by_id = {item.draft_id: item for item in drafts}
            family_pick = row.get("best_compiler_family")
            picks = [row.get("best_first_draft")] + [item.get("id") for item in (row.get("top") or [])[:3]]
            for draft in drafts:
                if "inits_replay" in draft.ops or draft.family == "inits_replay":
                    picks.insert(0, draft.draft_id)
                if draft.family in {
                    "algebraic_simplification",
                    "strength_reduction",
                    "pca_keep",
                    "reference",
                    "inits_replay",
                    "rewrite",
                    "drop",
                    "symbol_diffuse",
                }:
                    picks.append(draft.draft_id)
                if family_pick and draft.family == family_pick:
                    picks.append(draft.draft_id)
            seen: set[str] = set()
            lake_rows = []
            for draft_id in picks:
                if len(seen) >= 8:
                    break
                if not draft_id or draft_id in seen or draft_id not in by_id:
                    continue
                seen.add(draft_id)
                draft = by_id[draft_id]
                compiled = lra_kb.compile_tactics(
                    record,
                    draft.tactics,
                    state_root=args.state_root,
                    timeout=180.0,
                    restore=restore,
                )
                lake_rows.append(
                    {
                        "id": draft_id,
                        "family": draft.family,
                        "ops": list(draft.ops),
                        "token_count": compiled.get("token_count"),
                        "theorem_ok": compiled.get("theorem_ok"),
                        "exit_code": compiled.get("exit_code"),
                        "errors": compiled.get("errors"),
                    }
                )
            row["lake"] = {"candidates": lake_rows, "arena_score": None}
            del catalog
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if "apikey_" in text:
        raise SystemExit("refusing to write a receipt that contains an API key")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"pca-mca-fanout-{stamp}.json"
    latest = args.out / "pca-mca-fanout-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all(row.get("live") for row in report.get("canaries") or []),
                "latest": str(latest),
                "picks": [
                    {
                        "name": row.get("name"),
                        "best": row.get("best_first_draft"),
                        "families": row.get("families"),
                        "n_drafts": row.get("n_drafts"),
                    }
                    for row in report.get("canaries") or []
                ],
                "arena_score": None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
