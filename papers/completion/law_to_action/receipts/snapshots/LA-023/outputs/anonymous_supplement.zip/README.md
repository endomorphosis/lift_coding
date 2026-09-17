# Law to Action — anonymous reproducible artifact (LA-023)

This package is the anonymous workshop artifact for *From Law to Action:
Neuro-Symbolic Runtime Enforcement for MCP Agents*. It pins the sealed
validation environment, records SHA-256 identities for every reported result,
gives lawful retrieval instructions for sources that cannot be redistributed,
and provides one-command bounded reproduction and analysis.

It is **not** a 900-cell Docker rerun, a model study, expert legal review, or
independent human validation.

The declared path `anonymous_supplement.zip` is a UTF-8 **directory bundle**
(recipe/generator form). Bounded reproduce packs a real ZIP in memory for
member and credential scans; that packed archive is not stored as a git
binary. Workshop packing is `zip -r` of this directory with prefix
`law_to_action_anonymous_supplement/`.

## Environment setup (fresh checkout)

The authoritative validation environment is fail-closed:

| Pin | Value |
| --- | --- |
| `PATH` | exactly `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin` |
| Python | exactly `/usr/bin/python3.12` (CPython 3.12.3) |
| Python SHA-256 | `1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f` |
| `HOME` | a fresh directory named `ipfs-accelerate-validation-home-*` |
| XDG | `$HOME/.cache`, `$HOME/.config`, `$HOME/.local/share`, `$HOME/.local/state` |

Do not use operator profile toolchains (`~/.elan`, user-local TinyTeX, or
user-writable `PATH` entries). Those tools are unavailable under the sealed
`PATH` and are not required for bounded reproduction.

Pinned availability under that environment (see `environment.lock`):

- Present: stdlib, `cryptography 41.0.7`, `pytest 8.1.1` (module only), `sympy 1.12`
- Absent: `z3`, `cvc5`, `duckdb`, Docker, `latexmk`/`pdflatex`, any scientific model

The 900-cell admitted operator matrix used a digest-bound Docker image
`sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6`
with 1 CPU, 2 GiB / no swap, 16 pids, 20 s/cell, and an 18,000 CPU-second
stop. **Docker is not on the sealed `PATH` and is not required for
`reproduce.sh`.** Full-matrix rerun remains an operator-only retrieval of the
hashed retained records.

## One-command bounded reproduction and analysis

From a fresh checkout of this repository:

```bash
bash papers/completion/law_to_action/artifact/reproduce.sh
```

From this directory bundle (or an unpacked copy):

```bash
./reproduce.sh
```

That command:

1. Forces the sealed `PATH` and `/usr/bin/python3.12`.
2. Verifies `environment.lock` against the live interpreter digest.
3. Uses the directory bundle, or unpacks a packed ZIP if one is supplied.
4. Regenerates A0–A4 forbidden-effect and allowed-useful-work rates from the
   hashed admitted `raw.jsonl` using `subset/outcomes.recipe.json` (900 compact
   scientific rows; not a dumped envelope per cell).
5. Binds those rates to SHA-256 identities of the retained admitted
   `raw.jsonl`, `summary.json`, and `arm_safety_utility.json`.
6. Checks every frozen source artifact is `retrieval_only` with URI + SHA-256
   and `included_bytes = 0`.
7. Runs the LA-008 measurement-integrity harness smoke (fixture only; not a
   scored benchmark).
8. Packs the bundle in memory and scans it for credentials, private author
   companions, home directories, and Overleaf project URLs.

Expected bounded analysis outcome (admitted LA-029 matrix, 60 cases × 5 arms
× 3 seeds; forbidden/useful denominators are the 90 forbidden and 90 allowed
oracle cells per arm):

| Arm | Forbidden effects | Allowed useful work |
| --- | --- | --- |
| A0 unguarded | 90/90 | 90/90 |
| A1 prompt-text control | 90/90 | 90/90 |
| A2 retrieval-context control | 90/90 | 90/90 |
| A3 policy+UCAN | 33/90 | 90/90 |
| A4 full enforcement | 0/90 | 90/90 |

These are policy-relative sandbox observations. They are not legal validity,
expert fidelity, or independent human agreement. `independent_human_gold` is
false on every compact row. Closed-loop model planning remains withdrawn
(900/900 `not_started`).

## Reported results and hashes

`manifest.json` lists every reported result with SHA-256. Results are either:

- **included** in the anonymous directory bundle (recipe, tables, source
  manifests, harness, anonymized logs), or
- **explicitly retrievable** from this checkout at the recorded path and
  digest, or
- **lawful retrieval-only sources** (URI + SHA-256; bodies are not packaged).

Headline retained identities:

| Artifact | SHA-256 |
| --- | --- |
| `results/fixed_actions_admitted/raw.jsonl` | `d71c777523e454559bbc4936b89127bb7658a10ba684df44156a848c457aea07` |
| `results/fixed_actions_admitted/summary.json` | `26122e64debe4e1fcc7354dca42227f8d244ebc74e5939c29092e53e97a39656` |
| `results/tables/arm_safety_utility.json` | `ddbcf1b6128fd37e697df68002ae0658ba6e16338b6b5791dc3073abbe2ba75f` |
| `results/source_ir/metrics.json` | `dc60da670036e8f03cc982dc8b19993359583dddeb3ac2c10a827a85362e0564` |
| `benchmark/manifests/sources.json` | `55c69799805ce8466c7935f41c43a6656fbb2dce867496fb771ae07c4395feb6` |
| implementation revision | `ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c` |

The compact recipe stores only the SHA-256 of the 900 scientific outcome
rows plus the A0–A4 rates. The checker regenerates those rows from the live
`raw.jsonl` and requires the scientific fields to equal the corresponding
live values; log anonymization is forbidden from changing numeric tokens or
SHA-256 digests.

## Lawful source access (no source bodies)

Redistribution of the frozen legal PDFs, CVE shard, and SkillCenter bundle is
not included. Retrieve the exact URI, verify bytes against the recorded
SHA-256, and keep the upstream terms.

| Artifact | Revision | SHA-256 | URI |
| --- | --- | --- | --- |
| 18 USC 1030 | USCODE-2024:18-USC-1030 | `b403c8ea9d052478c35cdcdaa5361ba6ff09d3ca89b129e1bc031c870367ac76` | https://www.govinfo.gov/content/pkg/USCODE-2024-title18/pdf/USCODE-2024-title18-partI-chap47-sec1030.pdf |
| 5 USC 552a | USCODE-2024:5-USC-552a | `9a090bb5da1dd4bc151d2fc7651e659c3d56d23fad3932eaedd3f083638ab24a` | https://www.govinfo.gov/content/pkg/USCODE-2024-title5/pdf/USCODE-2024-title5-partI-chap5-subchapII-sec552a.pdf |
| 15 USC 6502 | USCODE-2024:15-USC-6502 | `39eede5f2f8dffb893574526f158e1c1bb16a3cd2047a6634d770e132b11348b` | https://www.govinfo.gov/content/pkg/USCODE-2024-title15/pdf/USCODE-2024-title15-chap91-sec6502.pdf |
| 17 USC 1201 | USCODE-2024:17-USC-1201 | `0878ee4ab36ad6fbfcbbc1fb6749ef5242f57a30f21e8119c84498edb05f1aa1` | https://www.govinfo.gov/content/pkg/USCODE-2024-title17/pdf/USCODE-2024-title17-chap12-sec1201.pdf |
| 42 USC 1320d-6 | USCODE-2024:42-USC-1320d-6 | `32bd2e92ac9ad9897e286c93b9373bdc88ad28f976215a2ff859ad029c0fefa0` | https://www.govinfo.gov/content/pkg/USCODE-2024-title42/pdf/USCODE-2024-title42-chap7-subchapXI-partC-sec1320d-6.pdf |
| 47 USC 222 | USCODE-2024:47-USC-222 | `4cc72f64f8f4a6b99809b2da804e90ba00d796f5e91e93d20b35751d21c1072e` | https://www.govinfo.gov/content/pkg/USCODE-2024-title47/pdf/USCODE-2024-title47-chap5-subchapII-partI-sec222.pdf |
| CVEfixes shard | `d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2` | `2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1` | https://huggingface.co/datasets/hitoshura25/cvefixes/resolve/d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2/data/train-00000-of-00003.parquet |
| SkillCenter security bundle | `f9dd4fec3c86d85ebf116c7408ac5ce602c418a1` | `8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4` | https://huggingface.co/datasets/Tommysha/skillcenter-bundles/resolve/f9dd4fec3c86d85ebf116c7408ac5ce602c418a1/clawskills-bundle-lite-security-v20260227.sqlite |

GovInfo U.S. Code PDFs remain U.S. government works; CVEfixes packaging is
declared Apache-2.0 but upstream repository licenses still govern any later
code copy; SkillCenter packaging MIT does not grant rights to every nested
source. This artifact includes **zero** source-body bytes.

## Anonymization and what is excluded

Raw logs packaged here are redacted by replacing `/home/<user>/` with
`/home/anonymous/` and validation-home suffixes with `REDACTED`. Scientific
numeric tokens and SHA-256 digests are required to be unchanged.

The anonymous bundle does **not** contain:

- the private author source-companion JSON (LA-001 recovery provenance)
- author identities, emails, or Overleaf project URLs
- provider credentials, API keys, or private UCAN study keys
- Docker private stores or operator home paths

Legitimate independent-source URIs (GovInfo, Hugging Face dataset pins) are
retained.

## Limitations

- Bounded `reproduce.sh` does not re-execute the 900 operator cells.
- SAT/UNSAT (`sympy` QF_BOOL) cannot authorize theorem-proof allows; Z3/cvc5
  kernels are unavailable on the sealed `PATH`.
- Expert legal fidelity, human agreement, and legal-validity rates are
  unmeasured.
- Optional author review is non-independent and was not collected as a gate.
