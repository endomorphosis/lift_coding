# iOS Audio Session Interruption Testing Guide

**Purpose**: Manual test checklist for validating iOS audio session interruption handling and background/foreground behavior.

---

## Prerequisites

- [ ] iPhone with iOS 14+ (physical device required)
- [ ] Ray-Ban Meta glasses or Bluetooth headphones paired and connected
- [ ] Lift mobile app installed with PR-085 changes
- [ ] Access to app diagnostics screen

---

## Test 1: Phone Call Interruption During Playback

**Goal**: Verify TTS playback pauses during phone call and resumes after.

### Setup
1. Pair and connect Bluetooth glasses/headphones
2. Open app diagnostics screen
3. Verify output route shows "Bluetooth"

### Test Steps
1. [ ] Start TTS playback through glasses
2. [ ] While audio is playing, receive or make a phone call
3. [ ] Verify: Playback pauses immediately when call begins
4. [ ] Take the call for 5-10 seconds
5. [ ] End the call
6. [ ] Verify: Audio session re-activates automatically
7. [ ] Verify: Playback resumes through glasses (not speaker)
8. [ ] Verify: Audio quality remains clear

### Expected Results
- ✅ Playback pauses cleanly during call
- ✅ No crash or error
- ✅ Audio session re-activates after call ends
- ✅ Route remains on Bluetooth (doesn't fallback to speaker)
- ✅ Playback can resume successfully

### Debug Info to Check
- Check Xcode console for `[GlassesPlayer] Interruption began - paused playback`
- Check for `[GlassesPlayer] Interruption ended - resumed playback`
- Verify no error messages about audio session activation

---

## Test 2: Siri Interruption During Playback

**Goal**: Verify Siri invocation is handled gracefully.

### Setup
1. Ensure Siri is enabled (Settings → Siri & Search)
2. Connect Bluetooth glasses
3. Start TTS playback

### Test Steps
1. [ ] Start TTS playback through glasses
2. [ ] While audio is playing, invoke Siri (hold side button or say "Hey Siri")
3. [ ] Verify: Playback pauses when Siri activates
4. [ ] Say a simple command to Siri (e.g., "What time is it?")
5. [ ] Dismiss Siri or let it complete
6. [ ] Verify: Audio session re-activates
7. [ ] Verify: Playback resumes through glasses

### Expected Results
- ✅ Playback pauses when Siri starts
- ✅ No crash or error
- ✅ Audio session re-activates after Siri dismisses
- ✅ Route remains on Bluetooth
- ✅ Playback resumes successfully

---

## Test 3: Phone Call Interruption During Recording

**Goal**: Verify recording pauses during phone call and resumes after.

### Setup
1. Connect Bluetooth glasses/headphones
2. Open app diagnostics screen

### Test Steps
1. [ ] Start audio recording
2. [ ] While recording, receive or make a phone call
3. [ ] Verify: Recording pauses immediately when call begins
4. [ ] Take the call for 5-10 seconds
5. [ ] End the call
6. [ ] Verify: Audio session re-activates
7. [ ] Verify: Recording resumes
8. [ ] Stop recording
9. [ ] Playback the recording to verify it captured audio before and after the call

### Expected Results
- ✅ Recording pauses during call
- ✅ No crash or error
- ✅ Recording resumes after call ends
- ✅ Route remains on Bluetooth
- ✅ Recorded file is valid and contains audio

### Debug Info to Check
- Check for `[GlassesRecorder] Interruption began - paused recording`
- Check for `[GlassesRecorder] Interruption ended - resumed recording`

---

## Test 4: Background/Foreground Transition During Playback

**Goal**: Verify audio session persists when app is backgrounded and foregrounded.

### Setup
1. Connect Bluetooth glasses
2. Start TTS playback

### Test Steps
1. [ ] Start TTS playback through glasses
2. [ ] Press home button to background the app (audio should continue)
3. [ ] Wait 5 seconds
4. [ ] Return to the app (tap app icon or use app switcher)
5. [ ] Verify: Audio session configuration is re-applied
6. [ ] Verify: Playback continues through glasses
7. [ ] Start a new playback
8. [ ] Verify: New playback routes correctly to glasses

### Expected Results
- ✅ Audio continues playing when app backgrounds (if system allows)
- ✅ Audio session re-applies configuration on foreground
- ✅ Route remains on Bluetooth after foreground
- ✅ New playback works correctly

### Debug Info to Check
- Check for `[ExpoGlassesAudio] Re-applied audio session configuration on foreground`

---

## Test 5: Multiple Interruptions in Sequence

**Goal**: Verify handling of rapid or sequential interruptions.

### Setup
1. Connect Bluetooth glasses
2. Start TTS playback

### Test Steps
1. [ ] Start TTS playback
2. [ ] Invoke Siri briefly, then dismiss
3. [ ] Immediately receive a phone call
4. [ ] End the call
5. [ ] Verify: Audio session recovers after each interruption
6. [ ] Verify: Playback can resume
7. [ ] Verify: Route remains on Bluetooth

### Expected Results
- ✅ System handles multiple interruptions without crashing
- ✅ Audio session re-activates after final interruption
- ✅ Route remains stable

---

## Test 6: Interruption While No Audio is Active

**Goal**: Verify system handles interruptions gracefully even when no audio is playing.

### Setup
1. Connect Bluetooth glasses
2. Open app (no playback or recording active)

### Test Steps
1. [ ] App is idle (no audio active)
2. [ ] Receive a phone call
3. [ ] Take the call
4. [ ] End the call
5. [ ] Start TTS playback
6. [ ] Verify: Playback starts successfully through glasses

### Expected Results
- ✅ No crash during idle interruption
- ✅ Subsequent playback works normally
- ✅ Route is correct

---

## Test 7: Notification Sound Interruption

**Goal**: Verify brief interruptions (notifications) don't disrupt audio routing.

### Setup
1. Connect Bluetooth glasses
2. Enable notification sounds (Settings → Sounds)
3. Start TTS playback

### Test Steps
1. [ ] Start TTS playback through glasses
2. [ ] Receive a notification (text message, email, etc.)
3. [ ] Verify: Brief interruption for notification sound
4. [ ] Verify: Playback continues or resumes automatically
5. [ ] Verify: Route remains on Bluetooth

### Expected Results
- ✅ Playback handles brief notification interruption
- ✅ Audio session remains stable
- ✅ Route doesn't fallback to speaker

---

## Test 8: Bluetooth Disconnect During Playback

**Goal**: Verify route fallback when Bluetooth disconnects mid-playback.

### Setup
1. Connect Bluetooth glasses
2. Start TTS playback

### Test Steps
1. [ ] Start TTS playback through glasses
2. [ ] While playing, turn off glasses or disconnect Bluetooth
3. [ ] Verify: Audio automatically falls back to phone speaker
4. [ ] Reconnect Bluetooth glasses
5. [ ] Start new playback
6. [ ] Verify: Route switches back to Bluetooth automatically

### Expected Results
- ✅ Playback falls back to speaker when Bluetooth disconnects
- ✅ No crash
- ✅ Route switches back to Bluetooth when reconnected
- ✅ New playback works through glasses

---

## Test 9: Start Playback During Active Interruption

**Goal**: Verify deferred playback when interruption is already active.

### Setup
1. Connect Bluetooth glasses
2. Start a phone call (keep it active)

### Test Steps
1. [ ] Make a phone call and keep it active
2. [ ] While on the call, attempt to start TTS playback in the app
3. [ ] Verify: Playback is deferred (not started during call)
4. [ ] End the phone call
5. [ ] Verify: Deferred playback starts automatically after call ends

### Expected Results
- ✅ Playback doesn't interfere with phone call
- ✅ Playback is deferred during interruption
- ✅ Playback starts automatically when interruption ends

### Debug Info to Check
- Check for `[GlassesPlayer] Playback deferred due to active interruption`

---

## Test 10: App Termination and Restart

**Goal**: Verify audio session configuration persists across app launches.

### Setup
1. Connect Bluetooth glasses

### Test Steps
1. [ ] Force quit the app (swipe up from app switcher)
2. [ ] Relaunch the app
3. [ ] Open diagnostics screen
4. [ ] Verify: Output route shows Bluetooth
5. [ ] Start TTS playback
6. [ ] Verify: Playback routes to glasses correctly

### Expected Results
- ✅ Audio session configuration is applied on app launch
- ✅ Route detection works correctly
- ✅ Playback works through glasses

---

## Diagnostic Verification Checklist

**Before each test, verify these values in the diagnostics screen:**

### Audio Route Status
- [ ] Current output route: _____________ (expect: "Bluetooth HFP" or "Bluetooth A2DP")
- [ ] Current input source: _____________ (expect: "Bluetooth HFP" or "Built-in Mic")
- [ ] Bluetooth status: Connected/Disconnected
- [ ] Sample rate: _____ Hz (expect: 16000 or higher)

### After Interruption
- [ ] Output route unchanged (still Bluetooth)
- [ ] No error messages in console
- [ ] Audio session state: Active
- [ ] Playback/recording can start successfully

---

## Known Limitations

1. **Recording may not resume automatically** - iOS may not always allow recording to resume after interruption. This is expected behavior.
2. **Background audio requires capabilities** - For background playback, ensure "Background Modes → Audio" is enabled in app capabilities.
3. **HFP profile limitations** - Some Bluetooth devices may not support simultaneous bidirectional audio (recording + playback).

---

## Troubleshooting

### Issue: Audio doesn't resume after interruption
**Check:**
- Xcode console for error messages
- Audio session is re-activated (look for log messages)
- Interruption notification included `shouldResume` option

**Fix:**
- Manually restart playback/recording
- Restart the app
- Reconnect Bluetooth

### Issue: Route falls back to speaker after interruption
**Check:**
- Bluetooth connection status in Settings
- `.allowBluetooth` option is set in audio session configuration
- Glasses didn't disconnect during interruption

**Fix:**
- Manually select Bluetooth route in Control Center
- Restart Bluetooth connection
- Re-apply audio session configuration

### Issue: App crashes during interruption
**Check:**
- Xcode crash logs for stack trace
- Interruption handler implementation
- Observer cleanup in deinit

**Report:**
- Include crash log and reproduction steps
- Note which interruption type caused the crash

---

## Related Documentation

- **Implementation**: `mobile/modules/expo-glasses-audio/ios/GlassesPlayer.swift`
- **Implementation**: `mobile/modules/expo-glasses-audio/ios/GlassesRecorder.swift`
- **Tracking**: `tracking/PR-085-ios-audio-session-interruptions-background.md`
- **Troubleshooting**: `docs/ios-rayban-troubleshooting.md` (lines 120-150)
- **Apple Docs**: [Responding to Audio Session Interruptions](https://developer.apple.com/documentation/avfaudio/avaudiosession/responding_to_audio_session_interruptions)

---

**Last updated**: 2026-01-20  
**PR**: PR-085  
**Maintained by**: Lift Coding Team
