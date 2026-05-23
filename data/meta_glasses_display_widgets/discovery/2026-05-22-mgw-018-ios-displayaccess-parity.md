# MGW-018 iOS DisplayAccess Bridge Parity

Date: 2026-05-22
Task: MGW-018 Add iOS DisplayAccess native-display bridge parity

## Outcome

The iOS DAT bridge now exposes the display widget lifecycle methods added on the JS/native boundary and no longer treats DAM metadata alone as native display support.

When `MWDATCore` or `MWDATDisplay` is not linked into the iOS build, widget actions return explicit SDK-unlinked diagnostics:

- `reason: dat_sdk_unlinked` when the core DAT SDK module is absent
- `reason: display_sdk_unlinked` when the core SDK is present but `MWDATDisplay` is absent
- `renderPath: mobile-card`
- blocked `displayConnectionState` matching the SDK gate
- preserved widget descriptor, widget, ORB receipt, policy, correlation, request, and fallback metadata

The diagnostics/configuration surface now reports `displaySdkLinked` and warns when the iOS DAT or Display SDK modules are not linked. Physical validation checklist coverage was expanded for iOS SDK-unlinked fallback and future `MWDATDisplay`-linked native display runs.

## Validation

Target validation:

```bash
cd mobile && npm test -- --runInBand modules/expo-meta-wearables-dat/__tests__/index.test.js
```

Result: passed on 2026-05-22.
