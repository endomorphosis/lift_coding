# Selective candidate capsules and obligations — 2026-10-12

The supervisor's coding worker can now request a catalog of exact capsule and
function identifiers, then retrieve selected native capsules or numerical
obligations by path, symbol, function and obligation kind. This makes the large
formal artifacts usable within the worker's bounded retrieval channel. The
existing datasets capsule builder and source-replay obligation pager own the
semantics; the accelerator supplies selection, paging and worker integration.

Accelerator implementation `06a437cdba28e148912d998bf2cb85a805a3d4d9` is published
to `origin/main` and includes the preceding native task-admission work.

- [Worker interface and limits](https://github.com/endomorphosis/ipfs_accelerate_py/blob/06a437cdba28e148912d998bf2cb85a805a3d4d9/docs/agent_supervisor/worker_candidate_context.md)
- [Tests, Docker results and retained evidence](https://github.com/endomorphosis/ipfs_accelerate_py/blob/06a437cdba28e148912d998bf2cb85a805a3d4d9/docs/agent_supervisor/evidence/candidate-context-selection-20261012/README.md)
- [Previous candidate refresh](96-supervisor-candidate-context-refresh-2026-10-12.md)
- [Native task admission and remaining production handoff](97-supervisor-native-source-task-admission-2026-10-12.md)

The main regression passed 984 cases. Two selector tests were added during that
run, so its recorded source-unchanged flag is false; no production file changed.
The final selector file then passed all 53 cases unchanged. After normalizing
pytest package-prefix aliases, **986 distinct repository tests passed across the
two runs**, with zero failures, errors or skips. Two network-disabled Docker
checks also passed through the generated owner/worker launch, separate UIDs,
real source channel and an authored router hook. Both retained the source and
runner hashes; the owner independently replayed each complete selected result.

| Complete result on `largest-eigenval` public inputs | Payload bytes | Response JSON bytes |
| --- | ---: | ---: |
| Catalog for `eigen.py` | 4,595 | 6,331 |
| One native capsule | 5,336 | 7,208 |
| One native obligation | 4,545 | 6,319 |

Discovery plus the two subsets consumed **19,858 response JSON bytes** in each
Docker run. The full parent capsule/formal artifacts were 48,309/476,030 bytes,
but contain more information. The full-artifact probe read only their prefixes;
the selected results were complete. The selected capsule disclosed 1 filtered
and 6 out-of-path rows; the obligation disclosed 15 filtered and 29 out-of-path
rows. Source, generation, producer and parent-artifact identities remain bound.
Unsupported coverage and empty matches do not acquire proof authority.

The default model-facing display of the selected obligation was 5,520 bytes,
versus its 6,319-byte raw envelope. Both exceed the source file's 642 bytes.
Thus these measurements establish smaller selective retrieval, not a provider
token benefit. The runs made no real model/provider/solver calls, discharged no
source obligations and did not run the official task verifier, `lake build`,
autoencoder inference or full live supervisor START. The broader methodology
still needs a matched native-model experiment with official rewards and complete
token, initialization, discovery, translation-table, refresh and retry costs.

The parent retains datasets `e39fe996bd9e786a84f739fda9dde9a6c70546da` and kit
`8ac00bb1974b1378e12091d546d8425af34049e0`. Qualification used datasets
`f47161b757190380e9898aff155067c1ad609217`; all 24 direct candidate-artifact
producer modules match the newer retained datasets pin byte for byte. This
comparison does not qualify unrelated datasets changes or the complete
dependency closure. Checkpoint families, source embeddings and training state
are unchanged by this retrieval work.

Candidate selections remain session-local advice. Publication of accepted
DuckLake proof/index state, a qualified native claim/allocation/child handoff,
and exact replay of edits made through reversible compact views remain separate
work items. The full-indexed source-view option stays opt-in.

All four [local documentation gates](../../artifacts/candidate-context-selection-publication-20261012/local-documentation-gates.json)
passed. The exact-commit hosted documentation job did not start: GitHub reported
an account billing lock with runner ID zero and no steps. Its
[CI observation](../../artifacts/candidate-context-selection-publication-20261012/hosted-ci.json)
retains that infrastructure result without attributing it to a test failure.
