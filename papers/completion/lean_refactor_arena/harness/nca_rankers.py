#!/usr/bin/env python3
"""NCA ranking skills: random forest, Bayesian estimation over time, MCMC.

These skills rank portable drafts / pipeline stems. They do not write Lean.
Lake remains the oracle. Jev does not generate tactic text. Never docker0.
Not Arena scores. Not Track 2.
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable, Mapping, Optional, Sequence

PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0
BAYES_DECAY = 0.98
RF_TREES = 7
RF_DEPTH = 4
MCMC_STEPS = 8
MCMC_TEMP = 1.0

RANKER_STEMS = ("random_forest", "bayes_time", "mcmc")


def is_ranker_stem(stem: str) -> bool:
    text = str(stem or "").lower().replace("port_", "")
    return any(tag in text for tag in RANKER_STEMS)


def _clip01(value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.5
    if number != number:
        return 0.5
    return max(0.0, min(1.0, number))


def _stem_of(kind: str) -> str:
    text = str(kind or "")
    if text.startswith("port_"):
        text = text[len("port_") :]
    return text.split("_pipeline")[0]


def _bayes_store(memory: dict[str, Any]) -> dict[str, Any]:
    return memory.setdefault("nca", {}).setdefault("bayes", {})


def _forest_store(memory: dict[str, Any]) -> dict[str, Any]:
    return memory.setdefault("nca", {}).setdefault("random_forest", {})


def feature_row(
    *,
    kind: str = "",
    tokens: int = 0,
    memory: Optional[Mapping[str, Any]] = None,
    name: str = "",
    leftover: int = 0,
    remaining_cut: int = 0,
) -> list[float]:
    """Closed feature bag for RF. No Lean text."""

    stem = _stem_of(kind)
    mem = dict(memory or {})
    wins = 0
    losses = 0
    for row in mem.get("successes") or []:
        if _stem_of(str(row.get("kind") or "")) == stem:
            wins += 1
    for row in mem.get("failures") or []:
        if _stem_of(str(row.get("kind") or "")) == stem:
            losses += 1
    help_score = 0.0
    unsafe = 0.0
    n_help = 0
    residual = ""
    try:
        import portable_rewrites as lra_port

        residual = str(lra_port.SKILL_RESIDUAL.get(stem) or "")
    except Exception:
        residual = ""
    for row in mem.get("research") or []:
        if name and row.get("name") != name:
            continue
        if residual and residual in (row.get("help") or {}):
            help_score += float((row.get("help") or {}).get(residual) or 0.0)
            unsafe += float((row.get("unsafe") or {}).get(residual) or 0.0)
            n_help += 1
    if n_help:
        help_score /= n_help
        unsafe /= n_help
    bayes = posterior(mem, stem)
    return [
        float(tokens) / 100.0,
        float(wins),
        float(losses),
        help_score,
        unsafe,
        float(remaining_cut) / 100.0,
        float(leftover),
        float(bayes.get("mean") or 0.5),
    ]


def observe_bayes(memory: dict[str, Any], stem: str, *, ok: bool, now: float = 0.0) -> dict[str, Any]:
    """One Bernoulli observation. Exponential forget toward the prior."""

    store = _bayes_store(memory)
    key = _stem_of(stem)
    row = dict(store.get(key) or {"alpha": PRIOR_ALPHA, "beta": PRIOR_BETA, "n": 0, "t": 0.0})
    row["alpha"] = PRIOR_ALPHA + BAYES_DECAY * max(0.0, float(row.get("alpha") or PRIOR_ALPHA) - PRIOR_ALPHA)
    row["beta"] = PRIOR_BETA + BAYES_DECAY * max(0.0, float(row.get("beta") or PRIOR_BETA) - PRIOR_BETA)
    if ok:
        row["alpha"] = float(row["alpha"]) + 1.0
    else:
        row["beta"] = float(row["beta"]) + 1.0
    row["n"] = int(row.get("n") or 0) + 1
    row["t"] = float(now or row.get("t") or 0.0) + 1.0
    store[key] = row
    return posterior(memory, key)


def posterior(memory: Mapping[str, Any], stem: str) -> dict[str, float]:
    store = ((memory.get("nca") or {}).get("bayes") or {}) if isinstance(memory, dict) else {}
    row = store.get(_stem_of(stem)) or {}
    alpha = float(row.get("alpha") or PRIOR_ALPHA)
    beta = float(row.get("beta") or PRIOR_BETA)
    total = max(alpha + beta, 1e-9)
    mean = alpha / total
    # Beta variance; used as uncertainty over time.
    var = (alpha * beta) / (total * total * (total + 1.0))
    return {
        "alpha": alpha,
        "beta": beta,
        "mean": _clip01(mean),
        "variance": max(0.0, var),
        "n": float(row.get("n") or 0.0),
        "t": float(row.get("t") or 0.0),
    }


def sync_bayes_from_memory(memory: dict[str, Any]) -> dict[str, Any]:
    """Conjugate Beta counts from successes/failures. Live `observe_bayes` adds time decay."""

    wins: dict[str, int] = {}
    losses: dict[str, int] = {}
    for row in memory.get("successes") or []:
        stem = _stem_of(str(row.get("kind") or ""))
        if stem:
            wins[stem] = wins.get(stem, 0) + 1
    for row in memory.get("failures") or []:
        stem = _stem_of(str(row.get("kind") or ""))
        if stem:
            losses[stem] = losses.get(stem, 0) + 1
    store = memory.setdefault("nca", {}).setdefault("bayes", {})
    store.clear()
    for stem in set(wins) | set(losses):
        w = int(wins.get(stem, 0))
        l = int(losses.get(stem, 0))
        store[stem] = {
            "alpha": PRIOR_ALPHA + float(w),
            "beta": PRIOR_BETA + float(l),
            "n": w + l,
            "t": float(w + l),
        }
    out = {stem: posterior(memory, stem) for stem in store}
    return {"ok": True, "n": len(out), "posteriors": out, "writes_lean": False}


def apply_bayes_to_grid(memory: dict[str, Any]) -> int:
    """Write posterior mean onto matching skill cells as energy."""

    import typesafe_nca as lra_nca

    n = 0
    for stem in list(_bayes_store(memory)):
        mean = float(posterior(memory, stem)["mean"])
        ptr = f"ptr://skill/port_{_stem_of(stem)}"
        lra_nca.upsert_from_event(memory, ptr=ptr, kind="skill", energy=mean)
        n += 1
    return n


def _gini(labels: Sequence[int]) -> float:
    if not labels:
        return 0.0
    p = sum(labels) / float(len(labels))
    return 2.0 * p * (1.0 - p)


def _fit_tree(
    rows: list[tuple[list[float], int]],
    *,
    depth: int,
    rng: random.Random,
    max_depth: int,
    min_leaf: int = 2,
) -> dict[str, Any]:
    labels = [lab for _feat, lab in rows]
    if depth >= max_depth or len(rows) < 2 * min_leaf or len(set(labels)) <= 1:
        return {"leaf": (sum(labels) / float(len(labels))) if labels else 0.5}
    n_feat = len(rows[0][0])
    n_try = max(1, int(math.sqrt(n_feat)) + 1)
    best: Optional[tuple[float, int, float, list, list]] = None
    for _ in range(n_try * 3):
        col = rng.randrange(n_feat)
        vals = sorted({feat[col] for feat, _lab in rows})
        if len(vals) < 2:
            continue
        thr = vals[rng.randrange(len(vals) - 1)]
        left = [row for row in rows if row[0][col] <= thr]
        right = [row for row in rows if row[0][col] > thr]
        if len(left) < min_leaf or len(right) < min_leaf:
            continue
        g = (
            len(left) * _gini([lab for _f, lab in left])
            + len(right) * _gini([lab for _f, lab in right])
        ) / float(len(rows))
        if best is None or g < best[0]:
            best = (g, col, thr, left, right)
    if best is None:
        return {"leaf": (sum(labels) / float(len(labels))) if labels else 0.5}
    return {
        "col": best[1],
        "thr": best[2],
        "left": _fit_tree(best[3], depth=depth + 1, rng=rng, max_depth=max_depth, min_leaf=min_leaf),
        "right": _fit_tree(best[4], depth=depth + 1, rng=rng, max_depth=max_depth, min_leaf=min_leaf),
    }


def _eval_tree(node: Mapping[str, Any], feat: Sequence[float]) -> float:
    if "leaf" in node:
        return float(node["leaf"])
    if feat[int(node["col"])] <= float(node["thr"]):
        return _eval_tree(node["left"], feat)
    return _eval_tree(node["right"], feat)


def train_random_forest(memory: dict[str, Any], *, rng: Optional[random.Random] = None) -> dict[str, Any]:
    """Bootstrap trees on memory successes (1) / failures (0)."""

    rng = rng or random.Random(0)
    rows: list[tuple[list[float], int]] = []
    for label, bucket in ((1, memory.get("successes") or []), (0, memory.get("failures") or [])):
        for item in bucket:
            kind = str(item.get("kind") or "")
            if not kind:
                continue
            feat = feature_row(
                kind=kind,
                tokens=int(item.get("tokens") or item.get("token_count") or 0),
                memory=memory,
                name=str(item.get("name") or ""),
            )
            rows.append((feat, label))
    if len(rows) < 4:
        _forest_store(memory)["trees"] = []
        _forest_store(memory)["n_rows"] = len(rows)
        return {"ok": True, "n_trees": 0, "n_rows": len(rows), "reason": "too_few_rows", "writes_lean": False}
    trees: list[dict[str, Any]] = []
    for _ in range(RF_TREES):
        bag = [rows[rng.randrange(len(rows))] for _ in rows]
        trees.append(_fit_tree(bag, depth=0, rng=rng, max_depth=RF_DEPTH))
    store = _forest_store(memory)
    store["trees"] = trees
    store["n_rows"] = len(rows)
    return {"ok": True, "n_trees": len(trees), "n_rows": len(rows), "writes_lean": False}


def score_forest(memory: Mapping[str, Any], feat: Sequence[float]) -> float:
    trees = ((memory.get("nca") or {}).get("random_forest") or {}).get("trees") or []
    if not trees:
        return 0.5
    return sum(_eval_tree(tree, feat) for tree in trees) / float(len(trees))


def rank_drafts_forest(
    drafts: Sequence[Mapping[str, Any]],
    *,
    memory: Mapping[str, Any],
    name: str = "",
    remaining_cut: int = 0,
) -> list[Mapping[str, Any]]:
    scored: list[tuple[float, Mapping[str, Any]]] = []
    leftover = len(drafts)
    for item in drafts:
        feat = feature_row(
            kind=str(item.get("kind") or ""),
            tokens=int(item.get("token_count") or 0),
            memory=memory,
            name=name,
            leftover=leftover,
            remaining_cut=remaining_cut,
        )
        scored.append((-score_forest(memory, feat), item))
    scored.sort(key=lambda row: (row[0], str(row[1].get("kind") or "")))
    return [item for _score, item in scored]


def metropolis_hastings(
    state: Any,
    *,
    propose: Callable[[Any, random.Random], Any],
    energy: Callable[[Any], float],
    accept: Optional[Callable[[Any], bool]] = None,
    rng: Optional[random.Random] = None,
    steps: int = MCMC_STEPS,
    temperature: float = MCMC_TEMP,
) -> dict[str, Any]:
    """Generic MH. `accept` is a hard constraint (lake / closed fold). No Lean write."""

    rng = rng or random.Random(0)
    current = state
    cur_e = float(energy(current))
    trace: list[dict[str, Any]] = []
    best = current
    best_e = cur_e
    n_acc = 0
    for step in range(max(1, int(steps))):
        nxt = propose(current, rng)
        if nxt is current or nxt == current:
            trace.append({"step": step, "accepted": False, "reason": "noop"})
            continue
        if accept is not None and not accept(nxt):
            trace.append({"step": step, "accepted": False, "reason": "hard_reject"})
            continue
        nxt_e = float(energy(nxt))
        delta = nxt_e - cur_e
        temp = max(1e-6, float(temperature))
        if delta <= 0.0 or rng.random() < math.exp(-delta / temp):
            current = nxt
            cur_e = nxt_e
            n_acc += 1
            if nxt_e < best_e:
                best = nxt
                best_e = nxt_e
            trace.append({"step": step, "accepted": True, "energy": nxt_e, "delta": delta})
        else:
            trace.append({"step": step, "accepted": False, "energy": nxt_e, "delta": delta, "reason": "mh"})
    return {
        "ok": True,
        "state": current,
        "energy": cur_e,
        "best": best,
        "best_energy": best_e,
        "n_accept": n_acc,
        "n_steps": max(1, int(steps)),
        "trace": trace[:32],
        "writes_lean": False,
        "called_docker0": False,
    }


def _pipeline_stems(memory: Mapping[str, Any], *, name: str = "") -> list[str]:
    try:
        import portable_rewrites as lra_port

        return [stem for stem, _fn in lra_port.pipeline_order(dict(memory), name=name)]
    except Exception:
        return []


def mcmc_pipeline_order(
    memory: dict[str, Any],
    *,
    name: str = "",
    rng: Optional[random.Random] = None,
    steps: int = MCMC_STEPS,
) -> dict[str, Any]:
    """MH over pipeline stem order. Energy = sum of (1 - Bayes mean)."""

    stems = _pipeline_stems(memory, name=name)
    if len(stems) < 2:
        return {"ok": True, "reason": "too_short", "stems": stems, "writes_lean": False}

    def energy(order: Sequence[str]) -> float:
        total = 0.0
        for index, stem in enumerate(order):
            mean = float(posterior(memory, stem).get("mean") or 0.5)
            total += (1.0 - mean) + 0.01 * float(index)
        return total

    def propose(order: Sequence[str], rng_local: random.Random) -> list[str]:
        nxt = list(order)
        i = rng_local.randrange(len(nxt))
        j = rng_local.randrange(len(nxt))
        nxt[i], nxt[j] = nxt[j], nxt[i]
        return nxt

    ran = metropolis_hastings(list(stems), propose=propose, energy=energy, rng=rng, steps=steps)
    best = list(ran.get("best") or stems)
    memory.setdefault("nca", {})["pipeline_bias"] = best
    ran["stems"] = best
    ran["kind"] = "port_mcmc"
    return ran


def call_ranker(
    stem: str,
    *,
    memory: dict[str, Any],
    tactics: str = "",
    problem: str = "",
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    """Dispatch CALL ptr://skill/port_{random_forest,bayes_time,mcmc}."""

    rng = rng or random.Random(0)
    text = str(stem or "").lower()
    name = str(problem or "")
    if "bayes" in text:
        synced = sync_bayes_from_memory(memory)
        synced["n_cells"] = apply_bayes_to_grid(memory)
        synced["kind"] = "port_bayes_time"
        synced["ok"] = True
        synced["writes_lean"] = False
        return synced
    if "forest" in text or "random_forest" in text:
        trained = train_random_forest(memory, rng=rng)
        drafts: list[Mapping[str, Any]] = []
        try:
            import portable_rewrites as lra_port

            drafts = list(lra_port.portable_drafts(tactics, memory=memory, name=name))
        except Exception:
            drafts = []
        ranked = rank_drafts_forest(drafts, memory=memory, name=name)
        bias = [_stem_of(str(item.get("kind") or "")) for item in ranked if item.get("kind")]
        if bias:
            memory.setdefault("nca", {})["pipeline_bias"] = bias
        trained["kind"] = "port_random_forest"
        trained["ranked"] = [str(item.get("kind")) for item in ranked]
        trained["ok"] = True
        trained["writes_lean"] = False
        return trained
    if "mcmc" in text:
        return mcmc_pipeline_order(memory, name=name, rng=rng)
    return {"ok": False, "reason": "unknown_ranker", "stem": stem, "writes_lean": False}


def score_record(
    drafts: Sequence[Mapping[str, Any]],
    *,
    memory: Mapping[str, Any],
    name: str = "",
    remaining_cut: int = 0,
) -> float:
    """Mean RF score of leftover drafts (live-rank tertiary key)."""

    if not drafts:
        return 0.0
    if not (((memory.get("nca") or {}).get("random_forest") or {}).get("trees")):
        return 0.0
    ranked = rank_drafts_forest(drafts, memory=memory, name=name, remaining_cut=remaining_cut)
    if not ranked:
        return 0.0
    feat = feature_row(
        kind=str(ranked[0].get("kind") or ""),
        tokens=int(ranked[0].get("token_count") or 0),
        memory=memory,
        name=name,
        leftover=len(drafts),
        remaining_cut=remaining_cut,
    )
    return float(score_forest(memory, feat))
