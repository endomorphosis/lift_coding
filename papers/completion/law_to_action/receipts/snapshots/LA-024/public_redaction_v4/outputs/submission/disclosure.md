# LLM, tool, and human-judgment disclosure (LA-024)

Paper: From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents.
Track: NeurIPS 2026 Workshop on AI for Verifiable Coding (research, double-blind).
Recorded: 2026-09-13T02:39:50.897749+00:00.

## Methodology-essential tools in the scored study

The scored method is pre-invocation runtime checking of a sandbox handler effect.
It does **not** use a language model as an important, original, or non-standard
component of that method.

| Tool | Version / pin | Role in scored method |
| --- | --- | --- |
| QF_BOOL SAT provider | SymPy 1.12 DPLL child process | Satisfiability authority only |
| Independent checker | Exhaustive truth table | Agrees with SAT/UNSAT; not a kernel theorem |
| Capability check | Real Ed25519 UCAN verification | A3/A4 grant check |
| Durable consumption | File-backed DuckDB typed Quack owner | A4 only |
| Effect observation | Independent filesystem journal | Forbidden-effect and useful-work counters |
| Scientific model calls | 0 | Closed-loop generated-code planning withdrawn |

Implementation revision of the admitted matrix:
`ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c`.
Docker image used only for the operator matrix (absent from the sealed PATH):
`sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6`.

Arms A1 and A2 are model-free prompt-text and retrieval-context labels. They are
instrumentation/equivalence controls, not LLM efficacy.

## Language-model use that is not a scored arm

Language-model assistance supported source inspection, implementation and control
development, execution orchestration, retained-data analysis, and manuscript writing.

| Assistant | Identifier | Use |
| --- | --- | --- |
| Grok | `grok-4.6` (xAI) | Primary drafting / inspection assistant |
| Codex | GPT-6 | Observed coordinating implementation, recovery, analysis, and final artifact corrections |
| Codex fallback configuration | `gpt-5.6-terra` | Configured fallback only; this record does not establish that it ran |

No model was invoked in the scored fixed-action study. These development assistants are not baselines,
not generators of expert legal labels, and not the A4 enforcement mechanism.

## Remaining human judgments

| Judgment | Status |
| --- | --- |
| Independent human legal / security / intent validation | Not collected; claims withdrawn |
| Inter-annotator agreement | Not collected; unmeasured |
| Expert legal fidelity / legal-validity rates | Unmeasured; not filled from compiler agreement |
| Frozen allowed/forbidden labels | Machine-checkable modeled policy, not expert legality |
| Optional author review | Non-independent; not a prerequisite; not recorded as completed |
| Outside reviewers | Not available and not required for this amended study |

Packet-preparer field extraction and shared-producer schema checks are not
independent human review.

## Official anonymous author block

The official style in default anonymous mode prints `Anonymous Author(s)`,
`Affiliation`, `Address`, and `email`. Those strings are retained. They are
style-generated anonymous text, not unanswered scientific fields.

This file is part of the anonymous package and contains no author names,
affiliations, or author-maintained repository URLs.
