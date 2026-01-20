# iPhone & Meta Glasses Testing - Quick Reference

**Quick Reference Card for Testing HandsFree with iPhone and Meta AI Glasses**

---

## 🎯 Pre-Test Checklist

Before starting any testing session:

- [ ] **Backend server running** and accessible from iPhone
- [ ] **iPhone charged** (testing is battery-intensive)
- [ ] **Meta Glasses charged** (at least 50% battery)
- [ ] **Glasses paired** with iPhone via Bluetooth
- [ ] **Development build** installed (not Expo Go)
- [ ] **WiFi/Network** - iPhone and backend on same network (or HTTPS endpoint)

---

## 🔧 Quick Setup Commands

### Start Backend

```bash
cd lift_coding
make compose-up  # Start Redis
make dev         # Start backend server
# Backend available at http://localhost:8080
```

### Build & Install Mobile App

```bash
cd mobile
npx expo run:ios --device
# Follow on-screen instructions to select device
```

---

## 📱 Device Configuration

### Find Your Computer's IP

```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr IPv4
```

### Configure in Mobile App

1. Open app → **Settings** tab
2. Enter: `http://YOUR_IP:8080`
3. Tap **Save Settings**
4. Check **Status** tab shows "Connected"

---

## 🎧 Audio Routing Setup

### 1. Pair Glasses

**Settings → Bluetooth → Ray-Ban Meta... → Connect**

### 2. Set Audio Output

1. Play test audio (Music app)
2. Open **Control Center** (swipe down from top-right)
3. Long-press audio card
4. Tap audio output icon
5. Select **"Ray-Ban Meta..."**
6. Verify audio plays through glasses

### 3. Verify in App

Open app → **Glasses** tab → Check:
- Connection State: **"✓ Bluetooth Connected"**
- Audio Route: **"Ray-Ban Meta..."**

---

## 🧪 Basic Test Flow

### Test 1: Voice Command → TTS Response

1. Open app → **Command** tab
2. Tap **🎤 Start Recording**
3. Speak: **"Show my inbox"**
4. Tap **⏹ Stop**
5. Tap **Send Audio**
6. **Verify**:
   - Response appears
   - TTS plays through glasses
   - No errors

**Expected**: Hear "You have X pull requests..." through glasses

---

### Test 2: Text Command (Fallback)

1. Open app → **Command** tab
2. Type: **"show my inbox"**
3. Tap **Send Command**
4. **Verify**:
   - Response appears
   - TTS plays through glasses

---

### Test 3: Navigation Commands

1. Send command: **"Show my inbox"**
2. Wait for response
3. Send command: **"Next"**
4. **Verify**: Different item spoken
5. Send command: **"Repeat"**
6. **Verify**: Same item repeated

---

### Test 4: Glasses Diagnostics

1. Open app → **Glasses** tab
2. Tap **🔄 Refresh Status**
3. **Verify**:
   - Connection: ✓ Bluetooth Connected
   - Input Device: Ray-Ban Meta...
   - Output Device: Ray-Ban Meta...
4. Tap **🎤 Start Recording**
5. Speak for 3 seconds
6. Tap **▶️ Play Last Recording**
7. **Verify**: Audio plays through glasses

---

## ⚠️ Common Issues & Quick Fixes

### Issue: Audio plays on phone, not glasses

**Quick Fix**:
1. Open Control Center
2. Change audio output to glasses
3. Restart app

---

### Issue: "Native module not available"

**Quick Fix**:
```bash
cd mobile
npx expo run:ios --device
# Must use development build, NOT Expo Go
```

---

### Issue: "Connection failed"

**Quick Fix**:
1. Check backend is running: `curl http://localhost:8080/v1/status`
2. Update backend URL in Settings to use computer's IP
3. Check firewall allows port 8080

---

### Issue: Glasses disconnect during test

**Quick Fix**:
1. Check glasses battery (LED indicator)
2. Re-pair in **Settings → Bluetooth**
3. Stay within 1-2 meters of phone

---

## 🎤 Known-Good Commands

Use these commands for reliable testing:

| Command | Expected Response |
|---------|------------------|
| "Show my inbox" | Lists PRs and issues |
| "Summarize PR 123" | Details about PR 123 |
| "Next" | Next item in list |
| "Repeat" | Repeat last item |
| "Help" | Available commands |

---

## 📊 Verification Checklist

After each test session, verify:

- [ ] Voice commands are captured correctly
- [ ] Audio plays through glasses (not phone)
- [ ] TTS quality is clear and understandable
- [ ] Bluetooth connection remains stable
- [ ] No audio routing issues
- [ ] Commands process within 2-3 seconds
- [ ] UI cards display correctly
- [ ] No app crashes or errors

---

## 📞 Getting Help

**Documentation**:
- Full Runbook: [docs/ios-rayban-mvp1-runbook.md](docs/ios-rayban-mvp1-runbook.md)
- Troubleshooting: [docs/ios-rayban-troubleshooting.md](docs/ios-rayban-troubleshooting.md)
- Getting Started: [GETTING_STARTED.md](GETTING_STARTED.md)

**Quick Checks**:

1. **Backend Health**:
   ```bash
   curl http://localhost:8080/v1/status
   ```

2. **Mobile App Logs**:
   - Check Expo dev tools console
   - Look for connection errors

3. **Bluetooth Status**:
   - Settings → Bluetooth → Check "Connected" status

---

## 🔄 Reset Procedures

### Reset Audio Routing

```
1. Settings → Bluetooth → Disconnect glasses
2. Force quit mobile app
3. Reconnect glasses
4. Launch app
5. Check audio route in Control Center
```

### Reset Mobile App

```
1. Force quit app
2. Delete app data (optional): Settings → [App] → Clear Data
3. Reinstall: npx expo run:ios --device
4. Reconfigure backend URL and user ID
```

### Reset Backend

```bash
# Stop services
make compose-down

# Clear data (optional)
rm -rf data/

# Restart
make compose-up
make dev
```

---

## 📝 Testing Notes Template

Use this template to document your testing session:

```markdown
## Test Session: [DATE]

### Setup
- Backend: Running ✅ / Not Running ❌
- Glasses Battery: [%]
- iPhone: [Model + iOS Version]
- Network: WiFi / Cellular / HTTPS

### Tests Performed
1. [Test Name]
   - Expected: [...]
   - Actual: [...]
   - Status: ✅ / ❌

### Issues Found
1. [Issue Description]
   - Severity: Critical / Major / Minor
   - Steps to Reproduce: [...]
   - Workaround: [...]

### Notes
- [Any additional observations]
```

---

## 🚀 Advanced Testing

### Test with Realistic Data

```bash
# Enable live GitHub mode
export GITHUB_LIVE_MODE=true
export GITHUB_TOKEN=ghp_...

# Enable OpenAI TTS/STT
export HANDSFREE_TTS_PROVIDER=openai
export HANDS_FREE_STT_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Restart backend
make dev
```

### Test Push Notifications

```bash
# Send test notification
curl -X POST http://localhost:8080/v1/dev/send-test-notification \
  -H "Content-Type: application/json" \
  -H "X-User-ID: YOUR_USER_ID" \
  -d '{"message": "Test notification"}'
```

### Test Confirmation Flow

1. Send command: **"Merge PR 123"**
2. Wait for confirmation prompt
3. Say: **"Confirm"**
4. Verify action executes

---

## 📱 Device Compatibility

### Tested Configurations

| Device | iOS Version | Glasses | Status |
|--------|-------------|---------|--------|
| iPhone 13 | iOS 17.1 | Ray-Ban Meta | ✅ Works |
| iPhone 12 | iOS 16.5 | Ray-Ban Meta | ✅ Works |
| iPhone 11 | iOS 15.7 | Ray-Ban Meta | ✅ Works |
| iPhone SE | iOS 16.0 | Generic BT | ⚠️ Limited |

### Known Limitations

- **iOS Simulator**: No Bluetooth support
- **Expo Go**: No native module support
- **Android**: Limited testing (implementation in progress)

---

**Quick Reference Version**: 1.0  
**Last Updated**: 2026-01-20

**Print this page for desk reference during testing sessions!**
