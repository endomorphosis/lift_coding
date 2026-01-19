# PR-063: iOS + Ray-Ban Meta MVP1 runbook (work log)

Scratchpad for iterating on the runbook in `docs/`.

## Checklist
- [x] Draft runbook outline
- [x] Add pairing + audio routing steps
- [x] Add backend bring-up steps + curl examples
- [x] Add troubleshooting matrix (6 failure modes documented)
- [x] Final pass for concision

## Work Summary (2026-01-19)

Created comprehensive runbook at `docs/ios-rayban-mvp1-runbook.md` that meets all acceptance criteria:

### Acceptance Criteria Met
✅ **Start-to-finish checklist**: Quick Start Checklist section with pre-demo, demo execution, and post-demo steps

✅ **5+ failure modes with diagnosis**: Documented 6 common failure modes:
1. Audio routing to iPhone speaker instead of glasses
2. Backend returns 401 Unauthorized
3. STT returns stub/placeholder text
4. Backend not responding / connection timeout
5. TTS not playing / silent audio
6. Bluetooth disconnection mid-demo (bonus)

✅ **Required endpoints referenced**:
- `POST /v1/command` - Command submission
- `POST /v1/tts` - Text-to-speech generation
- `GET /v1/notifications` - List notifications
- `GET /v1/notifications/{notification_id}` - Get notification details
- Plus additional endpoints: `GET /v1/status`, `POST /v1/commands/confirm`, `POST /v1/dev/audio`

✅ **No code changes**: Documentation only

### Structure Delivered

1. **Overview** - Purpose, audience, time estimate
2. **Quick Start Checklist** - 3-phase checklist for operators
3. **Prerequisites** - Hardware, software, environment variables
4. **iOS Setup** - Pairing, audio routing, app launch
5. **Backend Setup** - Server startup, health verification, data seeding
6. **Demo Script** - 5 known-good commands with expected responses
7. **Troubleshooting** - 6 failure modes with diagnosis and resolution
8. **Optional Notifications** - Deep-link flow for push notifications
9. **Rollback & Fallback** - 4 fallback strategies for demo failures
10. **API Reference** - Core endpoints with request/response examples
11. **Success Criteria** - 8 criteria for a successful demo

### Key Features

- **Operator-friendly**: Written for someone new to the system
- **Comprehensive**: Covers setup, execution, troubleshooting, and rollback
- **Actionable**: Every failure mode includes step-by-step resolution
- **Reference quality**: Includes curl examples, expected responses, verification steps
- **Production-ready**: Suitable for customer demos, internal testing, and onboarding

### Notes

- Runbook emphasizes **phone mic for input** (reliable) and **glasses speakers for output** (hands-free)
- All environment variables documented with stub vs. production modes
- Troubleshooting covers both iOS-side and backend-side issues
- Fallback procedures allow demo to continue even with partial failures
- Includes optional notification deep-link flow for advanced demos
