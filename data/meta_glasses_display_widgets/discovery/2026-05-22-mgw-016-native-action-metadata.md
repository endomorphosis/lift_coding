# MGW-016 Native Action Metadata Preservation

Date: 2026-05-22
Task: MGW-016 Preserve full widget action metadata through native DAT bridge calls

## Outcome

Display widget bridge methods now keep the existing narrow argument for compatibility and pass the full widget action payload as a second native argument. Android and iOS native bridge methods accept that context payload, derive descriptor CID, widget CID, receipt CID, policy decision, correlation ID, request ID, fallback, and render path from it, and include those fields in widget action responses and diagnostics.

Bridge-only and native-unavailable paths continue to return structured unsupported results, now with the same metadata fields when the action payload is available.

## Validation

```bash
cd mobile && npm test -- --runInBand modules/expo-meta-wearables-dat/__tests__/index.test.js src/native/__tests__/wearablesBridge.test.js
cd mobile/android && env JAVA_HOME=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8 PATH=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8/bin:$PATH ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
```

Result: both commands passed on 2026-05-22.
