# Glasses Diagnostics Screen - UI Preview

## Screen Layout

```
┌─────────────────────────────────────────┐
│  Glasses Audio Diagnostics              │
├─────────────────────────────────────────┤
│                                          │
│  ┌──────────────────────────────────┐  │
│  │ 📱 DEV Mode           [Toggle ✓] │  │
│  │ Phone mic/speaker for rapid      │  │
│  │ iteration                         │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │ Connection State                 │  │
│  │ Status: 🟢 ✓ DEV Mode Active    │  │
│  │ Audio Route:                     │  │
│  │   Phone mic → Phone speaker      │  │
│  │ [🔄 Refresh Status]              │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │ Audio Recording                  │  │
│  │ 📱 Recording from phone mic      │  │
│  │ [🎤 Start Recording]             │  │
│  │ ✓ Recording saved locally        │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │ Audio Playback                   │  │
│  │ 📱 Playing through phone speaker │  │
│  │ [▶️ Play Last Recording]         │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │ Audio Command Pipeline           │  │
│  │ Both modes use same pipeline:    │  │
│  │ Record → /v1/dev/audio →         │  │
│  │ /v1/command → /v1/tts → Play     │  │
│  │ [ℹ️ View Pipeline Details]       │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │ Implementation Status            │  │
│  │ ✓ DEV mode - Working             │  │
│  │ ✓ Recording/playback - Working   │  │
│  │ ✓ Error handling - Working       │  │
│  │ ⚠ Glasses mode - Needs native    │  │
│  │ ⚠ Backend integration - Ready    │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │ Documentation                    │  │
│  │ docs/meta-ai-glasses-audio-...   │  │
│  │ mobile/glasses/README.md         │  │
│  │ mobile/glasses/TODO.md           │  │
│  └──────────────────────────────────┘  │
│                                          │
└─────────────────────────────────────────┘
```

## Mode Comparison

### DEV Mode (Currently Active)
```
┌──────────────────────────────────┐
│ 📱 DEV Mode           [Toggle ✓] │
│ Phone mic/speaker for rapid      │
│ iteration                         │
└──────────────────────────────────┘

Status: 🟢 ✓ DEV Mode Active
Route:  Phone mic → Phone speaker
```

### Glasses Mode (Ready for Native Implementation)
```
┌──────────────────────────────────┐
│ 👓 Glasses Mode       [Toggle  ] │
│ Glasses mic/speaker (requires    │
│ native implementation)            │
└──────────────────────────────────┘

Status: 🟡 ⚠ Glasses mode (native implementation needed)
Route:  Bluetooth HFP (requires native code)
```

## Error Display Example
```
┌──────────────────────────────────┐
│ ⚠️ Last Error                    │
│ Microphone permission required   │
│ [Clear Error]                    │
└──────────────────────────────────┘
```

## Recording States

### Idle State
```
┌──────────────────────────────────┐
│ Audio Recording                  │
│ 📱 Recording from phone mic      │
│ [🎤 Start Recording]             │
└──────────────────────────────────┘
```

### Recording State
```
┌──────────────────────────────────┐
│ Audio Recording                  │
│ 📱 Recording from phone mic      │
│ [⏹ Stop Recording] (RED BUTTON) │
└──────────────────────────────────┘
```

### After Recording
```
┌──────────────────────────────────┐
│ Audio Recording                  │
│ 📱 Recording from phone mic      │
│ [🎤 Start Recording]             │
│ ✓ Recording saved locally        │
└──────────────────────────────────┘
```

## Playback States

### No Recording Available
```
┌──────────────────────────────────┐
│ Audio Playback                   │
│ 📱 Playing through phone speaker │
│ [▶️ Play Last Recording] (GRAY)  │
│ Record audio first to enable     │
└──────────────────────────────────┘
```

### Ready to Play
```
┌──────────────────────────────────┐
│ Audio Playback                   │
│ 📱 Playing through phone speaker │
│ [▶️ Play Last Recording]         │
└──────────────────────────────────┘
```

### Playing
```
┌──────────────────────────────────┐
│ Audio Playback                   │
│ 📱 Playing through phone speaker │
│ [⏹ Stop Playback] (RED BUTTON)  │
└──────────────────────────────────┘
```

## Pipeline Dialog

When "ℹ️ View Pipeline Details" is tapped:

### DEV Mode
```
┌──────────────────────────────────┐
│ Audio Pipeline Flow              │
├──────────────────────────────────┤
│ 📱 DEV MODE                      │
│                                  │
│ Record from: Phone mic           │
│ Playback through: Phone speaker  │
│                                  │
│ Full pipeline:                   │
│ 1. Record audio                  │
│ 2. Upload to /v1/dev/audio       │
│ 3. Send to /v1/command           │
│ 4. Receive /v1/tts response      │
│ 5. Play through phone speaker    │
│                                  │
│         [OK]                     │
└──────────────────────────────────┘
```

### Glasses Mode
```
┌──────────────────────────────────┐
│ Audio Pipeline Flow              │
├──────────────────────────────────┤
│ 👓 GLASSES MODE                  │
│                                  │
│ Record from: Glasses mic         │
│ Playback through: Glasses spkr   │
│                                  │
│ Full pipeline:                   │
│ 1. Record audio                  │
│ 2. Upload to /v1/dev/audio       │
│ 3. Send to /v1/command           │
│ 4. Receive /v1/tts response      │
│ 5. Play through glasses speakers │
│                                  │
│ ⚠️ Requires native Bluetooth     │
│    implementation                │
│                                  │
│         [OK]                     │
└──────────────────────────────────┘
```

## Color Scheme

- **Primary Blue**: #007AFF (buttons, toggles)
- **Success Green**: #4caf50 (success messages)
- **Warning Yellow**: #ff9800 (error card border)
- **Error Red**: #d32f2f (error text, recording button)
- **Background**: #f5f5f5 (screen background)
- **Card Background**: #ffffff (white cards)
- **Text Primary**: #000000 (titles)
- **Text Secondary**: #333333 (body text)
- **Text Tertiary**: #666666 (labels)
- **Text Hint**: #999999 (hints, disabled)

## Interaction Flow

1. User opens "Glasses" tab
2. User sees DEV mode toggle (default: off)
3. User toggles DEV mode ON
4. Status updates to "✓ DEV Mode Active"
5. User taps "Start Recording"
6. Button turns red, shows "Stop Recording"
7. User speaks into phone
8. User taps "Stop Recording"
9. Success message appears
10. "Play Last Recording" button becomes enabled
11. User taps "Play Last Recording"
12. Audio plays through phone speaker
13. Button shows "Stop Playback" while playing
14. Playback completes automatically

## Accessibility

- All buttons have descriptive labels
- Status indicators use both icons and text
- Error messages are clear and actionable
- Touch targets are at least 44x44 points
- Color is not the only indicator (icons + text)
