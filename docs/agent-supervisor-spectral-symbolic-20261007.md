# Provider-free spectral operator, 2026-10-07

The supervisor now has a reviewed deterministic dominant-eigenpair candidate,
conditional formal adapter checks, an isolated target-runtime probe, and a
source/task-bound native staging workflow. General planning remains unchanged.
The numerical computation and authored candidate qualification use zero
runtime provider calls.

The public `largest-eigenval` task defines dominant as maximum magnitude and
allows nonsymmetric real matrices with complex eigenpairs. Its original source
already computes with NumPy. The benchmark requires a consistently faster
implementation, so numerical correctness alone cannot complete it.

The fresh combined suite passed **113 tests** with zero failures, errors or
skips. It exercised 22 authored numerical fixtures, 13 scoped ideal-algebra
SMT lemmas, exact current evidence bindings and the existing allocated native
candidate materializer. Independent review passed 24 controls. A previous
combined run reused 58 AST-seal results; the final run used a new DuckDB seal
catalog with required sealing enabled.

Both local timing attempts failed the consistent-speed gate. Only the two
1 by 1 cases were faster; the final sizes 2–10 took 1.018–1.597 times the NumPy
reference. The public Python 3.13/NumPy 2.3 target initially lacks SciPy, and
target dependency and speed qualification remain outstanding. Doctor dispatch
retains a residual route rather than automatically executing this candidate.
No official benchmark or new training run was launched.

The improvement plan connects reviewed mathematical operator contracts with
native DuckDB/Quack state and immutable evidence references. Semantic capsules
can expose operator IDs, preconditions and residual obligations to the general
planner. The 8D, 384D and 768D indexes, or a separately evaluated Leanstral
embedding, can nominate those contracts; exact source/task and evidence checks
retain selection authority. Performance and numerical qualification stay
separate from conditional formal lemmas. No exact floating-point kernel proof
or measured total-token saving is claimed.

The tracked `external/ipfs_accelerate` reference advances to
`6972945b812a6db4b72a5b8c3d2496dbd49e68ad`. The
[source change](https://github.com/endomorphosis/ipfs_accelerate_py/commit/6972945b812a6db4b72a5b8c3d2496dbd49e68ad),
[implementation and plan](https://github.com/endomorphosis/ipfs_accelerate_py/blob/6972945b812a6db4b72a5b8c3d2496dbd49e68ad/docs/agent_supervisor/spectral_symbolic_operator.md),
and [qualification evidence](https://github.com/endomorphosis/ipfs_accelerate_py/blob/6972945b812a6db4b72a5b8c3d2496dbd49e68ad/docs/agent_supervisor/evidence/terminal-spectral-symbolic-20261007/README.md)
are published together. No model weights were produced, so this experiment
adds no Hugging Face upload. The original working checkout and index are
preserved; publication uses separate owned source and parent worktrees.
