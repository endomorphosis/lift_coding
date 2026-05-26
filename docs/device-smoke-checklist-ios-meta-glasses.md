# Device Smoke Checklist (iOS + Meta AI Glasses)

Use this checklist for the iPhone native DAT handoff. It validates the existing audio path, the browser Web App display fallback, and the native DAT display bridge contract before any physical-glasses rollout evidence is accepted.

## Prereqs

- Backend reachable from your iPhone over LAN at port **8080**.
- Mobile app built as an **Expo development build** (Expo Go will not load native modules).
- iPhone paired to Meta AI Glasses via iOS Bluetooth settings.
- Meta AI app installed on the iPhone, signed in with the test account, and able to manage `App Connections > Web apps`.
- Glasses firmware and the Meta AI app are updated before testing DAT display behavior.
- Display Web App package from `dev/meta-rayban-display-simulator/webapp/` is hosted at a publicly available HTTPS URL.
- Rollout flags are known before the run:
  - `HANDSFREE_DISPLAY_WIDGETS_ENABLED`
  - `HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK`
  - `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS`

## 0) Simulator Trace Parity Baseline

Run this once before moving to the physical iPhone. The same widget manifest and action sequence must be used later on device.

1. Open `dev/meta-rayban-display-simulator/index.html` in a desktop browser.
2. Select the `task-progress` fixture.
3. Set display state to `ready`.
4. Move focus through `pause` and `dismiss`.
5. Activate `pause`.
6. Export `meta-rayban-display-simulator-trace.json`.

Expected simulator trace:
- `manifest.widget_id` and `manifest.widget_cid` match the display widget action sent to iPhone.
- Trace includes `display_state`, at least one `focus`, and one `activate` event.
- Activated action maps to `operation: update_widget` or the expected display widget operation for the fixture.
- Fallback states, when selected, use explicit reasons such as `dat_native_display_unavailable`, `firmware_update_required`, `dat_app_update_required`, or `display_lifecycle_error`.

Record the trace file name, fixture, and correlation ID in `docs/meta-wearables-dat-display-rollout-evidence-template.md`.

## 1) Backend: Health Check

```bash
curl -sS http://localhost:8080/v1/status | cat
```

Expected:
- HTTP 200
- JSON payload indicating the server is up (exact fields may vary)

If testing from a phone, use your laptop’s LAN IP (example):

```bash
export BACKEND_URL="http://192.168.1.10:8080"
curl -sS "$BACKEND_URL/v1/status" | cat
```

If this fails:
- Make sure the backend is listening on `0.0.0.0:8080` (not only `127.0.0.1`).
- Open firewall for TCP 8080 on your laptop.

## 2) Backend: Dev Audio Upload Endpoint

The dev endpoint is `POST /v1/dev/audio` and expects `data_base64`.

```bash
# Create a tiny test payload (base64 of the string "test")
export BACKEND_URL="http://192.168.1.10:8080"
export B64="dGVzdA=="

curl -sS -X POST "$BACKEND_URL/v1/dev/audio" \
  -H 'Content-Type: application/json' \
  -d '{"data_base64":"'"$B64"'","format":"wav"}' | cat
```

Expected:
- HTTP 200
- JSON response that includes a `uri` field (often a `file://...` URI)

Common failure modes:
- 401/403: backend not in dev auth mode
- 400: wrong payload field (must be `data_base64`)

## 3) Mobile: Install/Run An iOS Dev Build

From `mobile/` on a Mac with Xcode:

```bash
cd mobile
npm ci
npx expo run:ios --device
```

(If you’re using EAS, install the development build .ipa and then run `npx expo start --dev-client`.)

Expected for the DAT handoff:
- SDK-unlinked iPhone build is acceptable for fallback validation only.
- SDK-linked iPhone build must include DAT `0.7.0+`, DAM metadata, and `MWDATDisplay` before native display can be considered.
- Expo Go is a hard failure for DAT validation because the native module and DisplayAccess bridge are absent.

## 4) Mobile: Configure Backend URL

On the iPhone app:
- Open **Settings** tab.
- Set Base URL to `http://<YOUR_LAPTOP_LAN_IP>:8080`.
- Confirm `GET /v1/status` works if the UI exposes status, or proceed to diagnostics.

## 5) Meta AI App + Web App Fallback

On iPhone:
- Open the Meta AI app.
- Confirm the glasses show connected and no firmware update is pending.
- Open `App Connections > Web apps`.
- Add the hosted Display Web App HTTPS URL by QR code or exact URL entry.
- Launch the Web App on glasses.

Expected:
- Web App loads without login or local-network dependency.
- Display stays within the 600x600 viewport.
- D-pad focus moves in the same order as the simulator trace.
- Enter/activate records the same action semantics as the simulator baseline.
- This path remains available when native DAT display rolls back.

## 6) Glasses: Validate Bluetooth Routing

On iPhone:
- Settings -> Bluetooth -> confirm glasses are connected.

In the app:
- Open **Glasses Diagnostics**.
- Confirm the native module is available (development build required).
- Confirm the audio route shows Bluetooth/glasses as the active input/output when in “glasses mode”.

Expected (high level):
- “Native module available” indicator is true/green
- Route shows Bluetooth/glasses in the input/output names

## 7) Record -> Upload -> Command Pipeline

In **Glasses Diagnostics** (or whichever screen drives the flow), run:
1. Record a short clip.
2. Upload to `POST /v1/dev/audio`.
3. Send to `/v1/command`.
4. (Optional) TTS/playback if enabled.

Expected (high level):
- Recording returns a non-empty `uri`
- Upload returns 200 and a JSON payload containing a `uri`
- Command request returns 200 with a response payload (exact shape depends on agent setup)

If upload fails:
- Ensure the payload field is `data_base64` (not `audio_data`).
- Ensure your backend auth mode allows dev uploads (common: `HANDSFREE_AUTH_MODE=dev`).

## 8) iPhone Native DAT Display Smoke

Run the display smoke from the same iPhone build and test account used for audio validation.

1. Open **Glasses Diagnostics**.
2. Capture the diagnostics panel before any display action.
3. Confirm these fields are visible or logged:
   - `platform: ios`
   - `sdkVersionTarget: 0.7.0`
   - `sdkMeetsMinimum`
   - `datAppModelEnabled`
   - `displayDamEnabled`
   - `displaySdkLinked`
   - `displayReady`
   - `displayConnectionState`
   - `displayLifecycleStages`
4. Select or reconnect the display-capable glasses target.
5. Run `renderDisplayTest`.
6. Run `renderDisplayWidget` using the same widget manifest used in the simulator trace.
7. Move focus once and activate the same action used in the simulator trace.
8. Run `updateDisplayWidget`.
9. Run `clearDisplay`.
10. Run `resetDisplaySession`.

Expected simulator trace parity on iPhone:
- `widgetId`, `widgetCid`, `descriptorCid`, `orbReceiptCid`, `correlationId`, and `requestId` match the simulator/exported action payloads when those fields are present.
- Native success reports `renderPath: native-dat`, `supported: true`, and no fallback reason.
- SDK-linked native success records DisplayAccess lifecycle evidence for target selection, session start, display attach, display start, and content send.
- SDK-unlinked or blocked builds report `renderPath: mobile-card`, `supported: false`, and an explicit `reason`.
- Focus and activation results preserve the same action ID and operation order as the simulator trace.

## Native DAT Fallback Criteria

Do not enable iPhone native DAT display for a rollout unless all success criteria above pass. Use these fallback criteria during smoke testing:

| Condition | Expected iPhone DAT result | Required action |
|---|---|---|
| DAT SDK classes are not linked | `reason: dat_sdk_unlinked`, `renderPath: mobile-card` | Keep `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS=false`; use Web App or mobile-card fallback. |
| `MWDATDisplay` is not linked | `reason: display_sdk_unlinked`, `renderPath: mobile-card` | Keep native DAT disabled until the iOS build links display SDK classes. |
| DAM/app-model disabled | `reason: dam_disabled`, `displayReady: false` | Rebuild with DAT app-model metadata before retest. |
| DAT target below `0.7.0` | `reason: sdk_version_unsupported` | Update DAT SDK target and retest. |
| No selected display-capable target | `reason: target_required` or `display_capability_missing` | Select/reconnect glasses; continue only if display capability is visible. |
| Glasses firmware update required | `reason: firmware_update_required` | Update firmware in the Meta AI app before native DAT retest. |
| Meta AI app or glasses DAT app update required | `reason: dat_app_update_required` | Update the Meta AI app/glasses app path before native DAT retest. |
| Repeated DisplayAccess timeout/lifecycle error | `reason: display_lifecycle_error` | Reset DAT display session once; if repeated, rollback to Web App/mobile-card. |

## Rollback Switches

Use the least broad rollback that restores the demo or test path:

- iOS native DAT hold: set `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS=false`.
- Backend display action stop: set `HANDSFREE_DISPLAY_WIDGETS_ENABLED=false`.
- Preserve browser fallback: keep `HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK=true`.
- Mobile release rollback: move the test group back to the last bridge-only iPhone build or channel.
- Physical display fallback: keep the HTTPS Web App registered in the Meta AI app and use phone/mobile-card rendering for native DAT failures.

After any rollback, repeat `GET /v1/status`, run one audio command, and confirm the display path reports `mobile-card` or `display-webapp` instead of `native-dat`.

## Evidence To Capture

- Simulator trace export and hosted `readiness.json` URL.
- iPhone build ID, iOS version, DAT SDK target, and `displaySdkLinked` value.
- Glasses model, firmware version, Meta AI app version, and connection state.
- Screenshots or logs for diagnostics before and after display actions.
- Result payloads for `renderDisplayWidget`, `updateDisplayWidget`, focus/activate, clear, and reset.
- Rollback flag values and the validation result after rollback.
- Completed `docs/meta-wearables-dat-display-rollout-evidence-template.md` for real glasses runs.

## Troubleshooting quick hits

- **“Native module not available”**: you’re in Expo Go; rebuild as dev-client.
- **Cannot reach backend from phone**: wrong IP, firewall, or backend only bound to localhost.
- **iOS local HTTP blocked**: ensure ATS local-network allowance is enabled in the app config.
- **Native DAT display unavailable**: verify DAT SDK linkage, `MWDATDisplay`, DAM metadata, selected target, firmware, and Meta AI app version before retesting.
