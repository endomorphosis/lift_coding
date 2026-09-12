#!/usr/bin/env python3
"""AF-017 retrieval and premise-selection measurement harness.

Freeze a common constructed corpus/query pool with independent relevance
and admitted-premise labels. Compare lexical BM25, exact inner-product
vector search, typed graph walks, and untrained reciprocal-rank fusion
under matched top-k budgets. Compare the deterministic Hammer baseline
and the hand-authored graph selector against explicit usefulness labels,
keeping import-overlap proxy scores as a separately labeled diagnostic.

Standard library only. Project packages are inspected and hashed, not
imported. FAISS, NumPy, MiniLM, and the GraphRAG thin-client vector
subcommand are probed on the process environment; missing libraries
cannot be counted as measured routes. The executed vector route is an
exact inner-product index over signed hashed character trigrams, which
is a real similarity computation, not a mock ranker and not the
undeployed thin-client CLI.

Natural AF-004 source bodies remain owner-only and AF-005 gold is
pending, so this pool is constructed_control. Those unavailable
conditions narrow natural held-out retrieval claims only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_JUDGMENT = "autoformalization-retrieval-judgment/v1"
SCHEMA_RETRIEVAL = "autoformalization-retrieval-result/v1"
SCHEMA_PREMISE = "autoformalization-premise-selection-result/v1"
SCHEMA_MANIFEST = "autoformalization-retrieval-manifest/v1"
TASK_ID = "AF-017"
POOL_ID = "AF-017-constructed-retrieval-pool/v1"
ENCODER_ID = "signed-char-trigram-hash/v1"
VECTOR_BACKEND_ID = "stdlib-exact-inner-product/v1"
BM25_K1 = 1.2
BM25_B = 0.75
TITLE_TF_WEIGHT = 2.0
BODY_TF_WEIGHT = 1.0
VECTOR_DIM = 256
CHAR_NGRAM = 3
RRF_K = 60
TOP_KS = (5, 10)
TOKEN_BUDGET = 256
GRAPH_HOPS = 1

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*'*")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOPWORDS = frozenset(
    word.lower()
    for word in [
        "forall", "exists", "fun", "let", "in", "if", "then", "else", "do",
        "match", "with", "end", "where", "class", "instance", "structure",
        "open", "import", "using", "from", "as", "return", "case", "of",
        "theorem", "lemma", "def", "definition", "example", "by", "have",
        "show", "suffices", "this", "sorry", "admit", "variable",
        "variables", "section", "namespace", "obtain", "rcases", "rintro",
        "intro", "intros", "apply", "exact", "simp", "rw", "calc",
        "noncomputable", "mutual", "deriving", "attribute",
        "proof", "qed", "fixpoint", "inductive", "context", "module",
        "require", "export", "axiom", "hypothesis", "corollary", "remark",
        "fact", "record", "notation", "begin", "assumption", "induction",
        "destruct", "reflexivity", "unfold", "auto",
        "primrec", "datatype", "locale", "assumes", "shows", "obtains",
        "hence", "thus", "fix", "next", "moreover", "ultimately", "value",
        "true", "false",
    ]
)
INSPECTED_SOURCES = {
    "faiss_store.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/vector_stores/faiss_store.py",
        "imported": False,
        "note": "Inspected FAISS store; constructor requires real FAISS/NumPy. MockFaiss in the file is not executed.",
    },
    "bench_itp_hammer_premise_selection.py": {
        "path": "external/ipfs_datasets/benchmarks/bench_itp_hammer_premise_selection.py",
        "imported": False,
        "note": "Held-out import-overlap proxy harness; proxy rows stay diagnostic.",
    },
    "learned_selector.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/hammers/learned_selector.py",
        "imported": False,
        "note": "Optional graph selector; default weights are hand-authored, not trained.",
    },
    "premise_selection.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/hammers/premise_selection.py",
        "imported": False,
        "note": "Deterministic symbol/type/import/graph Jaccard baseline; default weights hand-authored.",
    },
    "legal_samples.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_samples.py",
        "imported": False,
        "note": "stable_mock_embedding is excluded from semantic/retrieval claims.",
    },
    "premise_selection_corpus.json": {
        "path": "external/ipfs_datasets/tests/fixtures/logic/hammers/premise_selection_corpus.json",
        "imported": False,
        "note": "Synthetic Lean-named fixture; not a Mathlib excerpt.",
    },
    "learned_selector_model.json": {
        "path": "external/ipfs_datasets/tests/fixtures/logic/hammers/learned_selector_model.json",
        "imported": False,
        "note": "Pinned hand-authored linear weights and digest.",
    },
}

# Default Hammer baseline weights (premise_selection.PremiseSelectionWeights).
BASELINE_WEIGHTS = {
    "symbol_weight": 0.45,
    "type_weight": 0.20,
    "import_weight": 0.20,
    "graph_weight": 0.15,
    "provenance": "hand_authored_module_defaults",
    "trained": False,
}

# Fixture artifact weights (learned_selector.build_default_graph_selector_artifact).
GRAPH_SELECTOR_WEIGHTS = {
    "symbol_score": 3.2,
    "type_score": 1.0,
    "import_score": 1.2,
    "graph_score": 0.8,
    "shared_symbol_count": 0.15,
    "one_hop_neighbor_count": 0.05,
    "goal_symbol_count": 0.0,
    "candidate_symbol_count": -0.01,
    "candidate_import_count": 0.0,
}
GRAPH_SELECTOR_BIAS = -1.6
GRAPH_SELECTOR_FEATURE_NAMES = (
    "symbol_score",
    "type_score",
    "import_score",
    "graph_score",
    "goal_symbol_count",
    "candidate_symbol_count",
    "shared_symbol_count",
    "candidate_import_count",
    "one_hop_neighbor_count",
)
GRAPH_SELECTOR_FEATURE_VERSION = "learned-selector-features-v1"
GRAPH_SELECTOR_MODEL_ID = "graph-selector-default-v1"

THEOREMS = [
    {"theorem_id": "Nat.add_comm", "family": "nat_add",
     "statement": "theorem add_comm : forall a b : Nat, Nat.add a b = Nat.add b a",
     "imports": ["Mathlib.Algebra.Group.Defs", "Mathlib.Data.Nat.Basic"]},
    {"theorem_id": "Nat.add_assoc", "family": "nat_add",
     "statement": "theorem add_assoc : forall a b c : Nat, Nat.add (Nat.add a b) c = Nat.add a (Nat.add b c)",
     "imports": ["Mathlib.Algebra.Group.Defs", "Mathlib.Data.Nat.Basic"]},
    {"theorem_id": "Nat.add_zero", "family": "nat_add",
     "statement": "theorem add_zero : forall a : Nat, Nat.add a Nat.zero = a",
     "imports": ["Mathlib.Data.Nat.Basic"]},
    {"theorem_id": "Nat.mul_comm", "family": "nat_mul",
     "statement": "theorem mul_comm : forall a b : Nat, Nat.mul a b = Nat.mul b a",
     "imports": ["Mathlib.Algebra.Group.Defs", "Mathlib.Data.Nat.Basic"]},
    {"theorem_id": "Nat.mul_add", "family": "nat_mul",
     "statement": "theorem mul_add : forall a b c : Nat, Nat.mul a (Nat.add b c) = Nat.add (Nat.mul a b) (Nat.mul a c)",
     "imports": ["Mathlib.Data.Nat.Basic"]},
    {"theorem_id": "List.append_nil", "family": "list",
     "statement": "theorem append_nil : forall xs : List Nat, List.append xs List.nil = xs",
     "imports": ["Mathlib.Data.List.Basic"]},
    {"theorem_id": "List.append_assoc", "family": "list",
     "statement": "theorem append_assoc : forall xs ys zs : List Nat, List.append (List.append xs ys) zs = List.append xs (List.append ys zs)",
     "imports": ["Mathlib.Data.List.Basic"]},
    {"theorem_id": "List.length_append", "family": "list",
     "statement": "theorem length_append : forall xs ys : List Nat, List.length (List.append xs ys) = Nat.add (List.length xs) (List.length ys)",
     "imports": ["Mathlib.Data.List.Basic", "Mathlib.Data.Nat.Basic"]},
    {"theorem_id": "List.reverse_append", "family": "list",
     "statement": "theorem reverse_append : forall xs ys : List Nat, List.reverse (List.append xs ys) = List.append (List.reverse ys) (List.reverse xs)",
     "imports": ["Mathlib.Data.List.Basic"]},
    {"theorem_id": "List.map_append", "family": "list",
     "statement": "theorem map_append : forall f xs ys, List.map f (List.append xs ys) = List.append (List.map f xs) (List.map f ys)",
     "imports": ["Mathlib.Data.List.Basic"]},
    {"theorem_id": "Set.union_comm", "family": "set",
     "statement": "theorem union_comm : forall a b : Set Nat, Set.union a b = Set.union b a",
     "imports": ["Mathlib.Data.Set.Basic"]},
    {"theorem_id": "Set.inter_comm", "family": "set",
     "statement": "theorem inter_comm : forall a b : Set Nat, Set.inter a b = Set.inter b a",
     "imports": ["Mathlib.Data.Set.Basic"]},
    {"theorem_id": "Set.union_assoc", "family": "set",
     "statement": "theorem union_assoc : forall a b c : Set Nat, Set.union (Set.union a b) c = Set.union a (Set.union b c)",
     "imports": ["Mathlib.Data.Set.Basic"]},
    {"theorem_id": "Set.subset_union_left", "family": "set",
     "statement": "theorem subset_union_left : forall a b : Set Nat, Set.subset a (Set.union a b)",
     "imports": ["Mathlib.Data.Set.Basic"]},
    {"theorem_id": "Group.mul_left_inv", "family": "group",
     "statement": "theorem mul_left_inv : forall a : Group, Group.mul (Group.inv a) a = Group.one",
     "imports": ["Mathlib.Algebra.Group.Defs"]},
    {"theorem_id": "Group.mul_one", "family": "group",
     "statement": "theorem mul_one : forall a : Group, Group.mul a Group.one = a",
     "imports": ["Mathlib.Algebra.Group.Defs"]},
    {"theorem_id": "Group.inv_inv", "family": "group",
     "statement": "theorem inv_inv : forall a : Group, Group.inv (Group.inv a) = a",
     "imports": ["Mathlib.Algebra.Group.Defs"]},
    {"theorem_id": "Group.mul_assoc", "family": "group",
     "statement": "theorem mul_assoc : forall a b c : Group, Group.mul (Group.mul a b) c = Group.mul a (Group.mul b c)",
     "imports": ["Mathlib.Algebra.Group.Defs"]},
    {"theorem_id": "Order.le_refl", "family": "order",
     "statement": "theorem le_refl : forall a : Order, Order.le a a",
     "imports": ["Mathlib.Order.Basic"]},
    {"theorem_id": "Order.le_trans", "family": "order",
     "statement": "theorem le_trans : forall a b c : Order, Order.le a b -> Order.le b c -> Order.le a c",
     "imports": ["Mathlib.Order.Basic"]},
]

POLICY_DOCUMENTS = [
    {
        "doc_id": "policy.protected_write",
        "kind": "policy",
        "family": "protected_write",
        "authority": "controlling",
        "title": "Protected write requires prior approval",
        "body": (
            "A protected resource may be written only when an approval record already exists "
            "for that actor, tenant, and resource. Absence of approval forbids the write."
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "policy.protected_write_paraphrase",
        "kind": "policy",
        "family": "protected_write",
        "authority": "controlling",
        "title": "Approval must precede a guarded store",
        "body": (
            "Before storing into a guarded object the requester needs an already-issued "
            "authorization. No later waiver converts an unapproved store into a permitted one."
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "policy.audit_window",
        "kind": "policy",
        "family": "audit",
        "authority": "controlling",
        "title": "Writes must be audited within a bounded window",
        "body": (
            "Every write event must be followed by a matching audit record no later than "
            "deadline_offset steps, provided capture of the interval is complete."
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "policy.tenant_isolation",
        "kind": "policy",
        "family": "tenant",
        "authority": "controlling",
        "title": "Tenant identity must match before records join",
        "body": (
            "Audit, approval, and write records join only when actor, resource, request, "
            "and tenant identifiers are identical. A tenant-b audit does not discharge a tenant-a write."
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "policy.emergency_exception",
        "kind": "policy",
        "family": "protected_write",
        "authority": "exception",
        "title": "Emergency exception for protected writes",
        "body": (
            "During a declared emergency a protected write may proceed without prior approval "
            "if an incident commander records the override. This exception is not the standing rule."
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "policy.records_retention",
        "kind": "policy",
        "family": "records",
        "authority": "controlling",
        "title": "Retention of operational logs",
        "body": (
            "Operational logs including writes and audits are retained for seven years. "
            "Retention duration is not an approval or tenant-join condition."
        ),
        "identity": {},
    },
    {
        "doc_id": "impl.guarded_write",
        "kind": "implementation",
        "family": "protected_write",
        "authority": "implementation",
        "title": "Guarded write implementation",
        "body": (
            "function write(protected, approved): if protected and not approved then refuse; "
            "else perform the store. This is Write = not Protected or Approved."
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "impl.unguarded_write",
        "kind": "implementation",
        "family": "protected_write",
        "authority": "implementation",
        "title": "Unguarded write implementation",
        "body": (
            "function write(protected, approved): always perform the store. Approval is logged "
            "but not checked. This implementation admits unapproved protected writes."
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "impl.logging_helper",
        "kind": "implementation",
        "family": "records",
        "authority": "implementation",
        "title": "JSON log formatter",
        "body": (
            "function format_log(event): serialize timestamp, message, and severity. "
            "The helper does not authorize writes or join tenants."
        ),
        "identity": {},
    },
    {
        "doc_id": "trace.timely_audit",
        "kind": "trace",
        "family": "audit",
        "authority": "observation",
        "title": "Timely audit observation",
        "body": (
            "write_t=0 audit_t=1 deadline_offset=2 capture_complete_through=2 "
            "actor=alice tenant=tenant-a resource=r1 request=req-1"
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
    },
    {
        "doc_id": "trace.delayed_audit",
        "kind": "trace",
        "family": "audit",
        "authority": "observation",
        "title": "Delayed audit observation",
        "body": (
            "write_t=0 audit_t=3 deadline_offset=2 capture_complete_through=5 "
            "actor=alice tenant=tenant-a resource=r1 request=req-1"
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
    },
    {
        "doc_id": "trace.incomplete_window",
        "kind": "trace",
        "family": "audit",
        "authority": "observation",
        "title": "Incomplete capture window",
        "body": (
            "write_t=0 audit_t=1 deadline_offset=2 capture_complete_through=0 "
            "actor=alice tenant=tenant-a resource=r1 request=req-1"
        ),
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
    },
    {
        "doc_id": "trace.wrong_tenant",
        "kind": "trace",
        "family": "tenant",
        "authority": "observation",
        "title": "Tenant-b audit for a tenant-a write",
        "body": (
            "write identity actor=alice tenant=tenant-a resource=r1; "
            "audit identity actor=alice tenant=tenant-b resource=r1. Identities do not join."
        ),
        "identity": {"tenant": "tenant-b", "actor": "alice", "resource": "r1"},
    },
    {
        "doc_id": "frame.obligation_deontic",
        "kind": "frame",
        "family": "protected_write",
        "authority": "ontology",
        "title": "Obligation frame: forbidden unless approved",
        "body": (
            "Deontic frame slots: bearer=actor, object=resource, modality=forbidden, "
            "unless=prior-approval. Frame selection is not a human-validated label."
        ),
        "identity": {},
    },
]

# Retrieval graph: import/implements/observes/controls. Not usefulness.
POLICY_EDGES = [
    ("policy.protected_write", "controls", "impl.guarded_write"),
    ("policy.protected_write", "violated_by", "impl.unguarded_write"),
    ("policy.protected_write", "cites", "frame.obligation_deontic"),
    ("policy.audit_window", "observed_by", "trace.timely_audit"),
    ("policy.audit_window", "observed_by", "trace.delayed_audit"),
    ("policy.audit_window", "observed_by", "trace.incomplete_window"),
    ("policy.tenant_isolation", "observed_by", "trace.wrong_tenant"),
    ("impl.guarded_write", "implements", "policy.protected_write"),
    ("impl.unguarded_write", "implements", "policy.protected_write"),
]

# Independent relevance: controlling source / named-family definition.
# Authored before scoring; not derived from BM25, vectors, or import overlap.
RELEVANT_IDS = {
    "q.protected_write_rule": [
        "policy.protected_write",
        "policy.protected_write_paraphrase",
        "impl.guarded_write",
    ],
    "q.audit_deadline": [
        "policy.audit_window",
        "trace.timely_audit",
        "trace.delayed_audit",
    ],
    "q.tenant_join": [
        "policy.tenant_isolation",
        "trace.wrong_tenant",
    ],
    "q.emergency_override": [
        "policy.emergency_exception",
    ],
    "q.nat_add_identity": ["thm.Nat.add_comm", "thm.Nat.add_assoc", "thm.Nat.add_zero"],
    "q.list_concat_length": [
        "thm.List.length_append",
        "thm.List.append_nil",
        "thm.List.append_assoc",
    ],
    "q.group_inverse": [
        "thm.Group.mul_left_inv",
        "thm.Group.inv_inv",
        "thm.Group.mul_one",
    ],
    "g.List.length_append": [
        "thm.List.length_append",
        "thm.List.append_nil",
        "thm.List.append_assoc",
        "thm.List.reverse_append",
        "thm.List.map_append",
    ],
    "g.Group.inv_inv": [
        "thm.Group.inv_inv",
        "thm.Group.mul_left_inv",
        "thm.Group.mul_one",
        "thm.Group.mul_assoc",
    ],
    "g.Nat.add_assoc": ["thm.Nat.add_comm", "thm.Nat.add_assoc", "thm.Nat.add_zero"],
    "g.Set.union_assoc": [
        "thm.Set.union_comm",
        "thm.Set.union_assoc",
        "thm.Set.subset_union_left",
    ],
    "g.Order.le_trans": ["thm.Order.le_refl", "thm.Order.le_trans"],
}

# Independent usefulness / admitted-premise labels (schematic proof or
# grounding-admitted supporting sources). Distinct from relevance families
# and from import-overlap proxy.
USEFUL_IDS = {
    "q.protected_write_rule": [
        "policy.protected_write",
        "policy.protected_write_paraphrase",
        "impl.guarded_write",
    ],
    "q.audit_deadline": ["policy.audit_window"],
    "q.tenant_join": ["policy.tenant_isolation"],
    "q.emergency_override": ["policy.emergency_exception"],
    "q.nat_add_identity": ["thm.Nat.add_comm", "thm.Nat.add_zero"],
    "q.list_concat_length": [
        "thm.List.length_append",
        "thm.List.append_nil",
        "thm.Nat.add_zero",
        "thm.Nat.add_assoc",
    ],
    "q.group_inverse": ["thm.Group.mul_left_inv", "thm.Group.mul_one", "thm.Group.mul_assoc"],
    "g.List.length_append": [
        "thm.List.append_nil",
        "thm.List.append_assoc",
        "thm.Nat.add_comm",
        "thm.Nat.add_assoc",
        "thm.Nat.add_zero",
    ],
    "g.Group.inv_inv": [
        "thm.Group.mul_left_inv",
        "thm.Group.mul_one",
        "thm.Group.mul_assoc",
    ],
    "g.Nat.add_assoc": ["thm.Nat.add_comm", "thm.Nat.add_zero"],
    "g.Set.union_assoc": ["thm.Set.union_comm", "thm.Set.subset_union_left"],
    "g.Order.le_trans": ["thm.Order.le_refl"],
}

QUERIES = [
    {
        "query_id": "q.protected_write_rule",
        "role": "retrieval",
        "goal_kind": "rule",
        "allows_exception": False,
        "family": "protected_write",
        "title": "When may a protected resource be written?",
        "text": "When may a protected resource be written? Prior approval for actor tenant resource.",
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
        "seeds": ["protected", "write", "approval", "policy.protected_write"],
    },
    {
        "query_id": "q.audit_deadline",
        "role": "retrieval",
        "goal_kind": "observation",
        "allows_exception": False,
        "family": "audit",
        "title": "Must a write be audited within a bounded window?",
        "text": "Must a write be audited within a bounded window? deadline_offset capture complete.",
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
        "seeds": ["audit", "deadline", "policy.audit_window"],
    },
    {
        "query_id": "q.tenant_join",
        "role": "retrieval",
        "goal_kind": "rule",
        "allows_exception": False,
        "family": "tenant",
        "title": "Which records join on tenant identity?",
        "text": "Which records join on tenant identity? tenant-a versus tenant-b audit.",
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
        "seeds": ["tenant", "identity", "policy.tenant_isolation"],
    },
    {
        "query_id": "q.emergency_override",
        "role": "retrieval",
        "goal_kind": "exception",
        "allows_exception": True,
        "family": "protected_write",
        "title": "When does an emergency override permit an unapproved protected write?",
        "text": "When does an emergency override permit an unapproved protected write? incident commander.",
        "identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1"},
        "seeds": ["emergency", "exception", "policy.emergency_exception"],
    },
    {
        "query_id": "q.nat_add_identity",
        "role": "retrieval",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "nat_add",
        "title": "Addition of natural numbers is commutative",
        "text": "Addition of natural numbers is commutative. Nat.add a b equals Nat.add b a.",
        "identity": {},
        "seeds": ["Nat.add", "add_comm", "thm.Nat.add_comm"],
    },
    {
        "query_id": "q.list_concat_length",
        "role": "retrieval",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "list",
        "title": "Length of concatenated lists",
        "text": "The length of concatenated lists is the sum of lengths. List.length append Nat.add.",
        "identity": {},
        "seeds": ["List.length", "append", "thm.List.length_append"],
    },
    {
        "query_id": "q.group_inverse",
        "role": "retrieval",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "group",
        "title": "Left inverse and double inverse in a group",
        "text": "Left inverse and double inverse in a group. Group.inv Group.mul Group.one.",
        "identity": {},
        "seeds": ["Group.inv", "mul_left_inv", "thm.Group.mul_left_inv"],
    },
    {
        "query_id": "g.List.length_append",
        "role": "premise_goal",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "list",
        "title": "List.length_append",
        "text": "theorem length_append : forall xs ys : List Nat, List.length (List.append xs ys) = Nat.add (List.length xs) (List.length ys)",
        "identity": {},
        "seeds": ["List.length_append", "thm.List.length_append"],
        "goal_theorem_id": "List.length_append",
    },
    {
        "query_id": "g.Group.inv_inv",
        "role": "premise_goal",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "group",
        "title": "Group.inv_inv",
        "text": "theorem inv_inv : forall a : Group, Group.inv (Group.inv a) = a",
        "identity": {},
        "seeds": ["Group.inv_inv", "thm.Group.inv_inv"],
        "goal_theorem_id": "Group.inv_inv",
    },
    {
        "query_id": "g.Nat.add_assoc",
        "role": "premise_goal",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "nat_add",
        "title": "Nat.add_assoc",
        "text": "theorem add_assoc : forall a b c : Nat, Nat.add (Nat.add a b) c = Nat.add a (Nat.add b c)",
        "identity": {},
        "seeds": ["Nat.add_assoc", "thm.Nat.add_assoc"],
        "goal_theorem_id": "Nat.add_assoc",
    },
    {
        "query_id": "g.Set.union_assoc",
        "role": "premise_goal",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "set",
        "title": "Set.union_assoc",
        "text": "theorem union_assoc : forall a b c : Set Nat, Set.union (Set.union a b) c = Set.union a (Set.union b c)",
        "identity": {},
        "seeds": ["Set.union_assoc", "thm.Set.union_assoc"],
        "goal_theorem_id": "Set.union_assoc",
    },
    {
        "query_id": "g.Order.le_trans",
        "role": "premise_goal",
        "goal_kind": "theorem",
        "allows_exception": False,
        "family": "order",
        "title": "Order.le_trans",
        "text": "theorem le_trans : forall a b c : Order, Order.le a b -> Order.le b c -> Order.le a c",
        "identity": {},
        "seeds": ["Order.le_trans", "thm.Order.le_trans"],
        "goal_theorem_id": "Order.le_trans",
    },
]


class HarnessError(ValueError):
    """Raised when the frozen pool or measurement contract is violated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise HarnessError("canonical JSON requires finite numeric values") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [canonical_dumps(row) + "\n" for row in rows]
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text("".join(lines), encoding="utf-8")
    temporary.replace(path)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def extract_symbols(statement: str) -> frozenset[str]:
    symbols = set()
    for match in IDENTIFIER_RE.finditer(statement or ""):
        token = match.group(0)
        if len(token) <= 1:
            continue
        if token.lower() in STOPWORDS:
            continue
        symbols.add(token.lower())
    return frozenset(symbols)


def extract_types(statement: str) -> frozenset[str]:
    types = set()
    for match in IDENTIFIER_RE.finditer(statement or ""):
        token = match.group(0)
        if len(token) <= 1 or token.lower() in STOPWORDS:
            continue
        if token[0].isupper():
            types.add(token)
    return frozenset(types)


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return list(vector)
    return [value / norm for value in vector]


def dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def encode_hashed_trigrams(text: str, dimension: int = VECTOR_DIM, n: int = CHAR_NGRAM) -> list[float]:
    vector = [0.0] * dimension
    padded = f"^{text.lower()}$"
    if len(padded) < n:
        padded = padded.ljust(n, "_")
    for index in range(len(padded) - n + 1):
        gram = padded[index:index + n]
        digest = hashlib.sha256(gram.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    return l2_normalize(vector)


class ExactInnerProductIndex:
    """Brute-force IndexFlatIP equivalent. Scores are actual inner products."""

    def __init__(self, dimension: int):
        self.dimension = dimension
        self.ids: list[str] = []
        self.vectors: list[list[float]] = []

    @property
    def ntotal(self) -> int:
        return len(self.ids)

    def add(self, doc_id: str, vector: Sequence[float]) -> None:
        if len(vector) != self.dimension:
            raise HarnessError(f"vector dimension {len(vector)} != {self.dimension}")
        self.ids.append(doc_id)
        self.vectors.append([float(value) for value in vector])

    def search(self, query: Sequence[float], top_k: int) -> list[tuple[str, float]]:
        if len(query) != self.dimension:
            raise HarnessError("query dimension mismatch")
        scored = []
        for doc_id, vector in zip(self.ids, self.vectors):
            scored.append((doc_id, float(dot(query, vector))))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_k]


def bm25_idf(n_docs: int, df: int) -> float:
    return math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)


def build_bm25(documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    postings: dict[str, dict[str, float]] = defaultdict(dict)
    lengths: dict[str, int] = {}
    for document in documents:
        title_tokens = tokenize(document["title"])
        body_tokens = tokenize(document["body"])
        tf: dict[str, float] = defaultdict(float)
        for token in title_tokens:
            tf[token] += TITLE_TF_WEIGHT
        for token in body_tokens:
            tf[token] += BODY_TF_WEIGHT
        lengths[document["doc_id"]] = max(1, len(title_tokens) + len(body_tokens))
        for token, weight in tf.items():
            postings[token][document["doc_id"]] = weight
    avgdl = sum(lengths.values()) / max(1, len(lengths))
    n_docs = len(documents)
    idf = {token: bm25_idf(n_docs, len(doc_tf)) for token, doc_tf in postings.items()}
    return {
        "schema": "bm25-postings/v1",
        "k1": BM25_K1,
        "b": BM25_B,
        "title_tf_weight": TITLE_TF_WEIGHT,
        "body_tf_weight": BODY_TF_WEIGHT,
        "formula": "idf(t)*tf*(k1+1)/(tf+k1*(1-b+b*|d|/avgdl))",
        "n_docs": n_docs,
        "avgdl": avgdl,
        "postings": {token: dict(doc_tf) for token, doc_tf in postings.items()},
        "idf": idf,
        "lengths": lengths,
        "scoring_branch": "title_body_weighted_okapi",
    }


def bm25_search(index: Mapping[str, Any], query_text: str, top_k: int) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    k1 = index["k1"]
    b = index["b"]
    avgdl = index["avgdl"]
    for token in tokenize(query_text):
        doc_tf = index["postings"].get(token)
        if not doc_tf:
            continue
        idf = index["idf"][token]
        for doc_id, tf in doc_tf.items():
            length = index["lengths"][doc_id]
            denom = tf + k1 * (1.0 - b + b * length / avgdl)
            scores[doc_id] += idf * (tf * (k1 + 1.0) / denom)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:top_k]


def build_documents() -> list[dict[str, Any]]:
    documents = []
    for item in POLICY_DOCUMENTS:
        doc = dict(item)
        doc["imports"] = []
        doc["theorem_id"] = None
        doc["split"] = "constructed_control"
        doc["fixture"] = False
        documents.append(doc)
    for item in THEOREMS:
        doc_id = f"thm.{item['theorem_id']}"
        documents.append({
            "doc_id": doc_id,
            "kind": "theorem",
            "family": item["family"],
            "authority": "fixture_theorem",
            "title": item["theorem_id"],
            "body": item["statement"],
            "identity": {},
            "imports": list(item["imports"]),
            "theorem_id": item["theorem_id"],
            "split": "constructed_control",
            "fixture": True,
        })
    documents.sort(key=lambda row: row["doc_id"])
    if len({row["doc_id"] for row in documents}) != len(documents):
        raise HarnessError("duplicate document ids")
    return documents


def build_graph(documents: Sequence[Mapping[str, Any]]) -> dict[str, list[tuple[str, str]]]:
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for source, relation, target in POLICY_EDGES:
        adjacency[source].append((relation, target))
        adjacency[target].append((f"inv:{relation}", source))
    by_import: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        for module in document.get("imports") or []:
            by_import[module].append(document["doc_id"])
    for module, members in by_import.items():
        for left in members:
            for right in members:
                if left == right:
                    continue
                adjacency[left].append(("shares_import", right))
    for key in adjacency:
        adjacency[key] = sorted(set(adjacency[key]))
    return dict(adjacency)


def graph_search(
    query: Mapping[str, Any],
    documents: Sequence[Mapping[str, Any]],
    adjacency: Mapping[str, Sequence[tuple[str, str]]],
    top_k: int,
) -> list[tuple[str, float]]:
    doc_ids = {document["doc_id"] for document in documents}
    seeds = []
    query_tokens = set(tokenize(query["text"] + " " + query["title"]))
    for seed in query.get("seeds") or []:
        if seed in doc_ids:
            seeds.append(seed)
    for document in documents:
        haystack = set(tokenize(document["doc_id"] + " " + document["title"]))
        if haystack & query_tokens and document["doc_id"] not in seeds:
            if document["doc_id"].split(".")[-1].lower() in query_tokens or any(
                token in document["doc_id"].lower() for token in query_tokens if len(token) > 3
            ):
                seeds.append(document["doc_id"])
    if query.get("goal_theorem_id"):
        goal_id = f"thm.{query['goal_theorem_id']}"
        if goal_id in doc_ids and goal_id not in seeds:
            seeds.append(goal_id)
    scores: dict[str, float] = {}
    frontier = list(dict.fromkeys(seeds))
    for seed in frontier:
        scores[seed] = max(scores.get(seed, 0.0), 1.0)
    for _hop in range(GRAPH_HOPS):
        nxt = []
        for node in frontier:
            for relation, neighbor in adjacency.get(node, []):
                weight = 0.5 if relation.startswith("inv:") or relation == "shares_import" else 0.7
                new_score = scores[node] * weight
                if new_score > scores.get(neighbor, 0.0):
                    scores[neighbor] = new_score
                    nxt.append(neighbor)
        frontier = list(dict.fromkeys(nxt))
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:top_k]


def rrf_fuse(rankings: Mapping[str, Sequence[tuple[str, float]]], top_k: int) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranked in rankings.values():
        for rank, (doc_id, _score) in enumerate(ranked, start=1):
            scores[doc_id] += 1.0 / (RRF_K + rank)
    fused = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return fused[:top_k]


def admit_document(query: Mapping[str, Any], document: Mapping[str, Any]) -> tuple[bool, str]:
    if query.get("goal_theorem_id") and document.get("theorem_id") == query["goal_theorem_id"]:
        return False, "self_reference"
    qid = query.get("identity") or {}
    did = document.get("identity") or {}
    for key in ("tenant", "actor", "resource"):
        if key in qid and key in did and qid[key] != did[key]:
            return False, "identity_mismatch"
    if document.get("authority") == "exception" and not query.get("allows_exception"):
        return False, "inapplicable_exception"
    if document.get("kind") == "trace" and query.get("goal_kind") in {"rule", "theorem"}:
        return False, "observation_is_not_premise"
    if document.get("kind") == "frame" and query.get("goal_kind") in {"theorem", "rule"}:
        return False, "ontology_frame_not_admitted_premise"
    if document.get("kind") == "implementation" and query.get("goal_kind") == "theorem":
        return False, "code_not_theorem_premise"
    if document.get("kind") == "theorem" and query.get("goal_kind") in {"rule", "exception", "observation"}:
        return False, "theorem_not_policy_premise"
    return True, "admitted"


def expand_imports_one_hop(goal_imports: frozenset[str], documents: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    extra = set(goal_imports)
    for document in documents:
        imports = frozenset(document.get("imports") or [])
        if imports & goal_imports:
            extra |= imports
    return frozenset(extra)


def learned_digest(weights: Mapping[str, float], bias: float) -> str:
    payload = {
        "bias": bias,
        "feature_names": list(GRAPH_SELECTOR_FEATURE_NAMES),
        "feature_version": GRAPH_SELECTOR_FEATURE_VERSION,
        "model_id": GRAPH_SELECTOR_MODEL_ID,
        "weights": {key: weights[key] for key in sorted(weights)},
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def sigmoid(value: float) -> float:
    clamped = max(-60.0, min(60.0, value))
    return 1.0 / (1.0 + math.exp(-clamped))


def score_baseline(goal_statement: str, goal_imports: Sequence[str], goal_theorem_id: str | None,
                   candidate: Mapping[str, Any], expanded_goal_imports: frozenset[str]) -> dict[str, float]:
    goal_symbols = extract_symbols(goal_statement)
    goal_types = extract_types(goal_statement)
    goal_imp = frozenset(goal_imports)
    cand_symbols = extract_symbols(candidate["body"])
    cand_types = extract_types(candidate["body"])
    cand_imp = frozenset(candidate.get("imports") or [])
    symbol_score = jaccard(goal_symbols, cand_symbols)
    type_score = jaccard(goal_types, cand_types)
    import_score = jaccard(goal_imp, cand_imp)
    graph_score = jaccard(cand_imp, expanded_goal_imports)
    total = (
        BASELINE_WEIGHTS["symbol_weight"] * symbol_score
        + BASELINE_WEIGHTS["type_weight"] * type_score
        + BASELINE_WEIGHTS["import_weight"] * import_score
        + BASELINE_WEIGHTS["graph_weight"] * graph_score
    )
    return {
        "score": total,
        "symbol_score": symbol_score,
        "type_score": type_score,
        "import_score": import_score,
        "graph_score": graph_score,
        "goal_symbol_count": float(len(goal_symbols)),
        "candidate_symbol_count": float(len(cand_symbols)),
        "shared_symbol_count": float(len(goal_symbols & cand_symbols)),
        "candidate_import_count": float(len(cand_imp)),
        "one_hop_neighbor_count": float(len(cand_imp & expanded_goal_imports)),
    }


def score_graph_selector(features: Mapping[str, float]) -> float:
    total = GRAPH_SELECTOR_BIAS
    for name in GRAPH_SELECTOR_FEATURE_NAMES:
        total += GRAPH_SELECTOR_WEIGHTS.get(name, 0.0) * features.get(name, 0.0)
    return sigmoid(total)


def recall_at_k(ranked_ids: Sequence[str], gold: set[str], k: int) -> float | None:
    if not gold:
        return None
    return sum(1 for doc_id in ranked_ids[:k] if doc_id in gold) / len(gold)


def precision_at_k(ranked_ids: Sequence[str], gold: set[str], k: int) -> float:
    window = ranked_ids[:k]
    if not window:
        return 0.0
    return sum(1 for doc_id in window if doc_id in gold) / len(window)


def reciprocal_rank(ranked_ids: Sequence[str], gold: set[str]) -> float:
    for rank, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in gold:
            return 1.0 / rank
    return 0.0


def average_precision(ranked_ids: Sequence[str], gold: set[str], k: int) -> float | None:
    if not gold:
        return None
    hits = 0
    total = 0.0
    for rank, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in gold:
            hits += 1
            total += hits / rank
    return total / len(gold)


def token_count(document: Mapping[str, Any]) -> int:
    return max(1, len(tokenize(document["title"])) + len(tokenize(document["body"])))


def fill_to_budget(ranked: Sequence[tuple[str, float]], documents: Mapping[str, Mapping[str, Any]],
                   exclude: set[str]) -> list[tuple[str, float]]:
    selected = []
    used = 0
    for doc_id, score in ranked:
        if doc_id in exclude:
            continue
        cost = token_count(documents[doc_id])
        if used + cost > TOKEN_BUDGET and selected:
            break
        selected.append((doc_id, score))
        used += cost
        if len(selected) >= max(TOP_KS):
            break
    return selected


def import_overlap_ids(query: Mapping[str, Any], documents: Sequence[Mapping[str, Any]]) -> set[str]:
    goal_id = query.get("goal_theorem_id")
    if not goal_id:
        return set()
    goal = next((row for row in documents if row.get("theorem_id") == goal_id), None)
    if goal is None:
        return set()
    goal_imports = set(goal.get("imports") or [])
    hits = set()
    for document in documents:
        if document.get("theorem_id") in {None, goal_id}:
            continue
        if goal_imports & set(document.get("imports") or []):
            hits.add(document["doc_id"])
    return hits


def probe_backend() -> dict[str, Any]:
    report: dict[str, Any] = {
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "path": os.environ.get("PATH", ""),
        "home": os.environ.get("HOME", ""),
    }
    for name in ("faiss", "numpy", "torch", "transformers", "sentence_transformers", "sklearn", "spacy"):
        try:
            module = __import__(name)
            report[name] = {
                "available": True,
                "version": getattr(module, "__version__", None),
                "file": getattr(module, "__file__", None),
            }
        except Exception as exc:
            chain = []
            current: BaseException | None = exc
            seen: set[int] = set()
            while current is not None and id(current) not in seen:
                seen.add(id(current))
                chain.append(str(current))
                current = current.__cause__ or current.__context__
            blob = "\n".join(chain)
            if "libblas.so.3" in blob:
                summary = "NumPy C-extensions failed: libblas.so.3 is absent from the sealed environment"
            else:
                summary = str(exc).splitlines()[0][:300]
            report[name] = {
                "available": False,
                "error_type": type(exc).__name__,
                "error": summary,
            }
    faiss_ok = bool(report["faiss"]["available"] and report["numpy"]["available"])
    report["selected_vector_backend"] = "faiss.IndexFlatIP" if faiss_ok else VECTOR_BACKEND_ID
    report["mock_vectors"] = False
    report["declared_only_cli"] = False
    report["thin_client_vector_dispatch"] = "not_executed"
    report["minilm_encoder"] = {
        "available": False,
        "reason": "sealed HOME has no HuggingFace cache; transformers/torch unavailable",
    }
    return report


def inspect_sources(repo_root: Path) -> dict[str, Any]:
    rows = {}
    for key, meta in INSPECTED_SOURCES.items():
        path = repo_root / meta["path"]
        record = dict(meta)
        record["sha256"] = sha256_file(path)
        record["bytes"] = path.stat().st_size
        if key == "faiss_store.py":
            text = path.read_text(encoding="utf-8")
            record["contains_mock_faiss"] = "class MockFaiss" in text
            record["mentions_ensure_module"] = "ensure_module" in text
        rows[key] = record
    return rows


def load_upstream_counts(repo_root: Path) -> dict[str, Any]:
    corpus = json.loads((repo_root / "papers/completion/autoformalization/data/corpus_manifest.json").read_text())
    splits = json.loads((repo_root / "papers/completion/autoformalization/data/splits.json").read_text())
    return {
        "status": "unavailable_for_retrieval_evaluation",
        "reason": (
            "AF-004 natural source bodies are owner-only; AF-005 packets remain "
            "pending_independent_review without gold values; final-test lock forbids retrieval tuning."
        ),
        "corpus_manifest_sha256": sha256_file(repo_root / "papers/completion/autoformalization/data/corpus_manifest.json"),
        "splits_sha256": sha256_file(repo_root / "papers/completion/autoformalization/data/splits.json"),
        "natural_source_units": {
            "train": corpus["counts_by_split"]["train"]["natural_source_units"],
            "selection": corpus["counts_by_split"]["selection"]["natural_source_units"],
            "fixed_canary": corpus["counts_by_split"]["fixed_canary"]["natural_source_units"],
            "final_test": corpus["counts_by_split"]["final_test"]["natural_source_units"],
        },
        "annotation_packets_evaluation_eligible": False,
        "splits_assignment_seed": splits["assignment"]["seed"],
    }


def _label_provenance(task: str, family: str) -> dict[str, Any]:
    return {
        "family": family,
        "independent_of_retrieval_scores": True,
        "independent_of_other_label_task": task != "proxy_import_overlap",
        "derived_from_import_overlap": task == "proxy_import_overlap",
        "human_adjudication": False,
        "annotator_role": "constructed_protocol_before_scoring",
    }


def build_judgments(documents: Sequence[Mapping[str, Any]], queries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Emit compact qrels: one coverage row per label task plus positives.

    The generator still walks the full corpus/query product. Unlisted pairs
    are implicit negatives. Proxy rows exist only for premise goals.
    """
    doc_ids = [document["doc_id"] for document in documents]
    doc_id_set = set(doc_ids)
    families = {
        "relevance": "citation_and_controlling_source/v1",
        "admitted_premise_usefulness": "explicit_dependency_or_admission/v1",
        "proxy_import_overlap": "shared_import_proximity_proxy/v1",
    }
    positives: dict[str, list[tuple[str, str]]] = {
        "relevance": [],
        "admitted_premise_usefulness": [],
        "proxy_import_overlap": [],
    }
    n_pairs = {
        "relevance": 0,
        "admitted_premise_usefulness": 0,
        "proxy_import_overlap": 0,
    }
    n_queries_by_task = {
        "relevance": len(queries),
        "admitted_premise_usefulness": len(queries),
        "proxy_import_overlap": 0,
    }
    for query in queries:
        relevant = set(RELEVANT_IDS[query["query_id"]])
        useful = set(USEFUL_IDS[query["query_id"]])
        unknown = (relevant | useful) - doc_id_set
        if unknown:
            raise HarnessError(f"label refers to missing documents: {unknown}")
        proxy = import_overlap_ids(query, documents) if query.get("role") == "premise_goal" else set()
        for doc_id in doc_ids:
            n_pairs["relevance"] += 1
            n_pairs["admitted_premise_usefulness"] += 1
            if doc_id in relevant:
                positives["relevance"].append((query["query_id"], doc_id))
            if doc_id in useful:
                positives["admitted_premise_usefulness"].append((query["query_id"], doc_id))
            if query.get("role") == "premise_goal":
                n_pairs["proxy_import_overlap"] += 1
                if doc_id in proxy:
                    positives["proxy_import_overlap"].append((query["query_id"], doc_id))
        if query.get("role") == "premise_goal":
            n_queries_by_task["proxy_import_overlap"] += 1
    if n_pairs["relevance"] != len(doc_ids) * len(queries):
        raise HarnessError("relevance coverage is not the full corpus/query product")
    rows: list[dict[str, Any]] = []
    for task, family in families.items():
        provenance = _label_provenance(task, family)
        rows.append({
            "schema": SCHEMA_JUDGMENT,
            "kind": "coverage",
            "label_task": task,
            "n_documents": len(doc_ids),
            "n_queries": n_queries_by_task[task],
            "n_pairs": n_pairs[task],
            "n_positives": len(positives[task]),
            "implicit_negatives": True,
            "negative_encoding": "implicit_zero",
            "full_corpus_query_product": True,
            "provenance": provenance,
        })
        for query_id, doc_id in positives[task]:
            rows.append({
                "schema": SCHEMA_JUDGMENT,
                "query_id": query_id,
                "document_id": doc_id,
                "label_task": task,
                "label": 1,
                "provenance": provenance,
            })
    return rows


def ranked_payload(ranked: Sequence[tuple[str, float]], documents: Mapping[str, Mapping[str, Any]],
                   query: Mapping[str, Any], k: int) -> list[dict[str, Any]]:
    rows = []
    for rank, (doc_id, score) in enumerate(ranked[:k], start=1):
        document = documents[doc_id]
        admitted, reason = admit_document(query, document)
        rows.append({
            "rank": rank,
            "document_id": doc_id,
            "score": finite_round(score),
            "admitted": admitted,
            "admission_reason": reason,
        })
    return rows


def finite_round(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def mean(values: Sequence[float | None]) -> float | None:
    finite = [value for value in values if value is not None]
    if not finite:
        return None
    return finite_round(sum(finite) / len(finite))


def run(repo_root: Path, paper_root: Path) -> dict[str, Any]:
    started = utc_now()
    t0 = time.perf_counter()
    documents = build_documents()
    queries = list(QUERIES)
    doc_by_id = {row["doc_id"]: row for row in documents}
    query_by_id = {row["query_id"]: row for row in queries}
    if set(query_by_id) != set(RELEVANT_IDS) or set(query_by_id) != set(USEFUL_IDS):
        raise HarnessError("query ids must match both independent label maps")
    judgments = build_judgments(documents, queries)
    bm25_index = build_bm25(documents)
    backend = probe_backend()
    inspected = inspect_sources(repo_root)
    upstream = load_upstream_counts(repo_root)
    vector_index = ExactInnerProductIndex(VECTOR_DIM)
    encodings = {}
    for document in documents:
        text = document["title"] + "\n" + document["body"]
        vector = encode_hashed_trigrams(text)
        encodings[document["doc_id"]] = vector
        vector_index.add(document["doc_id"], vector)
    if vector_index.ntotal != len(documents):
        raise HarnessError("vector index did not ingest the full corpus")
    sample_scores = [dot(encodings[documents[0]["doc_id"]], encodings[row["doc_id"]]) for row in documents]
    if len(set(round(score, 6) for score in sample_scores)) <= 1:
        raise HarnessError("vector scores are degenerate; refusing mock-constant ranks")
    adjacency = build_graph(documents)
    selector_digest = learned_digest(GRAPH_SELECTOR_WEIGHTS, GRAPH_SELECTOR_BIAS)
    expected_digest = "sha256:ad48f4b45a454bc41b63bef17ed7b4c1695b8c21ab118c1ec16766f21a14aa75"
    if selector_digest != expected_digest:
        raise HarnessError(f"hand-authored selector digest {selector_digest} != fixture {expected_digest}")

    retrieval_rows = []
    for query in queries:
        query_text = query["title"] + " " + query["text"]
        lexical = bm25_search(bm25_index, query_text, max(TOP_KS))
        qvec = encode_hashed_trigrams(query_text)
        vector_hits = vector_index.search(qvec, max(TOP_KS))
        graph_hits = graph_search(query, documents, adjacency, max(TOP_KS))
        combined = rrf_fuse(
            {"lexical_bm25": lexical, "vector_exact_ip": vector_hits, "graph_walk": graph_hits},
            max(TOP_KS),
        )
        routes = {
            "lexical_bm25": lexical,
            "vector_exact_ip": vector_hits,
            "graph_walk": graph_hits,
            "combined_rrf": combined,
        }
        relevant = set(RELEVANT_IDS[query["query_id"]])
        useful = set(USEFUL_IDS[query["query_id"]])
        for route_id, ranked in routes.items():
            for k in TOP_KS:
                ranked_ids = [doc_id for doc_id, _score in ranked[:k]]
                hits = ranked_payload(ranked, doc_by_id, query, k)
                admitted_ids = [row["document_id"] for row in hits if row["admitted"]]
                admitted_useful = [doc_id for doc_id in admitted_ids if doc_id in useful]
                retrieval_rows.append({
                    "schema": SCHEMA_RETRIEVAL,
                    "record_id": f"{query['query_id']}:{route_id}:k{k}",
                    "query_id": query["query_id"],
                    "query_role": query["role"],
                    "route_id": route_id,
                    "k": k,
                    "corpus_n_documents": len(documents),
                    "query_n": len(queries),
                    "n_relevant": len(relevant),
                    "n_useful": len(useful),
                    "ranked": hits,
                    "metrics": {
                        "relevance_recall_at_k": finite_round(recall_at_k(ranked_ids, relevant, k)),
                        "relevance_precision_at_k": finite_round(precision_at_k(ranked_ids, relevant, k)),
                        "relevance_mrr": finite_round(reciprocal_rank(ranked_ids, relevant)),
                        "relevance_ap_at_k": finite_round(average_precision(ranked_ids, relevant, k)),
                        "admitted_premise_yield_at_k": finite_round(
                            (len(admitted_useful) / len(useful)) if useful else None
                        ),
                        "admitted_useful_count": len(admitted_useful),
                        "admitted_count": len(admitted_ids),
                    },
                    "label_tasks": {
                        "relevance": "citation_and_controlling_source/v1",
                        "admitted_premise_usefulness": "explicit_dependency_or_admission/v1",
                    },
                    "execution_status": "measured",
                    "result_kind": "bounded_observation",
                    "vector_backend": VECTOR_BACKEND_ID if route_id.startswith("vector") or route_id == "combined_rrf" else None,
                    "mock_vectors": False,
                    "declared_only_cli": False,
                })

    premise_rows = []
    theorem_docs = [row for row in documents if row["kind"] == "theorem"]
    for query in queries:
        if query["role"] != "premise_goal":
            continue
        goal_id = query["goal_theorem_id"]
        goal_doc = doc_by_id[f"thm.{goal_id}"]
        expanded = expand_imports_one_hop(frozenset(goal_doc["imports"]), theorem_docs)
        useful = set(USEFUL_IDS[query["query_id"]])
        proxy = import_overlap_ids(query, documents)
        scored = []
        for candidate in theorem_docs:
            if candidate["theorem_id"] == goal_id:
                continue
            features = score_baseline(query["text"], goal_doc["imports"], goal_id, candidate, expanded)
            graph_score = score_graph_selector(features)
            scored.append((candidate["doc_id"], features, graph_score))
        baseline_ranked = sorted(scored, key=lambda item: (-item[1]["score"], item[0]))
        graph_ranked = sorted(scored, key=lambda item: (-item[2], item[0]))
        for selector_id, ordered, trained in (
            ("deterministic_baseline", [(doc_id, feat["score"]) for doc_id, feat, _gs in baseline_ranked], False),
            ("hand_authored_graph_selector", [(doc_id, gs) for doc_id, _feat, gs in graph_ranked], False),
        ):
            for k in TOP_KS:
                ranked_ids = [doc_id for doc_id, _score in ordered[:k]]
                hits = []
                for rank, (doc_id, score) in enumerate(ordered[:k], start=1):
                    document = doc_by_id[doc_id]
                    admitted, reason = admit_document(query, document)
                    hits.append({
                        "rank": rank,
                        "document_id": doc_id,
                        "score": finite_round(score),
                        "admitted": admitted,
                        "admission_reason": reason,
                    })
                admitted_useful = [
                    row["document_id"] for row in hits if row["admitted"] and row["document_id"] in useful
                ]
                premise_rows.append({
                    "schema": SCHEMA_PREMISE,
                    "record_id": f"{query['query_id']}:{selector_id}:k{k}",
                    "query_id": query["query_id"],
                    "goal_theorem_id": goal_id,
                    "selector_id": selector_id,
                    "k": k,
                    "corpus_n_documents": len(theorem_docs),
                    "query_n": sum(1 for row in queries if row["role"] == "premise_goal"),
                    "n_useful": len(useful),
                    "n_proxy_positive": len(proxy),
                    "ranked": hits,
                    "metrics": {
                        "usefulness_recall_at_k": finite_round(recall_at_k(ranked_ids, useful, k)),
                        "usefulness_precision_at_k": finite_round(precision_at_k(ranked_ids, useful, k)),
                        "usefulness_mrr": finite_round(reciprocal_rank(ranked_ids, useful)),
                        "proxy_import_overlap_recall_at_k": finite_round(recall_at_k(ranked_ids, proxy, k)),
                        "proxy_import_overlap_precision_at_k": finite_round(precision_at_k(ranked_ids, proxy, k)),
                        "admitted_premise_yield_at_k": finite_round(
                            (len(admitted_useful) / len(useful)) if useful else None
                        ),
                    },
                    "weights": (
                        {
                            "symbol_weight": BASELINE_WEIGHTS["symbol_weight"],
                            "type_weight": BASELINE_WEIGHTS["type_weight"],
                            "import_weight": BASELINE_WEIGHTS["import_weight"],
                            "graph_weight": BASELINE_WEIGHTS["graph_weight"],
                            "provenance": BASELINE_WEIGHTS["provenance"],
                            "trained": False,
                        } if selector_id == "deterministic_baseline"
                        else {
                            "model_id": GRAPH_SELECTOR_MODEL_ID,
                            "model_digest": selector_digest,
                            "bias": GRAPH_SELECTOR_BIAS,
                            "provenance": "hand_authored_linear_combination",
                            "trained": False,
                            "independent_train_split": None,
                        }
                    ),
                    "label_tasks": {
                        "admitted_premise_usefulness": "explicit_dependency_or_admission/v1",
                        "proxy_import_overlap": "shared_import_proximity_proxy/v1",
                    },
                    "trained_selector_claimed": trained,
                    "execution_status": "measured",
                    "result_kind": "bounded_observation",
                })

    def summarize(rows: Sequence[Mapping[str, Any]], metric_key: str, route_key: str) -> dict[str, Any]:
        grouped: dict[str, list[float | None]] = defaultdict(list)
        for row in rows:
            if row["k"] != 5:
                continue
            grouped[row[route_key]].append(row["metrics"][metric_key])
        return {key: mean(vals) for key, vals in sorted(grouped.items())}

    retrieval_summary = {
        "relevance_recall_at_5": summarize(retrieval_rows, "relevance_recall_at_k", "route_id"),
        "admitted_premise_yield_at_5": summarize(retrieval_rows, "admitted_premise_yield_at_k", "route_id"),
    }
    premise_summary = {
        "usefulness_recall_at_5": summarize(premise_rows, "usefulness_recall_at_k", "selector_id"),
        "proxy_import_overlap_recall_at_5": summarize(premise_rows, "proxy_import_overlap_recall_at_k", "selector_id"),
        "admitted_premise_yield_at_5": summarize(premise_rows, "admitted_premise_yield_at_k", "selector_id"),
    }

    coverage_rows = {row["label_task"]: row for row in judgments if row.get("kind") == "coverage"}
    n_relevance = coverage_rows["relevance"]["n_pairs"]
    n_useful = coverage_rows["admitted_premise_usefulness"]["n_pairs"]
    n_proxy = coverage_rows["proxy_import_overlap"]["n_pairs"]
    if n_relevance != len(documents) * len(queries):
        raise HarnessError("relevance judgments must cover the full corpus/query product")
    if n_useful != len(documents) * len(queries):
        raise HarnessError("usefulness judgments must cover the full corpus/query product")
    n_premise_goals = sum(1 for row in queries if row["role"] == "premise_goal")
    if n_proxy != len(documents) * n_premise_goals:
        raise HarnessError("proxy judgments must cover every premise-goal/document pair")

    rel_pos = {(row["query_id"], row["document_id"]) for row in judgments
               if row.get("kind") != "coverage" and row["label_task"] == "relevance" and row["label"] == 1}
    use_pos = {(row["query_id"], row["document_id"]) for row in judgments
               if row.get("kind") != "coverage" and row["label_task"] == "admitted_premise_usefulness" and row["label"] == 1}
    if rel_pos == use_pos:
        raise HarnessError("relevance and usefulness positive sets must differ")
    if coverage_rows["relevance"]["n_positives"] != len(rel_pos):
        raise HarnessError("relevance coverage n_positives disagrees with listed positives")
    if coverage_rows["admitted_premise_usefulness"]["n_positives"] != len(use_pos):
        raise HarnessError("usefulness coverage n_positives disagrees with listed positives")

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    manifest = {
        "schema": SCHEMA_MANIFEST,
        "task_id": TASK_ID,
        "pool_id": POOL_ID,
        "created_at": started,
        "finished_at": utc_now(),
        "elapsed_ms": elapsed_ms,
        "population": "constructed_control",
        "eligible_natural_held_out": False,
        "corpus": {
            "n_documents": len(documents),
            "n_policy_code_trace_frame": sum(1 for row in documents if row["kind"] != "theorem"),
            "n_theorems": sum(1 for row in documents if row["kind"] == "theorem"),
            "document_ids": [row["doc_id"] for row in documents],
            "sha256": sha256_obj([{"doc_id": row["doc_id"], "body": row["body"]} for row in documents]),
        },
        "queries": {
            "n_queries": len(queries),
            "n_retrieval": sum(1 for row in queries if row["role"] == "retrieval"),
            "n_premise_goals": n_premise_goals,
            "query_ids": [row["query_id"] for row in queries],
            "sha256": sha256_obj([{"query_id": row["query_id"], "text": row["text"]} for row in queries]),
        },
        "judgments": {
            "encoding": "compact_qrels_implicit_negatives/v1",
            "n_file_rows": len(judgments),
            "n_rows": n_relevance + n_useful + n_proxy,
            "n_relevance_pairs": n_relevance,
            "n_usefulness_pairs": n_useful,
            "n_proxy_pairs": n_proxy,
            "n_relevance_positives": len(rel_pos),
            "n_usefulness_positives": len(use_pos),
            "full_corpus_query_relevance": True,
            "full_corpus_query_usefulness": True,
            "independent_label_tasks": [
                "relevance",
                "admitted_premise_usefulness",
            ],
            "proxy_label_task": "proxy_import_overlap",
            "positive_sets_differ": rel_pos != use_pos,
            "human_adjudication": False,
        },
        "budgets": {
            "top_k": list(TOP_KS),
            "token_budget": TOKEN_BUDGET,
            "graph_hops": GRAPH_HOPS,
            "rrf_k": RRF_K,
        },
        "routes": {
            "lexical_bm25": {
                "k1": BM25_K1,
                "b": BM25_B,
                "title_tf_weight": TITLE_TF_WEIGHT,
                "body_tf_weight": BODY_TF_WEIGHT,
                "scoring_branch": "title_body_weighted_okapi",
                "formula": bm25_index["formula"],
            },
            "vector_exact_ip": {
                "backend_id": VECTOR_BACKEND_ID,
                "algorithm": "exact inner product over L2-normalized vectors (IndexFlatIP equivalent)",
                "faiss_library": backend["faiss"],
                "numpy": backend["numpy"],
                "encoder": {
                    "id": ENCODER_ID,
                    "dimension": VECTOR_DIM,
                    "ngram": CHAR_NGRAM,
                    "normalization": "l2",
                    "semantic_minilm": False,
                    "mock": False,
                },
                "ntotal": vector_index.ntotal,
                "mock_vectors": False,
                "declared_only_cli": False,
                "thin_client_vector_subcommand": "not_dispatched",
            },
            "graph_walk": {
                "hops": GRAPH_HOPS,
                "edge_types": sorted({edge[1] for edge in POLICY_EDGES} | {"shares_import"}),
                "n_adjacency_nodes": len(adjacency),
                "usefulness_edges_included": False,
            },
            "combined_rrf": {
                "method": "reciprocal_rank_fusion",
                "rrf_k": RRF_K,
                "trained_fusion": False,
                "components": ["lexical_bm25", "vector_exact_ip", "graph_walk"],
            },
        },
        "selectors": {
            "deterministic_baseline": dict(BASELINE_WEIGHTS),
            "hand_authored_graph_selector": {
                "model_id": GRAPH_SELECTOR_MODEL_ID,
                "feature_version": GRAPH_SELECTOR_FEATURE_VERSION,
                "feature_names": list(GRAPH_SELECTOR_FEATURE_NAMES),
                "weights": dict(GRAPH_SELECTOR_WEIGHTS),
                "bias": GRAPH_SELECTOR_BIAS,
                "model_digest": selector_digest,
                "trained": False,
                "independent_train_split": None,
                "provenance": "hand_authored_linear_combination; matches tests/fixtures/logic/hammers/learned_selector_model.json",
            },
        },
        "unavailable_conditions": {
            "faiss": backend["faiss"],
            "numpy": backend["numpy"],
            "minilm": backend["minilm_encoder"],
            "natural_legal_corpus_retrieval": upstream,
            "trained_selector": {
                "available": False,
                "reason": "No independent train/split artifact; default graph-selector weights remain hand-authored.",
            },
            "claim_narrowing": [
                "No FAISS-library or MiniLM semantic-vector quality claim.",
                "No natural held-out legal/policy retrieval claim over AF-004 final-test units.",
                "No trained premise-selector claim.",
                "Constructed_control recall/yield do not fill Table 13 natural cells.",
            ],
        },
        "inspected_not_imported": inspected,
        "backend_probe": backend,
        "summaries": {
            "retrieval": retrieval_summary,
            "premise_selection": premise_summary,
        },
        "outputs": {
            "judgments": "papers/completion/autoformalization/data/retrieval_judgments.jsonl",
            "retrieval": "papers/completion/autoformalization/runs/retrieval/results.jsonl",
            "premise_selection": "papers/completion/autoformalization/runs/premise_selection/results.jsonl",
            "manifest": "papers/completion/autoformalization/config/retrieval_manifest.json",
        },
    }

    retrieval_rows.append({
        "schema": SCHEMA_RETRIEVAL,
        "record_id": "summary:retrieval",
        "kind": "summary",
        "corpus_n_documents": len(documents),
        "query_n": len(queries),
        "summaries": retrieval_summary,
        "execution_status": "measured",
        "mock_vectors": False,
        "declared_only_cli": False,
    })
    premise_rows.append({
        "schema": SCHEMA_PREMISE,
        "record_id": "summary:premise_selection",
        "kind": "summary",
        "corpus_n_documents": len(theorem_docs),
        "query_n": n_premise_goals,
        "summaries": premise_summary,
        "trained_selector_claimed": False,
        "execution_status": "measured",
        "hand_authored_weights_disclosed": True,
        "proxy_labels_disclosed": True,
        "weights": {
            "deterministic_baseline": dict(BASELINE_WEIGHTS),
            "hand_authored_graph_selector": {
                "weights": dict(GRAPH_SELECTOR_WEIGHTS),
                "bias": GRAPH_SELECTOR_BIAS,
                "model_id": GRAPH_SELECTOR_MODEL_ID,
                "model_digest": selector_digest,
                "provenance": "hand_authored_linear_combination",
                "trained": False,
                "independent_train_split": None,
            },
        },
    })

    paths = {
        "judgments": paper_root / "data" / "retrieval_judgments.jsonl",
        "retrieval": paper_root / "runs" / "retrieval" / "results.jsonl",
        "premise": paper_root / "runs" / "premise_selection" / "results.jsonl",
        "manifest": paper_root / "config" / "retrieval_manifest.json",
    }
    write_jsonl(paths["judgments"], judgments)
    write_jsonl(paths["retrieval"], retrieval_rows)
    write_jsonl(paths["premise"], premise_rows)
    write_json(paths["manifest"], manifest)
    return {
        "n_documents": len(documents),
        "n_queries": len(queries),
        "n_judgments": len(judgments),
        "n_retrieval_rows": len(retrieval_rows),
        "n_premise_rows": len(premise_rows),
        "vector_backend": VECTOR_BACKEND_ID,
        "faiss_available": backend["faiss"]["available"],
        "numpy_available": backend["numpy"]["available"],
        "selector_digest": selector_digest,
        "summaries": {"retrieval": retrieval_summary, "premise_selection": premise_summary},
        "paths": {key: str(path.relative_to(repo_root)) for key, path in paths.items()},
        "elapsed_ms": elapsed_ms,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--paper-root", type=Path, default=PAPER_ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    paper_root = args.paper_root.resolve()
    result = run(repo_root, paper_root)
    print(canonical_dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as exc:
        print(f"AF-017: {exc}", file=sys.stderr)
        raise SystemExit(1)
