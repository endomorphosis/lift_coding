This handoff preserves NS022 and NS019 ownership. It is preparation only: no live file, native task, receipt or envelope was changed here. Root accepted the integrated NS024 PDF in `actual_post32_v1/ns024_integrated_root_review_v1.private.json`, SHA256 `ad2da401c0e16ff07c0b4f469c464e40cdae10a1ce12f3ad2c7c0e9b79736e63`.

Use the task's current authenticated scope and preserve these existing outputs byte-for-byte:

- `papers/completion/neurosymbolic_supervision/manuscript/main.tex` and `manuscript/paper.pdf`, owned by NS022.
- `papers/completion/neurosymbolic_supervision/manuscript/generated/figures/family_useful.pdf` and all other NS019-generated outputs. In particular, do not replace the current NS019 figure with either figure stored in the off-live manuscript source package.
- Every foreign task receipt/snapshot and all shared user templates.

The simple route is to retain the complete final editable manuscript under NS024's already-owned snapshot directory, reconstruct only into a fresh temporary directory, and publish task outputs only at NS024's declared release, audit, checklist/style and template-input paths. No broader manuscript write authority is needed.

1. Copy the 26 text files under this handoff's `payload/` into `papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-024/manuscript_source_v1/`, preserving their relative paths. There are 22 original text sources, two PDF source carriers encoded as canonical base64 ASCII, a source manifest, and a helper. The manifest SHA256 is `89bffcb1545d491945dba5604dc11ea3fa0a0a9745d2b3ef44b0fd85a1aa0973`. All 24 decoded selected sources match the exact sources of the accepted actual compile. The original generated PDF and repaired layout PDF are separate source identities; the original generated PDF is retained for custody and the manuscript loads only the repaired `layout/family_useful.pdf`.

2. Use the retained helper for a real source verification command, retaining actual stdout/stderr and command metadata beneath NS024 snapshots:

   ```sh
   python3 -B papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-024/manuscript_source_v1/build_from_snapshot.py --manifest-sha256 89bffcb1545d491945dba5604dc11ea3fa0a0a9745d2b3ef44b0fd85a1aa0973 --verify-only
   ```

   This preparation actually ran that mode against the handoff: all 24 sources verified, including strict in-memory decoding of both PDFs; no materialized files or compiler calls occurred. The compile branch is supplied for an ordinary worker's real execution and has not been run by this preparation. To exercise it, use an unused absolute temporary output path, for example:

   ```sh
   python3 -B papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-024/manuscript_source_v1/build_from_snapshot.py --manifest-sha256 89bffcb1545d491945dba5604dc11ea3fa0a0a9745d2b3ef44b0fd85a1aa0973 --output /tmp/ns024-manuscript-build-v1
   ```

   The helper refuses an existing output, non-temporary output, or a path inside a Git repository. It resolves available `pdflatex`/`bibtex` commands without changing the `pdflatex` invocation name; explicit `--pdflatex` and `--bibtex` arguments can select the worker's already-available toolchain. Never assume host paths are available inside the worker. It decodes all 24 sources into `source/`, runs three `pdflatex -no-shell-escape` passes around one BibTeX pass, and records real source hashes, argv, time, exit status, logs and generated PDF hash in `execution/`. Retain those text records in a new NS024 snapshot subdirectory. No scientific reducer, provider, scorer or supplement reproducer is invoked by this helper.

3. The reviewed actual PDF to adopt is `ns024_actual_integrated_manuscript_v1/manuscript_v2/build/main.pdf`, SHA256 `0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862`, 252,576 bytes. Its existing actual four-command compile record is `build_execution_v2/result.private.json`, SHA256 `aef9146a234e08ebed053c4be53d703a5716ee601146e6e6ea341a463775435d`. Retain inherited evidence as inherited root execution, not a claim that the ordinary worker executed those commands. A fresh TeX build may change creation dates/PDF identifiers; compare its actual text, fonts, sections and source identities, and record its own byte hash. Do not silently substitute a different newly generated PDF for the reviewed byte-exact artifact or claim identical PDF bytes without measuring them.

4. Adopt the exact reviewed PDF and the already-built combined ZIP through the normal native artifact collection into the four precisely scoped raw binary files below. Root has applied the two additional snapshot paths through the normal ready-task body CAS (revision 7 to 8), recorded in `actual_post32_v1/ready_release_binary_receipt_guidance_v2/result.private.json`, SHA256 `6816b2edb5e09b13fab4c1ff25c1d3bbaaa8a33cae9977595d970c856e0c68e7`. This is a bound prior root update, not a native operation performed by this handoff. Check the current claimed task's envelope before proposing these files, and never broaden the binary scope yourself.

   | Kind | Exact repository path | Bytes | SHA256 |
   |---|---|---:|---|
   | PDF output | `papers/completion/neurosymbolic_supervision/release/paper.pdf` | 252576 | `0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862` |
   | PDF raw receipt snapshot | `papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-024/release/paper.pdf` | 252576 | `0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862` |
   | ZIP output | `papers/completion/neurosymbolic_supervision/release/supplement.zip` | 2280657 | `48cee756e4e1bcdcf4d541b6c8721f21cba0800e990e1159a64f3eeb888a0b07` |
   | ZIP raw receipt snapshot | `papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-024/release/supplement.zip` | 2280657 | `48cee756e4e1bcdcf4d541b6c8721f21cba0800e990e1159a64f3eeb888a0b07` |

   Keep the same ceilings: 16,000,000 bytes per file, 16,000,000 patch/materialization budget and 24,000,000 serialized output budget. These four raw binaries total 5,066,466 bytes, but that is not a measurement of the final native proposal envelope: measure the real serialized proposal and retain the native gate result. Existing before-content and text/log snapshots also count. Do not stage raw PDF/ZIP duplicates elsewhere. The normal verifier requires the raw output and its raw snapshot to hash identically; base64 text cannot substitute for these two receipt snapshots. Base64 is used only to carry otherwise-unowned editable source PDFs as ordinary text.

5. Complete all 12 NS024 deliverables from its current task contract: release README, manifest, reproduction wrapper, ZIP and PDF; anonymity report, LLM disclosure, author-attestation note and workshop compliance audit; manuscript checklist, unchanged official style; and submission template-input checksums. The latter checklist/style paths are explicitly owned by NS024; copying its full `main.tex` or any generated figure to the shared manuscript directory is not. The submitted source manifest can point to the selected editable snapshots instead. The release manifest should bind the actual final PDF/ZIP, the unchanged combined/component manifests, and the retained source/evidence; keep operational private handoffs and author-only notes outside the anonymous ZIP.

6. In the ordinary receipt, add all retained source carriers, helper, manifest, actual command logs and inherited evidence records to `artifacts` with their real raw file hashes. Retain actual logs under NS024's snapshots and bind named Python helpers with `script_artifact`. List only declared scientific/package deliverables in `outputs`, mapped to separate hashed snapshots. Do not map evidence snapshots to themselves as outputs and do not add snapshot-only editable sources to `outputs`; their role is immutable supporting evidence. Cover all nine exact current acceptance criteria in order, with factual explanations and artifact references. Preserve explicitly narrowed reproduction, missing human measurements, unmachine-checked conditional arguments, unsettled charges, and author-only confirmations.

7. Record actual ordinary validation, then let the native framework decide completion:

   ```sh
   python3 scripts/paper_supervisors.py verify-task --paper neurosymbolic_supervision --task NS-024
   ```

   Verify that NS022/NS019 protected output preimages remain unchanged and that their earlier validations are unaffected. Do not mark native success based on this handoff or fabricate a provider attempt, author proofread, ethics attestation, outside review or submission. The actual accepted PDF is main pages 1–6, references 7, existing technical appendices 8–12, disclosure 13 and checklist 14–20; root reviewed all eight new pages and the actual font/source checks. The ordinary worker must still keep its own real custody, audit and receipt evidence.

The active lane's v3 implementation, not the root external repository's older v2 baseline, is the relevant source for binary admission. The exact source/line bindings and allowed future paths are recorded in `framework_scope_review.private.json`. The v3 route keeps text changes within ordinary owned Outputs while separately restricting raw binary changes to the four exact declared PDF/ZIP paths. The NS024 snapshot assembly is self-contained and requires no NS022 path or native-task change.
