# Hands-Free Confirmation Flow Implementation

## Overview

This document describes the hands-free confirmation/cancel UX feature added to the mobile app for handling potentially unsafe actions that require user confirmation.

## Implementation Summary

### Changes Made

**File: `mobile/src/screens/CommandScreen.js`**

Added hands-free confirmation modal that appears when the backend returns a `pending_action` in the command response.

#### Key Features:

1. **Auto-detection of Confirmation Requirements**
   - Monitors command responses for `pending_action` field
   - Automatically triggers confirmation modal when detected
   - Logs token, summary, and expiration for debugging

2. **Voice-First UX**
   - TTS audio automatically plays when confirmation is required (if auto-play is enabled)
   - Clear spoken prompt tells user what needs confirmation
   - Large, easy-to-tap buttons for confirm/cancel (suitable for glasses with one-tap)

3. **Confirmation Modal**
   - Semi-transparent overlay with centered dialog
   - Displays action summary from backend
   - Shows token and expiration time in debug mode
   - Two large buttons: "✓ Confirm" (green) and "✗ Cancel" (red)
   - Loading indicator during API call

4. **Backend Integration**
   - Uses `confirmCommand(token)` API call from `client.js`
   - Sends confirmation token back to `/v1/commands/confirm` endpoint
   - Updates response state with confirmation result
   - Plays TTS response after confirmation

5. **Debug Logging**
   - Console logs for all confirmation events:
     - `[CommandScreen] Pending action detected`
     - `[CommandScreen] Confirming action with token`
     - `[CommandScreen] Confirmation successful`
     - `[CommandScreen] User cancelled confirmation`
   - Logs include token, summary, and expires_at

## User Flow

### Scenario: User sends a command requiring confirmation

1. User enters a command (text or audio) that requires confirmation
2. Backend returns response with `pending_action` object containing:
   - `token`: Confirmation token
   - `summary`: Human-readable description of the action
   - `expires_at`: Expiration timestamp
3. App automatically:
   - Logs the pending action details to console
   - Shows confirmation modal overlay
   - Plays TTS prompt (if auto-play enabled)
4. User sees:
   - Large warning icon and title: "⚠️ Confirmation Required"
   - Action summary (e.g., "Merge PR #123 to main branch")
   - Debug info (if debug panel enabled): token and expiration
   - Prompt: "Do you want to proceed with this action?"
   - Two buttons: "✓ Confirm" and "✗ Cancel"
5. User choices:
   - **Confirm**: Sends token to backend, executes action, plays response TTS
   - **Cancel**: Closes modal, shows "Cancelled" alert, no action taken

## API Contract

### Backend Response with Pending Action

```json
{
  "status": "confirmation_required",
  "spoken_text": "I found pull request 123. This will merge it to the main branch. Please confirm.",
  "pending_action": {
    "token": "conf-abc123xyz...",
    "summary": "Merge PR #123 to main branch",
    "expires_at": "2026-01-19T05:30:00Z"
  }
}
```

### Confirmation Request

```json
{
  "token": "conf-abc123xyz...",
  "idempotency_key": "optional-key"
}
```

### Confirmation Response

```json
{
  "status": "success",
  "spoken_text": "Pull request 123 has been merged successfully.",
  "intent": {
    "name": "pr.merge",
    "confidence": 0.95
  }
}
```

## Testing Instructions

### Manual Testing with Backend

1. **Start the Backend**
   ```bash
   cd /path/to/lift_coding
   source venv/bin/activate
   python -m src.main
   ```

2. **Configure Backend for Confirmations**
   - Ensure backend has policy-gated actions (e.g., `pr.merge`)
   - Backend should return `pending_action` for these commands

3. **Start Mobile App**
   ```bash
   cd mobile
   npm start
   # Choose iOS, Android, or Web platform
   ```

4. **Test Confirmation Flow**
   - Navigate to "Command" tab
   - Enable "Auto-play TTS" toggle (if desired)
   - Enable "Show Debug Panel" to see token details
   - Send a command that requires confirmation, for example:
     - "merge pr 123" (if backend has pr.merge policy gate)
     - Any command configured to require confirmation in backend
   - **Expected**: Confirmation modal appears with summary
   - **Expected**: TTS plays describing the action
   - **Expected**: Console logs show pending action details
   - Tap "✓ Confirm" to proceed
   - **Expected**: Modal closes, confirmation sent to backend
   - **Expected**: Success alert shown
   - **Expected**: Response updates with confirmation result
   - **Expected**: TTS plays confirmation response

5. **Test Cancel Flow**
   - Send another confirmation-required command
   - Tap "✗ Cancel"
   - **Expected**: Modal closes
   - **Expected**: "Cancelled" alert shown
   - **Expected**: No action executed on backend

### Console Debug Output Example

When a confirmation is required:
```
[CommandScreen] Pending action detected: {
  token: "conf-abc123xyz789",
  summary: "Merge PR #123 to main branch",
  expires_at: "2026-01-19T05:30:00Z"
}
```

When user confirms:
```
[CommandScreen] Confirming action with token: conf-abc123xyz789
[CommandScreen] Confirmation successful: { status: "success", spoken_text: "..." }
```

When user cancels:
```
[CommandScreen] User cancelled confirmation
```

## Design Decisions

1. **Modal vs Inline**: Chose modal for better focus and to prevent user from accidentally tapping other UI elements
2. **Auto-play TTS**: Enabled by default for voice-first experience, can be toggled off
3. **Large Buttons**: Sized for easy tapping, especially for glasses users with limited input options
4. **Debug Info**: Token and expiration shown only when debug panel is enabled to reduce clutter
5. **Console Logging**: Comprehensive logging for demo debugging without cluttering UI
6. **No Cancel API**: Cancel action only closes modal locally; backend doesn't need to be notified

## Future Enhancements

Potential improvements for production:
- Voice input for "confirm" or "cancel" commands
- Timeout countdown showing when confirmation expires
- "Repeat" button to replay the TTS prompt
- Haptic feedback on button press
- Accessibility labels for screen readers
- Multiple confirmation options (confirm/cancel/repeat/next)
- Queue multiple pending actions
