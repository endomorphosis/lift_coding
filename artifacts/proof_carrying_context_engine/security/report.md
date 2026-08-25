# PCCE-076 security qualification report: NO-GO

## Decision

The proof-carrying context engine is **not security-qualified and is not release-qualified** at evidence cut `d23e861fd4fc6293c888a6dc3377e8c94d4129d9` (tree `be83ad730f756ed170e174650165a088f5116323`). All 14 threat areas remain `NO-GO`. The frozen threat model contains 10 open release-blocking residual-risk findings: 9 critical and 1 high. Policy permits no waiver in this evidence-only gate.

This report records evidence; it does not repair a control, invoke a provider, run a security scanner, dispatch CI, publish a result, mutate DuckDB/Quack, or complete PCCE-076. The live read-only Quack projection identified PCCE-076 as task CID `baguqeera75yoyff76ew7hitxvpsyk7jqxa2vhgiddmnpyma5spkazkzxr3yq`, revision 1, status `todo`, dependent on PCCE-075.

The canonical findings bytes are bound as raw CID `bafkreiaj5oj6sqxpybal2q5rejdmtusbuqrhulbnkfhglw3gxbtjyz5ub4`, SHA-256 `09eb93e942efc040bd43b12246c9d241a4227a2c2d514e65db66b8669c67b40f`, size 18145.

## Release-blocking observed failures

PCCE-075 supplies real adversarial evidence, not a hypothetical warning:

- Concurrent publication schedule `two-runtime-stores-one-generation-minimized-failure` proved overlapping writers sharing one Kit root. The invariant allowed at most one accepted record and one published settlement; the observed result was **two accepted records and two published settlements**.
- Process-crash schedule `bounded-process-apply-during` did not observe durable resume. A no-cleanup restart was unavailable; after cleanup a fresh runtime accepted and published the proposal as `succeeded`. The preserved disposition is `no-go-lost-durable-checkpoint-false-success`.
- ABA schedule `delayed-generation-one-after-aba` rejected the stale generation-one call, but only in a synthetic in-process store. It is not integrated with the runtime Kit repository and earns no qualification credit.
- Authoritative integration schedule `authoritative-runtime-integration-gaps` found that the authoritative sandbox and hidden evaluator are not integrated; proof execution is unavailable, verification is marker-only, and a proposal was accepted despite those gaps.

PCCE-074 also remains a limited, non-authoritative boundary: no authoritative accelerator or provider consumes the module, no live benchmark or provider was invoked, trusted evaluator callbacks are not sandboxed by the module, and its final outer proof-context suite retained the PCCE-050 wheel/sdist binding blocker.

## Threat disposition

| Threat | Area | Evidence disposition | Release decision | Open risks |
|---|---|---|---|---|
| TH-001 | Untrusted repository and source prompt injection | Local limited controls only; no authoritative instruction/data separation | NO-GO | RR-001, RR-010 |
| TH-002 | Malicious tests and fixtures | Authoritative sandbox/evaluator integration absent | NO-GO | RR-002, RR-008, RR-009, RR-010 |
| TH-003 | Untrusted agent patch and policy weakening | Adversarial fixtures pass only inside limited, non-authoritative boundaries | NO-GO | RR-001, RR-010 |
| TH-004 | Scope and path escape | Symlink-safe descriptor-rooted containment is not proven | NO-GO | RR-004, RR-010 |
| TH-005 | Process and command escape | Tested direct boundary does not cover every execution path | NO-GO | RR-002, RR-008, RR-010 |
| TH-006 | Network escape | Route-scoped live endpoint enforcement is unavailable | NO-GO | RR-003, RR-010 |
| TH-007 | Secret and credential escape | Live credential-bearing execution paths are outside the qualified boundary | NO-GO | RR-002, RR-003, RR-010 |
| TH-008 | Evidence, receipt, and seal forgery | Authoritative signer and live provenance authorities are unavailable | NO-GO | RR-005, RR-009, RR-010 |
| TH-009 | Replay, stale cache, poisoning, and wrong parent | ABA evidence is synthetic-only; runtime/storage failures remain | NO-GO | RR-005, RR-007, RR-010 |
| TH-010 | Hidden benchmark and future-answer leakage | Authoritative hidden evaluator is not integrated | NO-GO | RR-006, RR-010 |
| TH-011 | Provider over-disclosure | No live provider or authoritative provider-payload observation exists | NO-GO | RR-003, RR-006, RR-010 |
| TH-012 | Concurrent mutation, stale or ABA writer, and duplicate result | Two accepted records and two publications were observed | NO-GO | RR-007, RR-010 |
| TH-013 | Interruption and ambiguous terminal execution | Lost durable checkpoint and false-success behavior were observed | NO-GO | RR-002, RR-008, RR-010 |
| TH-014 | Compromised adapter or transport | Authoritative sandbox/evaluator integration remains absent | NO-GO | RR-002, RR-003, RR-008, RR-010 |

## Residual-risk register

| Finding | Severity | Release blocking | Summary |
|---|---|---|---|
| RR-001 | critical | yes | No enforced instruction/data separation or semantic policy invariant |
| RR-002 | critical | yes | Tests, Codex, and arbitrary adapters remain outside the tested CommandAdapter boundary |
| RR-003 | critical | yes | Live Codex retains broad network and credential-bearing environment access |
| RR-004 | high | yes | Lexical path checks do not prove symlink-safe descriptor-rooted containment |
| RR-005 | critical | yes | Receipt, seal, signature, parent, environment, and transitive byte trust is incomplete |
| RR-006 | critical | yes | Hidden benchmark and least-disclosure provider projections are absent |
| RR-007 | critical | yes | In-process fencing does not prove cross-process CAS atomicity or ABA safety |
| RR-008 | critical | yes | Interruption cleanup is not proven for every process and lifecycle stage |
| RR-009 | critical | yes | Optional authorities, synthetic persistence, and marker-only verification can overstate evidence |
| RR-010 | critical | yes | Security modules are not integrated into authoritative runtime call paths |

## Bound source evidence

| Task | Live task CID | Receipt raw CID | Artifact identity |
|---|---|---|---|
| PCCE-070 | `baguqeerarm7v7cmisoyixe4zjghmeaqesudyaibazwhqofmwl4vppt6qprpq` | `bafkreify3t6xihrs4m35pv73glygdm6qcryldyjkbuodz6upwoo2rnaa7i` | `bafkreicqlvr2orogy3xemnyse4x5lkjs6t2w3wsrzd4w4utb4fvmsmif74` |
| PCCE-071 | `baguqeeraxkidpqi2tdgzdsymr4hc667d6fhzle7ctfvq7aozk63jrzbmnthq` | `bafkreiarjiqih3he6twziiulgzc6tdx7aydlxk2cvs4nqdkcjgvalichp4` | `bafkreib7oplhwookasl2k4chg2u4wsg7x2fva6n6aiq7pah2hp5ltg6xfq` |
| PCCE-072 | `baguqeerav5ovimddoeyqbxqcdmgh3czh7k5i2rzivapbc6fbhggjqv435kjq` | `bafkreig5kfcvi6rlhp3ebk46x7yghdw45gu745znf6b7wen6lzhfxtyeym` | `bafkreiaugowmsz2qz62hvpw4ellppuufxnzvfh5f2vr5vtxx4vdjp75wze` |
| PCCE-073 | `baguqeerahk74pqi4yfawsiqoxb7w5kmdwuojrvllpecm3vn5biw7pcqedl2q` | `bafkreieyukobizn6jmk6r5rflvoojhls6t4qnllji6q7ghe4a22bt4huoy` | `bafkreif535gd4tuokudj2djynif5uspk3lq56pro3zjwulxqyflrgk3xta` |
| PCCE-074 | `baguqeeraxgdyeia2nzxvhbdg7n33swyvteygipqo3l5ho53gxtznhcueyseq` | `bafkreiexjllqaezxl3ew473inaiw5dr5ianyxpxkapntz7gj5fw67noncu` | `baguqeera5ifpsadums6lrug6jcoi34hsvj7rhq4gv2xoordagmsvtbzr3cta` |
| PCCE-075 | `baguqeera24wipnfzevagzrgxdhl2zu5vazvy4enprtyqr2tobtetjjijihsq` | `bafkreickz4pwdhduqgb2hkzzndgdlvcqnc5affscfzwum5tzlycfd7kfsu` | `bafkreib4r2njyfnfi5pssta5ngeyjxtsf5pltkd3vuawlwonh4xytqfdy4` |

## Local validation and unavailable authority

The declared board command, invoked exactly as written without an explicit source-root environment, failed during collection before the suite ran. `external/ipfs_datasets/tests/proof_context/benchmarks/test_isolation.py` resolved an ambient `ipfs_datasets_py` that does not provide `logic.software_contracts.content`, raising `ModuleNotFoundError`. This is an explicit validation blocker; no pass is claimed for the declared command.

A diagnostic rerun of the same six test paths with `PYTHONHASHSEED=20260825` and the canonical repository roots explicitly prepended to `PYTHONPATH` reported **438 passed** and four pytest temporary-directory cleanup warnings. The warning audit found no live crash worker or probe descendant. This source-root-bound pass confirms that the checked-out sources and evidence are internally consistent; it neither satisfies the environment-dependent declared command nor converts limited boundaries or preserved adverse observations into qualification.

No immutable full-log artifact exists in the owned path set. No external CI run, security scan, provider call, live benchmark, authoritative sandbox execution, authoritative hidden-evaluator execution, signer authority, or production publication was observed. Unavailable evidence is `NO-GO` by policy.

## Required owner action

PCCE-080 and all higher release qualification levels remain blocked. Reopen the runtime/storage owners for double publication and durable checkpoint recovery; integrate the sandbox and hidden evaluator into authoritative call paths; replace synthetic ABA evidence with runtime/Kit repository evidence; resolve all RR-001 through RR-010; then rerun PCCE-076 from a fresh evidence cut. Never weaken or waive the preserved adverse schedules to obtain a green gate.
