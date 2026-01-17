# Glasses Audio Diagnostics - Implementation Checklist

## Phase 1: iOS Implementation

### Core Components
- [ ] Create `ios/` directory structure
- [ ] Implement `AudioRouteMonitor.swift`
  - [ ] Monitor AVAudioSession route changes
  - [ ] Format route information for display
  - [ ] Detect Bluetooth HFP/LE connections
  - [ ] Provide real-time updates via callback
- [ ] Implement `GlassesRecorder.swift`
  - [ ] Configure AVAudioSession for Bluetooth input
  - [ ] Set up AVAudioEngine for recording
  - [ ] Create WAV file with proper headers
  - [ ] Handle 10-second timed recording
  - [ ] Implement recording level monitoring
  - [ ] Save to Documents/audio_diagnostics/
- [ ] Implement `GlassesPlayer.swift`
  - [ ] Configure AVAudioSession for Bluetooth output
  - [ ] Set up AVAudioEngine with AVAudioPlayerNode
  - [ ] Load and play WAV files
  - [ ] Implement playback progress tracking
  - [ ] Handle stop/pause functionality
- [ ] Implement `GlassesAudioDiagnostics.swift`
  - [ ] Create main view controller
  - [ ] Build UI with route display
  - [ ] Add record button with visual feedback
  - [ ] Add playback controls
  - [ ] Add file list and export functionality
  - [ ] Wire up all components
  - [ ] Handle permissions (microphone, Bluetooth)

### UI/UX
- [ ] Design diagnostics screen layout
- [ ] Add recording indicator animation
- [ ] Add playback progress indicator
- [ ] Add Bluetooth connection status icon
- [ ] Implement share sheet for exports
- [ ] Add error/success messages

### Integration
- [ ] Add to app navigation (Settings > Audio Diagnostics)
- [ ] Update Info.plist with permissions
- [ ] Test on physical iPhone with Meta AI Glasses

## Phase 2: Android Implementation

### Core Components
- [ ] Create `android/` directory structure
- [ ] Implement `AudioRouteMonitor.kt`
  - [ ] Monitor AudioManager device changes
  - [ ] Format route information for display
  - [ ] Detect Bluetooth SCO connections
  - [ ] Provide real-time updates via callback
- [ ] Implement `GlassesRecorder.kt`
  - [ ] Configure AudioManager for Bluetooth SCO
  - [ ] Set up AudioRecord with VOICE_COMMUNICATION
  - [ ] Create WAV file with proper headers
  - [ ] Handle 10-second timed recording
  - [ ] Implement recording level monitoring
  - [ ] Save to external files directory
  - [ ] Register SCO state broadcast receiver
- [ ] Implement `GlassesPlayer.kt`
  - [ ] Configure AudioManager for Bluetooth SCO
  - [ ] Set up AudioTrack with proper attributes
  - [ ] Load and play WAV files
  - [ ] Implement playback progress tracking
  - [ ] Handle stop/pause functionality
  - [ ] Unregister receivers on cleanup
- [ ] Implement `GlassesAudioDiagnostics.kt`
  - [ ] Create main fragment/activity
  - [ ] Build UI with route display
  - [ ] Add record button with visual feedback
  - [ ] Add playback controls
  - [ ] Add file list and export functionality
  - [ ] Wire up all components
  - [ ] Handle permissions (microphone, Bluetooth)

### UI/UX
- [ ] Design diagnostics screen layout (XML/Compose)
- [ ] Add recording indicator animation
- [ ] Add playback progress indicator
- [ ] Add Bluetooth connection status icon
- [ ] Implement share intent for exports
- [ ] Add error/success messages (Snackbar/Toast)

### Integration
- [ ] Add to app navigation (Settings > Audio Diagnostics)
- [ ] Update AndroidManifest.xml with permissions
- [ ] Create foreground service for recording (if needed)
- [ ] Test on physical Android device with Meta AI Glasses

## Phase 3: Testing & Validation

### Unit Tests
- [ ] Test AudioRouteMonitor route detection
- [ ] Test recorder file creation and WAV format
- [ ] Test player audio output routing
- [ ] Test permission handling

### Integration Tests
- [ ] Test full record → save → play workflow
- [ ] Test Bluetooth connection/disconnection handling
- [ ] Test route changes during recording/playback
- [ ] Test file export functionality

### End-to-End Tests (with actual glasses)
- [ ] **Setup Test**
  - [ ] Pair Meta AI Glasses with test device
  - [ ] Launch diagnostics screen
  - [ ] Verify route display shows Bluetooth connection
- [ ] **Recording Test**
  - [ ] Record 10-second test audio
  - [ ] Verify file saved with correct format
  - [ ] Verify audio quality (clear, no dropouts)
  - [ ] Test with test phrase: "Testing Meta AI Glasses microphone one two three"
- [ ] **Playback Test**
  - [ ] Play recorded audio through glasses speakers
  - [ ] Verify audio is audible and clear
  - [ ] Verify no echo or feedback
  - [ ] Test stop functionality mid-playback
- [ ] **Export Test**
  - [ ] Export recorded file via share
  - [ ] Verify file opens in other apps
  - [ ] Verify WAV format is valid
- [ ] **Route Change Test**
  - [ ] Start recording
  - [ ] Disconnect glasses mid-recording
  - [ ] Verify graceful failure handling
  - [ ] Reconnect glasses
  - [ ] Verify route display updates
- [ ] **Interruption Test** (iOS)
  - [ ] Start recording
  - [ ] Receive phone call
  - [ ] Verify recording pauses/stops
  - [ ] End call and verify recovery
- [ ] **Background Test** (Android)
  - [ ] Start recording
  - [ ] Put app in background
  - [ ] Verify recording continues (if using foreground service)
  - [ ] Return to foreground and verify completion

### Performance Tests
- [ ] Monitor battery usage during 10-minute recording session
- [ ] Verify memory usage is reasonable (< 50MB)
- [ ] Test with low battery (< 20%)
- [ ] Test with poor Bluetooth signal

## Phase 4: Documentation & Polish

### Documentation
- [ ] Add inline code comments
- [ ] Document known limitations
- [ ] Create troubleshooting guide
- [ ] Add screenshots to README
- [ ] Document test results

### Polish
- [ ] Add haptic feedback on button taps (iOS)
- [ ] Improve error messages with actionable steps
- [ ] Add loading states for async operations
- [ ] Implement proper cleanup on view dismissal
- [ ] Add analytics for diagnostics usage (optional)

### Accessibility
- [ ] Add VoiceOver labels (iOS)
- [ ] Add TalkBack labels (Android)
- [ ] Ensure sufficient contrast ratios
- [ ] Test with accessibility tools

## Phase 5: Integration with Backend

### Backend Integration
- [ ] Test uploading recorded audio to `POST /v1/command`
- [ ] Verify backend accepts 16kHz WAV format
- [ ] Test receiving TTS audio from `POST /v1/tts`
- [ ] Test playing backend TTS through glasses
- [ ] Implement full round-trip: record → backend → TTS → playback

### End-to-End Workflow Test
- [ ] User says "Hello" into glasses mic
- [ ] App records and uploads to backend
- [ ] Backend processes command and returns TTS response
- [ ] App plays TTS through glasses speakers
- [ ] Verify total latency < 3 seconds
- [ ] Verify audio quality throughout pipeline

## Success Criteria

- [ ] iOS diagnostics fully functional on iPhone with Meta AI Glasses
- [ ] Android diagnostics fully functional on Android device with Meta AI Glasses
- [ ] All end-to-end tests pass
- [ ] Backend integration working
- [ ] Documentation complete
- [ ] No backend tests broken
- [ ] Ready for user testing and feedback

## Notes

- Prioritize iOS implementation first (more common platform for Meta glasses users)
- Use SwiftUI for iOS UI if targeting iOS 15+, otherwise UIKit
- Use Jetpack Compose for Android UI if targeting Android 5.0+, otherwise XML layouts
- Store recordings in app-specific directories (no external storage permissions needed)
- Keep diagnostics in developer/debug builds initially, promote to production later
- Consider adding telemetry to track diagnostics usage and issues

## References

- [README.md](README.md) - Full implementation guide
- [docs/meta-ai-glasses-audio-routing.md](../../docs/meta-ai-glasses-audio-routing.md) - Audio routing documentation
- [tracking/PR-033-meta-ai-glasses-audio-routing.md](../../tracking/PR-033-meta-ai-glasses-audio-routing.md) - Original work item
