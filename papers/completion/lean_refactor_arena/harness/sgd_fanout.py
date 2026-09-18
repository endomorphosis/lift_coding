#!/usr/bin/env python3
"""Jev-guided stochastic search over MCA holes with parallel hammers.

This is not neural SGD. Each round TypeSafe scores remaining hole-drops
(surrogate gradient). We sample the top Choice plus one random hole
(stochastic minibatch), apply the drop, then run identity / simp_all /
omega closers in parallel. Lake is the true loss. Leanstral is one
optional restart if no descent. Never docker0. Not official Track 2.
Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
ROOT_ACCEL = Path("/home/barberb/lift_coding/external/ipfs_accelerate")
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"
DEFAULT_STATE = Path.home() / ".local/state/ipfs_accelerate_py/vericodegen-2026-lra/track1-lake"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import draft_fanout as lra_fan  # noqa: E402
import mca_mask_replace as lra_mask  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import track1_mistral_leanstral as lra_mistral  # noqa: E402

PROTOCOL = "LRA/v1"
PR_ID = "PR-9e"
HARDWARE_CLASS = "mistral_labs_api"


def drop_subset(tactics: str, holes: Sequence[lra_mask.Hole], chosen: Sequence[str]) -> str:
    fills = {
        hole.hole_id: (lra_mask.template_fill(hole) if hole.hole_id in set(chosen) else hole.original)
        for hole in holes
    }
    return lra_mask.apply_fills(tactics, holes, fills)


def hammer_variants(tactics: str, reference: str) -> list[tuple[str, str]]:
    """Parallel tactician branches. Aesop is not a Strata/CSLib dep."""

    import inits_updates_shorten as lra_ius

    rows = [
        ("identity", tactics),
        ("simp_all", tactics.rstrip() + "\n  all_goals try simp_all"),
        ("omega", tactics.rstrip() + "\n  try omega"),
        (
            "restore+simp",
            lra_mask.hammer_repair(tactics, reference, [{"data": "unsolved goals"}]),
        ),
        ("inits_replay", lra_ius.replay(reference)),
        ("inits_step", lra_ius.replay(tactics)),
    ]
    for item in lra_ius.propose(tactics)[:8]:
        rows.append((str(item["kind"]), str(item["tactics"])))
    import symbol_diffuse as lra_sym

    for item in lra_sym.closed_candidates(tactics, max_candidates=6):
        rows.append((str(item["kind"]), str(item["tactics"])))
    return rows


def jev_round(
    record: Mapping[str, Any],
    holes: Sequence[lra_mask.Hole],
    history: Sequence[Mapping[str, Any]],
    keep_tokens: int,
) -> dict[str, Any]:
    lra_pca.pin_typesafe_path()
    from ipfs_accelerate_py.typesafe_inference import Choice, Noul, Score, TypeSafeClient, typesafe_configured

    if not typesafe_configured():
        return {"skipped": True, "reason": "no_key", "choice": None, "probabilities": {}}
    criteria = {
        hole.hole_id: f"{hole.family}; {len(hole.original.split())} words; {hole.original.strip()[:80]}"
        for hole in holes
    }
    if not criteria:
        return {"skipped": True, "reason": "no_holes", "choice": None, "probabilities": {}}
    state = {
        "problem": record.get("name"),
        "keep_tokens": keep_tokens,
        "history": list(history)[-8:],
        "holes": [
            {"id": hole.hole_id, "family": hole.family, "n_words": len(hole.original.split())}
            for hole in holes
        ],
        "goal": "Pick the MCA hole whose deletion is most likely to lake-compile AND cut tokens. Do not write Lean.",
    }
    questions = {
        "next_hole": Choice(
            instructions=(
                "Which hole id should we drop next in this stochastic descent? "
                "Prefer strength_reduction simp-at runs, then dead_code rename_i. "
                "Do not write Lean."
            ),
            criteria=criteria,
        ),
        "likely_compiles": Noul(instructions="Will dropping that hole still compile?"),
        "likely_token_cut": Score(
            instructions="How large a token cut if that hole is dropped?",
            criteria=list(lra_fan.LIKELY_SHORTER_CRITERIA),
        ),
    }
    client = TypeSafeClient(timeout=45.0)
    started = time.perf_counter()
    result = client.system_one(state, questions)
    choice = (getattr(result, "choices", None) or {}).get("next_hole")
    nouls = getattr(result, "nouls", None) or {}
    scores = getattr(result, "scores", None) or {}
    return lra_pca.redact(
        {
            "skipped": False,
            "choice": getattr(choice, "choice", None),
            "confidence": getattr(choice, "confidence", None),
            "probabilities": dict(getattr(choice, "probabilities", None) or {}),
            "likely_compiles": getattr(nouls.get("likely_compiles"), "noul", None),
            "likely_token_cut": getattr(scores.get("likely_token_cut"), "score", None),
            "usage": dict(getattr(result, "usage", None) or {}),
            "wall_ms": (time.perf_counter() - started) * 1000.0,
            "model": getattr(result, "model", None),
        }
    )


def evaluate_tactics(
    record: Mapping[str, Any],
    tactics: str,
    *,
    state_root: Path,
    timeout: float,
    restore: bytes,
    reference: str,
    memory: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    def _one(label: str, body: str) -> dict[str, Any]:
        import nca_kernel as lra_kern

        def _run() -> dict[str, Any]:
            return dict(
                lra_kb.compile_tactics(
                    record, body, state_root=state_root, timeout=timeout, restore=restore
                )
            )

        compiled = lra_kern.guarded_compile(
            memory,
            name=record.get("name"),
            kind=f"sgd:{label}",
            tactics=body,
            compile_fn=_run,
        )
        return {
            "hammer": label,
            "tactics": body,
            "token_count": compiled.get("token_count"),
            "theorem_ok": compiled.get("theorem_ok"),
            "exit_code": compiled.get("exit_code"),
            "errors": compiled.get("errors"),
            "n_chars": len(body),
        }

    variants = hammer_variants(tactics, reference)
    # Lake splices one file; serialize compiles. "Parallel hammers" means
    # four closer variants per minibatch, not concurrent writes.
    return [_one(label, body) for label, body in variants]


def sgd_search(
    name: str,
    *,
    state_root: Path,
    timeout: float,
    rounds: int,
    seed: int,
    use_leanstral: bool,
    memory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    rng = random.Random(seed)
    _raw, digest, records = lra_splice.load_warmup_records()
    record = next(item for item in records if item.get("name") == name)
    reference = lra_fan.tactic_block(record)
    holes = lra_mask.find_holes(reference)
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    keep = reference
    keep_tokens = lra_loop.token_count(reference)
    history: list[dict[str, Any]] = []
    rounds_out: list[dict[str, Any]] = []
    dropped: set[str] = set()
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    remaining = [hole for hole in holes if hole.hole_id not in dropped]
    for round_i in range(1, max(1, rounds) + 1):
        remaining = [hole for hole in holes if hole.hole_id not in dropped]
        if not remaining:
            break
        jev = jev_round(record, remaining, history, keep_tokens)
        ranked = sorted(
            (jev.get("probabilities") or {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )
        picked = []
        if jev.get("choice"):
            picked.append(str(jev["choice"]))
        if ranked:
            picked.append(str(ranked[0][0]))
        others = [hole.hole_id for hole in remaining if hole.hole_id not in picked]
        if others:
            picked.append(rng.choice(others))
        # unique, at most 2 holes this minibatch
        minibatch = []
        for hole_id in picked:
            if hole_id not in minibatch and any(h.hole_id == hole_id for h in remaining):
                minibatch.append(hole_id)
            if len(minibatch) >= 2:
                break
        trial = drop_subset(reference, holes, list(dropped) + minibatch)
        evals = evaluate_tactics(
            record,
            trial,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
            reference=reference,
            memory=memory,
        )
        accepted = None
        valid = [row for row in evals if row.get("theorem_ok")]
        if valid:
            best = sorted(valid, key=lambda row: int(row.get("token_count") or 10**9))[0]
            if int(best["token_count"] or keep_tokens) < keep_tokens:
                keep = str(best.get("tactics") or trial)
                keep_tokens = int(best["token_count"])
                dropped.update(minibatch)
                accepted = {k: v for k, v in best.items() if k != "tactics"}
        history.append(
            {
                "round": round_i,
                "minibatch": minibatch,
                "accepted": bool(accepted),
                "keep_tokens": keep_tokens,
                "jev_choice": jev.get("choice"),
            }
        )
        rounds_out.append(
            {
                "round": round_i,
                "jev": jev,
                "minibatch": minibatch,
                "evals": evals,
                "accepted": accepted,
                "keep_tokens": keep_tokens,
            }
        )
    leanstral = None
    if use_leanstral and keep_tokens >= lra_loop.token_count(reference):
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()
        ledger = lra_t1.ProblemLedger(name=f"{name}#sgd")
        shots = [
            lra_mask.few_shot_example(item)
            for item in records
            if item.get("name") in lra_mask.SHOT_NAMES and item.get("name") != name
        ]
        prompt = lra_mask.few_shot_prompt(record, shots)
        text, identity, _line = lra_mistral.generate_mistral(
            prompt, ledger, max_new_tokens=700, timeout=180.0
        )
        filled = lra_kb.flatten_overindent(
            reference, lra_kb.match_reference_indent(reference, lra_loop.extract_generated_tactics(text))
        )
        evals = evaluate_tactics(
            record, filled, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
        )
        hammered = lra_mask.hammer_repair(filled, reference, (evals[0].get("errors") if evals else None) or [])
        evals_h = evaluate_tactics(
            record, hammered, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
        )
        leanstral = {
            "identity": identity,
            "ledger": ledger.as_dict(),
            "evals": evals,
            "hammer_evals": evals_h,
        }
        for row in evals + evals_h:
            if row.get("theorem_ok") and int(row.get("token_count") or keep_tokens) < keep_tokens:
                keep = hammered if row in evals_h else filled
                keep_tokens = int(row["token_count"])
    ref_tokens = lra_loop.token_count(reference)
    return lra_pca.redact(
        {
            "schema": "lra-sgd-fanout/v1",
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "name": name,
            "warmup_jsonl_sha256": digest,
            "n_holes": len(holes),
            "ref_tokens": ref_tokens,
            "keep_tokens": keep_tokens,
            "ratio": round(keep_tokens / max(1, ref_tokens), 4),
            "dropped": sorted(dropped),
            "rounds": rounds_out,
            "leanstral": leanstral,
            "hardware_class": HARDWARE_CLASS,
            "called_docker0": False,
            "official_track2": False,
            "arena_score": None,
            "note": "Jev-guided stochastic coordinate descent on MCA holes; not neural SGD.",
        }
    )


def _accept(evals: Sequence[Mapping[str, Any]], keep_tokens: int) -> Optional[dict[str, Any]]:
    valid = [row for row in evals if row.get("theorem_ok")]
    if not valid:
        return None
    best = sorted(valid, key=lambda row: int(row.get("token_count") or 10**9))[0]
    if int(best.get("token_count") or keep_tokens) < keep_tokens:
        return best
    return None


def diffuse_search(
    name: str,
    *,
    state_root: Path,
    timeout: float,
    rounds: int,
    seed: int,
    use_leanstral: bool,
    tau: float = 0.12,
) -> dict[str, Any]:
    """Exploit: drop all high-p holes at once. Explore: random subset + Leanstral noise.

    Denoise: hammer variants. This is bandit/coordinate search with a diffusion
    restart, not neural SGD or a trained denoiser.
    """

    rng = random.Random(seed)
    _raw, digest, records = lra_splice.load_warmup_records()
    record = next(item for item in records if item.get("name") == name)
    reference = lra_fan.tactic_block(record)
    holes = lra_mask.find_holes(reference)
    clone = lra_kb.lra_cw.clone_dir(str(record["url"]), state_root)
    dest = clone / lra_kb.lra_cw.source_relpath(record)
    restore = dest.read_bytes() if dest.is_file() else b""
    keep = reference
    keep_tokens = lra_loop.token_count(reference)
    dropped: set[str] = set()
    history: list[dict[str, Any]] = []
    rounds_out: list[dict[str, Any]] = []
    lra_pca.load_keyfile()
    lra_pca.pin_typesafe_path()
    if use_leanstral:
        lra_mistral.load_keyfiles()
        lra_mistral.pin_paths()

    def consider(label: str, hole_ids: Sequence[str]) -> dict[str, Any]:
        nonlocal keep, keep_tokens, dropped
        trial = drop_subset(reference, holes, list(dict.fromkeys(list(dropped) + list(hole_ids))))
        evals = evaluate_tactics(
            record, trial, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
        )
        hit = _accept(evals, keep_tokens)
        if hit:
            keep = str(hit.get("tactics") or trial)
            keep_tokens = int(hit["token_count"])
            dropped.update(hole_ids)
        return {
            "label": label,
            "holes": list(hole_ids),
            "accepted": bool(hit),
            "keep_tokens": keep_tokens,
            "evals": [{k: v for k, v in row.items() if k != "tactics"} for row in evals],
        }

    # Exploit jump: delete every MCA hole (the 414 move on CallElimCorrect).
    full = consider("exploit_all_holes", [hole.hole_id for hole in holes])
    rounds_out.append({"round": 0, "phase": "exploit_all", **full})

    for round_i in range(1, max(1, rounds) + 1):
        remaining = [hole for hole in holes if hole.hole_id not in dropped]
        jev: dict[str, Any] = {"skipped": True, "reason": "no_holes"}
        step_exploit: Optional[dict[str, Any]] = None
        step_explore: Optional[dict[str, Any]] = None
        high: list[str] = []
        explore: list[str] = []
        if remaining:
            jev = jev_round(record, remaining, history, keep_tokens)
            probs = jev.get("probabilities") or {}
            high = [hid for hid, p in probs.items() if float(p) >= tau]
            if not high and jev.get("choice"):
                high = [str(jev["choice"])]
            explore = [rng.choice([hole.hole_id for hole in remaining])]
            step_exploit = consider("exploit_high_p", high)
            step_explore = consider("explore_random", explore)
        noise = None
        if use_leanstral:
            round_ledger = lra_t1.ProblemLedger(name=f"{name}#diffuse-r{round_i}")
            if remaining:
                hole = rng.choice(remaining)
                prompt = lra_mask.one_hole_prompt(record, keep, hole)
                noise_meta = {"hole": hole.hole_id, "mode": "one_hole"}
            else:
                shots = [
                    lra_mask.few_shot_example(item)
                    for item in records
                    if item.get("name") in lra_mask.SHOT_NAMES and item.get("name") != name
                ]
                prompt = (
                    f"Current lake-valid keep is {keep_tokens} tokens "
                    f"(reference {lra_loop.token_count(reference)}). "
                    "Shrink it further. Keep induction and every case arm. "
                    "Delete only residual simp-at/rename_i/have/rw. No sorry.\n\n"
                    + lra_mask.few_shot_prompt(record, shots)
                    + f"\nCURRENT KEEP ({keep_tokens} tokens):\n{keep[:1800]}\n"
                )
                noise_meta = {"hole": None, "mode": "shrink_keep"}
            try:
                text, identity, _line = lra_mistral.generate_mistral(
                    prompt, round_ledger, max_new_tokens=400, timeout=120.0
                )
            except (lra_t1.Track1LedgerError, lra_mistral.Track1MistralError):
                text, identity = "", {}
            filled = lra_loop.extract_generated_tactics(text) if text else ""
            if filled:
                noisy = lra_kb.flatten_overindent(
                    keep, lra_kb.match_reference_indent(keep, filled)
                )
                evals_n = evaluate_tactics(
                    record, noisy, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
                )
                denoised = lra_mask.hammer_repair(
                    noisy, reference, (evals_n[0].get("errors") if evals_n else None) or []
                )
                evals_d = evaluate_tactics(
                    record, denoised, state_root=state_root, timeout=timeout, restore=restore, reference=reference, memory=memory
                )
                hit = _accept(evals_n + evals_d, keep_tokens)
                if hit:
                    keep = str(hit.get("tactics") or denoised)
                    keep_tokens = int(hit["token_count"])
                noise = {
                    **noise_meta,
                    "identity": identity,
                    "accepted": bool(hit),
                    "noise_evals": [{k: v for k, v in row.items() if k != "tactics"} for row in evals_n],
                    "denoise_evals": [{k: v for k, v in row.items() if k != "tactics"} for row in evals_d],
                }
        history.append(
            {
                "round": round_i,
                "high_p": high,
                "explore": explore,
                "keep_tokens": keep_tokens,
                "jev_choice": jev.get("choice"),
            }
        )
        rounds_out.append(
            {
                "round": round_i,
                "jev": jev,
                "exploit": step_exploit,
                "explore": step_explore,
                "diffuse": noise,
                "keep_tokens": keep_tokens,
            }
        )
    ref_tokens = lra_loop.token_count(reference)
    return lra_pca.redact(
        {
            "schema": "lra-diffuse-denoise/v1",
            "protocol": PROTOCOL,
            "pr": PR_ID,
            "name": name,
            "warmup_jsonl_sha256": digest,
            "n_holes": len(holes),
            "ref_tokens": ref_tokens,
            "keep_tokens": keep_tokens,
            "ratio": round(keep_tokens / max(1, ref_tokens), 4),
            "dropped": sorted(dropped),
            "rounds": rounds_out,
            "ledger": None,
            "hardware_class": HARDWARE_CLASS,
            "called_docker0": False,
            "official_track2": False,
            "arena_score": None,
            "note": (
                "Exploit=drop high-p and all MCA holes; explore=random hole; "
                "diffuse=Leanstral one-hole noise; denoise=hammer. Not neural SGD."
            ),
        }
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", default="CallElimCorrect.substOldPostSubset,Core.InitsUpdatesComm")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-leanstral", action="store_true")
    parser.add_argument("--diffuse", action="store_true", help="multi-hole exploit + Leanstral noise/denoise")
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args(list(argv) if argv is not None else None)
    os.environ.setdefault("IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART", "0")
    names = [item.strip() for item in str(args.names).split(",") if item.strip()]
    started = time.perf_counter()
    reports = [
        (
            diffuse_search if args.diffuse else sgd_search
        )(
            name,
            state_root=args.state_root,
            timeout=args.timeout,
            rounds=args.rounds,
            seed=args.seed,
            use_leanstral=not args.no_leanstral,
        )
        for name in names
    ]
    payload = {
        "schema": "lra-sgd-fanout-batch/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "arena_score": None,
        "called_docker0": False,
        "wall_ms": (time.perf_counter() - started) * 1000.0,
        "problems": reports,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if "apikey_" in text:
        raise SystemExit("refusing to write a receipt that contains a secret")
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"sgd-fanout-{stamp}.json"
    latest = args.out / "sgd-fanout-latest.json"
    path.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "latest": str(latest),
                "results": [
                    {
                        "name": item.get("name"),
                        "ref": item.get("ref_tokens"),
                        "keep": item.get("keep_tokens"),
                        "ratio": item.get("ratio"),
                        "dropped": item.get("dropped"),
                    }
                    for item in reports
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
