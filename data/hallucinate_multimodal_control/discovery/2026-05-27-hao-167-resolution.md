# HAO-167 Resolution

Date: 2026-05-27
Task: HAO-167
Source finding: `work/PR-047-ios-audio-route-monitor.md:14`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-27-hao-167-codebase-scan-98ff09f42056.md`

## Finding

The codebase scanner flagged the PR-047 work plan because an earlier reference
list included `mobile/glasses/TODO.md`. That file is a broad glasses
implementation checklist with unrelated iOS, Android, testing, and polish
follow-up work, while PR-047 is scoped to the iOS AVAudioSession route monitor
and JS bridge.

## Resolution

- Confirmed `work/PR-047-ios-audio-route-monitor.md` no longer lists the broad
  checklist as a PR-047 reference.
- Kept the PR-047 references anchored to concrete evidence for this slice: the
  iOS Expo module route monitor and bridge, the JS module API surface, module
  documentation, and the diagnostics screen.
- Added a HAO-167 resolution note to the PR-047 work plan so the stale scanner
  finding is recorded without changing the machine-readable backlog fields.

## Validation

```bash
test -f work/PR-047-ios-audio-route-monitor.md
```

Result: passed.
