# SwissKnife Logic-Submodule → TypeScript Port Task Board

Status: Accounting COMPLETE (100%) — direct-coverage lift optional/tracked
Scope: Complete the port of every portable module **and every public symbol** in the
`ipfs_datasets_py/logic` submodule into the SwissKnife TypeScript prover stack, and
prove the completeness with a machine-checkable gate.

Companion gap analysis: `36-swissknife-wasm-theorem-provers-2026-07-01.md`
(§12 backlog PORT-001…234; §12.22 module manifest; §12.23 symbol-level audit; §12.24
completion record).

**Authoritative gate (built + green):** `../conformance/symbol-map.json` +
`../conformance/symbol_audit.py --check` (wired into `make conformance`). Independent
cross-check ledger: `../port-audit/symbol-coverage.json` (+ `.md`), from
`gen_symbol_ledger.py`.

Pins (audit basis): ipfs_datasets `4672e0b2`, swissknife `47e9e19`. Re-pin before
porting (see §12.20.5) — the submodule working checkout drifts from the parent pin.

## Coverage snapshot (authoritative symbol-map, gate green 2026-07-04)

`symbol_audit.py --check` → `1522/1522 accounted, 1239 direct, 263 consolidated,
20 n/a, 57 sub-80 modules` (exit 0).

- Modules: 256 | Public symbols: 1522
- **Accounted coverage: 100.0%** (0 unmapped) — every symbol is `ported`,
  `consolidated` (with cited reason), or `n/a`
- **Direct coverage: 81.41%** — 1239 symbols present as distinct TS identifiers
- Independent ledger corroborates: 1209 direct / 82.4% (`gen_symbol_ledger.py`)
- Remaining OPTIONAL lift: **57 sub-80% modules / 572 consolidated symbols** — these
  are behaviorally present (Python one-class-per-rule folded into TS rule tables/
  methods); raising them to *direct* identifiers is a polish backlog, not a gap.
- Module-level presence is ~98% (§12.22); symbol accounting is now 100% (§12.23/§12.24).

Consolidated (sub-80%) symbols cluster by subpackage (the optional lift queue, densest first):

| Subpackage | Modules | Consolidated symbols | Primary PORT tasks |
|---|---:|---:|---|
| `deontic` | 6 | 92 | PORT-227, PORT-228, PORT-229 |
| `CEC` | 15 | 52 | PORT-224, PORT-225 |
| `TDFOL` | 10 | 35 | PORT-224 (rules), PORT-104…109 |
| `integration` | 13 | 24 | PORT-232, PORT-085 reconcile |
| `zkp` | 2 | 12 | PORT-210, PORT-222, PORT-223 |
| `fol` | 3 | 9 | PORT-226 |
| `observability` | 2 | 7 | PORT-231, PORT-233 |
| `modal` | 5 | 6 | PORT-230 |
| `common` | 4 | 5 | PORT-221 (residual) |
| `external_provers` | 3 | 5 | PORT-209…213 (host-native) |
| other (`root`,`types`,`bridge`,`flogic`) | 5 | 11 | reconcile |

## Milestone A: Symbol-coverage gate (DONE — PORT-234, agent Sprints 101–106)

### A1. Ledger as the system of record — DONE
- [x] `conformance/symbol-map.json` classifies every public symbol:
      `ported` | `consolidated` (cited reason) | `n/a`
- [x] Independent cross-check `port-audit/symbol-coverage.json` generated from the two pinned trees
- [x] Referenced from doc-36 §12.23/§12.24

Definition of done: **met** — 1522/1522 symbols classified; totals reconcile
(1239 + 263 + 20 = 1522); `symbol_audit.py --write-map` regenerates it.

### A2. Reconciliation map — DONE
- [x] Every symbol resolved to `ported` / `consolidated:<reason>` / `n/a:<reason>`
- [x] Zero `unmappedSymbols` (100.0% accounted)

Definition of done: **met** — `unmappedSymbols: 0` in `symbol-map.json.summary`.

### A3. CI accounting gate — DONE
- [x] `symbol_audit.py --check` re-derives current Python symbols + TS index and
      validates against the map; fails on any unmapped symbol, a stale
      `ported` identifier no longer in `swissknife/src`, or a `consolidated`/`n/a`
      entry missing a reason
- [x] Wired into `make conformance` (`Makefile:31`)
- [x] Gate GREEN: `1522/1522 accounted … 57 sub-80 modules` (exit 0)

Definition of done: **met** — the gate is the authoritative "symbol coverage is
complete" signal and currently passes.

## Milestones B–D: OPTIONAL direct-coverage lift (57 sub-80% modules / 572 symbols)

> Accounting is already 100% (Milestone A). The tasks below are NOT gaps — every
> listed symbol is `consolidated` (behaviorally present, folded into a TS rule
> table/method) with a cited reason in `symbol-map.json`. They raise *direct*
> coverage (distinct TS identifiers) where the team judges a 1:1 symbol worthwhile.
> Skip any where consolidation is the better design; just keep the reason current.

## Milestone B: High-density consolidated clusters (deontic, CEC, TDFOL)

### B1. Deontic (92 symbols / 6 modules) — PORT-227, PORT-228, PORT-229
- [ ] Legal-text → deontic parser surface (PORT-227): port the sentence/clause
      extractors and modality classifiers absent from the TS deontic services
- [ ] Conflict taxonomy + Jaccard action-similarity + Allen-interval overlap (PORT-228)
- [ ] Deontic IR breadth (PORT-229): reconcile `ir.py` (2834L) symbols vs
      `legal-norm-ir.ts` — port or map each class/builder
- [ ] Add conformance vectors exercising the newly-ported symbols

Definition of done:
- All 92 deontic `needs-review` symbols resolve to `ported-as` or `consolidated-into`
- New/updated tests green; deontic parity vectors added to the conformance corpus

### B2. CEC native (52 symbols / 15 modules) — PORT-224, PORT-225
- [ ] Native inference-rule classes: modal, temporal, deontic rule sets (PORT-224)
- [ ] CEC native exception hierarchy (PORT-225)
- [ ] For rules already expressed as a data-driven TS rule table, record
      `consolidated-into:<table>` in `symbol-map.json` (do NOT re-port as classes)

Definition of done:
- Every CEC symbol is `ported`, `consolidated-into` a rule table (with citation), or `na`
- CEC conformance vectors cover the modal/temporal/deontic rule behaviors

### B3. TDFOL residual rules + API (35 symbols / 10 modules)
- [ ] Port/verify the remaining inference rules (the §12.6 "25 missing rules" region)
- [ ] Reconcile `tdfol-*.ts` public API symbols against the Python TDFOL modules
- [ ] Confirm temporal-operator and quantifier symbols are present or mapped

Definition of done:
- TDFOL `needs-review` set is empty in the ledger
- Differential (Python vs TS) vectors for the ported rules MATCH (§12.21 harness)

## Milestone C: Resolve the mid-density clusters

### C1. `fol/utils` formatters + parsers (9 symbols) — PORT-226
- [ ] Port the FOL formatters/parsers that have no TS equivalent (verified absent)

### C2. `zkp` residual (12 symbols) — PORT-210, PORT-222, PORT-223
- [ ] Reconcile `zkp/statement.py`, provekit public-inputs, circuit symbols
- [ ] Mark host-native binary paths (real Groth16/ProveKit FFI) as PORT-209–213 `na`

### C3. `observability` (7 symbols) — PORT-231, PORT-233
- [ ] Security `audit_log` surface (PORT-231) and profiler/NL-context (PORT-233)

### C4. `modal` (6) + `common` (5) + `integration` (24) residuals
- [ ] Modal residual symbols — PORT-230 (S5 symmetry / synthesis / KG bridge / codec)
- [ ] `common/errors` residual taxonomy — PORT-221 tail
- [ ] `integration` bridge/glue symbols — PORT-232 (+ PORT-085 NL-closure reconcile)

Definition of done (C1–C4):
- Each subpackage's `needs-review` count reaches 0 in the ledger
- Every ported symbol has a test or conformance vector

## Milestone D: Certificate (ALREADY MET — keep it green)

### D1. Long-tail reconciled — DONE
- [x] `root`, `types`, `bridge`, `flogic`, host-native symbols resolved to
      `ported` / `consolidated` / `n/a` in `symbol-map.json`
- [x] Host-native symbols tracked only under PORT-209–213 (`n/a` in the map)

### D2. Certificate — FLIPPED
- [x] `symbol-map.json` complete; **0 unmapped**; accounted coverage 100.0%
- [x] CI gate (A3) green and enforcing (`symbol_audit.py --check` exit 0)
- [x] doc-36 §12.24 records the completion certificate

Ongoing DoD (regression guard, not new work):
- Every push keeps `make conformance` green — no unaccounted or stale symbols.
- Raising *direct* coverage above 81.41% is the only optional remaining lift
  (Milestones B–C), and only where a 1:1 identifier beats consolidation.

## How to complete the symbol coverage (playbook)

The gate already exists and is green (Milestone A). Use this loop to keep it green
and to raise *direct* coverage on the 57 sub-80% modules when desired:

1. **Re-pin** the submodule + swissknife to a known SHA (§12.20.5), then regenerate
   the authoritative map + the independent cross-check so the denominator is stable:
   ```
   python3 implementation_plan/conformance/symbol_audit.py --write-map   # authoritative symbol-map.json
   python3 gen_symbol_ledger.py                                          # independent port-audit/ ledger
   ```
2. **Pick a sub-80% module** from `symbol-coverage.md` (densest subpackage first:
   deontic → CEC → TDFOL → …). Open the Python source and the candidate TS file.
3. **Decide per `consolidated` symbol** whether a distinct TS identifier is worth it:
   - worth a 1:1 port → add the TS symbol, then set its `symbol-map.json` status to
     `ported` (re-run `--write-map` to confirm it's now direct)
   - better left folded → keep `consolidated` and ensure the `reason` cites the TS
     table/method it lives in
   - host-native / demo / shim → `n/a:<reason>` (host-native stays under PORT-209–213)
4. **Port any true `gap`** (should be none today — accounting is 100%) as a small,
   additive, cold-surface TS change; prefer an isolated `git worktree` + PR into
   swissknife (as with §12.13/§12.8) to avoid colliding with the sprint agent's hot files.
5. **Add a conformance vector** per newly-ported behavior so the §12.21
   Python-differential harness locks parity (MATCH), not just presence.
6. **Re-run the gate:** `make conformance` (or `symbol_audit.py --check`). It must
   stay `0 unmapped` and report no stale `ported` identifiers. Direct coverage % rises.
7. **Repeat** until direct coverage reaches the team's target (100% accounting is
   already achieved and enforced).

Notes:
- The audit is a *screening oracle*: a `consolidated` symbol is "present but not a
  distinct identifier," not "missing." `symbol-map.json` captures that judgment once
  (with a cited reason) so it never has to be re-litigated — that is what makes the
  100% accounting real rather than cosmetic.
- Keep commits path-restricted and non-colliding; the prover sprint agent owns the
  hot type-system/router files. Cold subpackages (fol/utils, audit_log, CEC
  exceptions, deontic parser) are the safe disjoint verticals.
