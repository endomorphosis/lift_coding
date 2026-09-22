#!/usr/bin/env python3
"""Mask MCA residual spans, keep the PCA skeleton, fill holes, lake-check.

Principal structure (induction, ``case`` arms, closing exact/constructor) stays.
Minor residuals (simp-at runs, have/rename_i, rw chains) become holes.

Fills:
- deterministic compiler templates (dead_code / strength_reduction / algebraic)
- one hosted Labs Leanstral pass over the masked skeleton
- optional Track 1 grok-4.6 few-shot + one lake-error repair (max 2 grok calls)

TypeSafe ranks the reassembled candidates. Lake is the oracle.
Never docker0. Never LOCK_EX. Not official Track 2. Not an Arena ranking.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass

from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
OUT_DEFAULT = PAPER_ROOT / "evidence" / "canaries"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _jevops_path  # noqa: E402,F401
import draft_fanout as lra_fan  # noqa: E402
import pca_mca_fanout as lra_pca  # noqa: E402
import run_warmup as lra_loop  # noqa: E402
import splice as lra_splice  # noqa: E402
import track1_keepbest as lra_kb  # noqa: E402
import track1_ledger as lra_t1  # noqa: E402
import track1_mistral_leanstral as lra_mistral  # noqa: E402
from jevops.catalogs import DEFAULT_TRACK1_STATE as DEFAULT_STATE
from jevops.catalogs import GROK_MAX_NEW_TOKENS
from jevops.catalogs import GROK_TIMEOUT_SECONDS
from jevops.catalogs import HARDWARE_CLASS_GROK as GROK_HARDWARE_CLASS
from jevops.catalogs import MAX_GROK_FANOUT
from jevops.catalogs import MCA_READY as LAKE_READY
from jevops.catalogs import MISTRAL_HARDWARE_CLASS as HARDWARE_CLASS
from jevops.catalogs import PROTOCOL
from jevops.catalogs import SHOT_NAMES

PR_ID = "PR-9d"
_SIMP_AT = lra_fan._SIMP_AT
_RW = lra_pca._RW_BRACKET
_RENAME = lra_pca._RENAME
_HAVE = lra_pca._HAVE
from jevops.tactics import Hole
from jevops.tactics import MCA_HOLE as _HOLE
from jevops.tactics import SKELETON_PREFIXES
from jevops.tactics import apply_fills as _apply_fills
from jevops.tactics import find_holes as _find_holes
from jevops.tactics import hole_row as _as_row
from jevops.tactics import mask_mca
from jevops.tactics import mca_marker as _mca_marker
from jevops.tactics import template_fill as _template_fill


def find_holes(tactics: str) -> list[Hole]:
    """Residual MCA spans: simp-at runs, rw runs, rename_i, have."""

    return _find_holes(tactics)


def mask_skeleton(tactics: str, holes: Sequence[Hole]) -> str:
    """Replace MCA spans with hole markers. PCA skeleton (case/induction) stays."""

    return mask_mca(tactics, holes)


def template_fill(hole: Hole) -> str:
    return _template_fill(hole)


def apply_fills(tactics: str, holes: Sequence[Hole], fills: Mapping[str, str]) -> str:
    return _apply_fills(tactics, holes, fills)


def parse_leanstral_fills(text: str, holes: Sequence[Hole]) -> dict[str, str]:
    """Accept either per-hole blocks or a full tactic block."""

    from jevops.mask import parse_marked_fills

    return parse_marked_fills(
        text,
        holes,
        attr="family",
        fallback_fn=lra_loop.extract_generated_tactics,
    )


def leanstral_prompt(record: Mapping[str, Any], skeleton: str, holes: Sequence[Hole]) -> str:
    from jevops.tactics import mca_hole_prompt as _fn

    return _fn(record, skeleton, holes)


def one_hole_prompt(record: Mapping[str, Any], tactics: str, hole: Hole) -> str:
    from jevops.tactics import mca_one_hole_prompt as _fn

    return _fn(record, tactics, hole)


def few_shot_example(record: Mapping[str, Any]) -> dict[str, Any]:
    tactics = lra_fan.tactic_block(record)
    holes = find_holes(tactics)
    fills = {hole.hole_id: template_fill(hole) for hole in holes}
    filled = apply_fills(tactics, holes, fills)
    from jevops.outer import get_str
    from jevops.pick import shot_stats

    return shot_stats(
        get_str(record, "name"),
        tactics,
        filled,
        token_fn=lra_loop.token_count,
        extra={
            "n_holes": len(holes),
            "families": [hole.family for hole in holes],
            "skeleton": mask_skeleton(tactics, holes),
            "reference": tactics,
            "filled": filled,
        },
    )


def few_shot_prompt(target: Mapping[str, Any], shots: Sequence[Mapping[str, Any]]) -> str:
    from jevops.tactics import few_shot_prompt as _fn

    tactics = lra_fan.tactic_block(target)
    holes = find_holes(tactics)
    skeleton = mask_skeleton(tactics, holes)
    return _fn(
        target,
        shots,
        tactics=tactics,
        skeleton=skeleton,
        token_count=lra_loop.token_count(tactics),
    )


def shot_examples(records: Sequence[Mapping[str, Any]], *, skip_name: str) -> list[dict[str, Any]]:
    from jevops.outer import named_shots

    return named_shots(records, SHOT_NAMES, skip_name=skip_name, example_fn=few_shot_example)


def _kind_needs_hammer(kind: str) -> bool:
    from jevops.mask import starts_any

    return starts_any(kind, ("leanstral", "grok", "mca_leanstral", "tactician", "hybrid", "pca_"))


def _identity_dict(identity: Any) -> Optional[dict[str, Any]]:
    from jevops.outer import either, object_fields, overlay_map, set_if

    def _fields() -> Optional[dict[str, Any]]:
        row = object_fields(
            identity,
            (
                "requested_provider",
                "requested_model",
                "resolved_provider",
                "resolved_model",
                "fallback_used",
            ),
            extra={"arena_score": None},
        )
        set_if(row, row and "fallback_used" in row, "fallback_used", bool(overlay_map(row).get("fallback_used")))
        return row

    return either(isinstance(identity, Mapping), lambda: overlay_map(identity), _fields)


def _flatten_tactics(reference: str, text: str) -> str:
    from jevops.repair import align_generated

    return align_generated(
        reference,
        text,
        extract_fn=lra_loop.extract_generated_tactics,
        match_fn=lra_kb.match_reference_indent,
        flatten_fn=lra_kb.flatten_overindent,
    )


def _compile_row(item: Mapping[str, Any], compiled: Mapping[str, Any]) -> dict[str, Any]:
    from jevops.search import compile_head_row

    from jevops.outer import get_list, get_str

    return compile_head_row(
        get_str(item, "kind"),
        get_str(item, "tactics"),
        compiled,
        extra={
            "generator": item.get("generator"),
            "n_holes": len(get_list(item, "holes")),
        },
    )


def _hammer_passes(
    *,
    kind: str,
    tactics_now: str,
    reference: str,
    errors: Sequence[Mapping[str, Any]],
    record: Mapping[str, Any],
    state_root: Path,
    timeout: float,
    restore: bytes,
    generator: str,
) -> tuple[list[dict[str, Any]], str, list[Any], bool]:
    from jevops.tactics import hammer_until

    def _compile(body: str) -> Mapping[str, Any]:
        return lra_kb.compile_tactics(
            record, body, state_root=state_root, timeout=timeout, restore=restore
        )

    def _row(*, kind: str, generator: str, tactics: str, compiled: Mapping[str, Any]) -> Mapping[str, Any]:
        return _compile_row(
            {"kind": kind, "generator": generator, "tactics": tactics, "holes": []},
            compiled,
        )

    return hammer_until(
        tactics_now,
        reference,
        errors,
        _compile,
        _row,
        kind=kind,
        generator=generator,
    )


# Cslib scripts use ``grind`` / ``grind only [→ wf]``. Never rewrite grind
# unless the lake error is specifically "unknown tactic grind" (Strata).
from jevops.tactics import UNKNOWN_TACTICS as _UNKNOWN_TACTICS


def hammer_repair(draft: str, reference: str, errors: Sequence[Mapping[str, Any]]) -> str:
    """Local tactician: restore PCA glue, drop illegal tactics, then simp_all/omega.

    Strata/CSLib lake projects do not depend on Aesop. Portable closers are
    ``simp_all`` and ``omega``. Aesop is only safe on Putnam's Mathlib+Aesop lake.
    """

    from jevops.tactics import hammer_repair as _fn

    return _fn(draft, reference, errors)


def case_tag(label: str) -> str:
    from jevops.tactics import case_tag as _fn

    return _fn(label)


def replace_case_from(dst: str, src: str, tag: str) -> str:
    """Replace one top-level ``case`` arm in ``dst`` with the matching arm from ``src``."""

    from jevops.tactics import replace_case_from as _fn

    return _fn(dst, src, tag)


def drop_bare_simp_all(tactics: str) -> str:
    from jevops.tactics import drop_bare_simp_all as _fn

    return _fn(tactics)


def try_simp_all(tactics: str) -> str:
    from jevops.tactics import try_simp_all as _fn

    return _fn(tactics)


def grok_tactician_variants(grok: str, reference: str) -> list[dict[str, Any]]:
    """Deterministic repairs of a grok file draft. Jev does not write these."""

    import inits_updates_shorten as lra_ius
    from jevops.tactics import tactician_variants as _fn

    return _fn(grok, reference, replay_fn=lra_ius.replay, propose_fn=lra_ius.propose)





def assemble_candidates(
    record: Mapping[str, Any],
    tactics: str,
    holes: Sequence[Hole],
    *,
    leanstral_text: Optional[str],
) -> list[dict[str, Any]]:
    del record
    import inits_updates_shorten as lra_ius
    from jevops.outer import optional_fn
    from jevops.tactics import assemble_mca_candidates as _fn

    return _fn(
        tactics,
        holes,
        leanstral_text=leanstral_text,
        replay_fn=lra_ius.replay,
        parse_fills_fn=optional_fn(leanstral_text, parse_leanstral_fills),
        indent_fn=lra_kb.match_reference_indent,
        flatten_fn=lra_kb.flatten_overindent,
    )


def prioritize_holes(holes: Sequence[Hole], *, cap: int = 6) -> list[Hole]:
    from jevops.mask import rank_cap

    rank = {"strength_reduction": 0, "algebraic_simplification": 1, "dead_code": 2, "loop_invariant": 3}
    return rank_cap(
        holes,
        key=lambda hole: (rank.get(hole.family, 9), -len(hole.original), hole.hole_id),
        cap=cap,
    )


def ablate_holes(
    record: Mapping[str, Any],
    tactics: str,
    holes: Sequence[Hole],
    *,
    state_root: Path,
    timeout: float,
    restore: bytes,
) -> list[dict[str, Any]]:
    """Drop one MCA hole at a time, then combine lake-valid drops."""

    from jevops.search import ablate_then_combine

    def _compile(body: str) -> Mapping[str, Any]:
        return lra_kb.compile_tactics(
            record, body, state_root=state_root, timeout=timeout, restore=restore
        )

    return ablate_then_combine(
        tactics,
        holes,
        apply_fn=lambda text, fills: apply_fills(text, holes, fills),
        fill_fn=template_fill,
        compile_fn=_compile,
    )


def typesafe_rank_fanout(
    record: Mapping[str, Any],
    drafts: Sequence[dict[str, Any]],
    *,
    ledger: Optional[Any],
) -> dict[str, Any]:
    """One Jev Choice over tactician/PCA drafts. Jev does not write Lean."""

    from jevops.jev import skipped
    from jevops.outer import exc_head, first_call, head_chars, head_seq, pin_calls

    from jevops.outer import call_if, first_not_none

    early = first_call((not drafts, lambda: skipped("no_drafts", arena_score=None)))

    def _rank() -> dict[str, Any]:
        from jevops.jev import typesafe_session

        loaded, skip = typesafe_session(
            setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
            fallback=False,
            arena_score=None,
        )
        if skip is not None:
            return skip
        Choice = loaded["Choice"]
        TypeSafeClient = loaded["TypeSafeClient"]

        def _ask() -> dict[str, Any]:
            from jevops.jev import draft_rank_state

            from jevops.catalogs import RANK_FANOUT_BEST, RANK_FANOUT_GOAL

            packed = draft_rank_state(
                record,
                drafts,
                goal=RANK_FANOUT_GOAL,
            )
            criteria = packed["criteria"]
            state = packed["state"]
            questions = {
                "best_first_draft": Choice(
                    instructions=RANK_FANOUT_BEST,
                    criteria=criteria,
                )
            }
            from jevops.jev import charge_packed, invoke_or_skip, invoke_system_one, pack_best_draft
            from jevops.outer import dumps_compact

            def _project(result: Any, wall_ms: float) -> dict[str, Any]:
                return charge_packed(
                    pack_best_draft(result, wall_ms=wall_ms),
                    ledger,
                    model=lra_t1.JEV_MODEL_ID,
                    fallback_in=lra_t1.estimate_tokens(dumps_compact(state)),
                    redact_fn=lra_pca.redact,
                )

            return invoke_or_skip(
                invoke_fn=lambda: invoke_system_one(TypeSafeClient(timeout=60.0), state, questions),
                project_fn=_project,
                skip_fn=lambda exc: skipped(exc_head(exc, 400), arena_score=None),
            )

        return _ask()

    return first_not_none(early, factory=_rank)


def load_grok_tactics_file(path: Path) -> str:
    from jevops.outer import read_text

    text = read_text(path)
    return lra_loop.extract_generated_tactics(text)


def run_problem(
    name: str,
    *,
    state_root: Path,
    timeout: float,
    call_leanstral: bool,
    ablate: bool = False,
    one_hole: bool = False,
    few_shot: bool = False,
    grok_few_shot: bool = False,
    grok_generate: Optional[Callable[..., str]] = None,
    grok_trace: Optional[Callable[[], Mapping[str, Any]]] = None,
    grok_tactics_paths: Sequence[Path] = (),
    typesafe_fanout: bool = False,
) -> dict[str, Any]:
    from jevops.outer import (
        after_calls,
        call_caught,
        call_if,
        caught_reason,
        dict_call,
        either,
        first_truthy,
        fit_drop,
        get_list,
        get_str,
        head_chars,
        if_none,
        if_prefix,
        load_and_clone,
        mark_skipped,
        optional_fn,
        or_call,
        or_none,
        or_str,
        str_or_none,
        tagged_mapping,
        take_keys,
        text_or,
    )
    from jevops.repair import align_generated
    from jevops.search import (
        after_compile_row,
        begin_masked,
        collect_grok_fanout_extras,
        collect_one_hole_fills,
        collect_path_candidates,
        dispatch_mca_generation,
        flatten_shot,
        pack_failed_candidate,
        pack_generated_candidate,
        pin_grok_fanout,
        run_mca_problem,
    )

    record, records, digest, _clone, _dest, restore = load_and_clone(
        lra_splice.load_warmup_records,
        name,
        state_root,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
        error_cls=RuntimeError,
        miss=f"unknown warm-up problem: {name}",
    )
    masked = begin_masked(
        record,
        tactic_fn=lra_fan.tactic_block,
        find_fn=find_holes,
        mask_fn=mask_skeleton,
        fill_pred=lambda hole: hole.family in {"strength_reduction", "algebraic_simplification"},
    )
    tactics, holes, skeleton, fill_holes = take_keys(
        masked, "tactics", "holes", "skeleton", "fill_holes"
    )

    def _grok_paths() -> dict[str, Any]:
        ledger = lra_t1.ProblemLedger(name=f"{name}#grok-file-fanout")
        rows = collect_path_candidates(
            grok_tactics_paths,
            load_fn=load_grok_tactics_file,
            flatten_fn=lambda text: _flatten_tactics(tactics, text),
            pack_fn=pack_generated_candidate,
            generator="grok-file",
            extra={"chat_ignored": True},
            head_fn=head_chars,
        )
        return {"ledger": ledger, "grok_file_rows": rows}

    def _grok_few_shot() -> dict[str, Any]:
        shots = shot_examples(records, skip_name=name)
        ledger = lra_t1.ProblemLedger(name=f"{name}#grok-few-shot")
        if grok_generate is None and not lra_t1.grok_callable():
            mark_skipped(ledger, "no_key")
            return {"ledger": ledger, "grok_skip_reason": "no_key"}
        workspace = lra_t1.prepare_grok_workspace()
        prompt = lra_t1.grok_file_prompt(few_shot_prompt(record, shots))
        ok, grok_result, exc = call_caught(
            lambda: lra_t1.generate_grok_file(
                prompt,
                ledger,
                workspace=workspace,
                max_new_tokens=GROK_MAX_NEW_TOKENS,
                timeout=GROK_TIMEOUT_SECONDS,
                generate=grok_generate,
                fixture=grok_generate is not None,
                reset_stub=True,
            ),
            lra_t1.Track1LedgerError,
        )
        skip_reason, grok_result = caught_reason(ok, grok_result, exc)
        out: dict[str, Any] = {
            "ledger": ledger,
            "grok_workspace": workspace,
            "grok_skip_reason": skip_reason,
            "grok_file_meta": [],
        }
        if grok_result is not None:
            _tactics, row = flatten_shot(
                kind="grok_few_shot",
                generator="grok-4.6",
                text=grok_result.tactics,
                shots=shots,
                flatten_fn=lambda text: _flatten_tactics(tactics, text),
                pack_fn=pack_generated_candidate,
                extra={
                    "source": "tactics.lean",
                    "tactics_path": grok_result.tactics_path,
                    "chat_ignored": True,
                },
            )
            out["identity"] = grok_result.identity
            out["grok_few_shot_row"] = row
            out["grok_file_meta"] = [tagged_mapping("draft", grok_result)]
        return out

    def _few_shot() -> dict[str, Any]:
        shots = shot_examples(records, skip_name=name)
        ledger = lra_t1.ProblemLedger(name=f"{name}#few-shot")
        prompt = few_shot_prompt(record, shots)
        text, identity, _line = after_calls(
            (lra_mistral.load_keyfiles, lra_mistral.pin_paths),
            lra_mistral.generate_mistral,
            prompt,
            ledger,
            max_new_tokens=900,
            timeout=180.0,
        )
        _filled, row = flatten_shot(
            kind="leanstral_few_shot",
            generator="labs-leanstral-1-5",
            text=text,
            shots=shots,
            flatten_fn=lambda body: _flatten_tactics(tactics, body),
            pack_fn=pack_generated_candidate,
        )
        return {"ledger": ledger, "identity": identity, "few_shot_row": row}

    def _one_hole() -> dict[str, Any]:
        targets = prioritize_holes(first_truthy(fill_holes, holes), cap=2)
        if not targets:
            return {}
        ledger = lra_t1.ProblemLedger(name=f"{name}#mca-one-hole")
        after_calls((lra_mistral.load_keyfiles, lra_mistral.pin_paths), lambda: None)
        fills, identity = collect_one_hole_fills(
            targets,
            holes,
            tactics,
            generate_fn=lambda hole: lra_mistral.generate_mistral(
                one_hole_prompt(record, tactics, hole),
                ledger,
                max_new_tokens=256,
                timeout=120.0,
            ),
            parse_fn=parse_leanstral_fills,
            fallback_fn=lra_loop.extract_generated_tactics,
            apply_fn=apply_fills,
            align_fn=lambda filled: align_generated(
                tactics,
                filled,
                extract_fn=lambda text: text,
                match_fn=lra_kb.match_reference_indent,
                flatten_fn=lra_kb.flatten_overindent,
            ),
            pack_fn=pack_generated_candidate,
            asdict_fn=asdict,
            skip_exc=(lra_mistral.Track1MistralError,),
            generator="labs-leanstral-1-5",
            head_fn=head_chars,
        )
        return {"ledger": ledger, "identity": identity, "one_hole_fills": fills}

    def _mask() -> dict[str, Any]:
        ledger = lra_t1.ProblemLedger(name=f"{name}#mca-mask")
        prompt = leanstral_prompt(record, mask_skeleton(tactics, fill_holes), fill_holes)
        text, identity, _line = after_calls(
            (lra_mistral.load_keyfiles, lra_mistral.pin_paths),
            lra_mistral.generate_mistral,
            prompt,
            ledger,
            max_new_tokens=700,
            timeout=180.0,
        )
        return {"ledger": ledger, "identity": identity, "leanstral_text": text}

    generated = dispatch_mca_generation(
        grok_paths=grok_tactics_paths,
        grok_few_shot=grok_few_shot,
        few_shot=few_shot,
        call_leanstral=call_leanstral,
        one_hole=one_hole,
        fill_holes=fill_holes,
        holes=holes,
        grok_paths_fn=_grok_paths,
        grok_few_shot_fn=_grok_few_shot,
        few_shot_fn=_few_shot,
        one_hole_fn=_one_hole,
        mask_fn=_mask,
    )
    grok_few_shot = bool(generated.get("grok_few_shot"))

    def _compile(body: str) -> dict[str, Any]:
        return dict_call(
            lra_kb.compile_tactics,
            record,
            body,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )

    def _hammer(kind: str, item: Mapping[str, Any], compiled: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str, list[Any], bool]:
        hammer_gen = if_prefix(kind, "grok", "grok+simp_all/omega", "leanstral+simp_all/omega")
        return _hammer_passes(
            kind=kind,
            tactics_now=get_str(item, "tactics"),
            reference=tactics,
            errors=get_list(compiled, "errors"),
            record=record,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
            generator=hammer_gen,
        )

    def _repair(
        rows: list[dict[str, Any]], grok_ok: bool, grok_tactics: str, grok_errors: list[Any]
    ) -> tuple[list[dict[str, Any]], bool]:
        grok_few_shot_row = generated.get("grok_few_shot_row")
        ledger = generated.get("ledger")
        grok_tactics_current = first_truthy(grok_tactics, default="")
        grok_errors_current = get_list(grok_errors)
        if not (grok_few_shot and grok_few_shot_row is not None and not grok_ok and ledger is not None):
            return rows, grok_ok
        prompt = lra_t1.grok_file_prompt(
            lra_kb.repair_prompt(
                record,
                failed=or_call(grok_tactics_current, lambda: grok_few_shot_row["tactics"]),
                errors=grok_errors_current,
                reference=tactics,
            )
        )
        ok, grok_result, exc = call_caught(
            lambda: lra_t1.generate_grok_file(
                prompt,
                ledger,
                workspace=if_none(generated.get("grok_workspace"), factory=lra_t1.prepare_grok_workspace),
                max_new_tokens=GROK_MAX_NEW_TOKENS,
                timeout=GROK_TIMEOUT_SECONDS,
                generate=grok_generate,
                fixture=grok_generate is not None,
                reset_stub=False,
            ),
            lra_t1.Track1LedgerError,
        )
        if not ok:
            generated["grok_skip_reason"] = or_str(generated.get("grok_skip_reason"), exc)
            rows.append(
                pack_failed_candidate(
                    kind="grok_few_shot_repair",
                    generator="grok-4.6",
                    reason=text_or(exc),
                    extra={"source": "tactics.lean", "chat_ignored": True},
                )
            )
            return rows, grok_ok
        generated["identity"] = grok_result.identity
        generated.setdefault("grok_file_meta", []).append(tagged_mapping("repair", grok_result))
        repaired_tactics = _flatten_tactics(tactics, grok_result.tactics)
        compiled_r = lra_kb.compile_tactics(
            record,
            repaired_tactics,
            state_root=state_root,
            timeout=timeout,
            restore=restore,
        )
        rows, hammer_ok = after_compile_row(
            rows,
            {
                "kind": "grok_few_shot_repair",
                "generator": "grok-4.6",
                "tactics": repaired_tactics,
                "holes": [],
            },
            compiled_r,
            row_fn=_compile_row,
            hammer_fn=lambda: _hammer_passes(
                kind="grok_few_shot_repair",
                tactics_now=repaired_tactics,
                reference=tactics,
                errors=get_list(compiled_r, "errors"),
                record=record,
                state_root=state_root,
                timeout=timeout,
                restore=restore,
                generator="grok+simp_all/omega",
            ),
        )
        if compiled_r.get("theorem_ok"):
            return rows, True
        return rows, bool(first_truthy(grok_ok, hammer_ok, default=False))

    def _fanout(candidates: list[dict[str, Any]], ledger: Any) -> dict[str, Any]:
        from jevops.outer import first_where, kind_startswith

        seed_row = first_where(candidates, kind_startswith("grok"))
        if seed_row is None:
            seed_row = {"tactics": tactics}
        _raw, _digest, warmup_records = lra_splice.load_warmup_records()
        extras = collect_grok_fanout_extras(
            seed_row["tactics"],
            tactics,
            tactician_fn=grok_tactician_variants,
            feature_fn=lra_pca.count_tactics,
            family_fn=lra_pca.amenable_families,
            draft_fn=lra_pca.guided_drafts,
            model=fit_drop(warmup_records, lra_pca.feature_row, lra_pca.fit_pca_mca),
        )
        ranked = typesafe_rank_fanout(record, extras, ledger=ledger)
        pin_grok_fanout(
            candidates,
            extras,
            get_str(ranked, "best_first_draft"),
            cap=MAX_GROK_FANOUT,
            key_fn=lambda item: item["kind"],
        )
        return ranked

    return run_mca_problem(
        generated=generated,
        name=name,
        digest=digest,
        tactics=tactics,
        holes=holes,
        skeleton=skeleton,
        assemble_fn=lambda leanstral_text, holes: assemble_candidates(
            record, tactics, holes, leanstral_text=leanstral_text
        ),
        compile_fn=_compile,
        row_fn=_compile_row,
        hammer_fn=_hammer,
        needs_hammer_fn=_kind_needs_hammer,
        repair_fn=_repair,
        ablate_fn=optional_fn(
            ablate and holes,
            lambda: ablate_holes(
                record,
                tactics,
                prioritize_holes(holes, cap=6),
                state_root=state_root,
                timeout=timeout,
                restore=restore,
            ),
        ),
        fanout_fn=_fanout,
        extra_fn=lambda grok_ok, grok_tactics, grok_errors, generated, typesafe_meta: {
            "leanstral_identity": either(generated.get("grok_few_shot"), lambda: None, lambda: generated.get("identity")),
            "grok_identity": call_if(generated.get("grok_few_shot"), lambda: _identity_dict(generated.get("identity"))),
            "grok_few_shot": bool(generated.get("grok_few_shot")),
            "grok_ok": grok_ok,
            "grok_skip_reason": or_none(generated.get("grok_skip_reason")),
            "grok_used_file": bool(generated.get("grok_few_shot")),
            "grok_chat_ignored": bool(generated.get("grok_few_shot")),
            "grok_workspace": str_or_none(generated.get("grok_workspace")),
            "grok_file_calls": list(generated.get("grok_file_meta") or ()),
            "typesafe_fanout": typesafe_meta,
            "ledger": call_if(generated.get("ledger"), lambda: generated["ledger"].as_dict()),
        },
        redact_fn=lra_pca.redact,
        token_fn=lra_loop.token_count,
        head_fn=head_chars,
        asdict_fn=asdict,
        hardware_class=HARDWARE_CLASS,
        grok_hardware_class=GROK_HARDWARE_CLASS,
        grok_paths=grok_tactics_paths,
        typesafe_fanout=typesafe_fanout,
    )


def self_check() -> dict[str, Any]:
    tactics = (
        "  induction post <;> simp [substOld]\n"
        "  case fvar =>\n"
        "    intros x Hin\n"
        "    simp at m\n"
        "    simp at name\n"
        "    simp_all\n"
        "  case op =>\n"
        "    rename_i foo\n"
        "    exact h\n"
    )
    holes = find_holes(tactics)
    skeleton = mask_skeleton(tactics, holes)
    fills = {hole.hole_id: template_fill(hole) for hole in holes}
    filled = apply_fills(tactics, holes, fills)
    from jevops.outer import finalize_ok

    return finalize_ok(
        {
            "n_holes": len(holes),
            "families": [hole.family for hole in holes],
            "arena_score": None,
        },
        len(holes) >= 2,
        "<<<MCA_0" in skeleton,
        "induction post" in skeleton,
        "case fvar" in skeleton,
        "simp at m" not in filled,
        "rename_i" not in filled,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-leanstral", action="store_true")
    parser.add_argument("--ablate", action="store_true", help="lake-check dropping one MCA hole at a time")
    parser.add_argument("--one-hole", action="store_true", help="hosted Leanstral fills one MCA hole at a time")
    parser.add_argument("--few-shot", action="store_true", help="few-shot Leanstral from scored MCA hole examples")
    parser.add_argument(
        "--grok-few-shot",
        action="store_true",
        help="few-shot grok-4.6 + one lake-error repair (max 2 grok calls, no Leanstral)",
    )
    parser.add_argument(
        "--grok-tactics",
        default="",
        help="comma-separated grok tactics.lean files to repair (no new grok calls)",
    )
    parser.add_argument(
        "--typesafe-fanout",
        action="store_true",
        help="TypeSafe Choice + PCA/MCA/tactician fan-out over grok file drafts",
    )
    parser.add_argument("--names", default=",".join(LAKE_READY))
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    from jevops.outer import list_or_none

    args = parser.parse_args(list_or_none(argv))
    if args.few_shot and args.grok_few_shot:
        raise SystemExit("use either --few-shot (Leanstral) or --grok-few-shot, not both")
    if args.self_check or not args.live:
        from jevops.outer import print_ok

        return print_ok(self_check())
    from jevops.outer import pin_env

    pin_env({"IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART": "0"}, overwrite=False)
    from jevops.outer import split_csv

    names = split_csv(args.names)
    grok_paths = split_csv(args.grok_tactics, cast=Path)
    started = time.perf_counter()
    reports = [
        run_problem(
            name,
            state_root=args.state_root,
            timeout=args.timeout,
            call_leanstral=not args.no_leanstral and not args.grok_few_shot and not grok_paths,
            ablate=args.ablate,
            one_hole=args.one_hole,
            few_shot=args.few_shot,
            grok_few_shot=args.grok_few_shot,
            grok_tactics_paths=grok_paths,
            typesafe_fanout=args.typesafe_fanout,
        )
        for name in names
    ]
    from jevops.outer import elapsed_ms, utc_stamp, write_json_pair

    payload = {
        "schema": "lra-mca-mask-replace-batch/v1",
        "observed_at": utc_stamp(),
        "protocol": PROTOCOL,
        "pr": PR_ID,
        "called_docker0": False,
        "grok_few_shot": bool(args.grok_few_shot),
        "typesafe_fanout": bool(args.typesafe_fanout),
        "arena_score": None,
        "wall_ms": elapsed_ms(started),
        "problems": reports,
    }
    latest = write_json_pair(
        args.out,
        payload,
        prefix="mca-mask",
        latest="mca-mask-latest.json",
        refuse="apikey_",
    )
    stamp = utc_stamp(fmt="%Y%m%dT%H%M%SZ")
    from jevops.outer import copy_text, get_list, get_str, print_json, text_or

    copied = []
    for item in reports:
        for call in get_list(item, "grok_file_calls"):
            src = Path(get_str(call, "tactics_path"))
            if not src.is_file():
                continue
            dest = args.out / f"grok-{item.get('name')}-{call.get('call')}-{stamp}.lean"
            copy_text(src, dest)
            copied.append(text_or(dest))

    print_json(
        {
            "ok": True,
            "latest": text_or(latest),
            "kept": [{"name": item.get("name"), "kept": item.get("kept"), "n_holes": item.get("n_holes")} for item in reports],
            "grok_tactics_files": copied,
            "arena_score": None,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
