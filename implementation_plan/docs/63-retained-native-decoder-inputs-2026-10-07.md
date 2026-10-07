# Retained native inputs and the next reconstruction improvements

The selected Legal384/768 normative decoders now have a separate opt-in input
contract for existing source-only native caches. This extends
[original split replay](62-normative-decoder-runtime-2026-10-07.md) while reusing
the original selected weights, donor, preprocessing and GTE embeddings.
The source plan, raw producer record and assembled cache must agree before
model restoration. The [datasets contract](https://github.com/endomorphosis/ipfs_datasets_py/blob/c4382ae53ab9497245fccdf85855f0e314711fbc/docs/autoencoders/normative_cached_legal_ir_runtime.md)
describes the public API. See the [retained evidence](../../artifacts/normative-retained-cache-runtime-20261007/README.md).

## Completed scope

The first retained cohort is the earlier exposed-v3 modality wording panel:
48 paragraphs, 180 clauses, 216 unique vectors and 228 aliases, with twelve
paragraphs at each 1/2/4/8-clause size. Actual retained source lengths are 11–91
GTE-small tokens and 12–111 multilingual GTE tokens. Both producer experiments
used a 512-token ceiling. The 768D historical 8192-token profile remains a
separate field; this contribution does not extend actual encoder or decoder
budgets.

`normative-retained-source-cache-legal-ir/v1` requires the exact selected recipe,
checkpoint bytes, native width, semantic IR task and original 32-value codec.
It reassembles the full source packet using the existing producer validators,
then performs typed canonical equality against the supplied cache. It preserves
distinct producer/context digest conventions and literal UTF8 byte/character
spans. The original replay contract continues to require its saved validation
split, and both use the unchanged numerical model and saved TRAIN transforms.

Current owners, checkpoints and cache files retain single-link custody. Two
archived 384D producer files have 26 links and use a separately declared
historical metadata witness policy, with exact byte/hash/identity checks and
joint closing endpoints. Archived code is not executed. The report's declared
first-attempt source artifact locator is preserved. Current loaded origins,
including the dynamically created multilingual profile object, are checked
before helper use and at closing fences.

Review reproduced contradictory 768D records accepted by the older producer
validator: a different execution device, altered model/profile/directories,
partial checkpoint loading, unsuccessful dense-path checks, boolean token
masks, float source counts, substituted authority flags, extra targets and
modified published asset identities. The new adapter refuses these records
without changing the historical producer or claiming fresh encoder execution.
The recorded seven encoder asset identities are joined to the existing pinned
published constants; encoder payloads are not reloaded or reauthenticated.

Native ModelManager selectors remain exact and separate from this execution
contract. The previously imported/publicly uploaded weights remain the selected
assets. This contribution creates no new model version or database registration.
Schema/profile/format selectors remain null, binding resolution requires its own
catalog observation, and all runtime-release, quality, teacher and proof
qualification remains false.

## Validation

All 105 new controls and 240 existing controls pass: 345 distinct cases with no
failures/errors/skips. Independent review approved the final source contract.
Actual CPU1 replay generated four selected states × 48 rows, all EOS, with
unchanged model tensors/source vectors and preserved RNG. A separate process
found 48/48 exact token/status/EOS parity against each same-state archived
exposed-v3 prediction file. Generation opened neither targets nor prior
predictions and executed no encoder, optimizer, fitting, network or database
operation. No fresh gold, semantic holdout or prose reconstruction was scored.

## Next work in dependency order

1. **Measure the right reconstruction.** Keep source-vector MSE, exact semantic
   JSON, normalized meaning/facets, actual free-running token sequences and exact
   UTF8 prose reconstruction as separate metrics. Retain failed rows and their
   source spans. Low training loss or identical archived predictions cannot
   establish fresh semantic quality or recover original wording from a lossy IR.
   A legal prose head needs its own task/checkpoint and explicit lexical/residual
   information contract. Score formatting and punctuation separately from
   meaning; a source archive copy is not learned reconstruction.
2. **Improve learned meaning using existing evidence.** Follow the other agent's
   [balanced wording proposal](61-autoencoder-reconciliation-2026-10-07.md) across
   the original 90 rule identities. Its newly prepared source caches belong to
   a different TRAIN schema and must not be substituted into this exposed panel.
   Review source/formal targets and exclusions before fitting. Preserve the
   original and normative TRAIN banks, codec, initialization, budget and matched
   controls. Keep this exposed-v3 cohort and prior finals out of fitting/selection.
   Report all semantic facets and actual greedy outputs, not only scalar probes.
3. **Add independent qualifiers and semantic holdouts.** Use the existing
   qualifier intake/context/review owners for nonempty conditions, exceptions
   and temporal context. Keep unavailable source/context and rejected rows
   visible. Assign separate decoder tasks to normative32, word and byte codecs.
   Novel strings around already exposed meanings remain wording generalization;
   new semantic combinations need an independently reviewed held-out cohort.
4. **Reuse learned tensors across widths.** Retain each existing 8D, 384D and
   768D asset lineage and native embeddings. Define shape/name/dtype/codec maps
   for transferable output heads, token embeddings and recurrent layers, with
   explicit width-specific projections and saved preprocessing. Compare the
   retained native768 warm-start endpoint against matched transfer variants;
   do not restart an available decoder randomly or pad 384D vectors into native
   768D inputs. Separate teacher reliability, actual rollout distillation and
   target supervision; publish provenance and ablation results per task.
5. **Expand spans after those gates.** Keep encoder input budget, decoder output
   budget and source-clause geometry as separate experiments. A historical
   8192-token encoder profile does not make the eight-clause/output512 decoder
   a long-document reconstructor. Prepare complete long-span token/offset
   records, segmentation/context contracts and hierarchical decoding before
   evaluating enlarged source spans. Maintain the existing small paths alongside
   the new path.
6. **Ground IntentIR against the repository under test.** Scan an immutable
   repository revision into path/blob/span/dependency inventories. Bind each
   CodebaseIR candidate to the exact cache producer, decoder task/checkpoint,
   schema version and ModelManager catalog observation. Match IntentIR obligations
   to those current code spans; changed source or dependencies invalidate derived
   candidates, plans and proof entries. Let the supervisor planner distinguish
   candidate formalization, formally checked facts and verified proofs. Unknown
   or unproved obligations remain explicit, with counterexamples and repair
   actions rather than optimistic proof-cache entries.
7. **Keep inventories and training isolated.** Maintain CodebaseIR, SecurityIR,
   LegalIR and IntentIR × 8D/384D/768D cells, then separate schema/version/task/run
   and codebase revision beneath each cell. Use distinct DuckDB/DuckLake data
   inventories and Hugging Face model repositories/releases; the shared
   ModelManager catalogs exact assets rather than mixing training data. Online
   CodebaseIR adaptation belongs to a repository-specific shadow run with replay
   data, evaluation/exclusion records and a reviewed promotion decision. Preserve
   the current decoder and proof cache while the shadow run is measured.

Reconciliation includes the concurrent supervisor comparison/audit-IPC progress
pinned by workspace main `a9c3f943...`, and the subsequent qualified package
alias supervisor repairs at `dcb8eb8a...`; none of that work is overwritten by
this input adapter. Public GitHub integration and byte readback are required before
reporting the source/evidence contribution as available on main.
