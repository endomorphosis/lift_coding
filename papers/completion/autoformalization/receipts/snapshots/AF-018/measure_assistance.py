#!/usr/bin/env python3
"""AF-018 bounded planning, Hammer, and Leanstral comparison harness.

Replay unguided and pinned-guidance plans on a frozen constructed goal set.
Translate first-order-safe Hammer fragments, reject sorry/admit/unapproved
axioms, and probe sealed-PATH Hammer/Leanstral/native-checker availability.

Standard library only. Project packages and host toolchains are inspected
and hashed, not imported. No model service is called and no fine-tuning is
claimed. Plans never count as executed proofs. Solver answers, when absent,
are unavailable rather than invented candidates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

SCHEMA_PLAN = "autoformalization-planning-result/v1"
SCHEMA_ASSIST = "autoformalization-proof-assistance-result/v1"
SCHEMA_RECEIPT = "autoformalization-native-checker-receipt/v1"
TASK_ID = "AF-018"
POOL_ID = "AF-018-constructed-assistance-pool/v1"
PLANNER_ID = "logic.tactician.deterministic@1"
UNGUIDED_POLICY_ID = "logic.tactician.policy.unguided@1"
GUIDED_POLICY_ID = "logic.tactician.policy.guided-pinned-ranker@1"
LLM_POLICY_ID = "logic.tactician.policy.llm-nomination@1"
CHECKER_ID = "AF-010-shared-target-checker/v1"
CHECKER_DIGEST = "0d22c6e92be47a464452266e1a09d3b1d072f98ce3e5fec19bdbe9f47273f052"
LEANSTRAL_MODEL_ID = "Frosty40/Leanstral-1.5-119B-A6B-GGUF-NVFP4"
LEANSTRAL_REVISION = "abcc5ce2528c6375148d41dac6dce20f06c339f4"
LEANSTRAL_WEIGHT_BYTES = 67135119264
LEANSTRAL_PROPOSAL_SCHEMA = "legal-ir-leanstral-proposal-v1"
LEANSTRAL_CANDIDATE_SCHEMA = "legal-ir-leanstral-hammer-candidate-v1"
REPLAY_SEEDS = (104729, 130363, 155921)
NATIVE_TOOLS = ("lean", "lake", "elan", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle")
SORRY_RE = re.compile(r"\bsorry\b", re.IGNORECASE)
ADMIT_RE = re.compile(r"\badmit\b", re.IGNORECASE)
AXIOM_RE = re.compile(r"\b(?:axiom|sorryAx|oops|unsafe)\b")
UNAPPROVED_AXIOM_RE = re.compile(
    r"\b(?:axiom|sorryAx|constant\s+[A-Za-z_][A-Za-z0-9_']*\s*:|unsafe)\b"
)

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]

INSPECTED_SOURCES = {
    "planner.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/tactician/planner.py",
        "imported": False,
        "note": "LogicTactician replica in this harness; original is hashed, not imported.",
    },
    "tactician_models.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/tactician/models.py",
        "imported": False,
        "note": "Content-addressed plan records; replica uses sha256 body digests.",
    },
    "tactician_policy.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/tactician/policy.py",
        "imported": False,
        "note": "Closed baseline policy: no network, write, or proof execution.",
    },
    "translation.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/hammers/translation.py",
        "imported": False,
        "note": "First-order-safe fragment; dependent/HO constructs fail closed.",
    },
    "lean_reconstructor.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/hammers/reconstructors/lean.py",
        "imported": False,
        "note": "Rejects sorry and sorryAx; kernel check is not executed here.",
    },
    "leanstral.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/modal/leanstral.py",
        "imported": False,
        "note": "Prompt forbids sorry/admit/axioms; no model call is dispatched.",
    },
    "leanstral_verifier.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/modal/leanstral_verifier.py",
        "imported": False,
        "note": "Verifier treats model output as hypothesis; not imported.",
    },
    "bench_itp_hammer.py": {
        "path": "external/ipfs_datasets/benchmarks/bench_itp_hammer.py",
        "imported": False,
        "note": "Would import project packages; inspected only.",
    },
    "itp_hammer_user_guide.md": {
        "path": "external/ipfs_datasets/docs/logic/itp_hammer_user_guide.md",
        "imported": False,
        "note": "Solver output is an untrusted candidate until native reconstruction.",
    },
}

LEANSTRAL_PROMPT_SETTINGS = {
    "schema_version": LEANSTRAL_PROPOSAL_SCHEMA,
    "candidate_schema_version": LEANSTRAL_CANDIDATE_SCHEMA,
    "return_format": "strict_json_only",
    "proof_body_prefix": "by",
    "instructions": [
        "Return strict JSON only.",
        "Return a Lean proof body beginning with by for the fixed theorem.",
        "Do not change the theorem, introduce axioms, imports, sorry, admit, or executable tactics.",
        "Raw generated text remains untrusted until configured independent checks.",
    ],
    "forbidden": [
        "sorry",
        "admit",
        "axiom",
        "imports",
        "namespaces",
        "theorem_declaration_change",
        "executable_tactics",
    ],
    "model_call_authorized": False,
    "fine_tuning_authorized": False,
}

GUIDANCE_RANKER_SPEC = {
    "kind": "hand_authored_pinned_reorder",
    "operation": "reverse_admitted_source_ids",
    "may_invent_sources": False,
    "trained": False,
    "model_call": False,
    "note": "Optional guidance may only reorder admitted sources under a pinned digest.",
}


class HarnessError(RuntimeError):
    """Raised when the AF-018 harness cannot emit honest records."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_dumps(row) + "\n" for row in rows)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def empty_status(status: str, detail: str, score: Any = None) -> dict[str, Any]:
    return {"status": status, "score": score, "detail": detail}


def empty_cost(elapsed: float | None = 0.0) -> dict[str, Any]:
    return {
        "elapsed_seconds": elapsed,
        "cpu_seconds": None,
        "gpu_seconds": 0.0,
        "provider_units": 0.0,
        "memory_gib": None,
        "human_review_seconds": 0.0,
    }


def evaluation_projection(
    *,
    record_id: str,
    source_id: str,
    family: str,
    arm: str,
    execution_status: str,
    result_kind: str,
    checker_class: str,
    receipt_sha256: str | None,
    identities: Mapping[str, Any],
    cost: Mapping[str, Any],
    raw: Mapping[str, Any],
    notes: str,
) -> dict[str, Any]:
    phase = "unmeasured"
    if execution_status == "measured":
        phase = "success" if result_kind == "bounded_observation" else "failure"
    elif execution_status in {"unavailable", "unsupported", "timeout", "invalid", "failure", "no_run", "abstained"}:
        phase = execution_status
    return {
        "schema": "autoformalization-evaluation-result/v1",
        "record_id": record_id,
        "source_id": source_id,
        "source_family_time_group": family,
        "split": "constructed_control",
        "experiment_arm": arm,
        "eligible": True,
        "fixture": False,
        "constructed_control": True,
        "execution_status": execution_status,
        "result_kind": result_kind,
        "parse": empty_status(phase if phase != "success" else "success", "constructed obligation parse is not source gold"),
        "elaboration": empty_status("unmeasured", "no native elaborator in sealed PATH"),
        "source_facets": {
            "independent_gold_present": False,
            "all_facet_match": None,
            "ambiguity": {"status": "unmeasured", "labels": []},
            "status": "unmeasured",
        },
        "source_maps": empty_status("unmeasured", "planning/assistance is not source-map scoring"),
        "reconstruction": {
            "forward": empty_status("unmeasured", "not a compiler roundtrip"),
            "cycle": empty_status("unmeasured", "not a compiler roundtrip"),
            "final": empty_status("unmeasured", "not a compiler roundtrip"),
        },
        "consistency": empty_status("unmeasured", "not a semantic consistency score"),
        "proof": {
            "useful": False,
            "false_transfer": False,
            "checker_class": checker_class,
            "receipt_sha256": receipt_sha256,
            "theorem": source_id,
            "fragment": family,
        },
        "identities": dict(identities),
        "cost": dict(cost),
        "artifacts": {"raw_sha256": sha256_obj(raw), "command_log_sha256": None},
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Frozen constructed goals and sources
# ---------------------------------------------------------------------------

SOURCES = [
    {"source_id": "src.thm.Nat.add_comm", "source_class": "theorem", "precedence": 5,
     "rationale": "Admitted Nat.add_comm fixture theorem", "query_hints": ["add_comm"],
     "source_root": "constructed:thm.Nat.add_comm"},
    {"source_id": "src.thm.Nat.add_zero", "source_class": "theorem", "precedence": 6,
     "rationale": "Admitted Nat.add_zero fixture theorem", "query_hints": ["add_zero"],
     "source_root": "constructed:thm.Nat.add_zero"},
    {"source_id": "src.thm.List.append_nil", "source_class": "theorem", "precedence": 8,
     "rationale": "Admitted List.append_nil fixture theorem", "query_hints": ["append_nil"],
     "source_root": "constructed:thm.List.append_nil"},
    {"source_id": "src.impl.guarded_write", "source_class": "implementation", "precedence": 15,
     "rationale": "Guarded write implementation from AF-015 constructed cases",
     "query_hints": ["Protected", "Approved", "Write"],
     "source_root": "constructed:impl.guarded_write"},
    {"source_id": "src.policy.protected_write", "source_class": "policy", "precedence": 10,
     "rationale": "Protected-write policy from AF-015 constructed cases",
     "query_hints": ["Protected", "Approved"],
     "source_root": "constructed:policy.protected_write"},
    {"source_id": "src.policy.tenant_isolation", "source_class": "policy", "precedence": 20,
     "rationale": "Tenant isolation policy frame", "query_hints": ["tenant"],
     "source_root": "constructed:policy.tenant_isolation"},
    {"source_id": "src.trace.timely_audit", "source_class": "observation", "precedence": 50,
     "rationale": "Observation is not an admitted proof premise", "query_hints": ["audit"],
     "source_root": "constructed:trace.timely_audit"},
    {"source_id": "src.untrusted.web", "source_class": "network", "precedence": 90,
     "rationale": "Denied network source", "query_hints": ["http"],
     "source_root": "constructed:untrusted.web"},
]

PLAN_GOALS = [
    {"goal_id": "g.add_comm", "family": "nat_add", "statement_ref": "Nat.add_comm",
     "proof_gaps": ["intro", "rewrite", "close"],
     "nominated_deps": {}},
    {"goal_id": "g.add_zero", "family": "nat_add", "statement_ref": "Nat.add_zero",
     "proof_gaps": ["intro", "close"],
     "nominated_deps": {}},
    {"goal_id": "g.list_append_nil", "family": "list", "statement_ref": "List.append_nil",
     "proof_gaps": ["intro", "induction", "close"],
     "nominated_deps": {}},
    {"goal_id": "g.protected_write", "family": "policy", "statement_ref": "PCT-SAFE-Q1",
     "proof_gaps": ["guard", "implication", "close"],
     "nominated_deps": {}},
    {"goal_id": "g.audit_window", "family": "policy", "statement_ref": "PCT-TIMELY-AUDIT",
     "proof_gaps": ["window", "join", "close"],
     "nominated_deps": {}},
    {"goal_id": "g.identity_closed", "family": "fol", "statement_ref": "forall x. P(x) -> P(x)",
     "proof_gaps": [],
     "nominated_deps": {}},
    {"goal_id": "g.cycle_abstain", "family": "policy", "statement_ref": "cyclic-gap-nomination",
     "proof_gaps": ["a", "b"],
     "nominated_deps": {"a": ["b"], "b": ["a"]}},
    {"goal_id": "g.budget_exhausted", "family": "nat_add", "statement_ref": "many-gaps",
     "proof_gaps": ["g1", "g2", "g3", "g4"],
     "nominated_deps": {}},
]

ASSIST_GOALS = [
    {
        "goal_id": "h.fol_identity",
        "family": "fol_safe",
        "fragment": "first_order_safe",
        "statement": "forall x. P(x) -> P(x)",
        "term": {"op": "forall", "var": "x", "sort": "U",
                 "body": {"op": "implies",
                          "left": {"op": "pred", "name": "P", "args": ["x"]},
                          "right": {"op": "pred", "name": "P", "args": ["x"]}}},
        "supported": True,
    },
    {
        "goal_id": "h.fol_protected_write",
        "family": "fol_safe",
        "fragment": "first_order_safe",
        "statement": "(Protected /\\ ~Approved) -> ~Write",
        "term": {"op": "implies",
                 "left": {"op": "and",
                          "left": {"op": "pred", "name": "Protected", "args": []},
                          "right": {"op": "not", "arg": {"op": "pred", "name": "Approved", "args": []}}},
                 "right": {"op": "not", "arg": {"op": "pred", "name": "Write", "args": []}}},
        "supported": True,
    },
    {
        "goal_id": "h.fol_add_zero",
        "family": "fol_safe",
        "fragment": "first_order_safe",
        "statement": "forall a. add(a, zero) = a",
        "term": {"op": "forall", "var": "a", "sort": "Nat",
                 "body": {"op": "eq",
                          "left": {"op": "app", "name": "add", "args": ["a", "zero"]},
                          "right": {"op": "var", "name": "a"}}},
        "supported": True,
    },
    {
        "goal_id": "h.unsupported_dependent",
        "family": "dependent",
        "fragment": "dependent_type",
        "statement": "theorem id : forall {α : Type} (x : α), x = x",
        "term": {"op": "forall", "var": "α", "sort": "Type",
                 "body": {"op": "forall", "var": "x", "sort": "α",
                          "body": {"op": "eq", "left": {"op": "var", "name": "x"},
                                   "right": {"op": "var", "name": "x"}}}},
        "supported": False,
        "unsupported_reason": "dependent type is not supported: sort of x is bound variable α",
    },
    {
        "goal_id": "h.unsupported_higher_order",
        "family": "higher_order",
        "fragment": "higher_order_predicate",
        "statement": "forall (p : (Nat -> Nat) -> Prop), p id -> p id",
        "term": {"op": "forall_pred", "var": "p",
                 "sort": {"op": "arrow", "left": {"op": "arrow", "left": "Nat", "right": "Nat"}, "right": "Prop"},
                 "body": {"op": "implies",
                          "left": {"op": "pred", "name": "p", "args": ["id"]},
                          "right": {"op": "pred", "name": "p", "args": ["id"]}}},
        "supported": False,
        "unsupported_reason": "higher-order quantification over predicates is not supported",
    },
]

POLICY_FIXTURES = [
    {
        "goal_id": "p.sorry_lean",
        "family": "policy_reject",
        "kind": "sorry",
        "language": "lean4",
        "source": "theorem t : True := by sorry",
    },
    {
        "goal_id": "p.admit_lean",
        "family": "policy_reject",
        "kind": "admit",
        "language": "lean4",
        "source": "theorem t : True := by admit",
    },
    {
        "goal_id": "p.unapproved_axiom",
        "family": "policy_reject",
        "kind": "unapproved_axiom",
        "language": "lean4",
        "source": "axiom magic : True\ntheorem t : True := magic",
    },
    {
        "goal_id": "p.clean_rfl",
        "family": "policy_reject",
        "kind": "clean_rfl",
        "language": "lean4",
        "source": "theorem t : True := by trivial",
    },
]


# ---------------------------------------------------------------------------
# LogicTactician replica
# ---------------------------------------------------------------------------

def default_policy_fields(policy_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "policy_id": policy_id,
        "source_class_order": [],
        "max_sources": 4,
        "max_routes": 4,
        "max_subgoals": 3,
        "max_query_hints_per_source": 16,
        "max_refinement_rounds": 4,
        "allow_learned_ranking": False,
        "allow_llm_nomination": False,
        "learned_model_digest": "",
        "llm_model_digest": "",
        "denied_source_classes": ["network"],
        "network_allowed": False,
        "write_allowed": False,
        "proof_execution_allowed": False,
        "semantic_authority": False,
        "stop_conditions": ["budget_exhausted", "gaps_closed", "no_admissible_sources", "cycle_detected"],
        "abstain_conditions": ["cycle_detected", "no_selected_routes_with_gaps"],
    }
    payload.update(overrides)
    return payload


def order_sources(sources: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    class_order = list(policy["source_class_order"])
    rank = {name: index for index, name in enumerate(class_order)}
    unknown = len(class_order)

    def key(source: Mapping[str, Any]) -> tuple[Any, ...]:
        return (rank.get(source["source_class"], unknown), source["precedence"], source["source_id"])

    return [dict(source) for source in sorted(sources, key=key)]


def partition_by_denial(sources: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    denied_classes = set(policy["denied_source_classes"])
    admitted, denied = [], []
    for source in order_sources(sources, policy):
        if source["source_class"] in denied_classes:
            denied.append(source)
        else:
            admitted.append(source)
    return admitted, denied


def reverse_ranker(source_ids: Sequence[str], _context: Mapping[str, Any]) -> list[str]:
    return list(reversed(list(source_ids)))


def detect_cycle(nodes: Mapping[str, Sequence[str]]) -> Optional[tuple[str, ...]]:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> Optional[tuple[str, ...]]:
        if node in visiting:
            if node in stack:
                start = stack.index(node)
                return tuple(stack[start:] + [node])
            return (node, node)
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for nxt in nodes.get(node, ()):
            found = dfs(nxt)
            if found is not None:
                return found
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in nodes:
        found = dfs(node)
        if found is not None:
            return found
    return None


def plan_body(plan: Mapping[str, Any]) -> dict[str, Any]:
    skip = {"plan_id"}
    return {key: value for key, value in plan.items() if key not in skip}


def build_plan(
    goal: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
    *,
    guidance_applied: bool,
    guidance_digest: str,
    llm_applied: bool,
    llm_digest: str,
    ordered: Sequence[Mapping[str, Any]],
    admitted: Sequence[Mapping[str, Any]],
    denied: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    gaps = list(goal["proof_gaps"])
    budget = min(policy["max_sources"], policy["max_routes"])
    for index, source in enumerate(ordered):
        if len(selected) >= budget:
            excluded.append({
                "route_id": f"route:excluded:{source['source_id']}",
                "source_id": source["source_id"],
                "source_class": source["source_class"],
                "stage_index": index,
                "disposition": "excluded",
                "rationale": "Excluded after selection budget",
                "addresses_gaps": [],
            })
            continue
        selected.append({
            "route_id": f"route:selected:{source['source_id']}",
            "source_id": source["source_id"],
            "source_class": source["source_class"],
            "stage_index": len(selected),
            "disposition": "selected",
            "rationale": source["rationale"],
            "addresses_gaps": gaps[:1],
        })
    admitted_ids = {route["source_id"] for route in selected}
    admitted_ids.update(route["source_id"] for route in excluded)
    for source in denied:
        excluded.append({
            "route_id": f"route:excluded:{source['source_id']}",
            "source_id": source["source_id"],
            "source_class": source["source_class"],
            "stage_index": len(selected) + len(excluded),
            "disposition": "excluded",
            "rationale": f"Source class {source['source_class']!r} is denied by policy",
            "addresses_gaps": [],
        })
        admitted_ids.add(source["source_id"])
    for source in ordered:
        if source["source_id"] in admitted_ids:
            continue
        excluded.append({
            "route_id": f"route:excluded:{source['source_id']}",
            "source_id": source["source_id"],
            "source_class": source["source_class"],
            "stage_index": len(selected) + len(excluded),
            "disposition": "excluded",
            "rationale": "Excluded after max_sources/max_routes budget",
            "addresses_gaps": [],
        })

    subgoals: list[dict[str, Any]] = []
    stop = "continue"
    nominated = dict(goal.get("nominated_deps") or {})
    gap_slice = list(goal["proof_gaps"])[: policy["max_subgoals"]]
    if not goal["proof_gaps"]:
        stop = "gaps_closed"
    else:
        for index, gap in enumerate(gap_slice):
            raw_deps = list(nominated.get(gap, ()))
            depends_on = [f"subgoal:{dep}" for dep in raw_deps if dep in gap_slice and dep != gap]
            if not depends_on and index > 0 and gap not in nominated:
                depends_on = [f"subgoal:{gap_slice[index - 1]}"]
            subgoals.append({
                "subgoal_id": f"subgoal:{gap}",
                "parent_goal_id": goal["goal_id"],
                "statement_ref": f"{goal['statement_ref']}#gap:{gap}",
                "depends_on": depends_on,
                "addresses_gaps": [gap],
                "rationale": f"Cover proof gap {gap}",
            })
        graph = {sg["subgoal_id"]: list(sg["depends_on"]) for sg in subgoals}
        if detect_cycle(graph) is not None:
            subgoals = []
            stop = "cycle_detected"
        elif len(goal["proof_gaps"]) > policy["max_subgoals"]:
            stop = "budget_exhausted"

    if not selected and goal["proof_gaps"]:
        stop = "abstain"
    elif not selected:
        stop = "no_admissible_sources"
    elif stop == "continue":
        if len(selected) >= policy["max_routes"]:
            stop = "budget_exhausted"
        elif not goal["proof_gaps"]:
            stop = "gaps_closed"

    policy_digest = f"sha256:{sha256_obj(policy)}"
    plan = {
        "goal_id": goal["goal_id"],
        "goal_root": f"sha256:{sha256_obj({'goal_id': goal['goal_id'], 'statement_ref': goal['statement_ref'], 'proof_gaps': goal['proof_gaps']})}",
        "corpus_root": f"sha256:{sha256_obj([s['source_id'] for s in sources])}",
        "config_root": policy["policy_id"],
        "authority_roots": {"policy": policy_digest},
        "policy_id": policy["policy_id"],
        "planner_id": PLANNER_ID,
        "selected_routes": selected,
        "excluded_routes": excluded,
        "proof_gaps": list(goal["proof_gaps"]),
        "subgoals": subgoals,
        "stop_conditions": list(policy["stop_conditions"]),
        "abstain_conditions": list(policy["abstain_conditions"]),
        "stop_disposition": stop,
        "learned_guidance_applied": guidance_applied,
        "learned_model_digest": guidance_digest if guidance_applied else "",
        "llm_guidance_applied": llm_applied,
        "llm_model_digest": llm_digest if llm_applied else "",
        "semantic_authority": False,
        "proof_execution_allowed": False,
        "schema_version": "1.0.0",
    }
    plan["plan_id"] = f"sha256:{sha256_obj(plan)}"
    return plan


def run_planner(
    goal: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
    *,
    ranker: Any = None,
    ranker_digest: str = "",
    llm_nominator: Any = None,
    llm_digest: str = "",
) -> dict[str, Any]:
    admitted, denied = partition_by_denial(sources, policy)
    ordered = list(admitted)
    learned_applied = False
    learned_digest = ""
    llm_applied = False
    used_llm_digest = ""
    if ranker is not None and policy["allow_learned_ranking"]:
        pinned = (ranker_digest or policy["learned_model_digest"]).strip()
        if pinned and pinned == policy["learned_model_digest"]:
            source_ids = [source["source_id"] for source in ordered]
            ranked_ids = list(ranker(source_ids, {"model_digest": pinned, "policy_id": policy["policy_id"]}))
            if sorted(ranked_ids) == sorted(source_ids):
                by_id = {source["source_id"]: source for source in ordered}
                ordered = [by_id[source_id] for source_id in ranked_ids]
                learned_applied = True
                learned_digest = pinned
    if llm_nominator is not None and policy["allow_llm_nomination"]:
        # Intentionally unused: AF-018 does not invent LLM nominators.
        raise HarnessError("llm nominator must not be supplied; no model calls")
    return build_plan(
        goal, sources, policy,
        guidance_applied=learned_applied,
        guidance_digest=learned_digest,
        llm_applied=llm_applied,
        llm_digest=used_llm_digest,
        ordered=ordered,
        admitted=admitted,
        denied=denied,
    )


# ---------------------------------------------------------------------------
# Hammer translation replica
# ---------------------------------------------------------------------------

def term_unsupported(term: Mapping[str, Any], bound_sorts: frozenset[str] | None = None) -> Optional[str]:
    bound = set(bound_sorts or ())
    op = term.get("op")
    if op == "forall_pred":
        return "higher-order quantification over predicates is not supported"
    if op == "forall":
        sort = term.get("sort")
        if sort == "Type" or sort in bound:
            return f"dependent type is not supported: sort {sort!r}"
        if isinstance(sort, dict):
            return "higher-order sort is not supported"
        inner_bound = bound | {term["var"]}
        return term_unsupported(term["body"], frozenset(inner_bound))
    if op in {"implies", "and", "or", "eq"}:
        return term_unsupported(term["left"], frozenset(bound)) or term_unsupported(term["right"], frozenset(bound))
    if op == "not":
        return term_unsupported(term["arg"], frozenset(bound))
    if op == "pred":
        if any(not isinstance(arg, str) for arg in term.get("args") or []):
            return "predicate arguments must be first-order names"
        return None
    if op in {"app", "var"}:
        return None
    if op == "arrow":
        return "function sorts as propositions are not first-order-safe"
    return f"opaque construct is not supported: {op!r}"


def to_tptp(term: Mapping[str, Any]) -> str:
    op = term["op"]
    if op == "forall":
        return f"(![{term['var'].upper()}]: {to_tptp(term['body'])})"
    if op == "implies":
        return f"({to_tptp(term['left'])} => {to_tptp(term['right'])})"
    if op == "and":
        return f"({to_tptp(term['left'])} & {to_tptp(term['right'])})"
    if op == "or":
        return f"({to_tptp(term['left'])} | {to_tptp(term['right'])})"
    if op == "eq":
        return f"({to_tptp(term['left'])} = {to_tptp(term['right'])})"
    if op == "not":
        return f"(~{to_tptp(term['arg'])})"
    if op == "pred":
        args = term.get("args") or []
        if not args:
            return term["name"].lower()
        rendered = ",".join(arg.upper() if len(arg) == 1 else arg.lower() for arg in args)
        return f"{term['name'].lower()}({rendered})"
    if op == "app":
        rendered = ",".join(arg.upper() if len(arg) == 1 else arg.lower() for arg in term["args"])
        return f"{term['name'].lower()}({rendered})"
    if op == "var":
        name = term["name"]
        return name.upper() if len(name) == 1 else name.lower()
    raise HarnessError(f"cannot encode {op} as TPTP")


def to_smtlib(term: Mapping[str, Any]) -> str:
    op = term["op"]
    if op == "forall":
        return f"(forall (({term['var']} {term['sort']})) {to_smtlib(term['body'])})"
    if op == "implies":
        return f"(=> {to_smtlib(term['left'])} {to_smtlib(term['right'])})"
    if op == "and":
        return f"(and {to_smtlib(term['left'])} {to_smtlib(term['right'])})"
    if op == "or":
        return f"(or {to_smtlib(term['left'])} {to_smtlib(term['right'])})"
    if op == "eq":
        return f"(= {to_smtlib(term['left'])} {to_smtlib(term['right'])})"
    if op == "not":
        return f"(not {to_smtlib(term['arg'])})"
    if op == "pred":
        args = term.get("args") or []
        if not args:
            return term["name"]
        return "(" + " ".join([term["name"], *args]) + ")"
    if op == "app":
        return "(" + " ".join([term["name"], *term["args"]]) + ")"
    if op == "var":
        return term["name"]
    raise HarnessError(f"cannot encode {op} as SMT-LIB")


def collect_symbols(term: Mapping[str, Any], acc: dict[str, Any] | None = None) -> dict[str, Any]:
    acc = acc or {"sorts": set(), "preds": {}, "funs": {}, "consts": set()}
    op = term.get("op")
    if op == "forall":
        acc["sorts"].add(term["sort"])
        collect_symbols(term["body"], acc)
    elif op in {"implies", "and", "or", "eq"}:
        collect_symbols(term["left"], acc)
        collect_symbols(term["right"], acc)
    elif op == "not":
        collect_symbols(term["arg"], acc)
    elif op == "pred":
        acc["preds"][term["name"]] = len(term.get("args") or [])
        for arg in term.get("args") or []:
            if arg.lower() in {"zero"}:
                acc["consts"].add(arg)
    elif op == "app":
        acc["funs"][term["name"]] = len(term["args"])
        for arg in term["args"]:
            if arg.lower() in {"zero"}:
                acc["consts"].add(arg)
    return acc


def translate_goal(goal: Mapping[str, Any]) -> dict[str, Any]:
    reason = goal.get("unsupported_reason") or term_unsupported(goal["term"])
    if reason:
        return {
            "supported": False,
            "unsupported_reason": reason,
            "tptp": None,
            "smtlib": None,
            "encoding_sha256": None,
        }
    tptp = f"fof(goal,conjecture,{to_tptp(goal['term'])}).\n"
    symbols = collect_symbols(goal["term"])
    decls = ["(set-logic UF)"]
    for sort in sorted(symbols["sorts"]):
        decls.append(f"(declare-sort {sort} 0)")
    for name, arity in sorted(symbols["preds"].items()):
        args = " ".join(["U"] * arity) if arity else ""
        if arity:
            decls.append(f"(declare-fun {name} ({args}) Bool)")
        else:
            decls.append(f"(declare-const {name} Bool)")
    for name, arity in sorted(symbols["funs"].items()):
        args = " ".join(["Nat"] * arity)
        decls.append(f"(declare-fun {name} ({args}) Nat)")
    for const in sorted(symbols["consts"]):
        decls.append(f"(declare-const {const} Nat)")
    smt = "\n".join(decls + [f"(assert (not {to_smtlib(goal['term'])}))", "(check-sat)"]) + "\n"
    encoding = {"tptp": tptp, "smtlib": smt}
    return {
        "supported": True,
        "unsupported_reason": None,
        "tptp": tptp,
        "smtlib": smt,
        "encoding_sha256": sha256_obj(encoding),
    }


# ---------------------------------------------------------------------------
# Sorry/admit/axiom policy
# ---------------------------------------------------------------------------

def scan_lean_policy(source: str) -> dict[str, Any]:
    sorry_present = bool(SORRY_RE.search(source))
    admit_present = bool(ADMIT_RE.search(source))
    axiom_present = bool(UNAPPROVED_AXIOM_RE.search(source) or AXIOM_RE.search(source))
    reasons = []
    if sorry_present:
        reasons.append("lean_source_contains_sorry")
    if admit_present:
        reasons.append("lean_source_contains_admit")
    if axiom_present:
        reasons.append("lean_source_contains_unapproved_axiom")
    rejected = bool(reasons)
    return {
        "sorry_present": sorry_present,
        "admit_present": admit_present,
        "unapproved_axiom_present": axiom_present,
        "policy_rejected": rejected,
        "reasons": reasons,
        "accepted": False,
        "source_sha256": sha256_text(source),
    }


# ---------------------------------------------------------------------------
# Environment probe
# ---------------------------------------------------------------------------

def probe_environment() -> dict[str, Any]:
    path = os.environ.get("PATH", "")
    home = os.environ.get("HOME") or ""
    tools = []
    for name in NATIVE_TOOLS:
        resolved = shutil.which(name)
        tools.append({
            "name": name,
            "status": "available" if resolved else "unavailable",
            "resolved_path": resolved,
            "usable_in_sealed_validation": bool(resolved),
        })
    modules = {}
    for name in ("ipfs_datasets_py", "torch", "transformers", "llama_cpp"):
        try:
            module = __import__(name)
            modules[name] = {
                "available": True,
                "version": getattr(module, "__version__", None),
                "file": getattr(module, "__file__", None),
            }
        except Exception as exc:
            modules[name] = {
                "available": False,
                "error_type": type(exc).__name__,
                "error": str(exc).splitlines()[0][:300],
            }
    return {
        "path": path,
        "home": home,
        "home_is_validation_private": Path(home).name.startswith("ipfs-accelerate-validation-home-") if home else False,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "tools": tools,
        "modules": modules,
        "any_native_checker_usable": any(item["usable_in_sealed_validation"] for item in tools if item["name"] in {"lean", "coqc", "isabelle"}),
        "any_solver_usable": any(item["usable_in_sealed_validation"] for item in tools if item["name"] in {"z3", "cvc5", "vampire", "eprover"}),
        "leanstral_runtime_usable": False,
    }


def inspect_sources(repo_root: Path) -> dict[str, Any]:
    rows = {}
    for key, meta in INSPECTED_SOURCES.items():
        path = repo_root / meta["path"]
        record = dict(meta)
        record["sha256"] = sha256_file(path)
        record["bytes"] = path.stat().st_size
        rows[key] = record
    return rows


def load_frozen_inputs(repo_root: Path) -> dict[str, Any]:
    paper = repo_root / "papers/completion/autoformalization"
    paths = {
        "experiment_plan": paper / "config/experiment_plan.json",
        "environment_manifest": paper / "config/environment_manifest.json",
        "splits": paper / "data/splits.json",
        "corpus_manifest": paper / "data/corpus_manifest.json",
        "policy_code_trace_cases": paper / "data/policy_code_trace_cases.json",
        "result_schema": paper / "evaluation/result_schema.json",
    }
    return {name: sha256_file(path) for name, path in paths.items()}


# ---------------------------------------------------------------------------
# Record builders
# ---------------------------------------------------------------------------

def identities_for(arm: str, *, model: str | None, tool: str | None, checker: str | None) -> dict[str, Any]:
    return {
        "experiment_arm": arm,
        "model": model,
        "tool": tool,
        "checker": checker,
        "compiler": PLANNER_ID if arm.startswith("plan.") else "hammer-translation-replica/v1",
        "checker_id": CHECKER_ID,
        "checker_digest": CHECKER_DIGEST,
    }


def planning_row(
    *,
    goal: Mapping[str, Any],
    arm: str,
    plan: Mapping[str, Any],
    replay_index: int,
    replay_seed: int,
    execution_status: str,
    result_kind: str,
    guidance: Mapping[str, Any],
    elapsed: float,
    n_goals: int,
    notes: str,
) -> dict[str, Any]:
    raw = {
        "goal_id": goal["goal_id"],
        "arm": arm,
        "plan_id": plan["plan_id"],
        "replay_index": replay_index,
        "replay_seed": replay_seed,
        "selected": [route["source_id"] for route in plan["selected_routes"]],
        "stop": plan["stop_disposition"],
    }
    cost = empty_cost(elapsed)
    ident = identities_for(arm, model=guidance.get("digest") or None, tool=PLANNER_ID, checker=None)
    row = {
        "schema": SCHEMA_PLAN,
        "record_id": f"{goal['goal_id']}:{arm}:replay{replay_index}",
        "kind": "observation",
        "goal_id": goal["goal_id"],
        "source_family_time_group": goal["family"],
        "split": "constructed_control",
        "experiment_arm": arm,
        "eligible": True,
        "fixture": False,
        "constructed_control": True,
        "execution_status": execution_status,
        "result_kind": result_kind,
        "counts_as_executed_proof": False,
        "counts_as_native_checked_proof": False,
        "n_goals": n_goals,
        "n_replays": len(REPLAY_SEEDS),
        "plan": {
            "plan_id": plan["plan_id"],
            "planner_id": plan["planner_id"],
            "policy_id": plan["policy_id"],
            "selected_source_ids": [route["source_id"] for route in plan["selected_routes"]],
            "excluded_source_ids": [route["source_id"] for route in plan["excluded_routes"]],
            "subgoal_ids": [sg["subgoal_id"] for sg in plan["subgoals"]],
            "stop_disposition": plan["stop_disposition"],
            "learned_guidance_applied": plan["learned_guidance_applied"],
            "learned_model_digest": plan["learned_model_digest"],
            "llm_guidance_applied": plan["llm_guidance_applied"],
            "llm_model_digest": plan["llm_model_digest"],
            "semantic_authority": False,
            "proof_execution_allowed": False,
            "replay_index": replay_index,
            "replay_seed": replay_seed,
        },
        "guidance": dict(guidance),
        "cost": cost,
        "identities": ident,
        "artifacts": {"raw_sha256": sha256_obj(raw), "command_log_sha256": None},
        "notes": notes,
    }
    row["evaluation"] = evaluation_projection(
        record_id=row["record_id"],
        source_id=goal["goal_id"],
        family=goal["family"],
        arm=arm,
        execution_status=execution_status,
        result_kind=result_kind,
        checker_class="none",
        receipt_sha256=None,
        identities=ident,
        cost=cost,
        raw=raw,
        notes=notes,
    )
    return row


def assistance_row(
    *,
    goal_id: str,
    family: str,
    arm: str,
    stage: str,
    execution_status: str,
    result_kind: str,
    failure_category: str | None,
    candidate_produced: bool,
    encoding_produced: bool,
    policy: Mapping[str, Any] | None,
    model: Mapping[str, Any],
    tool: str | None,
    checker: str | None,
    elapsed: float,
    n_goals: int,
    native_receipt_id: str | None,
    extra: Mapping[str, Any],
    notes: str,
) -> dict[str, Any]:
    raw = {
        "goal_id": goal_id,
        "arm": arm,
        "stage": stage,
        "execution_status": execution_status,
        "failure_category": failure_category,
        **dict(extra),
    }
    cost = empty_cost(elapsed)
    ident = identities_for(arm, model=model.get("model_id"), tool=tool, checker=checker)
    row = {
        "schema": SCHEMA_ASSIST,
        "record_id": f"{goal_id}:{arm}:{stage}",
        "kind": "observation",
        "goal_id": goal_id,
        "source_family_time_group": family,
        "split": "constructed_control",
        "experiment_arm": arm,
        "stage": stage,
        "eligible": True,
        "fixture": extra.get("fixture", False),
        "constructed_control": True,
        "execution_status": execution_status,
        "result_kind": result_kind,
        "counts_as_executed_proof": False,
        "counts_as_native_checked_proof": False,
        "candidate_produced": candidate_produced,
        "encoding_produced": encoding_produced,
        "accepted_proof": False,
        "failure_category": failure_category,
        "n_goals": n_goals,
        "policy": dict(policy) if policy else None,
        "model": dict(model),
        "prompt_settings": extra.get("prompt_settings"),
        "native_receipt_id": native_receipt_id,
        "cost": cost,
        "identities": ident,
        "artifacts": {"raw_sha256": sha256_obj(raw), "command_log_sha256": None},
        "detail": {key: value for key, value in extra.items() if key not in {"prompt_settings", "fixture"}},
        "notes": notes,
    }
    row["evaluation"] = evaluation_projection(
        record_id=row["record_id"],
        source_id=goal_id,
        family=family,
        arm=arm,
        execution_status=execution_status,
        result_kind=result_kind,
        checker_class="native" if checker == "lean" else "none",
        receipt_sha256=None,
        identities=ident,
        cost=cost,
        raw=raw,
        notes=notes,
    )
    return row


def checker_receipt(
    *,
    receipt_id: str,
    attempt_id: str,
    goal_id: str | None,
    arm: str,
    checker_name: str,
    execution_status: str,
    policy: Mapping[str, Any] | None,
    resolved_path: str | None,
    elapsed: float,
    notes: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    body = {
        "receipt_id": receipt_id,
        "attempt_id": attempt_id,
        "goal_id": goal_id,
        "arm": arm,
        "checker_name": checker_name,
        "execution_status": execution_status,
        "policy": policy,
        "resolved_path": resolved_path,
        "extra": dict(extra or {}),
    }
    return {
        "schema": SCHEMA_RECEIPT,
        "receipt_id": receipt_id,
        "attempt_id": attempt_id,
        "goal_id": goal_id,
        "experiment_arm": arm,
        "checker_name": checker_name,
        "checker_class": "native" if checker_name in {"lean", "coqc", "isabelle"} else "none",
        "accepted": False,
        "counts_as_native_checked_proof": False,
        "execution_status": execution_status,
        "usable_in_sealed_validation": False,
        "resolved_path": resolved_path,
        "command": None,
        "stdout_sha256": None,
        "sorry_present": bool((policy or {}).get("sorry_present")),
        "admit_present": bool((policy or {}).get("admit_present")),
        "unapproved_axiom_present": bool((policy or {}).get("unapproved_axiom_present")),
        "policy_rejected": bool((policy or {}).get("policy_rejected")),
        "policy_rejection_reasons": list((policy or {}).get("reasons") or []),
        "cost": empty_cost(elapsed),
        "artifacts": {"raw_sha256": sha256_obj(body)},
        "notes": notes,
        "detail": dict(extra or {}),
    }


# ---------------------------------------------------------------------------
# Main measurement
# ---------------------------------------------------------------------------

def run(repo_root: Path, paper_root: Path, snapshot_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    env = probe_environment()
    inspected = inspect_sources(repo_root)
    frozen = load_frozen_inputs(repo_root)
    guidance_digest = f"sha256:{sha256_obj(GUIDANCE_RANKER_SPEC)}"
    prompt_digest = f"sha256:{sha256_obj(LEANSTRAL_PROMPT_SETTINGS)}"
    leanstral_model = {
        "model_id": LEANSTRAL_MODEL_ID,
        "revision": LEANSTRAL_REVISION,
        "weight_file_bytes": LEANSTRAL_WEIGHT_BYTES,
        "calls_executed": 0,
        "invented_model_call": False,
        "fine_tuning_claimed": False,
        "available": False,
        "blocker": (
            "weight file alone exceeds frozen 16GiB route envelope; "
            "no compatible served runtime qualified under sealed PATH"
        ),
        "prompt_settings_digest": prompt_digest,
    }

    missing_tools = [item["name"] for item in env["tools"] if not item["usable_in_sealed_validation"]]
    if env["any_native_checker_usable"] or env["any_solver_usable"]:
        # Sealed validation is the authority; usable tools would be recorded
        # rather than assumed absent. Presence is allowed but must be used.
        pass

    unguided_policy = default_policy_fields(UNGUIDED_POLICY_ID)
    guided_policy = default_policy_fields(
        GUIDED_POLICY_ID,
        allow_learned_ranking=True,
        learned_model_digest=guidance_digest,
    )
    llm_policy = default_policy_fields(
        LLM_POLICY_ID,
        allow_llm_nomination=True,
        llm_model_digest=f"sha256:{sha256_obj({'model_id': LEANSTRAL_MODEL_ID, 'revision': LEANSTRAL_REVISION})}",
    )

    planning_rows: list[dict[str, Any]] = []
    n_plan_goals = len(PLAN_GOALS)
    plan_elapsed = []

    def replay_arm(arm: str, policy: Mapping[str, Any], ranker: Any, digest: str, status: str, kind: str, notes: str, guidance: Mapping[str, Any]) -> None:
        for goal in PLAN_GOALS:
            plan_ids = []
            for replay_index, seed in enumerate(REPLAY_SEEDS):
                t0 = time.perf_counter()
                plan = run_planner(
                    goal, SOURCES, policy,
                    ranker=ranker, ranker_digest=digest,
                )
                elapsed = time.perf_counter() - t0
                plan_elapsed.append(elapsed)
                plan_ids.append(plan["plan_id"])
                planning_rows.append(planning_row(
                    goal=goal, arm=arm, plan=plan,
                    replay_index=replay_index, replay_seed=seed,
                    execution_status=status, result_kind=kind,
                    guidance=guidance, elapsed=elapsed, n_goals=n_plan_goals,
                    notes=notes,
                ))
            if status == "measured" and len(set(plan_ids)) != 1:
                raise HarnessError(f"nondeterministic plan replay for {goal['goal_id']} arm {arm}: {plan_ids}")

    replay_arm(
        "plan.unguided",
        unguided_policy,
        None,
        "",
        "measured",
        "bounded_observation",
        "Deterministic LogicTactician replica; no proof execution.",
        {"pinned": True, "kind": "none", "digest": "", "applied": False, "model_call": False, "trained": False},
    )
    replay_arm(
        "plan.guided_pinned_ranker",
        guided_policy,
        reverse_ranker,
        guidance_digest,
        "measured",
        "bounded_observation",
        "Pinned hand-authored reorder of admitted sources; not a model call and not a proof.",
        {"pinned": True, "kind": "hand_authored_pinned_reorder", "digest": guidance_digest,
         "applied": True, "model_call": False, "trained": False},
    )
    replay_arm(
        "plan.llm_nominated",
        llm_policy,
        None,
        "",
        "unavailable",
        "no_run",
        "LLM nomination arm is unavailable: no Leanstral/model service call was made; deterministic fallback is recorded without counting as LLM guidance.",
        {"pinned": True, "kind": "llm_nomination", "digest": llm_policy["llm_model_digest"],
         "applied": False, "model_call": False, "trained": False, "available": False},
    )

    unguided_ids = {
        (row["goal_id"], row["plan"]["replay_index"]): row["plan"]["plan_id"]
        for row in planning_rows if row["experiment_arm"] == "plan.unguided"
    }
    guided_ids = {
        (row["goal_id"], row["plan"]["replay_index"]): row["plan"]["plan_id"]
        for row in planning_rows if row["experiment_arm"] == "plan.guided_pinned_ranker"
    }
    if unguided_ids.keys() != guided_ids.keys():
        raise HarnessError("unguided/guided goal coverage mismatch")
    if unguided_ids == guided_ids:
        raise HarnessError("guided ranker did not change any plan identity")

    receipts: list[dict[str, Any]] = []
    t_probe = time.perf_counter()
    for tool in env["tools"]:
        receipts.append(checker_receipt(
            receipt_id=f"probe:{tool['name']}",
            attempt_id=f"env:{tool['name']}",
            goal_id=None,
            arm="environment_probe",
            checker_name=tool["name"],
            execution_status="unavailable" if not tool["usable_in_sealed_validation"] else "measured",
            policy=None,
            resolved_path=tool["resolved_path"],
            elapsed=0.0,
            notes="Sealed-PATH probe; host ~/.elan and ~/.local/bin are not on PATH.",
            extra={"probe": tool},
        ))
    probe_elapsed = time.perf_counter() - t_probe

    assistance_rows: list[dict[str, Any]] = []
    n_assist_goals = len(ASSIST_GOALS)
    hammer_model = {
        "model_id": None,
        "revision": None,
        "calls_executed": 0,
        "invented_model_call": False,
        "fine_tuning_claimed": False,
        "available": False,
        "selector": "deterministic_overlap_baseline",
        "trained": False,
    }

    for goal in ASSIST_GOALS:
        t0 = time.perf_counter()
        translation = translate_goal(goal)
        elapsed = time.perf_counter() - t0
        if not translation["supported"]:
            assistance_rows.append(assistance_row(
                goal_id=goal["goal_id"], family=goal["family"], arm="hammer",
                stage="candidate_generation",
                execution_status="unsupported", result_kind="failure",
                failure_category="unsupported_translation",
                candidate_produced=False, encoding_produced=False,
                policy=None, model=hammer_model, tool="hammer-translation-replica/v1",
                checker=None, elapsed=elapsed, n_goals=n_assist_goals,
                native_receipt_id=None,
                extra={"unsupported_reason": translation["unsupported_reason"], "fragment": goal["fragment"]},
                notes="Unsupported dependent/higher-order fragment failed closed; no silent erasure.",
            ))
            for stage, category in (
                ("solver_response", "unsupported_translation"),
                ("native_reconstruction", "unsupported_translation"),
            ):
                assistance_rows.append(assistance_row(
                    goal_id=goal["goal_id"], family=goal["family"], arm="hammer",
                    stage=stage, execution_status="unsupported", result_kind="failure",
                    failure_category=category, candidate_produced=False, encoding_produced=False,
                    policy=None, model=hammer_model, tool="hammer-translation-replica/v1",
                    checker="lean" if stage == "native_reconstruction" else None,
                    elapsed=0.0, n_goals=n_assist_goals, native_receipt_id=None,
                    extra={"unsupported_reason": translation["unsupported_reason"]},
                    notes="Downstream Hammer stages are not executed after unsupported translation.",
                ))
            continue

        assistance_rows.append(assistance_row(
            goal_id=goal["goal_id"], family=goal["family"], arm="hammer",
            stage="candidate_generation",
            execution_status="measured", result_kind="bounded_observation",
            failure_category=None,
            candidate_produced=False, encoding_produced=True,
            policy=None, model=hammer_model, tool="hammer-translation-replica/v1",
            checker=None, elapsed=elapsed, n_goals=n_assist_goals,
            native_receipt_id=None,
            extra={
                "tptp_sha256": sha256_text(translation["tptp"]),
                "smtlib_sha256": sha256_text(translation["smtlib"]),
                "encoding_sha256": translation["encoding_sha256"],
                "solver_candidate_produced": False,
                "fragment": goal["fragment"],
            },
            notes="TPTP/SMT-LIB encoding is not a solver candidate; solvers were not invoked.",
        ))
        assistance_rows.append(assistance_row(
            goal_id=goal["goal_id"], family=goal["family"], arm="hammer",
            stage="solver_response",
            execution_status="unavailable", result_kind="no_run",
            failure_category="unavailable_solver",
            candidate_produced=False, encoding_produced=True,
            policy=None, model=hammer_model, tool=None, checker=None,
            elapsed=0.0, n_goals=n_assist_goals, native_receipt_id=None,
            extra={
                "missing_solvers": [name for name in ("vampire", "eprover", "z3", "cvc5") if name in missing_tools],
                "opt_in": False,
                "default_allowed_solvers": [],
            },
            notes="HammerPolicy default allowed_solvers is empty and sealed PATH has no ATP/SMT binaries.",
        ))
        rec_id = f"hammer:{goal['goal_id']}:lean"
        receipts.append(checker_receipt(
            receipt_id=rec_id,
            attempt_id=f"recon:{goal['goal_id']}",
            goal_id=goal["goal_id"],
            arm="hammer",
            checker_name="lean",
            execution_status="unavailable",
            policy=None,
            resolved_path=None,
            elapsed=0.0,
            notes="Native reconstruction skipped: lean is absent from sealed PATH; no sorry bypass.",
            extra={"encoding_sha256": translation["encoding_sha256"]},
        ))
        assistance_rows.append(assistance_row(
            goal_id=goal["goal_id"], family=goal["family"], arm="hammer",
            stage="native_reconstruction",
            execution_status="unavailable", result_kind="no_run",
            failure_category="unavailable_native_checker",
            candidate_produced=False, encoding_produced=True,
            policy=None, model=hammer_model, tool="lean-reconstructor",
            checker="lean", elapsed=0.0, n_goals=n_assist_goals,
            native_receipt_id=rec_id,
            extra={"missing_checker": "lean"},
            notes="No reconstructed proof was submitted to a native kernel.",
        ))

    for goal in ASSIST_GOALS:
        assistance_rows.append(assistance_row(
            goal_id=goal["goal_id"], family=goal["family"], arm="leanstral",
            stage="candidate_generation",
            execution_status="unavailable", result_kind="no_run",
            failure_category="unavailable_model_service",
            candidate_produced=False, encoding_produced=False,
            policy=None, model=leanstral_model, tool=None, checker=None,
            elapsed=0.0, n_goals=n_assist_goals, native_receipt_id=None,
            extra={"prompt_settings": LEANSTRAL_PROMPT_SETTINGS, "prompt_settings_digest": prompt_digest},
            notes="No Leanstral model call was invented; identity and prompt settings are retained.",
        ))
        assistance_rows.append(assistance_row(
            goal_id=goal["goal_id"], family=goal["family"], arm="leanstral",
            stage="solver_response",
            execution_status="unavailable", result_kind="no_run",
            failure_category="unavailable_model_service",
            candidate_produced=False, encoding_produced=False,
            policy=None, model=leanstral_model, tool=None, checker=None,
            elapsed=0.0, n_goals=n_assist_goals, native_receipt_id=None,
            extra={"prompt_settings_digest": prompt_digest},
            notes="Leanstral does not use the ATP/SMT portfolio; no proposal exists to check.",
        ))
        rec_id = f"leanstral:{goal['goal_id']}:lean"
        receipts.append(checker_receipt(
            receipt_id=rec_id,
            attempt_id=f"leanstral:{goal['goal_id']}",
            goal_id=goal["goal_id"],
            arm="leanstral",
            checker_name="lean",
            execution_status="unavailable",
            policy=None,
            resolved_path=None,
            elapsed=0.0,
            notes="No Leanstral proposal was generated, so no native check ran.",
            extra={"model_calls_executed": 0},
        ))
        assistance_rows.append(assistance_row(
            goal_id=goal["goal_id"], family=goal["family"], arm="leanstral",
            stage="native_reconstruction",
            execution_status="unavailable", result_kind="no_run",
            failure_category="unavailable_model_service",
            candidate_produced=False, encoding_produced=False,
            policy=None, model=leanstral_model, tool=None, checker="lean",
            elapsed=0.0, n_goals=n_assist_goals, native_receipt_id=rec_id,
            extra={"prompt_settings_digest": prompt_digest},
            notes="Checker acceptance cannot occur without a generated candidate.",
        ))

    for fixture in POLICY_FIXTURES:
        t0 = time.perf_counter()
        policy = scan_lean_policy(fixture["source"])
        elapsed = time.perf_counter() - t0
        rejected = policy["policy_rejected"]
        if fixture["kind"] == "clean_rfl" and rejected:
            raise HarnessError("clean rfl fixture was incorrectly policy-rejected")
        if fixture["kind"] != "clean_rfl" and not rejected:
            raise HarnessError(f"{fixture['kind']} fixture was not rejected")
        for arm, model in (("hammer", hammer_model), ("leanstral", leanstral_model)):
            rec_id = f"policy:{arm}:{fixture['goal_id']}"
            if rejected:
                status, kind, category, notes = (
                    "invalid", "failure", f"policy_rejected_{fixture['kind']}",
                    "Generated Lean with sorry/admit/unapproved axioms is rejected before any kernel claim.",
                )
            else:
                status, kind, category, notes = (
                    "unavailable", "no_run", "unavailable_native_checker",
                    "Bypass-free Lean still requires a sealed-PATH kernel; no accepted proof is recorded.",
                )
            receipts.append(checker_receipt(
                receipt_id=rec_id,
                attempt_id=rec_id,
                goal_id=fixture["goal_id"],
                arm=arm,
                checker_name="lean",
                execution_status=status,
                policy=policy,
                resolved_path=None,
                elapsed=elapsed,
                notes=notes,
                extra={"fixture_kind": fixture["kind"], "source_sha256": policy["source_sha256"],
                       "not_a_model_output": True},
            ))
            extra = {
                "fixture": True,
                "fixture_kind": fixture["kind"],
                "not_a_model_output": True,
                "source_sha256": policy["source_sha256"],
            }
            if arm == "leanstral":
                extra["prompt_settings"] = LEANSTRAL_PROMPT_SETTINGS
                extra["prompt_settings_digest"] = prompt_digest
            assistance_rows.append(assistance_row(
                goal_id=fixture["goal_id"], family=fixture["family"], arm=arm,
                stage="policy_scan",
                execution_status=status, result_kind=kind,
                failure_category=category,
                candidate_produced=False, encoding_produced=False,
                policy=policy, model=model, tool="lean-policy-scan/v1",
                checker="lean", elapsed=elapsed, n_goals=n_assist_goals,
                native_receipt_id=rec_id, extra=extra, notes=notes,
            ))

    def rate(numerator: int, denominator: int) -> float:
        if denominator == 0:
            raise HarnessError("rate denominator is zero")
        return numerator / denominator

    plan_obs = [row for row in planning_rows if row["kind"] == "observation"]
    stop_counts = Counter(
        row["plan"]["stop_disposition"]
        for row in plan_obs if row["experiment_arm"] == "plan.unguided" and row["plan"]["replay_index"] == 0
    )
    guided_applied = all(
        row["plan"]["learned_guidance_applied"]
        for row in plan_obs if row["experiment_arm"] == "plan.guided_pinned_ranker"
    )
    llm_applied = any(
        row["plan"]["llm_guidance_applied"]
        for row in plan_obs if row["experiment_arm"] == "plan.llm_nominated"
    )
    if llm_applied:
        raise HarnessError("LLM guidance must not be applied without a model call")
    if not guided_applied:
        raise HarnessError("pinned ranker did not apply")

    planning_summary = {
        "schema": SCHEMA_PLAN,
        "record_id": "summary:planning",
        "kind": "summary",
        "n_goals": n_plan_goals,
        "n_replays": len(REPLAY_SEEDS),
        "n_observation_rows": len(plan_obs),
        "deterministic_replay": True,
        "counts_as_executed_proof": False,
        "counts_as_native_checked_proof": False,
        "guided_ranker_digest": guidance_digest,
        "guided_is_model_call": False,
        "llm_nomination_available": False,
        "stop_disposition_counts_unguided_replay0": dict(stop_counts),
        "subgoal_coverage_unguided_replay0": rate(sum(1 for row in plan_obs if row["experiment_arm"] == "plan.unguided" and row["plan"]["replay_index"] == 0 and row["plan"]["subgoal_ids"]), n_plan_goals),
        "abstention_rate_unguided_replay0": rate(stop_counts.get("abstain", 0) + stop_counts.get("cycle_detected", 0), n_plan_goals),
        "all_attempt_costs": {
            "elapsed_seconds": round(sum(plan_elapsed), 6),
            "cpu_seconds": None,
            "gpu_seconds": 0.0,
            "provider_units": 0.0,
            "memory_gib": None,
            "human_review_seconds": 0.0,
            "n_attempts": len(plan_obs),
        },
        "unavailable_arms": ["plan.llm_nominated"],
        "claim_narrowing": [
            "Plans are not executed proofs and do not fill native-checked proof cells.",
            "Pinned guidance is a hand-authored reorder, not a learned or Leanstral call.",
            "LLM nomination remains unavailable; no model call was invented.",
            "Constructed_control replay does not fill Table 13 natural held-out cells.",
        ],
        "execution_status": "measured",
        "result_kind": "bounded_observation",
    }
    planning_rows.append(planning_summary)

    assist_obs = [row for row in assistance_rows if row["kind"] == "observation"]
    denom = n_assist_goals

    def arm_stage(arm: str, stage: str) -> list[dict[str, Any]]:
        return [row for row in assist_obs if row["experiment_arm"] == arm and row["stage"] == stage and row["goal_id"].startswith("h.")]

    def category_counts() -> dict[str, int]:
        counts: dict[str, int] = Counter()
        for row in assist_obs:
            if row.get("failure_category"):
                counts[row["failure_category"]] += 1
        return dict(counts)

    hammer_candidates = sum(1 for row in arm_stage("hammer", "candidate_generation") if row["candidate_produced"])
    leanstral_candidates = sum(1 for row in arm_stage("leanstral", "candidate_generation") if row["candidate_produced"])
    accepted = sum(1 for row in assist_obs if row.get("accepted_proof"))
    native_ok = sum(1 for row in receipts if row["counts_as_native_checked_proof"])
    if accepted or native_ok or hammer_candidates or leanstral_candidates:
        raise HarnessError("accepted proofs or solver/model candidates were recorded without a real checker/model")

    assist_cost = round(sum(float(row["cost"]["elapsed_seconds"] or 0.0) for row in assist_obs) + probe_elapsed, 6)
    assistance_summary = {
        "schema": SCHEMA_ASSIST,
        "record_id": "summary:proof_assistance",
        "kind": "summary",
        "n_goals": n_assist_goals,
        "n_observation_rows": len(assist_obs),
        "counts_as_executed_proof": False,
        "counts_as_native_checked_proof": False,
        "candidate_rate": {
            "hammer": rate(hammer_candidates, denom),
            "leanstral": rate(leanstral_candidates, denom),
            "note": "Solver/model candidates only; TPTP/SMT encodings are not counted as candidates.",
        },
        "accepted_proof_rate": {
            "hammer": rate(0, denom),
            "leanstral": rate(0, denom),
        },
        "native_coverage": {
            "hammer": rate(0, denom),
            "leanstral": rate(0, denom),
            "denominator": denom,
            "native_checked_proofs": 0,
        },
        "encoding_rate_hammer": rate(sum(1 for row in arm_stage("hammer", "candidate_generation") if row["encoding_produced"]), denom),
        "failure_categories": category_counts(),
        "all_attempt_costs": {
            "elapsed_seconds": assist_cost,
            "cpu_seconds": None,
            "gpu_seconds": 0.0,
            "provider_units": 0.0,
            "memory_gib": None,
            "human_review_seconds": 0.0,
            "n_attempts": len(assist_obs) + len(env["tools"]),
        },
        "unavailable_arms": ["hammer.solver_portfolio", "hammer.native_reconstruction", "leanstral.model_service", "leanstral.native_check"],
        "model_identity": {
            "model_id": LEANSTRAL_MODEL_ID,
            "revision": LEANSTRAL_REVISION,
            "weight_file_bytes": LEANSTRAL_WEIGHT_BYTES,
            "prompt_settings_digest": prompt_digest,
            "calls_executed": 0,
            "invented_model_call": False,
            "fine_tuning_claimed": False,
        },
        "sorry_admit_axiom_policy": {
            "sorry_rejected": True,
            "admit_rejected": True,
            "unapproved_axiom_rejected": True,
            "clean_rfl_not_kernel_accepted": True,
        },
        "claim_narrowing": [
            "No native checked proof is claimed.",
            "No solver-local result is treated as an ITP theorem.",
            "No Leanstral model call or fine-tuning is claimed.",
            "Policy fixtures are not model outputs.",
            "Constructed_control rates do not fill Table 13 natural cells.",
        ],
        "execution_status": "measured",
        "result_kind": "bounded_observation",
    }
    assistance_rows.append(assistance_summary)

    receipt_summary = {
        "schema": SCHEMA_RECEIPT,
        "receipt_id": "summary:native_checker",
        "kind": "summary",
        "n_receipts": len(receipts),
        "accepted_proofs": 0,
        "counts_as_native_checked_proof": False,
        "missing_tools": missing_tools,
        "any_native_checker_usable": env["any_native_checker_usable"],
        "any_solver_usable": env["any_solver_usable"],
        "policy_rejections": sum(1 for row in receipts if row.get("policy_rejected")),
        "claim_narrowing": [
            "Sealed PATH has no lean/lake/elan/z3/cvc5/vampire/eprover/coqc/isabelle.",
            "Host AF-003 ~/.elan Lean and ~/.local/bin solvers are out of validation scope.",
        ],
        "execution_status": "unavailable",
        "accepted": False,
    }
    receipts.append(receipt_summary)

    for row in planning_rows:
        if row.get("counts_as_executed_proof"):
            raise HarnessError("a plan row counted as an executed proof")
        if row.get("result_kind") == "native_checked_proof":
            raise HarnessError("a plan row used native_checked_proof")
    for row in assistance_rows:
        if row.get("counts_as_native_checked_proof") or row.get("accepted_proof"):
            raise HarnessError("an assistance row claimed a native accepted proof")
        if row.get("result_kind") == "native_checked_proof":
            raise HarnessError("native_checked_proof recorded without a kernel")
        model = row.get("model") or {}
        if model.get("calls_executed"):
            raise HarnessError("invented model call")
        if model.get("fine_tuning_claimed") or model.get("invented_model_call"):
            raise HarnessError("fine-tuning or invented-call flag set")

    paths = {
        "planning": paper_root / "runs" / "planning" / "results.jsonl",
        "assistance": paper_root / "runs" / "proof_assistance" / "results.jsonl",
        "receipts": paper_root / "evidence" / "native_checker_receipts.jsonl",
        "snap_planning": snapshot_root / "runs" / "planning" / "results.jsonl",
        "snap_assistance": snapshot_root / "runs" / "proof_assistance" / "results.jsonl",
        "snap_receipts": snapshot_root / "evidence" / "native_checker_receipts.jsonl",
    }
    write_jsonl(paths["planning"], planning_rows)
    write_jsonl(paths["assistance"], assistance_rows)
    write_jsonl(paths["receipts"], receipts)
    write_jsonl(paths["snap_planning"], planning_rows)
    write_jsonl(paths["snap_assistance"], assistance_rows)
    write_jsonl(paths["snap_receipts"], receipts)

    report = {
        "task_id": TASK_ID,
        "pool_id": POOL_ID,
        "n_plan_goals": n_plan_goals,
        "n_assist_goals": n_assist_goals,
        "n_planning_rows": len(planning_rows),
        "n_assistance_rows": len(assistance_rows),
        "n_receipts": len(receipts),
        "guidance_digest": guidance_digest,
        "prompt_settings_digest": prompt_digest,
        "missing_tools": missing_tools,
        "any_native_checker_usable": env["any_native_checker_usable"],
        "any_solver_usable": env["any_solver_usable"],
        "model_calls_executed": 0,
        "fine_tuning_claimed": False,
        "accepted_proofs": 0,
        "frozen_inputs": frozen,
        "inspected_not_imported": {key: value["sha256"] for key, value in inspected.items()},
        "environment": {
            "path": env["path"],
            "home": env["home"],
            "home_is_validation_private": env["home_is_validation_private"],
            "python": env["python_version"],
            "interpreter": env["python_executable"],
        },
        "summaries": {
            "planning": {
                "deterministic_replay": True,
                "counts_as_executed_proof": False,
                "unavailable_arms": planning_summary["unavailable_arms"],
            },
            "assistance": {
                "candidate_rate": assistance_summary["candidate_rate"],
                "accepted_proof_rate": assistance_summary["accepted_proof_rate"],
                "native_coverage": assistance_summary["native_coverage"],
                "failure_categories": assistance_summary["failure_categories"],
            },
        },
        "paths": {key: str(path.relative_to(repo_root)) for key, path in paths.items()},
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "completed_at": utc_now(),
    }
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--paper-root", type=Path, default=PAPER_ROOT)
    parser.add_argument("--snapshot-root", type=Path, default=HERE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args.repo_root.resolve(), args.paper_root.resolve(), args.snapshot_root.resolve())
    print(canonical_dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as exc:
        print(f"AF-018: {exc}", file=sys.stderr)
        raise SystemExit(1)
