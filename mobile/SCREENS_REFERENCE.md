# Mobile Screens Reference

This reference documents the screens currently implemented under [mobile/src/screens/](src/screens/).

## Screen Inventory

### `StatusScreen`

Purpose:
- Backend connectivity and service status checks.

### `CommandScreen`

Purpose:
- Primary command entry surface for text/audio command submission.

Notes:
- Supports debug visibility for request/response inspection.

### `ConfirmationScreen`

Purpose:
- Confirm or cancel pending destructive operations.

### `TTSScreen`

Purpose:
- Text-to-speech testing utilities for backend audio generation.

### `SettingsScreen`

Purpose:
- Local app settings such as backend URL, user identity, and notification behavior.

### `NotificationsScreen`

Purpose:
- Notification list, filtering, and navigation to relevant task/command detail.

### `ResultsScreen`

Purpose:
- Agent and command result browsing, including follow-on task handoff.

### `ActiveTasksScreen`

Purpose:
- Active task monitoring view with state updates and deduplicated task list behavior.

### `TaskDetailScreen`

Purpose:
- Detail view for an individual task and lifecycle state.

### `GlassesDiagnosticsScreen`

Purpose:
- Audio route and wearable diagnostics, local capture/playback checks, transport-session cursor checks.

### `PeerChatDiagnosticsScreen`

Purpose:
- Peer chat diagnostics, outbox state controls, and transport debugging utilities.

## Navigation Notes

The app includes both primary user workflows and diagnostics workflows. Some diagnostics surfaces are intended for development/testing and may be hidden or deprioritized in production-oriented builds.

## Related Docs

- [mobile/README.md](README.md)
- [docs/mobile-client-integration.md](../docs/mobile-client-integration.md)
- [docs/meta-ai-glasses.md](../docs/meta-ai-glasses.md)
