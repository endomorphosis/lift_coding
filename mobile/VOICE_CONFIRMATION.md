# Voice Confirmation Implementation

## Overview
This document describes the voice confirmation feature for hands-free operation on mobile.

## Implementation Location
Voice confirmation is implemented in:
- **CommandScreen.js**: Main command interface with integrated voice confirmation modal
- **voiceConfirmation.js**: Reusable utility for transcript interpretation

## Features

### 1. Voice Confirmation Modal
When a command requires confirmation, a modal appears with:
- Confirm/Cancel buttons (traditional UI)
- Voice button: "🎙 Voice: say 'confirm' or 'cancel'"
- Visual feedback during recording ("Listening…")
- Transcript display (in debug mode)

### 2. Voice Recognition Flow
1. User taps voice button
2. App records 1.4 seconds of audio (sufficient for single-word responses like "yes" or "no" while minimizing latency)
3. Audio is uploaded to backend for transcription
4. Transcript is parsed using `inferConfirmationDecision()`
5. Action is taken based on decision:
   - **confirm**: Confirms the action
   - **cancel**: Cancels without confirming
   - **null** (unclear): Shows dialog with what was heard, asks user to try again

### 3. Supported Keywords

#### Confirm keywords:
- "yes"
- "confirm"
- "do it"
- "proceed"
- "ok" / "okay"
- "approve"

#### Cancel keywords (priority):
- "no"
- "cancel"
- "stop"
- "never mind" / "nevermind"
- "abort"
- "don't"

**Note**: Cancel keywords take priority for safety. If both "yes" and "no" appear in transcript, the system treats it as cancel.

### 4. UX States
- **Idle**: Shows voice button and confirm/cancel buttons
- **Listening**: Shows "Listening…" indicator with spinner
- **Processing**: Brief moment while transcript is analyzed
- **Understood**: Action is executed (confirm or cancel)
- **Did not understand**: Shows alert with transcript and prompts retry

## Usage Example

```javascript
import { inferConfirmationDecision } from '../utils/voiceConfirmation';

const transcript = "yes please";
const decision = inferConfirmationDecision(transcript);

if (decision === 'confirm') {
  // Execute confirmation
} else if (decision === 'cancel') {
  // Cancel action
} else {
  // Ask user to try again
}
```

## Testing

Unit tests are provided in `mobile/src/utils/__tests__/voiceConfirmation.test.js`:
- Tests all confirm keywords
- Tests all cancel keywords
- Tests priority (cancel > confirm)
- Tests ambiguous input handling
- Tests edge cases (whitespace, punctuation, etc.)

To run tests (when Jest is configured):
```bash
cd mobile
npm test -- voiceConfirmation.test.js
```

## Audio Setup

The implementation uses:
- **Expo AV** for audio recording
- **expo-file-system** for file operations
- **Backend /v1/command** endpoint with audio input for transcription
- **Backend /v1/commands/confirm** for executing confirmations

Audio is recorded at HIGH_QUALITY preset (44.1kHz) and uploaded as base64 m4a.

## Privacy Considerations

- Voice recording duration is limited to 1.4 seconds (sufficient for single-word responses while minimizing data collection)
- Audio is deleted after transcription
- Transcript is only stored temporarily for display
- Users can always use manual buttons as fallback

## Fallback Behavior

The voice confirmation is an enhancement, not a requirement:
- Traditional Confirm/Cancel buttons always remain visible
- If voice fails, user can tap buttons
- If unclear, system prompts retry but keeps buttons available
- Works in noisy environments with manual fallback

## Future Enhancements

Potential improvements not in current scope:
- Custom wake word detection
- Longer recording duration option
- Multi-language support
- Confidence scoring from transcription
- Audio quality pre-check before recording
