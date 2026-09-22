#!/usr/bin/env python3
"""Recursive TypeSafe inner loop over the skill decision tree.

Outer Grok (llm_router) decides whether to enter. This module is the inner
TypeSafe walker: keep looping at a tree node, and nest a child loop when
compose=nest. Lake is the oracle. Jev does not write Lean. Never docker0.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional

import _jevops_path  # noqa: F401
import binder_use as lra_bind
import draft_fanout as lra_fan
import mca_mask_replace as lra_mask
import portable_rewrites as lra_port
import random_canary as lra_rand
import track1_keepbest as lra_kb
import typesafe_tools as lra_tools
from jevops.walk import begin_session
from jevops.walk import flatten_trace
from jevops.walk import inner_loop


def apply_lake_round(
    *,
    record: Mapping[str, Any],
    tactics: str,
    analysis: Mapping[str, Any],
    drafts: list[dict[str, Any]],
    intent: Mapping[str, Any],
    ranked: Mapping[str, Any],
    memory: dict[str, Any],
    args: Any,
    restore: bytes,
    round_i: int,
    compile_one: Callable[..., Mapping[str, Any]],
) -> tuple[Optional[str], list[dict[str, Any]]]:
    """Lake up to lake_top drafts. Returns (accepted_body, lake_rows)."""

    from jevops.nca import credit_skill
    from jevops.oracle import apply_round
    from jevops.oracle import lake_budget as _lake_budget
    from jevops.outer import arg_value, first_int, get_list, get_str

    too_big, lake_budget = _lake_budget(
        analysis.get("n_tokens"),
        cap=lra_rand.MAX_LIVE_TOKENS,
        top=arg_value(args, "lake_top", 3, cast=int),
    )
    timeout = arg_value(args, "timeout", 180.0, cast=float)
    out_dir = arg_value(args, "out", None)
    tactics_ref = tactics

    def _compile_kind(_kind: str, script: str) -> Mapping[str, Any]:
        return compile_one(
            record,
            script,
            state_root=lra_rand.DEFAULT_STATE,
            timeout=timeout,
            restore=restore,
        )

    def _repair(*, kind: str, tactics: str, compiled: Mapping[str, Any], row: Mapping[str, Any]) -> Optional[str]:
        del kind
        from jevops.outer import either, pipe

        errors = get_list(compiled, "errors")
        return either(
            row.get("error_class") == "unknown_identifier",
            lambda: pipe(
                tactics,
                lambda body: lra_bind.restore_unknown_binders(body, tactics_ref, errors),
                lambda body: lra_mask.hammer_repair(body, tactics_ref, errors),
            ),
            lambda: None,
        )

    def _on_ok(row: Mapping[str, Any], body: str, draft: Mapping[str, Any], *, better: bool) -> None:
        from jevops.outer import first_int, get_str

        lra_bind.remember_success(
            memory,
            name=get_str(record, "name"),
            kind=get_str(row, "kind"),
            family=get_str(draft, "family"),
            from_tokens=first_int(analysis.get("n_tokens")),
            to_tokens=first_int(row.get("tokens"), analysis.get("n_tokens")),
        )
        credit_skill(memory, row["kind"], ok=True, tokens=first_int(row.get("tokens")))

        def _sidecar() -> None:
            import codepath_graph as lra_cp

            from jevops.outer import call_if, nested_get

            call_if(
                nested_get(memory, "nca", "sidecar_built") and lra_cp.SIDECAR_DUCKDB.is_file(),
                lra_cp.build_sidecar_duckdb,
            )

        def _credit() -> None:
            import board_graph as lra_board

            from jevops.outer import get_str

            lra_board.credit_theorem(
                memory,
                get_str(record, "name"),
                theorem_ok=True,
                tokens=first_int(row.get("tokens")),
            )

        from jevops.outer import assign_if, call_if, ignore_each, text_or, write_best_body

        call_if(better, lambda: ignore_each(_sidecar, _credit))
        assign_if(
            row,
            "best_path",
            better and out_dir is not None,
            lambda: text_or(
                write_best_body(out_dir, get_str(record, "name"), first_int(row.get("tokens")), body)
            ),
        )

    def _on_fail(
        row: Mapping[str, Any],
        body: str,
        draft: Mapping[str, Any],
        *,
        compiled: Mapping[str, Any],
        kind: str,
    ) -> None:
        del draft
        from jevops.outer import first_truthy, get_list, get_str, text_or

        lra_bind.remember_failure(
            memory,
            name=get_str(record, "name"),
            kind=text_or(kind),
            errors=first_truthy(get_list(row, "errors"), get_list(compiled, "errors"), default=[]),
            tactics=body,
        )
        credit_skill(memory, kind, ok=False)

    return apply_round(
        memory=memory,
        name=get_str(record, "name"),
        drafts=drafts,
        intent=intent,
        ranked=ranked,
        round_i=round_i,
        budget=lake_budget,
        compile_fn=_compile_kind,
        repair_fn=_repair,
        error_class_fn=lra_bind.error_class,
        on_ok=_on_ok,
        on_fail=_on_fail,
        from_tokens=first_int(analysis.get("n_tokens"), default=10**9),
        too_big=too_big,
    )


def eval_theorem(
    name: str,
    *,
    current: Mapping[str, Any],
    tactics: str,
    compile_fn: Callable[..., Mapping[str, Any]],
    args: Any,
    restore: bytes,
    memory: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Lake a small warmup theorem. Other names fail closed if not small."""

    import draft_fanout as lra_fan
    import splice as lra_splice
    import track1_keepbest as lra_kb

    from jevops.oracle import eval_named_or_current
    from jevops.outer import arg_value, read_bytes_if

    def _records() -> list:
        _raw, _digest, records = lra_splice.load_warmup_records()
        return records

    return eval_named_or_current(
        name,
        current=current,
        tactics=tactics,
        compile_fn=compile_fn,
        memory=memory,
        timeout=arg_value(args, "timeout", 180.0, cast=float),
        load_records_fn=_records,
        tactic_block_fn=lra_fan.tactic_block,
        clone_dir_fn=lambda url: lra_kb.lra_cw.clone_dir(url, lra_rand.DEFAULT_STATE),
        relpath_fn=lra_kb.lra_cw.source_relpath,
        read_bytes_fn=read_bytes_if,
        cap=lra_rand.MAX_LIVE_TOKENS,
        state_root=lra_rand.DEFAULT_STATE,
        restore=restore,
    )


def inner_typesafe_walk(
    record: Mapping[str, Any],
    tactics: str,
    *,
    args: Any,
    memory: dict[str, Any],
    ledger: Any,
    rng: Any,
    model: Optional[Mapping[str, Any]],
    restore: bytes,
    depth: int = 0,
    node: str = "root",
    allow_families: Optional[set[str]] = None,
    allow_skills: Optional[set[str]] = None,
    steps: Optional[list[int]] = None,
    max_steps: int = lra_rand.INNER_MAX_STEPS,
    max_depth: int = lra_rand.NEST_MAX_DEPTH,
    compile_one: Optional[Callable[..., Mapping[str, Any]]] = None,
    research_fn: Optional[Callable[..., dict[str, Any]]] = None,
    pick_fn: Optional[Callable[..., dict[str, Any]]] = None,
    router_fn: Optional[Callable[..., dict[str, Any]]] = None,
    tape: Optional[Any] = None,
    stack: Optional[Any] = None,
) -> dict[str, Any]:
    """Keep-looping TypeSafe walker. nest/spawn recurse; analyze/self_improve skip grok."""

    import mcmc_beam as lra_mcmc
    import call_stack as lra_cs
    import neural_tape as lra_tape

    from jevops.walk import bind_walk_defaults

    raw_compile, research, pick, counter, tape, stack = bind_walk_defaults(
        compile_one=compile_one,
        research_fn=research_fn,
        pick_fn=pick_fn,
        steps=steps,
        tape=tape,
        stack=stack,
        default_compile=lra_mcmc.compile_one,
        default_research=lra_rand.typesafe_autoresearch,
        default_pick=lra_rand.typesafe_pick,
        tape_factory=lambda: lra_tape.Tape.from_memory(memory),
        stack_factory=lra_cs.CallStack,
    )

    def compile_fn(record: Mapping[str, Any], tactics: str, **kwargs: Any) -> Mapping[str, Any]:
        from jevops.outer import replace_if, with_defaults

        kwargs = replace_if(compile_one is None, with_defaults(kwargs, memory=memory), kwargs)
        return raw_compile(record, tactics, **kwargs)
    from jevops.outer import get_str, stripped_or

    body = stripped_or(tactics, "")

    def _link(mem: dict[str, Any], problem: str) -> None:
        import board_graph as lra_board

        lra_board.link_current_theorem(mem, problem)

    def _overlay(mem: dict[str, Any]) -> None:
        import board_graph as lra_board

        lra_board.overlay_live_board(mem)

    tape = begin_session(
        memory=memory,
        tape=tape,
        stack=stack,
        problem=get_str(record, "name"),
        body=body,
        depth=depth,
        link_fn=_link,
        overlay_fn=_overlay,
    )

    def _analyze(nxt: str) -> dict[str, Any]:
        return lra_rand.analyze_proof(record, tactics=nxt, model=model)

    def _research(analysis: Mapping[str, Any], nxt: str) -> dict[str, Any]:
        return research(
            record,
            analysis,
            tactics=nxt,
            ledger=ledger,
            memory=memory,
            allow_families=allow_families,
            allow_skills=allow_skills,
            tree_node=node,
        )

    def _remember(intent: Mapping[str, Any], nxt: str) -> None:
        from jevops.memory import remember_intent

        from jevops.outer import get_str

        remember_intent(
            memory,
            name=get_str(record, "name"),
            tactics=nxt,
            intent=intent,
            residual_fn=lra_port.analyze_residuals,
        )

    def _expand(nxt: str) -> None:
        from jevops.outer import get_str

        lra_bind.expand_skills_from_memory(memory, name=get_str(record, "name"), tactics=nxt)

    def _drafts(nxt: str, analysis: Mapping[str, Any], intent: Mapping[str, Any]) -> list[dict[str, Any]]:
        from jevops.outer import first_set, get_list, get_str, or_int

        allow = first_set(allow_families, intent.get("allow_families"))
        return lra_rand.random_drafts(
            nxt,
            rng,
            n=or_int(getattr(args, "drafts", 6), 6, floor=2),
            families=get_list(analysis, "families"),
            counts=analysis.get("counts"),
            name=get_str(record, "name"),
            memory=memory,
            allow_families=allow,
        )

    def _extra(compose: str, nest_child: str, tool_name: str, nxt: str) -> dict[str, Any]:
        from jevops.outer import get_str, overlay_map
        from jevops.walk import extra_payload

        return extra_payload(
            compose,
            nest_child=nest_child,
            tool_name=tool_name,
            default_hook="portable_rewrites.py",
            fork=overlay_map(
                base,
                record=record,
                tactics=nxt,
                problem=get_str(record, "name"),
            ),
        )

    walk_args = args
    walk_allow_families = allow_families
    walk_allow_skills = allow_skills

    def _theorem(name: str, *, tactics: str, resolved: Mapping[str, Any], args: Mapping[str, Any]) -> dict[str, Any]:
        del resolved, args
        evaled = eval_theorem(
            name,
            current=record,
            tactics=tactics,
            compile_fn=compile_fn,
            args=walk_args,
            restore=restore,
            memory=memory,
        )
        from jevops.outer import ignore_error

        def _credit() -> None:
            import board_graph as lra_board

            from jevops.outer import first_int, first_truthy, get_str, text_or

            lra_board.credit_theorem(
                memory,
                text_or(first_truthy(evaled.get("name"), get_str(record, "name"), default="")),
                theorem_ok=bool(evaled.get("theorem_ok")),
                tokens=first_int(evaled.get("tokens")),
            )

        ignore_error(_credit)
        return evaled

    from jevops.walk import child_base

    base = child_base(
        args=args,
        memory=memory,
        ledger=ledger,
        rng=rng,
        model=model,
        restore=restore,
        depth=depth + 1,
        steps=counter,
        max_steps=max_steps,
        max_depth=max_depth,
        compile_one=compile_fn,
        research_fn=research,
        pick_fn=pick,
        router_fn=router_fn,
    )

    def _ptr_nest(
        *,
        tactics: str,
        node: str,
        allow_families: Optional[set[str]] = None,
        allow_skills: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        from jevops.outer import first_truthy
        from jevops.walk import recurse_walk

        return recurse_walk(
            inner_typesafe_walk,
            record,
            tactics,
            base,
            node=node,
            tape=tape,
            stack=stack,
            allow_families=first_truthy(allow_families, walk_allow_families),
            allow_skills=first_truthy(allow_skills, walk_allow_skills),
        )

    def _spawn(child: str, tactics: str = "") -> dict[str, Any]:
        from jevops.outer import first_truthy

        return lra_tools.spawn_subloop(
            child,
            record=record,
            tactics=first_truthy(tactics, body),
            **base,
            node=child,
        )

    def _nest(
        *,
        child: str,
        allow_families: Optional[set[str]] = None,
        allow_skills: Optional[set[str]] = None,
        tactics: str = "",
    ) -> dict[str, Any]:
        from jevops.outer import first_truthy
        from jevops.walk import recurse_walk

        return recurse_walk(
            inner_typesafe_walk,
            record,
            first_truthy(tactics, body),
            base,
            node=child,
            tape=tape,
            stack=stack,
            allow_families=allow_families,
            allow_skills=allow_skills,
        )

    return inner_loop(
        memory=memory,
        tape=tape,
        stack=stack,
        record=record,
        body=body,
        depth=depth,
        node=node,
        max_steps=max_steps,
        max_depth=max_depth,
        counter=counter,
        analyze_fn=_analyze,
        research_fn=_research,
        remember_fn=_remember,
        expand_fn=_expand,
        draft_fn=_drafts,
        pick_fn=pick,
        lake_round=apply_lake_round,
        compile_fn=compile_fn,
        ledger=ledger,
        args=args,
        restore=restore,
        spawn_fn=_spawn,
        nest_fn=_nest,
        ptr_nest_fn=_ptr_nest,
        theorem_fn=_theorem,
        subloops=lra_tools.SUBLOOPS,
        extra_fn=_extra,
        router_fn=router_fn,
        allow_families=allow_families,
        allow_skills=allow_skills,
    )


def starting_tactics(record: Mapping[str, Any], *, out: Any = None, from_best: bool = False) -> str:
    """Keep-best body when --from-best, else frozen warmup tactics."""

    from jevops.outer import get_str, starting_body

    tactics = lra_fan.tactic_block(record)
    if not from_best:
        return tactics
    return starting_body(
        tactics,
        out,
        get_str(record, "name", default="canary"),
        extras={"Core.InitsUpdatesComm": "cascade-best-139.lean"},
    )


def run_nested_canary(
    record: Mapping[str, Any],
    *,
    args: Any,
    memory: dict[str, Any],
    ledger: Any,
    rng: Any,
    model: Optional[Mapping[str, Any]],
    compile_one: Optional[Callable[..., Mapping[str, Any]]] = None,
    research_fn: Optional[Callable[..., dict[str, Any]]] = None,
    pick_fn: Optional[Callable[..., dict[str, Any]]] = None,
    router_fn: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Load keep-best tactics, walk the TypeSafe tree, restore the clone."""

    tactics = starting_tactics(
        record, out=getattr(args, "out", None), from_best=bool(getattr(args, "from_best", False))
    )
    from jevops.outer import clone_restore, get_str, inner_budget, restore_if
    from jevops.walk import pack_canary, run_nested

    _clone, dest, restore = clone_restore(
        record,
        lra_rand.DEFAULT_STATE,
        clone_fn=lra_kb.lra_cw.clone_dir,
        relpath_fn=lra_kb.lra_cw.source_relpath,
    )
    return run_nested(
        tactics=tactics,
        dest=dest,
        restore=restore,
        name=get_str(record, "name"),
        analyze_fn=lambda body: lra_rand.analyze_proof(record, tactics=body, model=model),
        pack_fn=pack_canary,
        budget_fn=lambda: inner_budget(
            args, min_steps=lra_rand.INNER_MAX_STEPS, default_depth=lra_rand.NEST_MAX_DEPTH
        ),
        walk_fn=lambda body, restore, max_steps, max_depth: inner_typesafe_walk(
            record,
            body,
            args=args,
            memory=memory,
            ledger=ledger,
            rng=rng,
            model=model,
            restore=restore,
            max_steps=max_steps,
            max_depth=max_depth,
            compile_one=compile_one,
            research_fn=research_fn,
            pick_fn=pick_fn,
            router_fn=router_fn,
        ),
        restore_fn=restore_if,
    )


def _skill_walk_entry(**kwargs: Any) -> dict[str, Any]:
    from jevops.outer import stripped_or

    record = kwargs.pop("record")
    tactics = stripped_or(kwargs.pop("tactics", ""), "")
    return inner_typesafe_walk(record, tactics, **kwargs)


lra_tools.register_subloop("skill_walk", _skill_walk_entry)


def _eval_theorem_entry(**kwargs: Any) -> dict[str, Any]:
    from jevops.outer import as_dict, first_truthy, get_str, overlay_map, text_or

    record = overlay_map(kwargs.get("record"))
    return eval_theorem(
        text_or(
            first_truthy(
                kwargs.get("name"), kwargs.get("theorem"), record.get("name"), default=""
            )
        ),
        current=record,
        tactics=get_str(kwargs, "tactics"),
        compile_fn=first_truthy(kwargs.get("compile_one"), kwargs.get("compile_fn")),
        args=kwargs.get("args"),
        restore=first_truthy(kwargs.get("restore"), default=b""),
        memory=as_dict(kwargs.get("memory")),
    )


lra_tools.register_subloop("eval_theorem", _eval_theorem_entry)
