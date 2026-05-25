# HAO-046 Through HAO-049 Codebase Scan Noise Unblock

Date: 2026-05-25
Tasks: HAO-046, HAO-047, HAO-048, HAO-049

## Finding

The codebase feeder correctly drained the original HAO board and then scanned
for more work, but four follow-up findings came from generated discovery
evidence rather than live implementation surfaces:

- HAO-046 flagged historical `Status: todo` prose in the HAO-025 discovery note.
- HAO-047 flagged a fenced evidence command that referenced the todo board path.
- HAO-048 flagged a sentence in the HAO-041 validation-unblock evidence.
- HAO-049 flagged a sentence in the HAO-044 merge-unblock evidence.

These are not actionable source defects. Keeping them open would make the
supervisor feed itself cleanup work from its own generated reports.

## Resolution

- The HAO codebase scanner now skips generated discovery report directories.
- Markdown and reStructuredText fenced code blocks are ignored by annotation
  scanning, so evidence commands do not become backlog items.
- HAO-046 through HAO-049 are marked completed because the feeder behavior that
  produced them has been corrected.

## Validation

Focused validation:

```bash
pytest tests/test_hallucinate_multimodal_control_todo_queue.py -k 'codebase_scan'
```

Expected result: the scanner still files real source annotations, waits for low
open backlog, and ignores generated discovery reports plus fenced markdown
examples.
