Read-only research environment inventory, observed **2026-09-11 15:36 UTC**. Full executable paths, metadata, repository identities, and source hashes are in [research_environment.json](research_environment.json). This is planning input for all three papers, not benchmark evidence or task completion.

| Resource | Observed availability |
|---|---|
| CPU | AArch64, 20 logical CPUs, all 20 in this process's affinity; load averages 33.09 / 28.28 / 25.40 |
| Host memory | 121.7 GiB total; approximately 100.0 GiB available at observation |
| Disk | Approximately 129.7 GiB available on the filesystem shared by the repository, home, and `/tmp` |
| GPU | One NVIDIA GB10 reported by `nvidia-smi`; driver 580.142; GPU total/free memory reported as `[N/A]` |
| CUDA compiler | `nvcc` 13.0.88; no CUDA execution or model inference tested |

Resource measurements are shared-host observations, not reservations. CPU, GPU, temporary-data, and checkpoint budgets therefore need coordination across the three paper protocols.

The current and system Python metadata report Torch **2.13.0**, torchaudio **2.8.0**, Transformers **4.52.1**, Accelerate **1.8.1**, sentence-transformers **5.4.1**, spaCy **3.8.14**, NumPy **1.26.4**, and DuckDB **1.5.5**. This does not establish that these versions work together or support this GPU. The campaign interpreter reports DuckDB **1.5.5**, with the selected ML distributions absent from its metadata. Repository modules supplied through `PYTHONPATH` are a separate source-access mechanism. The sealed validator interpreter rejected the general `-c` metadata probe; no bypass was attempted.

Z3 **4.15.4** and cvc5 **1.3.3** executables answered version probes. Nine installed Lean toolchains answered direct binary version probes: **4.29.0, 4.29.1, 4.30.0, 4.31.0, 4.32.0, 4.32.1, 4.32.2, 4.33.0, and 4.33.1**. Matching Lake binaries are inventoried. The Elan launchers were not invoked, avoiding implicit downloads. Neither `coqc` nor `rocq` was found on `PATH`; this is not a claim about every possible installation elsewhere.

pdfLaTeX, XeLaTeX, and LuaLaTeX report **TeX Live 2026**; latexmk reports **4.88**. No manuscript compilation, checker project/import qualification, proof checking, training, or experiment was performed by this inventory. No previously established unauthenticated model-backend health URL was available to this task, so backend health was not probed.

The JSON pins the exact canonical heads and dirty source hashes for the parent repository, `external/ipfs_accelerate`, `external/ipfs_datasets`, and `external/ipfs_kit`: respectively **40, 19, 30, and 1** source/config/document entries. Every hashed file was stable during its individual hash. Git status entries are retained; hidden runtime/quarantine trees and generated bootstrap artifacts are explicitly excluded from source hashing. These mutable canonical checkouts are distinct from the isolated campaign lane runtime snapshots, whose update was pending during collection.

For autoformalization, select and qualify a model environment and one compatible Lean/checker project before training. For law-to-action, qualify the actual enforcement/checker route and corpus inputs. For neurosymbolic supervision, pin the lane runtime and qualify the replay, validation, and execution paths. Each paper still needs its own measured evidence, protocol checks, and reproducibility receipts.
