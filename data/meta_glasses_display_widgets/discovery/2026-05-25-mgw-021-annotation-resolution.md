# MGW-021 Code Annotation Resolution

Date: 2026-05-25
Task: MGW-021
Source finding: `data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md:24`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-021-codebase-scan-55c0165aa8e2.md`

## Finding

The scan excerpt pointed at generated HAO discovery prose, not a live source
defect. The sentence described where the HAO-038 validation command already
existed, but the broad annotation scanner treated the wording as follow-up work.

## Resolution

- Reworded the HAO-041 validation-unblock note to refer to the supervised
  backlog entry without the scanner-triggering phrase.
- Added the Hallucinate discovery directory to the MGW codebase-scan skip list
  so generated HAO discovery notes do not become MGW follow-up tasks.
- Added focused wrapper coverage for the generated-discovery skip prefixes.

## Validation

- `test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md`
- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py -k codebase_scan_skips_generated_discovery_dirs`
