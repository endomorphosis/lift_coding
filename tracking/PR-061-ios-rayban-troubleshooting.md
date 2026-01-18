# PR-061: iOS + Ray-Ban Meta troubleshooting guide (docs-only)

## Goal
Document the common failure modes for Ray-Ban Meta Bluetooth audio on iOS and how to recover quickly during demos.

## Why
Bluetooth audio routing is the biggest source of demo flakiness. A single troubleshooting guide makes the team faster and prevents repeated rediscovery.

## Scope
- Create a troubleshooting guide that covers:
  - output routing failures (speaker vs bluetooth)
  - input mic selection issues (HFP mic not available)
  - interruptions (phone calls, Siri, background/foreground)
  - sample rate/format issues for recording and backend ingestion
  - "known good" AVAudioSession category/mode/options guidance
  - a minimal on-device diagnostics checklist (what to display)

## Deliverables
- `docs/ios-rayban-troubleshooting.md`

## Acceptance criteria
- The guide is actionable in a live demo.
- Includes a short "if it breaks, do this" flowchart.
- References the MVP1 runbook and the audio routing PRs.
