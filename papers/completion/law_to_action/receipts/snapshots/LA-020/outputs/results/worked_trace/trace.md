# Worked source-to-effect trace

This replaces the manuscript §7 composition walkthrough and Appendix D twelve-step list with a replay of frozen LA-015 A4 identities. Compact LA-015 rows remain the scored outcomes. Intermediate SAT, UCAN, ENFORCE, handler, and DuckDB artifacts below were retained on a detailed replay of those identities. No kernel theorem, generated program, or independent human gold is claimed.

## Run identity

- Source run: `LA-015`
- Implementation revision: `ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c`
- Seed / arm: `104729` / `A4`
- Permitted attempt: `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0`
- Case: `family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` (skill, mutation `none`)
- Decision / useful work / effects: `allow` / `True` / `1`

## Twelve-step trace for permitted useful work

| Step | Status | Transition | Attempt |
| ---: | --- | --- | --- |
| 1 | ran | Resolve source and declaration manifests by exact revision/CID. Frozen source_id skill:cde85f1fbfa19461702271bc52c9b65be4eb944e75e427a2470e9f34227dd693 with content identity ef917528b31bf690eda2fac57a9f568f7f66f15a99384d00447e12fdeb40e7e0; IPFS publication was not performed. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 2 | ran | Import skill procedure as data; derive or validate IntentIR. SkillCenter normalizer produced skill_intent_ir document_id=intent:skillcenter:8e128cbf4c4daa54d7d61c54864dd1759b03d3279f5379611420f54dd9397967 schema_valid=True. Typed compiler available=False. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 3 | partial | Select applicable LegalIR and reviewed SecurityIR constraints. LegalIRCompilerAPI was not the selected adapter. Independent human legal/security review was not used. Machine-contract span linkage ran. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 4 | ran | Bind actual requested tool, arguments, actor and expected effects. Bound actor=did:client:tenant-a tool=export_json path=exports/fa-075d8327ad20c2d4.json candidate_digest=b0875e6b1a86ac83. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 5 | partial | Correlate intent-side effects with code/handler-side observations. The handler accepts a declarative export_json instruction, not generated source. LA-016 produced 0 generated programs. Declared filesystem.export_json effects were compared with the independent journal observer. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 6 | ran | Compose and execute the required formal jobs; retain non-successes. QF_BOOL SAT provider=unsat checker agrees=True. Authority is satisfiability, not theorem_proof. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 7 | ran | Produce an exact-context decision, not an effect. An internal BoundContext decision receipt and capability were derived for the exact actor/tool/args digest. Harness selected_evidence_cids are constants, not a published proof. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 8 | ran | Check signed delegation and host-controlled current policy/state. Real Ed25519 UCAN verifier decision=allow token_sha256=7c3c672fef671199 signature_present=True. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 9 | ran | In enforce mode, revalidate and consume the exact permitted use. ENFORCE decision=allow store=duckdb-file-typed-quack-owner in_memory=False consume=accepted. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 10 | ran | Dispatch once through the selected protected path. BoundedExportHandler.export_json handler_calls=1 delegate_called=True. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 11 | ran | Record observed outcome separately from proof and authorization. Independent observer v2 counted effects=1 journal=1 useful_work=True (LA-015 compact useful_work=True). | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |
| 12 | ran | Commit operational progression through the DuckDB owner. Typed Quack owner consume CAS outcome=accepted generation=1 revision=1. | `104729:A4:family:10df17dbfee02e86d083e2784e7aaec79a4691d1441d1ceff4ef944f2695b949:case-0` |

## Matched forbidden variants

### rejected_recipient

- Family `family:02b8daf26d6786a78c5c17ddb8bf3380e0d37a26cbbb67e06a8118c09d03dc85` mutation `wrong_audience`
- Allowed control `104729:A4:family:02b8daf26d6786a78c5c17ddb8bf3380e0d37a26cbbb67e06a8118c09d03dc85:case-0`: decision `allow`, useful_work `True`, effects `1`
- Forbidden `104729:A4:family:02b8daf26d6786a78c5c17ddb8bf3380e0d37a26cbbb67e06a8118c09d03dc85:case-1`: decision `deny`, forbidden_effect `False`, effects `0`, denial `context-mismatch`
- Divergence: Step 8 signed delegation: UCAN audience did:wrong decision=deny reason=ucan_denied; handler was not dispatched.

### undeclared_effect

- Family `family:0bbb54a64a61f2c7f5a5522e5949eb61a6c4ff7a854c41ede84623e060a3752a` mutation `undeclared_handler_effect`
- Allowed control `104729:A4:family:0bbb54a64a61f2c7f5a5522e5949eb61a6c4ff7a854c41ede84623e060a3752a:case-0`: decision `allow`, useful_work `True`, effects `1`
- Forbidden `104729:A4:family:0bbb54a64a61f2c7f5a5522e5949eb61a6c4ff7a854c41ede84623e060a3752a:case-1`: decision `deny`, forbidden_effect `False`, effects `0`, denial `context-mismatch`
- Divergence: Step 9 ENFORCE revalidation: supervisor context listed an extra undeclared effect and enforce_decision=deny denial=context-mismatch.

### replay

- Family `family:336629d04e385ffc653cb53a747a48b39405152e8a0bd6fc136bc38035bfd3c8` mutation `replay`
- Allowed control `104729:A4:family:336629d04e385ffc653cb53a747a48b39405152e8a0bd6fc136bc38035bfd3c8:case-0`: decision `allow`, useful_work `True`, effects `1`
- Forbidden `104729:A4:family:336629d04e385ffc653cb53a747a48b39405152e8a0bd6fc136bc38035bfd3c8:case-1`: decision `deny`, forbidden_effect `False`, effects `0`, denial `replayed`
- Divergence: Step 9 consumption: warmup consume accepted then replay consume idempotent_replay; enforce_decision=deny.

## Absent or narrowed steps

- **Generated-code AST / model program**: LA-016 generated_program_count=0; the handler consumes a declarative export_json instruction, not generated source text.
- **LegalIRCompilerAPI**: LegalIRCompilerAPI was not selected; the deterministic deontic parser is the recorded adapter. Independent legal review was not used.
- **Kernel theorem_proof**: The executed job is QF_BOOL SAT with satisfiability authority. SAT/UNSAT cannot authorize theorem_proof allows.
- **Published IPFS proof CID**: Source pins are SHA-256 content identities. Harness selected_evidence_cids include a constant stub CID that is labeled not-proof and is not shown as a receipt.
- **Independent human gold**: independent_human_gold remains false on the frozen LA-015 and LA-009 records.

## Claim limits

- Allowed and forbidden refer only to the frozen modeled policy and machine-checkable behavior contract.
- Independent effect observation is the filesystem-journal observer, not an outside human reviewer.
- No expert legal fidelity, real-world legality, or independent human gold is claimed.
- SAT/UNSAT cannot authorize theorem_proof allows.
- No fabricated signature or conceptual step is presented as executed.
- Closed-loop model-generated programs remain unrun.
- Detailed replay artifacts recover omitted intermediate fields; compact LA-015 rows remain the scored identities.
