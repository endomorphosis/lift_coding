#!/usr/bin/env python3
"""Binder-use gates and lake-error repair for MCA drops.

Dropping ``rename_i`` / ``have`` is only safe when the bound names do not
appear later in the proof. Lake ``Unknown identifier`` restores the line
that bound that name. No LLM. Not an Arena ranking.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

# Unicode letters so CCS ``μ`` counts as a binder.
IDENT = re.compile(r"[^\W\d][\w']*", re.UNICODE)
_UNKNOWN = re.compile(r"Unknown identifier `([^`]+)`")
KEYWORDS = frozenset(
    {
        "have",
        "rename_i",
        "simp",
        "simp_all",
        "rw",
        "exact",
        "apply",
        "intro",
        "intros",
        "induction",
        "case",
        "constructor",
        "refine",
        "exists",
        "by",
        "at",
        "with",
        "only",
        "all_goals",
        "obtain",
        "let",
        "show",
        "fun",
        "if",
        "then",
        "else",
        "match",
        "do",
        "pure",
        "return",
    }
)
MEMORY_DEFAULT = (
    Path(__file__).resolve().parent.parent / "evidence" / "canaries" / "refactor-memory.json"
)
SKILL_ANALYSIS_DEFAULT = MEMORY_DEFAULT.parent / "skill-analysis.json"


def binders_from_line(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("rename_i "):
        return [tok for tok in IDENT.findall(stripped[len("rename_i ") :]) if tok not in KEYWORDS]
    if stripped.startswith(("have ", "obtain ", "let ")):
        # ``have ⟨a, b⟩ :=`` / ``obtain ⟨s2', ...⟩`` bind unicode names; never treat as unused.
        if "⟨" in stripped:
            return ["__keep__"]
        rest = stripped.split(" ", 1)[1].lstrip()
        if rest.startswith(":=") or rest.startswith(":"):
            return ["this"]
        left = rest.split(":=", 1)[0]
        # Only the binder name, not identifiers in the type ascription
        # (``have der' : Typing Γ t τ := der`` binds der', not Typing/Γ/t/τ).
        name_part = left.split(":", 1)[0]
        names = [tok for tok in IDENT.findall(name_part) if tok not in KEYWORDS]
        if not names:
            names = ["this"]
        if stripped.startswith("have "):
            names.append("this")
        return list(dict.fromkeys(names))
    return []


def idents_in(text: str) -> set[str]:
    return {tok for tok in IDENT.findall(text) if tok not in KEYWORDS}


def binders_used_later(tactics: str, start: int, end: int, original: str) -> list[str]:
    names = binders_from_line(original)
    if "__keep__" in names:
        return ["__keep__"]
    if not names:
        return []
    later = idents_in(tactics[end:])
    return [name for name in names if name in later]


def _is_prefix_have(tactics: str, start: int) -> bool:
    before = tactics[:start]
    return not re.search(r"(?m)^[ \t]*(induction |cases |case )", before)


def _have_casts_inducted_hyp(tactics: str, end: int, original: str) -> bool:
    """``have der' : T := der`` then ``induction der`` is a motive cast, not dead code.

    Fsub.progress failed with ``Function expected at ih_l rfl`` after dropping it.
    """

    if ":=" not in original:
        return False
    rhs = original.split(":=", 1)[1].strip()
    match = IDENT.match(rhs)
    if not match:
        return False
    hyp = match.group(0)
    rest = tactics[end:]
    return bool(re.search(rf"(?m)^[ \t]*(induction|cases) {re.escape(hyp)}\b", rest))


def safe_to_drop_span(tactics: str, start: int, end: int, original: str) -> bool:
    """True when dropping this span cannot remove a still-referenced binder."""

    stripped = original.strip()
    if stripped.startswith(("rename_i ", "have ", "obtain ", "let ")):
        if binders_used_later(tactics, start, end, original):
            return False
        # Prefix ``have`` before induction/cases is often simp_all fuel even if
        # the name never appears (Hk / Hlen2 on InitsUpdatesComm).
        if stripped.startswith("have ") and _is_prefix_have(tactics, start) and "simp_all" in tactics[end:]:
            return False
        if stripped.startswith("have ") and _have_casts_inducted_hyp(tactics, end, original):
            return False
        return True
    if stripped.startswith("simp at"):
        return True
    return False


def drop_unused_binders(tactics: str, *, kinds: tuple[str, ...] = ("rename_i", "have")) -> str:
    """Delete rename_i/have lines whose binders are not used later."""

    lines = tactics.splitlines(keepends=True)
    offset = 0
    keep: list[str] = []
    for line in lines:
        start, end = offset, offset + len(line)
        stripped = line.strip()
        drop = False
        if "rename_i" in kinds and stripped.startswith("rename_i "):
            drop = safe_to_drop_span(tactics, start, end, line.rstrip("\n"))
        if "have" in kinds and stripped.startswith("have "):
            drop = safe_to_drop_span(tactics, start, end, line.rstrip("\n"))
        if "obtain" in kinds and stripped.startswith("obtain "):
            drop = safe_to_drop_span(tactics, start, end, line.rstrip("\n"))
        if not drop:
            keep.append(line)
        offset = end
    return "".join(keep).strip("\n")


def unknown_identifiers(errors: Sequence[Mapping[str, Any]]) -> list[str]:
    blob = "\n".join(str(item.get("data") or "") for item in errors)
    return list(dict.fromkeys(_UNKNOWN.findall(blob)))


def insert_missing_line(draft: str, reference: str, missing_line: str) -> str:
    """Put ``missing_line`` back next to a neighbor that still exists in draft."""

    if missing_line.strip() in {line.strip() for line in draft.splitlines()}:
        return draft
    ref_lines = reference.splitlines()
    try:
        index = next(i for i, line in enumerate(ref_lines) if line == missing_line)
    except StopIteration:
        try:
            index = next(i for i, line in enumerate(ref_lines) if missing_line.strip() in line)
            missing_line = ref_lines[index]
        except StopIteration:
            return missing_line + "\n" + draft
    draft_lines = draft.splitlines()
    for delta in range(1, 10):
        for neighbor_i in (index - delta, index + delta):
            if not 0 <= neighbor_i < len(ref_lines):
                continue
            neighbor = ref_lines[neighbor_i]
            if neighbor in draft_lines:
                pos = draft_lines.index(neighbor)
                insert_at = pos + 1 if neighbor_i < index else pos
                draft_lines.insert(insert_at, missing_line)
                return "\n".join(draft_lines)
    return missing_line + "\n" + draft


def restore_unknown_binders(draft: str, reference: str, errors: Sequence[Mapping[str, Any]]) -> str:
    """If lake says Unknown identifier X, restore the reference line that bound X."""

    out = draft
    for ident in unknown_identifiers(errors):
        bound = None
        for line in reference.splitlines():
            left = line.split(":=", 1)[0]
            if ident in binders_from_line(line) or ident in IDENT.findall(left):
                bound = line
                break
        if bound is None:
            continue
        out = insert_missing_line(out, reference, bound)
    return out.strip("\n")


def error_class(errors: Sequence[Mapping[str, Any]]) -> str:
    blob = "\n".join(str(item.get("data") or "") for item in errors)
    if "Unknown identifier" in blob:
        return "unknown_identifier"
    if "unsolved goals" in blob.lower() or "tactic" in blob.lower() and "unsolved" in blob.lower():
        return "unsolved_goals"
    if "type mismatch" in blob.lower() or "Application type mismatch" in blob:
        return "type_mismatch"
    if "unknown tactic" in blob.lower():
        return "unknown_tactic"
    if "don't know how to synthesize placeholder" in blob:
        return "placeholder"
    return "other"


# Draft IDs like pca_search_space_d012 change every round; ban the body, not the slot.
_EPHEMERAL = ("pca_", "sweep_rand_")
# Skills whose implementation was patched after they were banned.
_PATCHED_UNBAN = (
    "port_unused_intros",  # now skips arms whose next tactic is assumption
    "port_intro_x_hin",  # skill removed
    # binder_from_line no longer treats type ascriptions as binders (Fsub der').
    # hammer_repair used to rewrite grind → simp_all (illegal `simp_all only [→`).
    "port_apply_ih_assumption",  # skill removed
    "port_dot_ctor_apply",  # skill removed
    "port_ccs_choiceL_exact",
    "port_ccs_choiceL_hr1",
    "port_ccs_choiceR_exact",
)


def is_ephemeral_kind(kind: str) -> bool:
    text = str(kind)
    return text.startswith(_EPHEMERAL) or "_MCA_" in text


def blacklist_key(name: str, kind: str, tactics: str = "") -> str:
    if is_ephemeral_kind(kind):
        digest = hashlib.sha256((tactics or "").strip("\n").encode("utf-8")).hexdigest()[:12]
        text = str(kind)
        if "_MCA_" in text:
            family = text.rsplit("_MCA_", 1)[0]
        else:
            family = text.split("_d")[0]
        return f"{name}::{family}::{digest}"
    return f"{name}::{kind}"


def scrub_blacklist(memory: dict[str, Any]) -> dict[str, Any]:
    """Drop slot-id bans and skills whose implementation was patched."""

    kept: list[str] = []
    for key in memory.get("blacklist") or []:
        parts = str(key).split("::")
        if len(parts) < 2:
            continue
        kind = parts[1]
        if kind in _PATCHED_UNBAN or str(key) in _PATCHED_UNBAN:
            continue
        if is_ephemeral_kind(kind) and len(parts) < 3:
            continue
        kept.append(str(key))
    memory["blacklist"] = kept
    return memory


def rehydrate_from_skill_analysis(
    memory: dict[str, Any], *, path: Optional[Path] = None
) -> dict[str, Any]:
    """Restore blacklist/research from skill-analysis.json when memory was wiped."""

    target = path or SKILL_ANALYSIS_DEFAULT
    if not target.is_file():
        return {"ok": False, "reason": "no_skill_analysis", "n_blacklist": 0, "n_research": 0}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "reason": "bad_json", "n_blacklist": 0, "n_research": 0}
    gaps = list(payload.get("gaps") or [])
    empty = not (memory.get("blacklist") or memory.get("failures") or memory.get("research"))
    if not empty:
        return {
            "ok": True,
            "reason": "already_populated",
            "n_blacklist": len(memory.get("blacklist") or []),
            "n_research": len(memory.get("research") or []),
        }
    blacklist = memory.setdefault("blacklist", [])
    research = memory.setdefault("research", [])
    n_bl = 0
    n_rs = 0
    for gap in gaps:
        name = str(gap.get("name") or "")
        if not name:
            continue
        for stem in gap.get("failed_stems") or []:
            kind = str(stem)
            if not kind.startswith("port_"):
                kind = f"port_{kind}"
            key = f"{name}::{kind}"
            if key not in blacklist:
                blacklist.append(key)
                n_bl += 1
        help_scores = {
            str(row.get("residual")): float(row.get("help") or 0.0)
            for row in (gap.get("top_help") or [])
            if row.get("residual")
        }
        unsafe = {
            str(row.get("residual")): float(row.get("unsafe") or 0.0)
            for row in (gap.get("top_help") or [])
            if row.get("residual")
        }
        if help_scores or unsafe:
            research.append({"name": name, "help": help_scores, "unsafe": unsafe})
            n_rs += 1
    scrub_blacklist(memory)
    return {"ok": True, "reason": "rehydrated", "n_blacklist": n_bl, "n_research": n_rs}


def load_memory(path: Optional[Path] = None) -> dict[str, Any]:
    target = path or MEMORY_DEFAULT
    if not target.is_file():
        data: dict[str, Any] = {"successes": [], "failures": [], "blacklist": []}
    else:
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"successes": [], "failures": [], "blacklist": []}
    data.setdefault("successes", [])
    data.setdefault("failures", [])
    data.setdefault("blacklist", [])
    data.setdefault("research", [])
    data.setdefault("expanded", [])
    data.setdefault("skills", [])
    data.setdefault("skill_params", {})
    data.setdefault("observations", {})
    data.setdefault("subloop_returns", [])
    data.setdefault("nca", {})
    data.setdefault("tape", {})
    scrub_blacklist(data)
    if path is None:
        rehydrate_from_skill_analysis(data)
    return data


def save_memory(memory: Mapping[str, Any], path: Optional[Path] = None) -> Path:
    target = path or MEMORY_DEFAULT
    target.parent.mkdir(parents=True, exist_ok=True)
    cleaned = scrub_blacklist(dict(memory))
    payload = {
        "successes": list(cleaned.get("successes") or []),
        "failures": list(cleaned.get("failures") or []),
        "blacklist": list(cleaned.get("blacklist") or []),
        "research": list(cleaned.get("research") or []),
        "expanded": list(cleaned.get("expanded") or []),
        "skills": list(cleaned.get("skills") or []),
        "skill_params": dict(cleaned.get("skill_params") or {}),
        "observations": dict(cleaned.get("observations") or {}),
        "subloop_returns": list(cleaned.get("subloop_returns") or [])[-32:],
        "nca": dict(cleaned.get("nca") or {}),
        "tape": dict(cleaned.get("tape") or {}),
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def remember_research(
    memory: dict[str, Any],
    *,
    name: str,
    residuals: Mapping[str, Any],
    unsafe: Mapping[str, Any],
    help_scores: Mapping[str, Any],
    skill: str,
    compose: str,
) -> None:
    """Store AutoResearch features so later rounds can expand/skip skills."""

    memory.setdefault("research", []).append(
        {
            "name": name,
            "residuals": dict(residuals or {}),
            "unsafe": {str(k): float(v) for k, v in (unsafe or {}).items()},
            "help": {str(k): float(v) for k, v in (help_scores or {}).items()},
            "skill": skill,
            "compose": compose,
        }
    )
    # Keep last 8 snapshots per problem.
    rows = [row for row in memory["research"] if row.get("name") != name]
    mine = [row for row in memory["research"] if row.get("name") == name][-8:]
    memory["research"] = rows + mine


def failed_skill_stems(memory: Mapping[str, Any], name: str) -> set[str]:
    """Portable skill stems that lake-failed on this problem (do not re-compose)."""

    stems: set[str] = set()
    prefix = f"{name}::"
    for key in memory.get("blacklist") or []:
        if not str(key).startswith(prefix):
            continue
        kind = str(key).split("::")[1]
        if kind.startswith("port_"):
            stems.add(kind[len("port_") :])
            stems.add(kind)
    for row in memory.get("failures") or []:
        if row.get("name") != name:
            continue
        kind = str(row.get("kind") or "")
        if kind.startswith("port_"):
            stems.add(kind[len("port_") :].split("_pipeline")[0])
            stems.add(kind)
    return stems


# Drop residuals that AutoResearch marked do_not_cut mint these keep-structure skills.
KEEP_MINTS: dict[str, tuple[str, ...]] = {
    "intro_then_simp_all": ("hoist_repeated_simp", "redundant_inner_simp"),
    "ctor_lone": (),
    "grind": (),
    "use_then_exact": ("trailing_tuple_comma",),
    "have": (),
    "apply_semi_assumption": (),
    "apply_seq_assumption": (),
    "intros_x_Hin": (),
    "repeated_simp_list": ("hoist_repeated_simp",),
    "inner_simp_subset": ("redundant_inner_simp",),
    "trailing_tuple_comma": ("trailing_tuple_comma",),
}


def skill_gap_report(memory: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Per-problem next-skill notes from AutoResearch snapshots + bans."""

    import portable_rewrites as lra_port

    rows: list[dict[str, Any]] = []
    names = []
    for snap in memory.get("research") or []:
        n = str(snap.get("name") or "")
        if n and n not in names:
            names.append(n)
    for name in names:
        prior = prior_research(memory, name)
        prop = propose_skill_from_research(memory, name)
        help_scores = dict(prior.get("help") or {})
        unsafe = dict(prior.get("unsafe") or {})
        ranked_residuals = sorted(
            help_scores,
            key=lambda key: float(help_scores.get(key) or 0.0),
            reverse=True,
        )
        compose_plan = [stem for stem, _fn in lra_port.pipeline_order(dict(memory), name=name)]
        rows.append(
            {
                "name": name,
                "proposed": prop,
                "keep_intro": "intro_then_simp_all" in unsafe,
                "keep_constructor": "ctor_lone" in unsafe,
                "keep_structure": list(prop.get("mint") or []),
                "compose_plan": compose_plan,
                "failed_stems": sorted(failed_skill_stems(memory, name)),
                "top_help": [
                    {
                        "residual": key,
                        "help": round(float(help_scores.get(key) or 0.0), 3),
                        "unsafe": round(float(unsafe.get(key) or 0.0), 3),
                        "do_not_cut": float(unsafe.get(key) or 0.0) >= 0.45,
                    }
                    for key in ranked_residuals[:4]
                ],
            }
        )
    return rows


def propose_skill_from_research(memory: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Highest-help residual that is safe to cut; else a keep-structure mint."""

    prior = prior_research(memory, name)
    help_scores = dict(prior.get("help") or {})
    unsafe = dict(prior.get("unsafe") or {})
    best = None
    best_help = -1.0
    for residual, help in help_scores.items():
        u = float(unsafe.get(residual) or 0.0)
        h = float(help or 0.0)
        if u < 0.45 and h > best_help:
            best = residual
            best_help = h
    if best is not None:
        return {
            "residual": best,
            "help": best_help,
            "unsafe": float(unsafe.get(best) or 0.0),
            "keep_structure": False,
        }
    ranked = sorted(
        help_scores,
        key=lambda key: float(help_scores.get(key) or 0.0),
        reverse=True,
    )
    for residual in ranked:
        mints = KEEP_MINTS.get(residual)
        if mints:
            return {
                "residual": residual,
                "help": float(help_scores.get(residual) or 0.0),
                "unsafe": float(unsafe.get(residual) or 0.0),
                "keep_structure": True,
                "mint": list(mints),
            }
    return {}


def expand_skills_from_memory(
    memory: dict[str, Any], *, name: str, tactics: str = ""
) -> list[dict[str, Any]]:
    """Record keep-structure mints when AutoResearch says do not cut the residual."""

    import portable_rewrites as lra_port

    prop = propose_skill_from_research(memory, name)
    notes: list[dict[str, Any]] = []
    if prop.get("keep_structure") and prop.get("mint"):
        notes.append({**prop, "name": name, "action": "keep_structure"})
    if tactics:
        residuals = lra_port.analyze_residuals(tactics)
        for stem in lra_port.KEEP_STRUCTURE:
            residual = lra_port.SKILL_RESIDUAL.get(stem, stem)
            if residuals.get(residual):
                notes.append(
                    {
                        "name": name,
                        "action": "keep_structure",
                        "residual": residual,
                        "mint": [stem],
                        "present": residuals.get(residual),
                    }
                )
    if notes:
        memory.setdefault("expanded", []).append({"name": name, "notes": notes})
        rows = [row for row in memory["expanded"] if row.get("name") != name]
        mine = [row for row in memory["expanded"] if row.get("name") == name][-8:]
        memory["expanded"] = rows + mine
    return notes


ALLOWED_KEEP = frozenset(
    {
        "intro",
        "intros",
        "constructor",
        "grind",
        "induction",
        "case",
        "exact",
        "use",
        "have",
        "simp_all",
    }
)
_STEM_OK = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,40}$")


def install_memory_skill(memory: dict[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    """Store a closed keep-structure fold spec. Does not exec Python or write Lean."""

    stem = str(spec.get("stem") or "").strip()
    old = str(spec.get("old") or "")
    new = str(spec.get("new") or "")
    keep = [str(item) for item in (spec.get("keep") or []) if str(item) in ALLOWED_KEEP]
    if not _STEM_OK.match(stem):
        return {"ok": False, "reason": "bad_stem"}
    if not old or old == new:
        return {"ok": False, "reason": "empty_fold"}
    if len(old) > 400 or len(new) > 400:
        return {"ok": False, "reason": "fold_too_long"}
    for word in keep:
        if word in old and word not in new:
            return {"ok": False, "reason": f"drops_{word}"}
    row = {
        "stem": stem,
        "old": old,
        "new": new,
        "keep": keep,
        "family": str(spec.get("family") or "search_space"),
        "count": max(1, int(spec.get("count") or 1)),
    }
    skills = memory.setdefault("skills", [])
    skills[:] = [item for item in skills if str(item.get("stem")) != stem]
    skills.append(row)
    return {"ok": True, "skill": row}


def prior_research(memory: Mapping[str, Any], name: str) -> dict[str, Any]:
    rows = [row for row in memory.get("research") or [] if row.get("name") == name]
    return dict(rows[-1]) if rows else {}


def remember_success(
    memory: dict[str, Any],
    *,
    name: str,
    kind: str,
    family: str,
    from_tokens: int,
    to_tokens: int,
) -> None:
    memory.setdefault("successes", []).append(
        {
            "name": name,
            "kind": kind,
            "family": family,
            "from_tokens": int(from_tokens),
            "to_tokens": int(to_tokens),
        }
    )


def remember_failure(
    memory: dict[str, Any],
    *,
    name: str,
    kind: str,
    errors: Sequence[Mapping[str, Any]],
    tactics: str = "",
) -> None:
    unknowns = unknown_identifiers(errors)
    key = blacklist_key(name, kind, tactics)
    memory.setdefault("failures", []).append(
        {
            "name": name,
            "kind": kind,
            "error_class": error_class(errors),
            "unknown": unknowns,
            "key": key,
        }
    )
    blacklist = memory.setdefault("blacklist", [])
    if key not in blacklist:
        blacklist.append(key)
    if tactics:
        digest = hashlib.sha256(tactics.strip("\n").encode("utf-8")).hexdigest()[:12]
        body_key = f"{name}::body::{digest}"
        if body_key not in blacklist:
            blacklist.append(body_key)


def is_blacklisted(
    memory: Mapping[str, Any], name: str, kind: str, tactics: str = ""
) -> bool:
    keys = set(memory.get("blacklist") or [])
    if blacklist_key(name, kind, tactics) in keys:
        return True
    # Stable skills also match the old name::kind form.
    if not is_ephemeral_kind(kind) and f"{name}::{kind}" in keys:
        return True
    # Same body under a different kind (port_use_exact_reuse vs pca_search_space).
    if tactics:
        digest = hashlib.sha256(tactics.strip("\n").encode("utf-8")).hexdigest()[:12]
        if any(str(key).endswith(f"::{digest}") for key in keys):
            return True
    return False
