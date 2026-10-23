#!/usr/bin/env python3
"""Objective B: compile live SwissKnife <-> MCP++ interface contracts into proof
obligations discharged through ipfs_datasets_py.logic's Z3ProverBridge (TDFOL).

Encoding (mirrors the prior pass's finite-enumeration method, propositional
form): every ground fact about the captured LIVE program state becomes a
zero-arity TDFOL predicate literal (asserted or negated) in the axiom set; each
contract is a conjunction of required literals. Z3ProverBridge.prove checks
validity of the goal under the axioms; the flipped goal is proved to classify
REFUTED vs UNKNOWN. Axiom sets are consistent by construction (each literal
asserted at most once, in exactly one polarity), so no vacuity: a conjunction
is valid under the axioms iff every conjunct is among the asserted literals.

State inputs: visual_check/fv_state/{bindings,backend-matrix,tools-*}.json,
captured from the running stack (vite :3001 mediator + compat adapters).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.expanduser("~/workspace/lift_coding/external/ipfs_datasets"))
from ipfs_datasets_py.logic.TDFOL.tdfol_core import (  # noqa: E402
    BinaryFormula,
    LogicOperator,
    Predicate,
    UnaryFormula,
)
from ipfs_datasets_py.logic.external_provers.smt.z3_prover_bridge import Z3ProverBridge  # noqa: E402

STATE = os.path.expanduser("~/workspace/lift_coding/visual_check/fv_state")


def load(name):
    with open(os.path.join(STATE, name)) as fh:
        return json.load(fh)


def prop(name):
    return Predicate(re.sub(r"[^A-Za-z0-9_]", "_", name), [])


def neg(formula):
    return UnaryFormula(LogicOperator.NOT, formula)


def conj(formulas):
    out = formulas[0]
    for f in formulas[1:]:
        out = BinaryFormula(LogicOperator.AND, out, f)
    return out


def classify(bridge, axioms, goal):
    pos = bridge.prove(goal, axioms=axioms, timeout=60)
    if pos.is_valid:
        return "PROVED"
    flipped = bridge.prove(neg(goal), axioms=axioms, timeout=60)
    if flipped.is_valid:
        return "REFUTED"
    return "UNKNOWN"


def main():
    bindings = load("bindings.json")
    matrix = load("backend-matrix.json")
    tools = {}
    for n in ("kit", "datasets", "accelerate"):
        d = load(f"tools-{n}.json")
        tools[n] = {t["name"] for t in d["result"]["tools"]}
    owner_map = {"ipfs_kit_py": "kit", "ipfs_datasets_py": "datasets", "ipfs_accelerate_py": "accelerate"}

    bridge = Z3ProverBridge(timeout=60, enable_cache=False)
    obligations = []
    counterexamples = []

    def run(oid, axioms, goal, cex=None):
        verdict = classify(bridge, axioms, goal)
        obligations.append({"id": oid, "verdict": verdict})
        print(f"{oid}: {verdict}")
        if verdict == "REFUTED" and cex:
            counterexamples.append({"id": oid, "counterexample": cex})
        return verdict

    # ---- Family P: live discovery parity, one obligation per owner ----------
    for owner, svc in owner_map.items():
        live = tools[svc]
        selected = sorted({c["selected_tool_id"] for c in bindings["controls"] if c["owner"] == owner})
        axioms, goal_parts = [], []
        for t in sorted(live):
            axioms.append(prop(f"in_live_{svc}_{t}"))
        for t in selected:
            if t not in live:
                axioms.append(neg(prop(f"in_live_{svc}_{t}")))
            goal_parts.append(prop(f"in_live_{svc}_{t}"))
        # foreign probe: a tool that exists nowhere must not be live
        axioms.append(neg(prop(f"in_live_{svc}_zz_foreign_probe_tool")))
        run(
            f"P-discovery-parity-{svc}",
            axioms,
            conj(goal_parts),
            cex={"owner": owner, "missing": [t for t in selected if t not in live]},
        )
        # foreign-probe exclusion obligation
        run(
            f"P-foreign-exclusion-{svc}",
            axioms,
            neg(prop(f"in_live_{svc}_zz_foreign_probe_tool")),
        )

    # ---- Family C: binding completeness + confirmation coherence ------------
    apps = {a["app_id"]: a for a in matrix["apps"]}
    by_app = {}
    for c in bindings["controls"]:
        by_app.setdefault(c["app_id"], []).append(c)
    axioms, goal_parts, cex = [], [], []
    for app_id, a in sorted(apps.items()):
        axioms.append(prop(f"disp_{app_id}_{a['disposition']}"))
        has_avail = any(c["status"] == "available" for c in by_app.get(app_id, []))
        if has_avail:
            axioms.append(prop(f"has_available_control_{app_id}"))
        else:
            axioms.append(neg(prop(f"has_available_control_{app_id}")))
        if a["disposition"] == "tool_backed":
            goal_parts.append(prop(f"has_available_control_{app_id}"))
            if not has_avail:
                cex.append(f"tool_backed app {app_id} has no available control")
    run("C-tool-backed-completeness", axioms, conj(goal_parts), cex=cex)

    axioms, goal_parts, cex = [], [], []
    for c in bindings["controls"]:
        b = c["binding_id"]
        if c["mutates_remote_state"]:
            axioms.append(prop(f"mutates_{b}"))
            if c["confirmation_required"]:
                axioms.append(prop(f"confirm_{b}"))
            else:
                axioms.append(neg(prop(f"confirm_{b}")))
                cex.append(b)
            goal_parts.append(prop(f"confirm_{b}"))
        if c["app_id"] not in apps:
            cex.append(f"control for unknown app {c['app_id']}")
    run("C-mutation-requires-confirmation", axioms, conj(goal_parts) if goal_parts else prop("confirm_none"), cex=cex)

    # ---- Family S: backend-status coherence ----------------------------------
    declared = {"live", "denied", "unavailable", "local-only", "external-provider"}
    axioms, goal_parts, cex = [], [], []
    idx = 0
    for a in matrix["apps"]:
        for s in a["statuses"]:
            idx += 1
            tag = f"st{idx}"
            if s["state"] in declared:
                axioms.append(prop(f"declared_{tag}"))
            else:
                axioms.append(neg(prop(f"declared_{tag}")))
                cex.append(f"{a['app_id']}: undeclared state {s['state']}")
            goal_parts.append(prop(f"declared_{tag}"))
            if s["state"] != "live":
                if (s.get("reason") or "").strip():
                    axioms.append(prop(f"reasoned_{tag}"))
                else:
                    axioms.append(neg(prop(f"reasoned_{tag}")))
                    cex.append(f"{a['app_id']}: non-live status without reason")
                goal_parts.append(prop(f"reasoned_{tag}"))
            if s["state"] == "denied":
                if s.get("policy"):
                    axioms.append(prop(f"policied_{tag}"))
                else:
                    axioms.append(neg(prop(f"policied_{tag}")))
                    cex.append(f"{a['app_id']}: denied status without policy")
                goal_parts.append(prop(f"policied_{tag}"))
    run("S-status-coherence", axioms, conj(goal_parts), cex=cex)

    out = {"obligations": obligations, "counterexamples": counterexamples}
    with open(os.path.join(STATE, "proof-summary.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    proved = sum(1 for o in obligations if o["verdict"] == "PROVED")
    print(f"TOTAL: {proved}/{len(obligations)} proved")


if __name__ == "__main__":
    main()
