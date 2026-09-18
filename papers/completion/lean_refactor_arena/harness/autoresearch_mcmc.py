#!/usr/bin/env python3
"""TypeSafe autoresearch features to rank MCMC Lean edits.

Follows https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery
at Lean-proof scale: many Noul/Score questions become numeric features;
code combines them (no CatBoost in this tree). Lake is the label.

Jev does not write Lean. Prefix haves stay locked. Not Track 2. Not Arena.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
DEFAULT_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake"
TS_PATH = Path("/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/typesafe_inference.py")
HARDWARE_CLASS = "spark_gb10"
PROTOCOL = "LRA/v1"
PR_ID = "PR-9h"
MAX_JEV = 20

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import mcmc_beam as lra_mcmc  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402

SEED_FEATURES = (
    ("likely_compiles", "noul", "After this edit the Lean file will still lake-compile."),
    ("likely_shorter", "noul", "This edit uses fewer Lean tokens than the current script."),
    ("drops_pca_glue", "noul", "This edit deletes induction, a case header, or intros/exists."),
    ("drops_prefix_have", "noul", "This edit deletes a prefix have (Hk, Hlen1, or Hlen2) that simp_all uses."),
    ("breaks_refine", "noul", "This edit will leave a refine ⟨rfl, ?_, ?_⟩ subgoal unsolved."),
    ("duplicate_needed", "noul", "A line this edit drops is a load-bearing duplicate exact/simp_all/apply."),
    ("local_one_line", "noul", "The edit changes exactly one tactic line."),
)
# From lake misses on the 260-token script (autoresearch round 2).
MISS_FEATURES = (
    (
        "opens_refine_2a",
        "noul",
        "This edit will leave case refine_2.a or refine_2.a.h unsolved.",
    ),
    (
        "semicolon_apply_longer",
        "noul",
        "This edit joins apply lines with <;> and will use more tokens, not fewer.",
    ),
    (
        "constructor_for_rfl_refine",
        "noul",
        "This edit replaces refine ⟨rfl, ?_, ?_⟩ with constructor and will fail updatedStatesInit.",
    ),
    (
        "drops_second_exact",
        "noul",
        "This edit deletes a second exact InitStatesNotDefined or InitStatesNodup that still has an open refine hole.",
    ),
)
ALL_FEATURES = SEED_FEATURES + MISS_FEATURES
PENALTY = {
    "drops_pca_glue",
    "drops_prefix_have",
    "breaks_refine",
    "duplicate_needed",
    "opens_refine_2a",
    "semicolon_apply_longer",
    "constructor_for_rfl_refine",
    "drops_second_exact",
}


def load_typesafe():
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    if not TS_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("lra_typesafe_autoresearch", TS_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not module.typesafe_configured():
        return None
    return module


def feature_questions(module) -> dict:
    questions = {}
    for name, kind, question in ALL_FEATURES:
        if kind == "noul":
            questions[name] = module.Noul(instructions=question)
        else:
            questions[name] = module.Score(
                instructions=question,
                criteria=list(__import__("draft_fanout", fromlist=["LIKELY_SHORTER_CRITERIA"]).LIKELY_SHORTER_CRITERIA),
            )
    return questions


def featurize_proposal(
    record: Mapping[str, Any],
    current: str,
    proposal: Mapping[str, str],
    *,
    ledger: lra_t1.ProblemLedger,
    module,
    weights: Mapping[str, float],
) -> dict[str, Any]:
    state = {
        "problem": record.get("name"),
        "current_tokens": lra_loop.token_count(current),
        "current_tail": current[-500:],
        "edit_kind": proposal.get("kind"),
        "edit_note": proposal.get("note"),
        "proposed_tokens": lra_loop.token_count(proposal.get("tactics") or ""),
        "proposed_tail": str(proposal.get("tactics") or "")[-500:],
        "goal": "Judge this MCMC edit of a lake-valid Lean 4 proof. Do not write Lean.",
    }
    try:
        result = module.TypeSafeClient(timeout=45.0).system_one(state, feature_questions(module))
    except Exception as exc:  # noqa: BLE001
        return {"skipped": True, "reason": str(exc)[:300], "score": 0.0, "features": {}}
    usage = dict(getattr(result, "usage", None) or {})
    inn = int(usage.get("input_tokens") or usage.get("prompt_tokens") or lra_t1.estimate_tokens(json.dumps(state)))
    out = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    ledger.record("jev", input_tokens=inn, output_tokens=out, model=lra_t1.JEV_MODEL_ID)
    nouls = getattr(result, "nouls", None) or {}
    features: dict[str, float] = {}
    for name, _kind, _q in ALL_FEATURES:
        got = nouls.get(name)
        features[name] = float(getattr(got, "noul", 0.0) or 0.0)
    # Cookbook: combine in code. Miss-driven features subtract.
    score = 0.0
    for name, _kind, _q in ALL_FEATURES:
        w = float(weights.get(name) or 0.5)
        val = features.get(name, 0.0)
        score += (-w if name in PENALTY else w) * val
    return {
        "skipped": False,
        "score": score,
        "features": features,
        "jev_generated_lean": False,
    }


def update_weights(rows: list[dict[str, Any]], weights: dict[str, float]) -> dict[str, float]:
    """One autoresearch step: nudge weights from lake labels (ok vs fail)."""

    ok = [row for row in rows if row.get("ok")]
    bad = [row for row in rows if row.get("ok") is False]
    if not ok or not bad:
        return weights
    updated = dict(weights)
    for name, _kind, _q in ALL_FEATURES:
        mean_ok = sum(float((r.get("features") or {}).get(name) or 0.0) for r in ok) / len(ok)
        mean_bad = sum(float((r.get("features") or {}).get(name) or 0.0) for r in bad) / len(bad)
        if name in PENALTY:
            gap = mean_bad - mean_ok
            sign = 1.0
        else:
            gap = mean_ok - mean_bad
            sign = 1.0
        updated[name] = max(0.05, float(updated.get(name) or 0.5) + 0.3 * sign * gap)
    return updated


def self_check() -> dict[str, Any]:
    names = [item[0] for item in ALL_FEATURES]
    return {
        "ok": "likely_compiles" in names
        and "opens_refine_2a" in names
        and "drops_second_exact" in names
        and len(ALL_FEATURES) >= 10,
        "n_features": len(ALL_FEATURES),
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "arena_score": None,
        "cookbook": "https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--init-file", type=Path, required=False)
    parser.add_argument("--names", default="Core.InitsUpdatesComm")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_check or not args.live:
        report = self_check()
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    module = load_typesafe()
    if module is None:
        print(json.dumps({"ok": False, "reason": "no_typesafe", "arena_score": None}, indent=2))
        return 1
    _raw, digest, records = lra_splice.load_warmup_records()
    name = str(args.names).split(",")[0].strip()
    record = next(item for item in records if item.get("name") == name)
    init = Path(args.init_file).read_text(encoding="utf-8") if args.init_file else None
    import draft_fanout as lra_fan

    reference = lra_fan.tactic_block(record)
    current = (init or reference).strip("\n")
    rng = random.Random(int(args.seed))
    ledger = lra_t1.ProblemLedger(name=f"{name}#autoresearch-mcmc", max_jev_calls=MAX_JEV, max_mistral_calls=0, max_grok_calls=0)
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), args.state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    start = lra_mcmc.compile_one(record, current, state_root=args.state_root, timeout=args.timeout, restore=restore)
    best = {
        "kind": "init",
        "tactics": current,
        "token_count": int(start.get("token_count") or lra_loop.token_count(current)),
        "theorem_ok": bool(start.get("theorem_ok")),
    }
    weights = {name: 0.8 for name, _k, _q in ALL_FEATURES}
    weights.update(
        {
            "likely_compiles": 1.1,
            "likely_shorter": 0.15,
            "local_one_line": 0.2,
            "opens_refine_2a": 1.0,
            "semicolon_apply_longer": 1.0,
            "constructor_for_rfl_refine": 1.0,
            "drops_second_exact": 1.0,
        }
    )
    history: list[dict[str, Any]] = []
    labeled: list[dict[str, Any]] = []
    started = time.perf_counter()
    for round_i in range(int(args.rounds)):
        if ledger.hard_stopped:
            break
        proposals = lra_mcmc.propose_edits(current, reference, rng)
        scored = []
        for proposal in proposals[:6]:
            feat = featurize_proposal(record, current, proposal, ledger=ledger, module=module, weights=weights)
            scored.append({**proposal, **feat})
            if ledger.hard_stopped:
                break
        scored.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
        current_tok = lra_loop.token_count(current)
        shorter = [
            item
            for item in scored
            if lra_loop.token_count(item.get("tactics") or "") < current_tok
        ]
        to_lake = (shorter or scored)[:2]
        for proposal in to_lake:
            compiled = lra_mcmc.compile_one(
                record,
                proposal["tactics"],
                state_root=args.state_root,
                timeout=args.timeout,
                restore=restore,
            )
            ok = bool(compiled.get("theorem_ok"))
            tok = int(compiled.get("token_count") or lra_loop.token_count(proposal["tactics"]))
            row = {
                "round": round_i,
                "kind": proposal.get("kind"),
                "note": proposal.get("note"),
                "score": proposal.get("score"),
                "features": proposal.get("features"),
                "ok": ok,
                "tokens": tok,
                "errors": (compiled.get("errors") or [])[:1],
            }
            history.append(row)
            labeled.append(row)
            if ok and tok < int(best["token_count"]):
                best = {"kind": f"ar_r{round_i}_{proposal.get('kind')}", "tactics": proposal["tactics"], "token_count": tok, "theorem_ok": True}
                current = proposal["tactics"]
        weights = update_weights(labeled, weights)
    payload = {
        "schema": "lra-autoresearch-mcmc/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "cookbook": "https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery",
        "name": name,
        "warmup_jsonl_sha256": digest,
        "rounds": int(args.rounds),
        "features": [item[0] for item in ALL_FEATURES],
        "miss_features": [item[0] for item in MISS_FEATURES],
        "final_weights": weights,
        "best": {k: best[k] for k in ("kind", "token_count", "theorem_ok")},
        "best_tactics": best.get("tactics"),
        "history": history,
        "ledger": ledger.as_dict(),
        "reference_token_count": lra_loop.token_count(reference),
        "beats_reference": bool(best.get("theorem_ok") and int(best["token_count"]) < lra_loop.token_count(reference)),
        "hardware_class": HARDWARE_CLASS,
        "called_docker0": False,
        "official_track2": False,
        "arena_score": None,
        "jev_generated_lean": False,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
    }
    text = json.dumps(lra_pca.redact(payload), indent=2, sort_keys=True) + "\n"
    if "apikey_" in text:
        raise SystemExit("refusing to write a receipt that contains an API key")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"autoresearch-mcmc-{stamp}.json"
    latest = args.out / "autoresearch-mcmc-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "latest": str(latest),
                "kept": {"kind": best.get("kind"), "token_count": best.get("token_count"), "theorem_ok": best.get("theorem_ok")},
                "beats_reference": payload["beats_reference"],
                "arena_score": None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
