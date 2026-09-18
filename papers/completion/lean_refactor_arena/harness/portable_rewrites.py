#!/usr/bin/env python3
"""Portable, lake-checked tactic skills for every small warmup canary.

Skills are pattern folds, not one-off strings. TypeSafe Choice picks a skill;
code applies it; lake is the oracle. Jev does not write Lean.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

import run_warmup as lra_loop

_EXACT_HYP = re.compile(r"\bexact ([A-Za-z][A-Za-z0-9']{0,6})\b")
_USE_EXACT = re.compile(r"use ([^;\n]+); exact ⟨")
_USE_EXACT_NL = re.compile(r"use ([^;\n]+)\n([ \t]*)exact ⟨")
_INTRO_SIMP = re.compile(
    r"(?m)^(?P<ind>[ \t]*)intro\n(?:[ \t]*\n)*(?P=ind)simp_all$"
)
_USE_EXACT_BLOCK = re.compile(
    r"use (?P<term>[^;\n]+)\n(?P<ind>[ \t]*)exact ⟨(?P<body>[^⟩]*)⟩"
)
_CTOR_PAIR = re.compile(
    r"(?m)^(?P<indent>[ \t]*)constructor\n"
    r"(?P=indent)· exact (?P<a>.+)\n"
    r"(?P=indent)· exact (?P<b>.+)$"
)
_REPEAT_PAR = re.compile(
    r"(?m)^(?P<indent>[ \t]*)apply ParallelReduction\.par <;>\n"
    r"(?P=indent)  apply ParallelReduction\.par <;>\n"
    r"(?P=indent)  grind$"
)
_HYP_NAME = re.compile(r"^(H[A-Za-z0-9']*|h[a-z0-9']*|this)$")


def fold_exact_hyp(tactics: str) -> str:
    """``exact Hin`` / ``exact H1`` → ``assumption`` when the name looks like a hyp."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if "." in name:
            return match.group(0)
        if name.startswith("H") or name.startswith("h") or name == "this":
            return "assumption"
        return match.group(0)

    nxt, n = _EXACT_HYP.subn(repl, tactics)
    return nxt if n else tactics


def fold_use_exact(tactics: str) -> str:
    """``use t; exact ⟨p, q⟩`` → ``exact ⟨t, p, q⟩`` (Exists.intro packing)."""

    nxt, n_same = _USE_EXACT.subn(r"exact ⟨\1, ", tactics)
    nxt, n_nl = _USE_EXACT_NL.subn(r"\2exact ⟨\1, ", nxt)
    return nxt if (n_same or n_nl) else tactics


def fold_use_exact_reuse(tactics: str) -> str:
    """``use t`` / ``exact ⟨.refl t, p⟩`` → ``exact ⟨t, .refl _, p⟩`` when t repeats."""

    def repl(match: re.Match[str]) -> str:
        term = match.group("term").strip()
        body = match.group("body")
        ind = match.group("ind")
        if f"({term})" in body:
            body2 = body.replace(f"({term})", "_", 1)
        elif term in body:
            body2 = body.replace(term, "_", 1)
        else:
            return match.group(0)
        return f"{ind}exact ⟨{term}, {body2}⟩"

    nxt, n = _USE_EXACT_BLOCK.subn(repl, tactics)
    if not n:
        return tactics
    # Only keep if strictly shorter.
    if lra_loop.token_count(nxt) >= lra_loop.token_count(tactics):
        return tactics
    return nxt


def fold_ctor_pair_exacts(tactics: str) -> str:
    """``constructor / · exact A / · exact B`` → ``exact ⟨A, B⟩``."""

    def repl(match: re.Match[str]) -> str:
        return f"{match.group('indent')}exact ⟨{match.group('a')}, {match.group('b')}⟩"

    nxt, n = _CTOR_PAIR.subn(repl, tactics)
    return nxt if n else tactics


def fold_semi_assumption(tactics: str) -> str:
    """``<;> assumption`` → ``; assumption`` only when the next tactic is not intros/cases.

    substOldPostSubset needs ``<;>`` because ``apply cih`` leaves extra goals that
    ``intros x Hin`` consumes. extractedOldExprInVars does not.
    """

    lines = tactics.splitlines()
    out: list[str] = []
    changed = False
    for index, line in enumerate(lines):
        if "<;> assumption" not in line:
            out.append(line)
            continue
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        nxt = lines[cursor].strip() if cursor < len(lines) else ""
        # substOldPostSubset: both ``intros x Hin`` and bare ``intro`` still need <;>
        # (extra goals from apply cih/eih). Only rewrite when the next tactic is a closer.
        if nxt.split()[:1] in (["simp_all"], ["rfl"], ["constructor"], ["exact"]):
            out.append(line.replace("<;> assumption", "; assumption", 1))
            changed = True
            continue
        out.append(line)
    return "\n".join(out) if changed else tactics


def fold_repeat_par_grind(tactics: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"{match.group('indent')}repeat (first | apply ParallelReduction.par | grind)"

    nxt, n = _REPEAT_PAR.subn(repl, tactics)
    return nxt if n else tactics


# Repeated dotted names on CallElim keep-bests (token analysis). Each is a
# separate skill so lake can ban one without killing the others.
SHORTEN_IDENTS: tuple[tuple[str, str, str], ...] = (
    ("llexpr_getvars", "Lambda.LExpr.LExpr.getVars", "LExpr.getVars"),
    ("list_subset_trans", "List.Subset.trans", "Subset.trans"),
    ("list_subset_app", "List.Subset.app", "Subset.app"),
    ("hasvars_getvars", "Imperative.HasVarsPure.getVars", "HasVarsPure.getVars"),
)


def fold_shorten_ident(tactics: str, old: str, new: str) -> str:
    if old not in tactics:
        return tactics
    nxt = tactics.replace(old, new)
    if lra_loop.token_count(nxt) >= lra_loop.token_count(tactics):
        return tactics
    return nxt


_GRIND_ONLY = re.compile(r"grind only \[[^\]]+\]")


def fold_grind_only_to_grind(tactics: str) -> str:
    """``grind only [...]`` → ``grind`` (Fsub/SKI). AutoResearch gates this residual."""

    if "grind only [" not in tactics:
        return tactics
    nxt = _GRIND_ONLY.sub("grind", tactics)
    if lra_loop.token_count(nxt) >= lra_loop.token_count(tactics):
        return tactics
    return nxt


def fold_drop_unfold_before_split(tactics: str) -> str:
    """``unfold name`` immediately before ``split`` is often redundant."""

    nxt, n = re.subn(
        r"(?m)^(?P<ind>[ \t]*)unfold \S+\n(?P=ind)split$",
        r"\g<ind>split",
        tactics,
    )
    return nxt if n else tactics


def fold_drop_try_simp_all(tactics: str) -> str:
    """Drop ``try simp_all`` hanging off ``induction … simp at * ;``.

    extractedOldExprInVars still has that tail. Memory said keep ``intro``;
    this is a different residual (optional simp after a closing ``at *``).
    """

    nxt, n = re.subn(
        r"(at \* )\s*;\n([ \t]*)try simp_all",
        r"\1",
        tactics,
        count=1,
    )
    return nxt if n else tactics


def fold_drop_intro_before_simp_all(tactics: str) -> str:
    """``intro`` / ``simp_all`` → ``simp_all`` when they are the whole remaining arm.

    AutoResearch ranked intro_then_simp_all as the highest-help residual on CallElim
    keep-bests (unsafe still under FIRE_T). Lake is the oracle.
    """

    nxt, n = _INTRO_SIMP.subn(r"\g<ind>simp_all", tactics)
    return nxt if n else tactics


def fold_trim_intro_names(tactics: str) -> str:
    """Drop trailing unused names on ``intro a b c`` (keep constructor / intro).

    CCS: ``intro s1 s2 r μ`` uses only ``r``; μ can drop from the end.
    ``intro h`` unused → nameless ``intro``.
    """

    import binder_use as lra_bind

    lines = tactics.splitlines()
    out: list[str] = []
    changed = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("intro ") or stripped.startswith("intros"):
            out.append(line)
            continue
        names = lra_bind.IDENT.findall(stripped[len("intro ") :])
        if not names:
            out.append(line)
            continue
        later = lra_bind.idents_in("\n".join(lines[index + 1 :]))
        trimmed = list(names)
        while trimmed and trimmed[-1] not in later:
            trimmed.pop()
        if trimmed == names:
            out.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        if not trimmed:
            out.append(f"{indent}intro")
        else:
            out.append(f"{indent}intro {' '.join(trimmed)}")
        changed = True
    return "\n".join(out) if changed else tactics


def fold_unused_intros(tactics: str) -> str:
    """``intros x Hin`` → nameless ``intros`` when Hin is unused in the arm.

    Skip when the next tactic is ``assumption``: that arm needs the named hyps
    (extractedOldExprInVars ``intros x Hin / assumption``).
    """

    lines = tactics.splitlines()
    out: list[str] = []
    index = 0
    changed = False
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped == "intros x Hin":
            rest: list[str] = []
            cursor = index + 1
            while cursor < len(lines) and not lines[cursor].lstrip():
                cursor += 1
            next_tac = lines[cursor].strip() if cursor < len(lines) else ""
            cursor = index + 1
            while cursor < len(lines) and not lines[cursor].lstrip().startswith("case "):
                rest.append(lines[cursor])
                cursor += 1
            if next_tac == "assumption":
                out.append(lines[index])
                index += 1
                continue
            if "Hin" not in "\n".join(rest):
                indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
                out.append(f"{indent}intros")
                changed = True
                index += 1
                continue
        out.append(lines[index])
        index += 1
    return "\n".join(out) if changed else tactics


_TRAILING_TUPLE_COMMA = re.compile(r",\s*⟩")
_SIMP_OPEN = re.compile(
    r"(?m)(?:^(?P<ind>[ \t]*)(?:[·.][ \t]+)?|(?P<semi><;>[ \t]*))(?P<head>simp(?:_all)?)[ \t]*\["
)


def _split_lemmas(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "," and depth == 0:
            item = "".join(buf).strip()
            if item:
                parts.append(item)
            buf = []
        else:
            buf.append(ch)
    item = "".join(buf).strip()
    if item:
        parts.append(item)
    return parts


def _simp_spans(tactics: str) -> list[dict[str, Any]]:
    """Locations of ``simp[lemmas]`` / ``simp_all[lemmas]``, including ``<;> simp``."""

    rows: list[dict[str, Any]] = []
    for match in _SIMP_OPEN.finditer(tactics):
        br_open = match.end() - 1
        depth = 0
        cursor = br_open
        while cursor < len(tactics):
            ch = tactics[cursor]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    break
            cursor += 1
        if cursor >= len(tactics):
            continue
        rest = tactics[cursor + 1 :]
        at = re.match(r"[ \t]+at[ \t]+\*", rest)
        end = cursor + 1 + (at.end() if at else 0)
        indent = match.group("ind") or ""
        rows.append(
            {
                "start": match.start(),
                "end": end,
                "ind": indent,
                "head": match.group("head"),
                "lemmas": _split_lemmas(tactics[br_open + 1 : cursor]),
                "at_star": bool(at),
                "is_simp_all": match.group("head") == "simp_all",
                "semi": bool(match.group("semi")),
            }
        )
    return rows


def _parent_induction_simp(tactics: str, spans: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    match = re.search(r"(?m)^[ \t]*induction .*<;>", tactics)
    if not match:
        return None
    for span in spans:
        if span["is_simp_all"] or span["start"] < match.start():
            continue
        between = tactics[match.end() : span["start"]]
        if between.strip() == "":
            return span
        return None
    return None


def fold_trailing_tuple_comma(tactics: str) -> str:
    """Drop a trailing comma in ``⟨a, b,⟩`` (keep exact/use/constructor)."""

    nxt, n = _TRAILING_TUPLE_COMMA.subn("⟩", tactics)
    return nxt if n else tactics


def fold_redundant_inner_simp(tactics: str) -> str:
    """Drop a case-local ``simp [subset]`` when the induction parent already has those lemmas.

    Keeps intro/constructor. extractedOldExprInVars still has
    ``simp [Lambda.LExpr.LExpr.getVars]`` under a parent that lists getVars.
    """

    spans = _simp_spans(tactics)
    parent = _parent_induction_simp(tactics, spans)
    if not parent:
        return tactics
    parent_set = set(parent["lemmas"])
    if not parent_set:
        return tactics
    drop: list[tuple[int, int]] = []
    for span in spans:
        if span is parent or span["is_simp_all"] or span["semi"]:
            continue
        inner = set(span["lemmas"])
        if inner and inner <= parent_set:
            start = tactics.find("simp", span["start"], span["end"])
            if start < 0:
                start = span["start"]
            end = span["end"]
            if end < len(tactics) and tactics[end] == "\n":
                end += 1
            drop.append((start, end))
    if not drop:
        return tactics
    nxt = tactics
    for start, end in reversed(drop):
        nxt = nxt[:start] + nxt[end:]
    nxt = re.sub(
        r"(?m)^(?P<ind>[ \t]*)(?P<dot>[·.])[ \t]*\n(?P=ind)[ \t]*",
        r"\g<ind>\g<dot> ",
        nxt,
    )
    nxt = re.sub(r"(?m)^(?P<ind>[ \t]*)(?P<dot>[·.])[ \t]+", r"\g<ind>\g<dot> ", nxt)
    return nxt if nxt.strip() else tactics


def fold_hoist_repeated_simp(tactics: str) -> str:
    """Merge a repeated case-local ``simp [lemmas] at *`` into the induction parent.

    Keeps intro/constructor/qualified names. substOldPostSubset repeats the same
    getVars list six times under ``induction post <;> simp [substOld]``.
    """

    spans = _simp_spans(tactics)
    parent = _parent_induction_simp(tactics, spans)
    if not parent:
        return tactics
    parent_set = set(parent["lemmas"])
    counts: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for span in spans:
        if span is parent or span["is_simp_all"] or span["semi"]:
            continue
        key = tuple(span["lemmas"])
        if not key:
            continue
        counts.setdefault(key, []).append(span)
    best_key = None
    best_rows: list[dict[str, Any]] = []
    for key, rows in counts.items():
        if len(rows) >= 2 and len(rows) > len(best_rows):
            best_key = key
            best_rows = rows
    if not best_key:
        return tactics
    extra = [item for item in best_key if item not in parent_set]
    need_at = any(row["at_star"] for row in best_rows)
    # substOldPostSubset: adding `at *` to `induction … <;> simp [substOld]` closed
    # the intro-only fvar/op arms (lake: Case tag `op` not found). Only hoist when
    # the parent already uses `at *`.
    if need_at and not parent["at_star"]:
        return tactics
    if not extra and (parent["at_star"] or not need_at):
        return tactics
    merged = parent["lemmas"] + extra
    at = " at *" if (parent["at_star"] or need_at) else ""
    new_simp = f"{parent['head']} [{', '.join(merged)}]{at}"
    replace_start = parent["start"]
    if parent["semi"]:
        simp_at = tactics.find("simp", parent["start"], parent["end"])
        if simp_at >= 0:
            replace_start = simp_at
    nxt = tactics[:replace_start] + new_simp + tactics[parent["end"] :]
    shift = len(new_simp) - (parent["end"] - replace_start)
    drop: list[tuple[int, int]] = []
    for span in best_rows:
        start = span["start"] + shift
        end = span["end"] + shift
        if end < len(nxt) and nxt[end] == "\n":
            end += 1
        drop.append((start, end))
    for start, end in reversed(drop):
        nxt = nxt[:start] + nxt[end:]
    if lra_loop.token_count(nxt) >= lra_loop.token_count(tactics):
        return tactics
    return nxt


# Residual name used by AutoResearch Score/Noul for each pipeline stem.
SKILL_RESIDUAL: dict[str, str] = {
    "unused_intros": "intros_x_Hin",
    "trim_intro_names": "intro_then_simp_all",
    "drop_try_simp_all": "try_simp_all",
    "drop_intro_before_simp_all": "intro_then_simp_all",
    "grind_only_to_grind": "grind",
    "repeat_par_grind": "grind",
    "use_exact": "use_then_exact",
    "use_exact_reuse": "use_then_exact",
    "ctor_pair_exacts": "ctor_lone",
    "semi_assumption": "apply_semi_assumption",
    "hoist_repeated_simp": "repeated_simp_list",
    "redundant_inner_simp": "inner_simp_subset",
    "trailing_tuple_comma": "trailing_tuple_comma",
}

KEEP_STRUCTURE: tuple[str, ...] = (
    "trailing_tuple_comma",
    "redundant_inner_simp",
    "hoist_repeated_simp",
)


PIPELINE: tuple[tuple[str, Any], ...] = (
    ("trailing_tuple_comma", fold_trailing_tuple_comma),
    ("redundant_inner_simp", fold_redundant_inner_simp),
    ("hoist_repeated_simp", fold_hoist_repeated_simp),
    ("exact_hyp", fold_exact_hyp),
    ("unused_intros", fold_unused_intros),
    ("trim_intro_names", fold_trim_intro_names),
    ("drop_try_simp_all", fold_drop_try_simp_all),
    ("drop_unfold_before_split", fold_drop_unfold_before_split),
    ("grind_only_to_grind", fold_grind_only_to_grind),
    # drop_intro_before_simp_all is not default: AutoResearch help was high but lake
    # failed (simp_all no progress / unsolved subset). Only via portable_drafts if not skipped.
    ("use_exact", fold_use_exact),
    ("use_exact_reuse", fold_use_exact_reuse),
    ("ctor_pair_exacts", fold_ctor_pair_exacts),
    ("repeat_par_grind", fold_repeat_par_grind),
    ("semi_assumption", fold_semi_assumption),
)


def _research_help(memory: Optional[dict[str, Any]], stem: str, *, name: str = "") -> float:
    residual = SKILL_RESIDUAL.get(stem)
    if not residual:
        return 0.0
    total = 0.0
    n = 0
    for row in (memory or {}).get("research") or []:
        if name and row.get("name") != name:
            continue
        help_scores = row.get("help") or {}
        if residual in help_scores:
            total += float(help_scores.get(residual) or 0.0)
            n += 1
    if n:
        return total / n
    if name:
        return _research_help(memory, stem, name="")
    return 0.0


def pipeline_order(
    memory: Optional[dict[str, Any]] = None, *, name: str = ""
) -> tuple[tuple[str, Any], ...]:
    """Reorder PIPELINE by memory: wins, then AutoResearch help, failures last."""

    from collections import Counter

    wins: Counter[str] = Counter()
    losses: Counter[str] = Counter()
    for row in (memory or {}).get("successes") or []:
        kind = str(row.get("kind") or "")
        if kind.startswith("port_"):
            stem = kind[len("port_") :].split("_pipeline")[0]
            wins[stem] += 1
        elif kind in {"drop_unused_binders", "collapse_simp_at"}:
            wins[kind] += 1
    for row in (memory or {}).get("failures") or []:
        kind = str(row.get("kind") or "")
        if kind.startswith("port_"):
            stem = kind[len("port_") :].split("_pipeline")[0]
            losses[stem] += 1
    bias = list(((memory or {}).get("nca") or {}).get("pipeline_bias") or [])
    bayes_mean: dict[str, float] = {}
    try:
        import nca_rankers as lra_rank

        for stem, _fn in PIPELINE:
            bayes_mean[stem] = float(lra_rank.posterior(dict(memory or {}), stem).get("mean") or 0.5)
    except Exception:
        bayes_mean = {}
    ranked = sorted(
        PIPELINE,
        key=lambda item: (
            -wins[item[0]],
            losses[item[0]],
            bias.index(item[0]) if item[0] in bias else len(bias),
            -bayes_mean.get(item[0], 0.5),
            -_research_help(memory, item[0], name=name),
            0 if item[0] in KEEP_STRUCTURE else 1,
            item[0],
        ),
    )
    return tuple(ranked)


def fold_from_memory_skill(tactics: str, spec: Mapping[str, Any]) -> str:
    """Apply a memory-installed literal fold. Keeps listed tactic words."""

    old = str(spec.get("old") or "")
    new = str(spec.get("new") or "")
    if not old or old not in tactics:
        return tactics
    keep = [str(item) for item in (spec.get("keep") or [])]
    nxt = tactics.replace(old, new, max(1, int(spec.get("count") or 1)))
    for word in keep:
        if word in old and word not in nxt:
            return tactics
    if lra_loop.token_count(nxt) >= lra_loop.token_count(tactics):
        return tactics
    return nxt


def compose_pipeline(
    tactics: str,
    *,
    skip: Optional[set[str]] = None,
    memory: Optional[dict[str, Any]] = None,
    name: str = "",
) -> tuple[str, list[str]]:
    """Apply un-blacklisted skills in memory-weighted order."""

    blocked = skip or set()
    body = tactics.strip("\n")
    applied: list[str] = []
    for stem, fn in pipeline_order(memory, name=name):
        if stem in blocked or f"port_{stem}" in blocked:
            continue
        nxt = fn(body).strip("\n")
        if nxt and nxt != body:
            body = nxt
            applied.append(stem)
    return body, applied


def portable_drafts(
    tactics: str,
    *,
    skip: Optional[set[str]] = None,
    memory: Optional[dict[str, Any]] = None,
    name: str = "",
) -> list[dict[str, object]]:
    """Shorter closed-vocab folds present in this script."""

    body = tactics.strip("\n")
    base = lra_loop.token_count(body)
    rows: list[dict[str, object]] = []
    seen = {body}
    def push(kind: str, family: str, nxt: str) -> None:
        nxt = nxt.strip("\n")
        if not nxt or nxt in seen:
            return
        tok = lra_loop.token_count(nxt)
        if tok >= base:
            return
        seen.add(nxt)
        rows.append(
            {
                "kind": f"port_{kind}",
                "family": family,
                "tactics": nxt,
                "token_count": tok,
                "generator": "portable_rewrites",
                "llm": "off",
                "n_masks": 1,
            }
        )

    push("trailing_tuple_comma", "search_space", fold_trailing_tuple_comma(body))
    push("redundant_inner_simp", "strength_reduction", fold_redundant_inner_simp(body))
    push("hoist_repeated_simp", "strength_reduction", fold_hoist_repeated_simp(body))
    push("exact_hyp", "search_space", fold_exact_hyp(body))
    push("use_exact", "search_space", fold_use_exact(body))
    push("use_exact_reuse", "search_space", fold_use_exact_reuse(body))
    push("ctor_pair_exacts", "algebraic_simplification", fold_ctor_pair_exacts(body))
    push("repeat_par_grind", "algebraic_simplification", fold_repeat_par_grind(body))
    push("semi_assumption", "search_space", fold_semi_assumption(body))
    push("unused_intros", "search_space", fold_unused_intros(body))
    push("trim_intro_names", "search_space", fold_trim_intro_names(body))
    push("drop_try_simp_all", "strength_reduction", fold_drop_try_simp_all(body))
    push("drop_unfold_before_split", "search_space", fold_drop_unfold_before_split(body))
    push("grind_only_to_grind", "algebraic_simplification", fold_grind_only_to_grind(body))
    for stem, old, new in SHORTEN_IDENTS:
        push(f"shorten_{stem}", "search_space", fold_shorten_ident(body, old, new))
    push("drop_intro_before_simp_all", "search_space", fold_drop_intro_before_simp_all(body))
    collapsed = re.sub(r"\n{3,}", "\n\n", body)
    push("collapse_blanks", "dead_code", collapsed)
    blocked = skip or set()
    for spec in (memory or {}).get("skills") or []:
        stem = str(spec.get("stem") or "mem")
        if stem in blocked or f"port_{stem}" in blocked or f"port_mem_{stem}" in blocked:
            continue
        push(
            f"mem_{stem}",
            str(spec.get("family") or "search_space"),
            fold_from_memory_skill(body, spec),
        )
    piped, applied = compose_pipeline(body, skip=skip, memory=memory, name=name)
    if applied:
        push("pipeline_" + "_".join(applied), "search_space", piped)
    return rows


SKILL_CRITERIA: dict[str, dict[str, str]] = {
    "keep": {
        "what": "Leave the current lake-valid script unchanged",
        "not_for": "When a closed fold below is present and unused-binder-safe",
    },
    "port_exact_hyp": {
        "what": "Replace exact H/Hin/H1 with assumption when the name is a local hyp",
        "not_for": "exact Lemma.foo or dotted constructors",
    },
    "port_use_exact": {
        "what": "Pack `use t; exact ⟨p, q⟩` into `exact ⟨t, p, q⟩`",
        "not_for": "use with a following tactic that is not exact ⟨",
    },
    "port_use_exact_reuse": {
        "what": "Pack `use t` / `exact ⟨.refl t, p⟩` into `exact ⟨t, .refl _, p⟩` when t repeats",
        "not_for": "When t is not in the exact tuple (would change the witness)",
    },
    "port_ctor_pair_exacts": {
        "what": "Pack constructor + two · exact into exact ⟨A, B⟩",
        "not_for": "constructor that builds a non-And/Exists type (CCS ChoiceBisim)",
    },
    "port_repeat_par_grind": {
        "what": "Collapse nested apply ParallelReduction.par <;> grind",
        "not_for": "Proofs without ParallelReduction",
    },
    "port_semi_assumption": {
        "what": "Replace <;> assumption with ; assumption when the next tactic is not intros/cases",
        "not_for": "apply cih <;> assumption followed by intros x Hin (multi-goal)",
    },
    "port_grind_only_to_grind": {
        "what": "Replace grind only [lemmas] with grind when extra lemmas are unnecessary",
        "not_for": "When grind without only fails or changes which lemmas fire (Fsub → wf)",
    },
    "port_shorten_llexpr_getvars": {
        "what": "Shorten Lambda.LExpr.LExpr.getVars to LExpr.getVars in simp lists",
        "not_for": "When LExpr.getVars is ambiguous",
    },
    "port_shorten_list_subset_trans": {
        "what": "Shorten List.Subset.trans to Subset.trans",
        "not_for": "When Subset.trans is ambiguous or not in scope",
    },
    "port_shorten_list_subset_app": {
        "what": "Shorten List.Subset.app to Subset.app",
        "not_for": "When Subset.app is ambiguous",
    },
    "port_shorten_hasvars_getvars": {
        "what": "Shorten Imperative.HasVarsPure.getVars to HasVarsPure.getVars",
        "not_for": "When HasVarsPure.getVars is ambiguous",
    },
    "port_drop_unfold_before_split": {
        "what": "Drop unfold name immediately before split",
        "not_for": "When split needs the unfolded definition in the goal",
    },
    "port_drop_try_simp_all": {
        "what": "Drop try simp_all after induction simp at * ;",
        "not_for": "When remaining cases still need the try (unsolved goals)",
    },
    "port_drop_intro_before_simp_all": {
        "what": "Drop a nameless intro immediately before simp_all when that is the rest of the case arm",
        "not_for": "When intro binds a hyp simp_all cannot recover (forall/subset goals)",
    },
    "port_trim_intro_names": {
        "what": "Drop trailing unused intro names; keep intro and constructor",
        "not_for": "Names used later (cases r, exists s1')",
    },
    "port_unused_intros": {
        "what": "Nameless intros when Hin is unused in the case arm",
        "not_for": "Arm whose next tactic is assumption (needs named hyps)",
    },
    "port_collapse_blanks": {
        "what": "Collapse extra blank lines (no token change unless tokens count them)",
        "not_for": "Already tight scripts",
    },
    "port_trailing_tuple_comma": {
        "what": "Drop a trailing comma in ⟨a, b,⟩; keep exact/use/constructor",
        "not_for": "A comma that separates a following field",
    },
    "port_redundant_inner_simp": {
        "what": "Drop a case-local simp [subset] when the induction parent already lists those lemmas; keep intro",
        "not_for": "When split/cases created a goal the parent simp did not close",
    },
    "port_hoist_repeated_simp": {
        "what": "Hoist a repeated case-local simp [lemmas] at * onto induction <;> simp; keep intro/constructor",
        "not_for": "When adding at * to the parent over-simps intro-only arms",
    },
    "port_pipeline": {
        "what": "Compose un-blacklisted skills in memory-weighted order (keep-structure first, then wins)",
        "not_for": "When a step is Noul-fired or binder-unsafe",
    },
    "port_random_forest": {
        "what": "Train a tiny forest on lake successes/failures and rank leftover drafts",
        "not_for": "Writing Lean; fewer than four labeled rows; Arena scores",
    },
    "port_bayes_time": {
        "what": "Beta-Bernoulli skill win-rate with exponential forget; write posterior onto cells",
        "not_for": "Writing Lean; treating posterior mean as a lake admit",
    },
    "port_mcmc": {
        "what": "Metropolis-Hastings over pipeline stem order; energy is 1 - Bayes mean",
        "not_for": "Writing Lean; docker0; replacing lake as the oracle",
    },
    "port_svd": {
        "what": "Truncated SVD on the theorem×skill lake matrix; recommend skills for a theorem",
        "not_for": "Proof-AST PCA (that is port_pca); writing Lean; n_theorems<2",
    },
    "port_pca": {
        "what": "CALL existing pca_mca_fanout SVD: keep principal style, surface MCA families",
        "not_for": "A second SVD ranker of leftover drafts; docker0; Arena scores",
    },
    "port_thompson": {
        "what": "Thompson-sample Beta(α,β) so high-variance stems still get a lake try",
        "not_for": "Treating a draw as a lake admit",
    },
    "port_ridge": {
        "what": "Integer milles ridge P(lake-ok | feature_row); companion to the forest",
        "not_for": "Writing Lean; fewer than four labeled rows",
    },
    "port_ols": {
        "what": "Integer ordinary least squares on milles features",
        "not_for": "Writing Lean; fewer than four labeled rows",
    },
    "port_logistic": {
        "what": "Integer logistic (OLS + milles sigmoid LUT)",
        "not_for": "Writing Lean; treating score as a lake admit",
    },
    "port_kmeans": {
        "what": "Integer k-means on milles feature rows; rank stems by cluster win-rate",
        "not_for": "Writing Lean; k greater than labeled rows",
    },
    "port_knn": {
        "what": "Integer k-NN milles distance to labeled lake rows",
        "not_for": "Writing Lean; empty memory",
    },
    "port_ica": {
        "what": "Integer FastICA-style deflation on the theorem×skill matrix",
        "not_for": "Writing Lean; n_theorems<2",
    },
    "port_nmf": {
        "what": "Integer NMF of nonnegative lake counts; rank skills by H mass",
        "not_for": "Writing Lean; negative-only matrices",
    },
    "port_kalman": {
        "what": "Integer 1-D Kalman on skill win milles (x,P,Q,R all ints)",
        "not_for": "Writing Lean; float covariance",
    },
}


def analyze_residuals(tactics: str) -> dict[str, int]:
    """Counts of leftover patterns for TypeSafe / AutoResearch features."""

    spans = _simp_spans(tactics)
    parent = _parent_induction_simp(tactics, spans)
    parent_set = set(parent["lemmas"]) if parent else set()
    inner_subset = 0
    repeated = 0
    freq: dict[tuple[str, ...], int] = {}
    for span in spans:
        if parent is not None and span is parent:
            continue
        if span["is_simp_all"]:
            continue
        key = tuple(span["lemmas"])
        freq[key] = freq.get(key, 0) + 1
        if parent_set and set(span["lemmas"]) <= parent_set:
            inner_subset += 1
    repeated = sum(n for n in freq.values() if n >= 2)
    counts = {
        "intros_x_Hin": len(re.findall(r"intros x Hin", tactics)),
        "intro_then_simp_all": len(re.findall(r"intro\n[ \t]*simp_all", tactics)),
        "apply_semi_assumption": len(re.findall(r"<;> assumption", tactics)),
        "apply_seq_assumption": len(re.findall(r"; assumption", tactics)),
        "use_then_exact": len(re.findall(r"use .+\n[ \t]*exact ⟨", tactics)),
        "ctor_lone": len(re.findall(r"(?m)^[ \t]*constructor[ \t]*$", tactics)),
        "grind": tactics.count("grind"),
        "try_simp_all": len(re.findall(r"try simp_all", tactics)),
        "have": len(re.findall(r"(?m)^[ \t]*have ", tactics)),
        "repeated_simp_list": repeated,
        "inner_simp_subset": inner_subset,
        "trailing_tuple_comma": len(_TRAILING_TUPLE_COMMA.findall(tactics)),
    }
    return {key: val for key, val in counts.items() if val}


def available_skills(
    tactics: str, *, memory: Optional[dict[str, Any]] = None, name: str = ""
) -> dict[str, object]:
    """Named skills that actually change this script (skill-suggestion cookbook)."""

    skills: dict[str, object] = {"keep": SKILL_CRITERIA["keep"]}
    for item in portable_drafts(tactics, memory=memory, name=name):
        kind = str(item["kind"])
        key = "port_pipeline" if kind.startswith("port_pipeline_") else kind
        skills[kind] = SKILL_CRITERIA.get(
            key,
            {
                "what": f"{item.get('family')}; {item.get('token_count')} tok closed fold",
                "not_for": "A fold that TypeSafe Noul has already fired on this problem",
            },
        )
    return skills


def decision_tree(
    tactics: str,
    *,
    memory: Optional[dict[str, Any]] = None,
    name: str = "",
    skip: Optional[set[str]] = None,
) -> dict[str, list[str]]:
    """Family → skill kinds TypeSafe can nest into (decision-tree cookbook)."""

    tree: dict[str, list[str]] = {}
    for item in portable_drafts(tactics, skip=skip, memory=memory, name=name):
        fam = str(item.get("family") or "search_space")
        kind = str(item.get("kind") or "")
        if not kind:
            continue
        kids = tree.setdefault(fam, [])
        if kind not in kids:
            kids.append(kind)
    return tree
