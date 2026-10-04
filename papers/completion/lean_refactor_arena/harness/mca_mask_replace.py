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
    from jevops.pick import drive_shot_example

    return drive_shot_example(
        record,
        tactic_fn=lra_fan.tactic_block,
        holes_fn=find_holes,
        fill_one_fn=template_fill,
        apply_fn=apply_fills,
        skeleton_fn=mask_skeleton,
        token_fn=lra_loop.token_count,
    )


def few_shot_prompt(target: Mapping[str, Any], shots: Sequence[Mapping[str, Any]]) -> str:
    from jevops.tactics import drive_few_shot_block
    from jevops.tactics import few_shot_prompt as _fn

    return drive_few_shot_block(
        target,
        shots,
        tactic_fn=lra_fan.tactic_block,
        holes_fn=find_holes,
        skeleton_fn=mask_skeleton,
        token_fn=lra_loop.token_count,
        prompt_fn=_fn,
    )


def shot_examples(records: Sequence[Mapping[str, Any]], *, skip_name: str) -> list[dict[str, Any]]:
    from jevops.outer import named_shots

    return named_shots(records, SHOT_NAMES, skip_name=skip_name, example_fn=few_shot_example)


def _kind_needs_hammer(kind: str) -> bool:
    from jevops.mask import starts_any

    return starts_any(kind, ("leanstral", "grok", "mca_leanstral", "tactician", "hybrid", "pca_"))


def _identity_dict(identity: Any) -> Optional[dict[str, Any]]:
    from jevops.outer import drive_identity_public

    return drive_identity_public(
        identity,
        (
            "requested_provider",
            "requested_model",
            "resolved_provider",
            "resolved_model",
            "fallback_used",
        ),
    )


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
    from jevops.tactics import drive_compile_head

    return drive_compile_head(item, compiled)


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
    from jevops.tactics import drive_assemble_candidates

    return drive_assemble_candidates(
        tactics,
        holes,
        leanstral_text=leanstral_text,
        replay_fn=lra_ius.replay,
        parse_fn=parse_leanstral_fills,
        indent_fn=lra_kb.match_reference_indent,
        flatten_fn=lra_kb.flatten_overindent,
    )


def prioritize_holes(holes: Sequence[Hole], *, cap: int = 6) -> list[Hole]:
    from jevops.mask import drive_family_rank

    return drive_family_rank(
        holes,
        rank={
            "strength_reduction": 0,
            "algebraic_simplification": 1,
            "dead_code": 2,
            "loop_invariant": 3,
        },
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

    from jevops.search import drive_ablate

    return drive_ablate(
        record,
        tactics,
        holes,
        compile_fn=lra_kb.compile_tactics,
        apply_fn=apply_fills,
        fill_fn=template_fill,
        state_root=state_root,
        timeout=timeout,
        restore=restore,
    )


def typesafe_rank_fanout(
    record: Mapping[str, Any],
    drafts: Sequence[dict[str, Any]],
    *,
    ledger: Optional[Any],
) -> dict[str, Any]:
    """One Jev Choice over tactician/PCA drafts. Jev does not write Lean."""

    from jevops.catalogs import RANK_FANOUT_BEST, RANK_FANOUT_GOAL
    from jevops.jev import drive_rank_fanout

    return drive_rank_fanout(
        record,
        drafts,
        ledger=ledger,
        setup=(lra_pca.load_keyfile, lra_pca.pin_typesafe_path),
        goal=RANK_FANOUT_GOAL,
        best_instructions=RANK_FANOUT_BEST,
        model_id=lra_t1.JEV_MODEL_ID,
        estimate_fn=lra_t1.estimate_tokens,
        redact_fn=lra_pca.redact,
    )


def load_grok_tactics_file(path: Path) -> str:
    from jevops.outer import drive_read_extract, read_text

    return drive_read_extract(path, read_fn=read_text, extract_fn=lra_loop.extract_generated_tactics)


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
    del grok_trace
    from jevops.search import drive_mca_problem

    return drive_mca_problem(
        name,
        state_root=state_root,
        timeout=timeout,
        call_leanstral=call_leanstral,
        ablate=ablate,
        one_hole=one_hole,
        few_shot=few_shot,
        grok_few_shot=grok_few_shot,
        grok_generate=grok_generate,
        grok_tactics_paths=grok_tactics_paths,
        typesafe_fanout=typesafe_fanout,
        load_fn=lra_splice.load_warmup_records,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
        tactic_fn=lra_fan.tactic_block,
        find_fn=find_holes,
        mask_fn=mask_skeleton,
        ledger_cls=lra_t1.ProblemLedger,
        load_grok_fn=load_grok_tactics_file,
        flatten_fn=_flatten_tactics,
        shot_fn=shot_examples,
        grok_callable_fn=lra_t1.grok_callable,
        workspace_fn=lra_t1.prepare_grok_workspace,
        grok_prompt_fn=lra_t1.grok_file_prompt,
        grok_file_fn=lra_t1.generate_grok_file,
        grok_error=lra_t1.Track1LedgerError,
        grok_max_new=GROK_MAX_NEW_TOKENS,
        grok_timeout=GROK_TIMEOUT_SECONDS,
        few_prompt_fn=few_shot_prompt,
        key_fns=(lra_mistral.load_keyfiles, lra_mistral.pin_paths),
        generate_mistral_fn=lra_mistral.generate_mistral,
        prioritize_fn=prioritize_holes,
        one_prompt_fn=one_hole_prompt,
        parse_fn=parse_leanstral_fills,
        extract_fn=lra_loop.extract_generated_tactics,
        apply_fn=apply_fills,
        match_fn=lra_kb.match_reference_indent,
        flatten_over_fn=lra_kb.flatten_overindent,
        asdict_fn=asdict,
        mistral_error=lra_mistral.Track1MistralError,
        lean_prompt_fn=leanstral_prompt,
        compile_body_fn=lra_kb.compile_tactics,
        compile_row_fn=_compile_row,
        hammer_passes_fn=_hammer_passes,
        needs_hammer_fn=_kind_needs_hammer,
        repair_prompt_fn=lra_kb.repair_prompt,
        assemble_fn=assemble_candidates,
        ablate_holes_fn=ablate_holes,
        tactician_fn=grok_tactician_variants,
        feature_fn=lra_pca.count_tactics,
        family_fn=lra_pca.amenable_families,
        draft_fn=lra_pca.guided_drafts,
        row_feature_fn=lra_pca.feature_row,
        fit_fn=lra_pca.fit_pca_mca,
        rank_fn=typesafe_rank_fanout,
        identity_fn=_identity_dict,
        redact_fn=lra_pca.redact,
        token_fn=lra_loop.token_count,
        fanout_cap=MAX_GROK_FANOUT,
        hardware_class=HARDWARE_CLASS,
        grok_hardware_class=GROK_HARDWARE_CLASS,
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
