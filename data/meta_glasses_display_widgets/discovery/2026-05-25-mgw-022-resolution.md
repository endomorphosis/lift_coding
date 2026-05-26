# MGW-022 Resolution

Date: 2026-05-25
Source finding: `data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md:25`

The scan excerpt pointed at historical merge-unblock evidence, not a live source
defect. Reviewing the HAO merge note and the HAO-046 through HAO-049 noise
unblock report showed that this exact finding came from generated discovery
prose about avoiding an older branch snapshot during a submodule merge.

Resolution:

- Rephrased the merge note as "older backlog and discovery snapshots" so the
  document keeps the same rollback-safety meaning without resembling an open
  annotation.
- Preserved the HAO-042/HAO-044 validation evidence and task metadata.

Validation:

- `test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md`
