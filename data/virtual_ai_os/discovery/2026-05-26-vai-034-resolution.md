# VAI-034 Resolution

Date: 2026-05-26
Source finding: `data/hallucinate_multimodal_control/discovery/2026-05-25-hao-060-objective-gap-8e0fb6e29f18.md:33`

The scan excerpt was generated HAO objective-gap discovery prose, not live source
debt. It used the static-annotation keyword in ordinary guidance for splitting
large objective gaps, so the VAI static scan treated generated evidence as a new
source finding.

## Resolution

- Reworded the cited HAO discovery sentence to describe a generated backlog item.
- Added sibling generated discovery, state, and worktree directories to the VAI
  supervisor static-scan skip list.
- Added focused coverage proving VAI static scans still report real source
  annotations while ignoring generated discovery reports from the VAI, HAO, and
  Meta display feeds.

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py -k codebase_scan
test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-060-objective-gap-8e0fb6e29f18.md
```
