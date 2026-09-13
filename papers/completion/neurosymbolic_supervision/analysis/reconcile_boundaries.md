This prepared helper completes the NS020 reconciliation only after actual complete NS017 evidence and the committed NS019 results exist. Installing these two source files does not complete NS020. No actual final output has been generated during preparation.

From the repository root, supply the actual reviewed file digests:

```sh
python3.12 -B papers/completion/neurosymbolic_supervision/analysis/reconcile_boundaries.py \
  --repository "$PWD" \
  --manifest-sha256 ACTUAL_REVIEWED_NS017_MANIFEST_SHA256 \
  --ablation-manifest-sha256 ACTUAL_COMMITTED_NS018_MANIFEST_SHA256 \
  --results-sha256 ACTUAL_COMMITTED_NS019_RESULTS_SHA256 \
  --output /absolute/fresh/ns020-reconciled-final32
```

The command writes exactly four files relative to that fresh directory:

- `analysis/boundary_witnesses.json`
- `manuscript/generated/table18.tex`
- `audit/final_claim_evidence_matrix.json`
- `analysis/failure_cases.md`

The ordinary NS020 worker reviews and adopts them under `papers/completion/neurosymbolic_supervision/`, runs its normal validator, and retains an actual task receipt. This helper makes no task or native API calls and creates no completion authority.

The exact existing NS019 renderer/input reader (SHA256 `1aa277d0539216b7071ec81ba8f6b6b44acbb0dece9c00894d4b4b8c8d031363`) supplies complete32, root-review, frozen order/policy, Ed25519 signature and deterministic numerical checks. The helper imports that hash-bound module with its main disabled, calls only `inputs` and the deterministic nonplotting `render`, and requires `analysis/results.json` to equal the reader's full regenerated result bytes. It creates no second estimator or uncertainty rule. Python 3.12 and the NS019 reader's original metadata, prior-cost, NS018 and OpenSSL prerequisites remain required. An incomplete NS017 manifest is rejected before any cell document is opened.

The six installed `writing_inputs/ns020_boundary_preparation_v2/` inputs are pinned byte for byte. Their original source-evidence references are provenance, not instructions to open author-host paths or rerun old tests. All six historical table rows, all 32 original claim IDs/text, the historical false reuse of 1/26, unavailable native proof and optional extension scope, local-shim limitations, and every prior failure paragraph remain preserved. The historical Table18 is byte-identical at its correct manuscript path. Five separate final joins receive 32 original-order actual metadata rows each.

Signed original response/proposal digests, signed terminal disposition digests, and operator terminal-observation digests are different commitments. The helper verifies their distinct joins. It reads only retained objects through the NS017 object map, never original private paths. Signed/public receipt and candidate-review metadata are directly read and hash checked. Candidate inventory/patch digests are read from retained binding metadata; candidate code, patches, public archives and hidden oracle bodies are not opened. Original grant/client/cleanup/source bodies may not be included in the bundle; their records explicitly distinguish available objects from original digest commitments already checked by strict analysis and root review. This command does not claim to rerun the full service/native admission or original cleanup checks.

For a reconstructed zero-change binding after a known proposal failure, the complete candidate-source allowlist/payload entry should carry `candidate_binding_metadata_origin: "derived_zero_change_after_failed_proposal"`. Its corresponding root-reviewed additive disclosure must use category `derived_zero_change_candidate_metadata` and retain a sanitized statement plus evidence references for the original file's absence, signed baseline inventory and reconstruction/root review. The unchanged candidate exporter preserves this extra entry field. Marked derivations without that disclosure fail closed. A separately present derivation disclosure is also recognized. Zero-change shape alone does not imply that the original binding file was absent. A known failure with no derivation disclosure remains labeled with file origin unclaimed, and no pre-score review is invented. Administrative/authentication/environment delays remain separate additive disclosures and do not change the frozen outcome/resource rule.

The claim matrix resolves each original claim's disposition. “Resolved” means retained, narrowed, conditional, untested or withdrawn; it does not mean all original claims were proved. Only the original aggregate/design claims `C-ABS-01` and `C-19` receive the copied, limited actual A/B summary. Net settled cost, isolated false admission and human semantic fidelity remain null. Other architectural, reuse, routing, proof, publication and extension claims retain their historical bounded scope without invented final efficacy. The frozen descriptive interval stays conditional on eight family blocks with two nested repetitions.

The failure report places current actual rows/disclosures before the exact historical preparation text. It clearly labels the older text as historical, including its then-deferred final rows. Child, wrapper, gateway, scorer, client, grant-to-terminal and operator clocks remain separate and non-additive. Missing charges and AI effort are unavailable, not zero. Incomplete hidden collection is not an observed hidden assertion failure or a proved infrastructure fault. No outside human reviewer is introduced as a completion gate.

These outputs are internal evidence and may contain private provenance paths. They are not an anonymous release component or an authorization to publish. NS024 still combines the separately reviewed boundary, prior-cost and actual final32 public components with the eligible source/licence material, retaining the original-to-derivative mappings.
