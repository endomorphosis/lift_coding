import ExpoModulesCore

public class ExpoMetaWearablesDatModule: Module {
  private let minimumDatSdkVersion = "0.7.0"
  private let selectedDeviceDefaultsKey = "expo.meta.wearables.selectedDeviceId"
  private var sessionState = "idle"
  private var selectedDeviceId: String?
  private var selectedDeviceLastSeenAt: Double?
  private var selectedDeviceRssi: Int?

  private func stateChangedPayload() -> [String: Any] {
    return [
      "state": self.sessionState,
      "sessionState": self.sessionState,
      "deviceId": self.selectedDeviceId as Any,
      "deviceName": self.selectedDeviceId as Any,
      "targetConnectionState": self.selectedDeviceId == nil ? "unselected" : (self.sessionState == "target_connected" ? "connected" : (self.sessionState == "target_ready" ? "ready" : (self.sessionState == "target_discovered" ? "discovered" : (self.sessionState == "reconnecting_target" ? "reconnecting" : "selected")))),
      "targetLastSeenAt": self.selectedDeviceLastSeenAt as Any,
      "targetRssi": self.selectedDeviceRssi as Any
    ]
  }

  private func mediaActionResult(
    action: String,
    message: String,
    supported: Bool = false,
    mode: String = "reference_only"
  ) -> [String: Any] {
    return [
      "state": supported ? "ready" : "not_supported",
      "mode": mode,
      "supported": supported,
      "action": action,
      "message": message,
      "deviceId": self.selectedDeviceId as Any,
      "targetConnectionState": self.selectedDeviceId == nil ? "unselected" : (self.sessionState == "target_connected" ? "connected" : (self.sessionState == "target_ready" ? "ready" : "selected")),
      "assetUri": NSNull(),
      "mimeType": NSNull()
    ]
  }

  private func mwdatInfo() -> [String: Any] {
    return (Bundle.main.infoDictionary ?? [:])["MWDAT"] as? [String: Any] ?? [:]
  }

  private func analyticsOptOut(from mwdat: [String: Any]) -> Bool {
    let analytics = mwdat["Analytics"] as? [String: Any]
    return analytics?["OptOut"] as? Bool ?? false
  }

  private func appModelDamEnabled(from mwdat: [String: Any]) -> Bool {
    let appModel = mwdat["AppModel"] as? [String: Any]
    return appModel?["DAMEnabled"] as? Bool ?? false
  }

  private func sdkMeetsMinimum(from mwdat: [String: Any]) -> Bool {
    guard let sdkVersion = mwdat["SDKVersion"] as? String else {
      return false
    }
    let actualVersionComponents = sdkVersion.split(separator: ".").map { Int($0) ?? 0 }
    let minimumVersionComponents = minimumDatSdkVersion.split(separator: ".").map { Int($0) ?? 0 }
    let maxCount = max(actualVersionComponents.count, minimumVersionComponents.count)
    for idx in 0..<maxCount {
      let lhs = idx < actualVersionComponents.count ? actualVersionComponents[idx] : 0
      let rhs = idx < minimumVersionComponents.count ? minimumVersionComponents[idx] : 0
      if lhs > rhs { return true }
      if lhs < rhs { return false }
    }
    return true
  }

  private func appModelDisplayReady() -> Bool {
    let mwdat = mwdatInfo()
    return appModelDamEnabled(from: mwdat) && sdkMeetsMinimum(from: mwdat) && self.selectedDeviceId != nil
  }

  private func datConfigWarnings() -> [String] {
    if appModelDamEnabled(from: mwdatInfo()) {
      return ["DAT SDK linkage is not active; display capability is in bridge-reference mode."]
    }
    return ["DAM app-model is disabled; DAT display capability remains unavailable in this build."]
  }

  private func displayStubMessage(action: String, videoUrl: String? = nil) -> String {
    let damEnabled = appModelDamEnabled(from: mwdatInfo())
    if !damEnabled {
      return "Display actions require DAM app-model enablement."
    }
    if action == "play_display_video", videoUrl?.isEmpty != false {
      return "Display video playback requires an MP4 URL and DAM app-model support."
    }
    switch action {
    case "render_display_test":
      return "Display test rendering is not implemented in the iOS DAT bridge yet."
    case "clear_display":
      return "Display clearing is not implemented in the iOS DAT bridge yet."
    case "play_display_video":
      return "Display video playback is not implemented in the iOS DAT bridge yet."
    case "reset_display_session":
      return "Display session reset is not implemented in the iOS DAT bridge yet."
    default:
      return "Display action is not implemented in the iOS DAT bridge yet."
    }
  }

  public func definition() -> ModuleDefinition {
    Name("ExpoMetaWearablesDat")

    Events("onDatStateChanged")

    OnCreate {
      self.selectedDeviceId = UserDefaults.standard.string(forKey: self.selectedDeviceDefaultsKey)
    }

    AsyncFunction("isDatAvailable") { () -> Bool in
      false
    }

    AsyncFunction("getConfiguration") { () -> [String: Any] in
      let mwdat = mwdatInfo()
      return [
        "platform": "ios",
        "sdkLinked": false,
        "sdkConfigured": false,
        "sdkMeetsMinimum": sdkMeetsMinimum(from: mwdat),
        "analyticsOptOut": analyticsOptOut(from: mwdat),
        "sdkVersion": NSNull(),
        "sdkVersionTarget": minimumDatSdkVersion,
        "datAppModelEnabled": appModelDamEnabled(from: mwdat),
        "displayDamRequired": true,
        "displayDamEnabled": appModelDamEnabled(from: mwdat),
        "applicationId": mwdat["ApplicationId"] as? String,
        "provider": "internal_bridge",
        "integrationMode": "reference_only"
      ]
    }

    AsyncFunction("getCapabilities") { () -> [String: Any] in
      return [
        "session": true,
        "camera": false,
        "photoCapture": false,
        "videoStream": false,
        "audio": false,
        "display": false,
        "displayVideo": false
      ]
    }

    AsyncFunction("getConnectedDevice") { () -> [String: Any]? in
      return [
        "platform": "ios",
        "sdkLinked": false,
        "sdkConfigured": false,
        "applicationId": NSNull(),
        "deviceId": NSNull(),
        "registrationState": self.sessionState,
        "deviceName": UIDevice.current.name,
        "deviceModel": UIDevice.current.model
      ]
    }

    AsyncFunction("getSessionState") { () -> String in
      self.sessionState
    }

    AsyncFunction("getAdapterState") { () -> [String: Any] in
      return [
        "transport": "bluetooth",
        "adapterAvailable": true,
        "adapterEnabled": true,
        "scanPermissionGranted": true,
        "connectPermissionGranted": true,
        "advertisePermissionGranted": true,
        "state": "unknown"
      ]
    }

    AsyncFunction("getKnownDevices") { () -> [[String: Any]] in
      return []
    }

    AsyncFunction("scanKnownAndNearbyDevices") { (_ timeoutMs: Int) -> [[String: Any]] in
      return []
    }

    AsyncFunction("getSelectedDeviceTarget") { () -> [String: Any]? in
      guard let selectedDeviceId else {
        return nil
      }
      return [
        "deviceId": selectedDeviceId,
        "deviceName": selectedDeviceId,
        "source": "selected_only",
        "lastSeenAt": self.selectedDeviceLastSeenAt as Any,
        "rssi": self.selectedDeviceRssi as Any
      ]
    }

    AsyncFunction("selectDeviceTarget") { (deviceId: String) -> [String: Any] in
      self.selectedDeviceId = deviceId
      self.selectedDeviceLastSeenAt = Date().timeIntervalSince1970 * 1000
      self.selectedDeviceRssi = nil
      UserDefaults.standard.set(deviceId, forKey: self.selectedDeviceDefaultsKey)
      return [
        "deviceId": deviceId,
        "deviceName": deviceId,
        "source": "selected_only",
        "lastSeenAt": self.selectedDeviceLastSeenAt as Any,
        "rssi": self.selectedDeviceRssi as Any
      ]
    }

    AsyncFunction("clearDeviceTarget") { () -> [String: Any] in
      let previous = self.selectedDeviceId
      self.selectedDeviceId = nil
      self.selectedDeviceLastSeenAt = nil
      self.selectedDeviceRssi = nil
      UserDefaults.standard.removeObject(forKey: self.selectedDeviceDefaultsKey)
      return [
        "deviceId": previous as Any,
        "deviceName": previous as Any
      ]
    }

    AsyncFunction("reconnectSelectedDeviceTarget") { () -> [String: Any] in
      let selectedId = self.selectedDeviceId ?? UserDefaults.standard.string(forKey: self.selectedDeviceDefaultsKey)
      self.selectedDeviceId = selectedId
      let previousSessionState = self.sessionState
      self.selectedDeviceLastSeenAt = selectedId == nil ? nil : Date().timeIntervalSince1970 * 1000
      self.sessionState = selectedId == nil ? "awaiting_target" : (previousSessionState == "target_ready" ? "target_ready" : "target_discovered")
      self.sendEvent("onDatStateChanged", self.stateChangedPayload())
      return [
        "state": self.sessionState,
        "mode": "reference_only",
        "deviceId": selectedId as Any,
        "targetConnectionState": selectedId == nil ? "unselected" : (previousSessionState == "target_ready" ? "ready" : "discovered"),
        "targetLastSeenAt": self.selectedDeviceLastSeenAt as Any,
        "targetRssi": self.selectedDeviceRssi as Any
      ]
    }

    AsyncFunction("connectSelectedDeviceTarget") { () -> [String: Any] in
      let selectedId = self.selectedDeviceId ?? UserDefaults.standard.string(forKey: self.selectedDeviceDefaultsKey)
      self.selectedDeviceId = selectedId
      if selectedId == nil {
        self.sessionState = "awaiting_target"
        self.sendEvent("onDatStateChanged", self.stateChangedPayload())
        return [
          "state": self.sessionState,
          "mode": "reference_only",
          "deviceId": NSNull(),
          "targetConnectionState": "unselected"
        ]
      }

      self.selectedDeviceLastSeenAt = Date().timeIntervalSince1970 * 1000
      self.sessionState = "target_connected"
      self.sendEvent("onDatStateChanged", self.stateChangedPayload())
      return [
        "state": self.sessionState,
        "mode": "reference_only",
        "deviceId": selectedId as Any,
        "targetConnectionState": "connected",
        "targetLastSeenAt": self.selectedDeviceLastSeenAt as Any,
        "targetRssi": self.selectedDeviceRssi as Any
      ]
    }

    AsyncFunction("getDiagnostics") { () -> [String: Any] in
      let mwdat = mwdatInfo()
      let damEnabled = appModelDamEnabled(from: mwdat)
      let sdkMeetsMinimumValue = sdkMeetsMinimum(from: mwdat)
      return [
        "available": true,
        "platform": "ios",
        "sdkLinked": false,
        "sdkConfigured": false,
        "sdkMeetsMinimum": sdkMeetsMinimumValue,
        "analyticsOptOut": analyticsOptOut(from: mwdat),
        "sdkVersion": NSNull(),
        "sdkVersionTarget": minimumDatSdkVersion,
        "datAppModelEnabled": damEnabled,
        "displayDamRequired": true,
        "displayDamEnabled": damEnabled,
        "displayReady": damEnabled && sdkMeetsMinimumValue && appModelDisplayReady(),
        "configWarnings": datConfigWarnings(),
        "applicationId": mwdat["ApplicationId"] as? String as Any,
        "provider": "internal_bridge",
        "integrationMode": "reference_only",
        "capabilities": [
          "session": true,
          "camera": false,
          "photoCapture": false,
          "videoStream": false,
          "audio": false,
          "display": false,
          "displayVideo": false
        ],
        "sessionState": self.sessionState,
        "registrationState": self.sessionState,
        "deviceCount": 0,
        "activeDeviceId": NSNull(),
        "adapterState": [
          "transport": "bluetooth",
          "adapterAvailable": true,
          "adapterEnabled": true,
          "scanPermissionGranted": true,
          "connectPermissionGranted": true,
          "advertisePermissionGranted": true,
          "state": "unknown"
        ],
        "knownDeviceCount": 0,
        "selectedDeviceId": self.selectedDeviceId as Any,
        "selectedDeviceName": self.selectedDeviceId as Any,
        "targetConnectionState": self.selectedDeviceId == nil ? "unselected" : (self.sessionState == "target_connected" ? "connected" : (self.sessionState == "target_ready" ? "ready" : (self.sessionState == "target_discovered" ? "discovered" : "selected"))),
        "targetLastSeenAt": self.selectedDeviceLastSeenAt as Any,
        "targetRssi": self.selectedDeviceRssi as Any
      ]
    }

    AsyncFunction("startDeviceSession") { () -> [String: Any] in
      self.sessionState = self.selectedDeviceId == nil ? "awaiting_target" : "target_ready"
      self.sendEvent("onDatStateChanged", self.stateChangedPayload())
      return [
        "state": self.sessionState,
        "mode": "reference_only",
        "deviceId": self.selectedDeviceId as Any,
        "targetConnectionState": self.selectedDeviceId == nil ? "unselected" : "ready"
      ]
    }

    AsyncFunction("stopDeviceSession") { () -> [String: Any] in
      self.sessionState = "idle"
      self.sendEvent("onDatStateChanged", self.stateChangedPayload())
      return [
        "state": self.sessionState,
        "mode": "reference_only",
        "deviceId": self.selectedDeviceId as Any,
        "targetConnectionState": self.selectedDeviceId == nil ? "unselected" : "selected"
      ]
    }

    AsyncFunction("capturePhoto") { () -> [String: Any] in
      self.mediaActionResult(
        action: "capture_photo",
        message: "Photo capture is not implemented in the iOS reference-only DAT bridge yet."
      )
    }

    AsyncFunction("startVideoStream") { () -> [String: Any] in
      self.mediaActionResult(
        action: "start_video_stream",
        message: "Video streaming is not implemented in the iOS reference-only DAT bridge yet."
      )
    }

    AsyncFunction("stopVideoStream") { () -> [String: Any] in
      self.mediaActionResult(
        action: "stop_video_stream",
        message: "Video streaming is not implemented in the iOS reference-only DAT bridge yet."
      )
    }

    AsyncFunction("renderDisplayTest") { () -> [String: Any] in
      self.mediaActionResult(
        action: "render_display_test",
        message: displayStubMessage(action: "render_display_test")
      )
    }

    AsyncFunction("clearDisplay") { () -> [String: Any] in
      self.mediaActionResult(
        action: "clear_display",
        message: displayStubMessage(action: "clear_display")
      )
    }

    AsyncFunction("playDisplayVideo") { (_ videoUrl: String?) -> [String: Any] in
      self.mediaActionResult(
        action: "play_display_video",
        message: displayStubMessage(action: "play_display_video", videoUrl: videoUrl)
      )
    }

    AsyncFunction("resetDisplaySession") { () -> [String: Any] in
      self.mediaActionResult(
        action: "reset_display_session",
        message: displayStubMessage(action: "reset_display_session")
      )
    }
  }
}
