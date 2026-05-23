import ExpoModulesCore
#if canImport(MWDATCore)
import MWDATCore
#endif
#if canImport(MWDATDisplay)
import MWDATDisplay
#endif

public class ExpoMetaWearablesDatModule: Module {
  private let minimumDatSdkVersion = "0.7.0"
  private let selectedDeviceDefaultsKey = "expo.meta.wearables.selectedDeviceId"
  private var sessionState = "idle"
  private var selectedDeviceId: String?
  private var selectedDeviceLastSeenAt: Double?
  private var selectedDeviceRssi: Int?
  private var displayConnectionState = "idle"
  private var displayLastAction: String?
  private var displayLastStatus: String?
  private var displayLastUpdatedAt: Double?
  private var displayRenderPath: String?
  private var displayLastError: String?
  private var displayActiveWidgetId: String?
  private var displayDescriptorCid: String?
  private var displayInterfaceCid: String?
  private var displayManifestCid: String?
  private var displayWidgetCid: String?
  private var displayOrbReceiptCid: String?
  private var displayPolicyDecision: Any?
  private var displayCorrelationId: String?
  private var displayRequestId: String?
  private var displayFallback: [String: Any]?
  private var displayFocusTarget: String?
  private var displayUpdateCount = 0
  private var displayLifecycleStages: [String] = []

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
      "mimeType": NSNull(),
      "displayConnectionState": self.displayConnectionState,
      "displayLastAction": self.displayLastAction as Any,
      "displayLastStatus": self.displayLastStatus as Any,
      "displayLastUpdatedAt": self.displayLastUpdatedAt as Any
    ]
  }

  private func mwdatInfo() -> [String: Any] {
    return (Bundle.main.infoDictionary ?? [:])["MWDAT"] as? [String: Any] ?? [:]
  }

  private func analyticsOptOut(from mwdat: [String: Any]) -> Bool {
    let analytics = mwdat["Analytics"] as? [String: Any]
    return analytics?["OptOut"] as? Bool ?? false
  }

  private func isDatSdkLinked() -> Bool {
#if canImport(MWDATCore)
    return true
#else
    return false
#endif
  }

  private func isDisplaySdkLinked() -> Bool {
#if canImport(MWDATCore) && canImport(MWDATDisplay)
    return true
#else
    return false
#endif
  }

  private func integrationMode() -> String {
    return isDatSdkLinked() ? "sdk_reflection" : "reference_only"
  }

  private func appModelDamEnabled(from mwdat: [String: Any]) -> Bool {
    if let damEnabled = mwdat["DAMEnabled"] as? Bool {
      return damEnabled
    }
    let appModel = mwdat["AppModel"] as? [String: Any]
    return appModel?["DAMEnabled"] as? Bool ?? false
  }

  private func sdkMeetsMinimum(from mwdat: [String: Any]) -> Bool {
    guard let sdkVersion = (mwdat["SDKVersion"] as? String) ?? (mwdat["DATSDKVersionTarget"] as? String) else {
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
    return isDisplaySdkLinked() && appModelDamEnabled(from: mwdat) && sdkMeetsMinimum(from: mwdat) && self.selectedDeviceId != nil
  }

  private func datConfigWarnings() -> [String] {
    let mwdat = mwdatInfo()
    var warnings: [String] = []
    if !isDatSdkLinked() {
      warnings.append("DAT SDK classes are not linked into this iOS build.")
    } else if !isDisplaySdkLinked() {
      warnings.append("DAT display SDK classes are not linked into this iOS build.")
    }
    if !appModelDamEnabled(from: mwdat) {
      warnings.append("DAM app-model is disabled; DAT display capability remains unavailable.")
    }
    if !sdkMeetsMinimum(from: mwdat) {
      warnings.append("Configured iOS DAT SDK metadata is below required \(minimumDatSdkVersion) for display.")
    }
    return warnings
  }

  private func buildCapabilitiesMap(
    sdkLinked: Bool,
    displaySdkLinked: Bool,
    damEnabled: Bool,
    sdkMeetsMinimum: Bool
  ) -> [String: Bool] {
    let displayAvailable = sdkLinked && displaySdkLinked && damEnabled && sdkMeetsMinimum
    return [
      "session": true,
      "camera": sdkLinked,
      "photoCapture": sdkLinked,
      "videoStream": sdkLinked,
      "audio": false,
      "display": displayAvailable,
      "displayVideo": displayAvailable
    ]
  }

  private func displayActionAvailability(
    action: String,
    videoUrl: String? = nil,
    requiresVideoUrl: Bool = false
  ) -> DisplayActionAvailability {
    let mwdat = mwdatInfo()
    if !isDatSdkLinked() {
      return DisplayActionAvailability.blocked(
        state: "sdk_unlinked",
        reason: "dat_sdk_unlinked",
        message: "DAT SDK classes are not linked into this iOS build."
      )
    }
    if !isDisplaySdkLinked() {
      return DisplayActionAvailability.blocked(
        state: "display_sdk_unlinked",
        reason: "display_sdk_unlinked",
        message: "DAT display SDK classes are not linked into this iOS build."
      )
    }
    if !appModelDamEnabled(from: mwdat) {
      return DisplayActionAvailability.blocked(
        state: "dam_disabled",
        reason: "dam_disabled",
        message: "DAT display actions require DAM app-model enablement."
      )
    }
    if !sdkMeetsMinimum(from: mwdat) {
      return DisplayActionAvailability.blocked(
        state: "sdk_version_unsupported",
        reason: "sdk_version_unsupported",
        message: "DAT display actions require iOS DAT SDK \(minimumDatSdkVersion) or newer."
      )
    }
    if self.selectedDeviceId == nil {
      return DisplayActionAvailability.blocked(
        state: "awaiting_target",
        reason: "target_required",
        message: "Select a display-capable glasses target before running this DAT display action."
      )
    }
    if requiresVideoUrl {
      guard let videoUrl, !videoUrl.isEmpty else {
        return DisplayActionAvailability.blocked(
          state: "video_url_required",
          reason: "video_url_required",
          message: "Display video playback requires an HTTPS MP4 URL and DAM app-model support."
        )
      }
      if !videoUrl.lowercased().hasPrefix("https://") {
        return DisplayActionAvailability.blocked(
          state: "video_uri_unsupported",
          reason: "video_uri_unsupported",
          message: "DAT display video playback requires an HTTPS MP4 URL."
        )
      }
    }
    return DisplayActionAvailability.ready(state: successConnectionState(for: action))
  }

  private func successConnectionState(for action: String) -> String {
    switch action {
    case "render_display_test", "render_display_widget":
      return "rendered"
    case "clear_display", "clear_display_widget":
      return "cleared"
    case "play_display_video", "play_display_widget_video":
      return "video_playing"
    case "reset_display_session", "reset_display_widget_session":
      return "reset"
    case "update_display_widget":
      return "updated"
    case "focus_display_widget":
      return "focused"
    case "activate_display_widget_action":
      return "action_activated"
    case "subscribe_display_widget_updates":
      return "updates_subscribed"
    default:
      return "ready"
    }
  }

  private func displayActionSuccessMessage(action: String) -> String {
    switch action {
    case "render_display_test":
      return "Display test card queued by the iOS DAT bridge lifecycle."
    case "clear_display":
      return "Display clear queued by the iOS DAT bridge lifecycle."
    case "play_display_video":
      return "Display video playback queued by the iOS DAT bridge lifecycle."
    case "reset_display_session":
      return "Display session reset queued by the iOS DAT bridge lifecycle."
    case "render_display_widget":
      return "Display widget render queued by the iOS DAT bridge lifecycle."
    case "update_display_widget":
      return "Display widget update queued by the iOS DAT bridge lifecycle."
    case "clear_display_widget":
      return "Display widget clear queued by the iOS DAT bridge lifecycle."
    case "focus_display_widget":
      return "Display widget focus queued by the iOS DAT bridge lifecycle."
    case "activate_display_widget_action":
      return "Display widget action activation queued by the iOS DAT bridge lifecycle."
    case "reset_display_widget_session":
      return "Display widget session reset queued by the iOS DAT bridge lifecycle."
    case "play_display_widget_video":
      return "Display widget video playback queued by the iOS DAT bridge lifecycle."
    case "subscribe_display_widget_updates":
      return "Display widget update subscription queued by the iOS DAT bridge lifecycle."
    default:
      return "DAT display action queued by the iOS DAT bridge lifecycle."
    }
  }

  private func fallbackDisplayConnectionState() -> String {
    return self.selectedDeviceId == nil ? "awaiting_target" : "blocked"
  }

  private func updateDisplayState(
    action: String,
    status: String,
    connectionState: String,
    renderPath: String? = nil,
    error: String? = nil,
    lifecycleStage: String? = nil
  ) {
    self.displayLastAction = action
    self.displayLastStatus = status
    self.displayConnectionState = connectionState
    self.displayLastUpdatedAt = Date().timeIntervalSince1970 * 1000
    self.displayRenderPath = renderPath
    self.displayLastError = error
    if let lifecycleStage, !lifecycleStage.isEmpty, self.displayLifecycleStages.last != lifecycleStage {
      self.displayLifecycleStages.append(lifecycleStage)
      self.displayLifecycleStages = Array(self.displayLifecycleStages.suffix(16))
    }
  }

  private func mapValue(_ value: Any?) -> [String: Any]? {
    return value as? [String: Any]
  }

  private func stringValue(_ value: Any?) -> String? {
    if value == nil || value is NSNull {
      return nil
    }
    guard let string = value as? String, !string.isEmpty else {
      return nil
    }
    return string
  }

  private func firstString(_ values: Any?...) -> String? {
    for value in values {
      if let string = stringValue(value) {
        return string
      }
    }
    return nil
  }

  private func firstValue(_ values: Any?...) -> Any? {
    for value in values {
      if value != nil && !(value is NSNull) {
        return value
      }
    }
    return nil
  }

  private func displayWidgetPayload(_ context: [String: Any]?) -> [String: Any]? {
    guard let context else {
      return nil
    }
    return mapValue(context["display_widget_action"])
      ?? mapValue(context["mobile_payload"])
      ?? context
  }

  private func displayWidgetActionInput(
    action: String,
    operation: String,
    input: [String: Any] = [:],
    context: [String: Any]? = nil,
    inputKey: String? = nil
  ) -> [String: Any] {
    var payload = displayWidgetPayload(context) ?? displayWidgetPayload(input) ?? input
    if let inputKey, payload[inputKey] == nil {
      payload[inputKey] = input
    }
    if payload["operation"] == nil {
      payload["operation"] = operation
    }
    if payload["action"] == nil {
      payload["action"] = action
    }
    return payload
  }

  private func displayWidgetMetadata(_ input: [String: Any]) -> DisplayWidgetMetadata {
    let manifest = mapValue(input["manifest"]) ?? input
    let focus = mapValue(input["focus"])
    return DisplayWidgetMetadata(
      contract: stringValue(input["contract"]),
      type: stringValue(input["type"]),
      operation: firstString(input["operation"], manifest["operation"]),
      descriptorCid: firstString(input["descriptor_cid"], input["descriptorCid"], manifest["descriptor_cid"], manifest["descriptorCid"]),
      interfaceCid: firstString(input["interface_cid"], input["interfaceCid"], manifest["interface_cid"], manifest["interfaceCid"]),
      manifestCid: firstString(input["manifest_cid"], input["manifestCid"], manifest["manifest_cid"], manifest["manifestCid"]),
      widgetId: firstString(input["widget_id"], input["widgetId"], manifest["widget_id"], manifest["widgetId"], manifest["id"], self.displayActiveWidgetId),
      widgetCid: firstString(input["widget_cid"], input["widgetCid"], manifest["widget_cid"], manifest["widgetCid"], manifest["cid"]),
      orbReceiptCid: firstString(input["orb_receipt_cid"], input["orbReceiptCid"], input["receipt_cid"], input["receiptCid"]),
      policyDecision: firstValue(input["policy_decision"], input["policyDecision"]),
      correlationId: firstString(input["correlation_id"], input["correlationId"]),
      requestId: firstString(input["request_id"], input["requestId"]),
      issuedAt: firstString(input["issued_at"], input["issuedAt"]),
      focusDirection: firstString(focus?["direction"], input["direction"]),
      activatedActionId: firstString(input["activated_action_id"], input["activatedActionId"], input["action_id"], input["actionId"]),
      fallback: mapValue(input["fallback"])
    )
  }

  private func fallbackRenderPath(_ metadata: DisplayWidgetMetadata) -> String {
    return firstString(metadata.fallback?["renderPath"], metadata.fallback?["render_path"]) ?? "mobile-card"
  }

  private func displayWidgetFallback(
    _ metadata: DisplayWidgetMetadata,
    reason: String?,
    message: String
  ) -> [String: Any] {
    var fallback = metadata.fallback ?? [:]
    if firstString(fallback["reason"]) == nil {
      fallback["reason"] = reason ?? "dat_native_display_unavailable"
    }
    if firstString(fallback["renderPath"]) == nil {
      fallback["renderPath"] = firstString(fallback["render_path"]) ?? "mobile-card"
    }
    if firstString(fallback["message"]) == nil {
      fallback["message"] = message
    }
    return fallback
  }

  private func applyDisplayWidgetState(
    action: String,
    metadata: DisplayWidgetMetadata,
    supported: Bool,
    reason: String?,
    message: String,
    connectionState: String,
    unavailableConnectionState: String? = nil
  ) -> [String: Any]? {
    switch action {
    case "render_display_widget":
      if supported {
        self.displayActiveWidgetId = metadata.widgetId
        self.displayUpdateCount = 0
      }
    case "update_display_widget":
      if supported {
        self.displayActiveWidgetId = metadata.widgetId ?? self.displayActiveWidgetId
        self.displayUpdateCount += 1
      }
    case "clear_display_widget":
      self.displayActiveWidgetId = nil
      self.displayFocusTarget = nil
    case "focus_display_widget":
      self.displayFocusTarget = metadata.focusDirection
    case "reset_display_widget_session":
      self.displayActiveWidgetId = nil
      self.displayFocusTarget = nil
      self.displayUpdateCount = 0
    default:
      break
    }

    self.displayDescriptorCid = metadata.descriptorCid ?? self.displayDescriptorCid
    self.displayInterfaceCid = metadata.interfaceCid ?? self.displayInterfaceCid
    self.displayManifestCid = metadata.manifestCid ?? self.displayManifestCid
    self.displayWidgetCid = metadata.widgetCid ?? self.displayWidgetCid
    self.displayOrbReceiptCid = metadata.orbReceiptCid ?? self.displayOrbReceiptCid
    self.displayPolicyDecision = metadata.policyDecision ?? self.displayPolicyDecision
    self.displayCorrelationId = metadata.correlationId ?? self.displayCorrelationId
    self.displayRequestId = metadata.requestId ?? self.displayRequestId
    self.displayFallback = metadata.fallback ?? (supported ? nil : displayWidgetFallback(metadata, reason: reason, message: message))

    let renderPath = supported ? "native-dat" : fallbackRenderPath(metadata)
    updateDisplayState(
      action: action,
      status: supported ? "ready" : "blocked",
      connectionState: supported ? connectionState : (unavailableConnectionState ?? fallbackDisplayConnectionState()),
      renderPath: renderPath,
      error: reason,
      lifecycleStage: supported ? "content_sent" : unavailableConnectionState
    )
    return supported ? nil : displayWidgetFallback(metadata, reason: reason, message: message)
  }

  private func displayWidgetActionResult(
    action: String,
    operation: String,
    input: [String: Any],
    supported: Bool,
    reason: String?,
    message: String,
    connectionState: String,
    unavailableConnectionState: String? = nil,
    requiredAction: String? = nil
  ) -> [String: Any] {
    let metadata = displayWidgetMetadata(input)
    let resolvedReason = supported ? nil : (reason ?? "dat_native_display_unavailable")
    let fallback = applyDisplayWidgetState(
      action: action,
      metadata: metadata,
      supported: supported,
      reason: resolvedReason,
      message: message,
      connectionState: connectionState,
      unavailableConnectionState: unavailableConnectionState
    )
    let renderPath = supported ? "native-dat" : fallbackRenderPath(metadata)
    let result: [String: Any] = [
      "state": supported ? "ready" : "not_supported",
      "mode": supported ? "native_display" : integrationMode(),
      "supported": supported,
      "action": action,
      "operation": metadata.operation ?? operation,
      "reason": resolvedReason as Any,
      "message": message,
      "renderPath": renderPath,
      "requiredAction": requiredAction as Any,
      "deviceId": self.selectedDeviceId as Any,
      "targetConnectionState": self.selectedDeviceId == nil ? "unselected" : (self.sessionState == "target_ready" ? "ready" : "selected"),
      "assetUri": NSNull(),
      "mimeType": NSNull(),
      "displayConnectionState": self.displayConnectionState,
      "displayLastAction": self.displayLastAction as Any,
      "displayLastStatus": self.displayLastStatus as Any,
      "displayLastUpdatedAt": self.displayLastUpdatedAt as Any,
      "displayRenderPath": self.displayRenderPath as Any,
      "displayLastError": self.displayLastError as Any,
      "displayUpdateCount": self.displayUpdateCount,
      "displayLifecycleStages": self.displayLifecycleStages,
      "widgetId": metadata.widgetId as Any,
      "widgetCid": metadata.widgetCid as Any,
      "descriptorCid": metadata.descriptorCid as Any,
      "interfaceCid": metadata.interfaceCid as Any,
      "manifestCid": metadata.manifestCid as Any,
      "orbReceiptCid": metadata.orbReceiptCid as Any,
      "policyDecision": metadata.policyDecision as Any,
      "correlationId": metadata.correlationId as Any,
      "requestId": metadata.requestId as Any,
      "issuedAt": metadata.issuedAt as Any,
      "focusDirection": metadata.focusDirection as Any,
      "activatedActionId": metadata.activatedActionId as Any,
      "fallback": supported
        ? NSNull() as Any
        : (fallback ?? displayWidgetFallback(metadata, reason: resolvedReason, message: message)) as Any
    ]
    emitDisplayWidgetEvent(action: action, supported: supported, payload: result)
    return result
  }

  private func emitDisplayWidgetEvent(action: String, supported: Bool, payload: [String: Any]) {
    if !supported {
      self.sendEvent("display_widget_error", payload)
      return
    }
    switch action {
    case "render_display_widget":
      self.sendEvent("display_widget_rendered", payload)
    case "update_display_widget":
      self.sendEvent("display_widget_updated", payload)
    case "clear_display_widget":
      self.sendEvent("display_widget_cleared", payload)
    case "reset_display_widget_session":
      self.sendEvent("display_widget_session_reset", payload)
    default:
      self.sendEvent("display_widget_action", payload)
    }
  }

  public func definition() -> ModuleDefinition {
    Name("ExpoMetaWearablesDat")

    Events(
      "onDatStateChanged",
      "display_widget_rendered",
      "display_widget_updated",
      "display_widget_cleared",
      "display_widget_action",
      "display_widget_error",
      "display_widget_session_reset"
    )

    OnCreate {
      self.selectedDeviceId = UserDefaults.standard.string(forKey: self.selectedDeviceDefaultsKey)
    }

    AsyncFunction("isDatAvailable") { () -> Bool in
      isDatSdkLinked()
    }

    AsyncFunction("getConfiguration") { () -> [String: Any] in
      let mwdat = mwdatInfo()
      let sdkLinked = isDatSdkLinked()
      let displaySdkLinked = isDisplaySdkLinked()
      return [
        "platform": "ios",
        "sdkLinked": sdkLinked,
        "sdkConfigured": sdkLinked,
        "sdkMeetsMinimum": sdkMeetsMinimum(from: mwdat),
        "analyticsOptOut": analyticsOptOut(from: mwdat),
        "sdkVersion": mwdat["SDKVersion"] as? String as Any,
        "sdkVersionTarget": (mwdat["DATSDKVersionTarget"] as? String) ?? minimumDatSdkVersion,
        "datAppModelEnabled": appModelDamEnabled(from: mwdat),
        "displayDamRequired": true,
        "displayDamEnabled": appModelDamEnabled(from: mwdat),
        "displaySdkLinked": displaySdkLinked,
        "applicationId": mwdat["ApplicationId"] as? String,
        "provider": "internal_bridge",
        "integrationMode": integrationMode()
      ]
    }

    AsyncFunction("getCapabilities") { () -> [String: Any] in
      let mwdat = mwdatInfo()
      return buildCapabilitiesMap(
        sdkLinked: isDatSdkLinked(),
        displaySdkLinked: isDisplaySdkLinked(),
        damEnabled: appModelDamEnabled(from: mwdat),
        sdkMeetsMinimum: sdkMeetsMinimum(from: mwdat)
      )
    }

    AsyncFunction("getConnectedDevice") { () -> [String: Any]? in
      return [
        "platform": "ios",
        "sdkLinked": isDatSdkLinked(),
        "sdkConfigured": isDatSdkLinked(),
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
      let sdkLinked = isDatSdkLinked()
      let displaySdkLinked = isDisplaySdkLinked()
      return [
        "available": true,
        "platform": "ios",
        "sdkLinked": sdkLinked,
        "sdkConfigured": sdkLinked,
        "sdkMeetsMinimum": sdkMeetsMinimumValue,
        "analyticsOptOut": analyticsOptOut(from: mwdat),
        "sdkVersion": mwdat["SDKVersion"] as? String as Any,
        "sdkVersionTarget": (mwdat["DATSDKVersionTarget"] as? String) ?? minimumDatSdkVersion,
        "datAppModelEnabled": damEnabled,
        "displayDamRequired": true,
        "displayDamEnabled": damEnabled,
        "displaySdkLinked": displaySdkLinked,
        "displayReady": displaySdkLinked && damEnabled && sdkMeetsMinimumValue && appModelDisplayReady(),
        "configWarnings": datConfigWarnings(),
        "applicationId": mwdat["ApplicationId"] as? String as Any,
        "provider": "internal_bridge",
        "integrationMode": integrationMode(),
        "capabilities": buildCapabilitiesMap(
          sdkLinked: sdkLinked,
          displaySdkLinked: displaySdkLinked,
          damEnabled: damEnabled,
          sdkMeetsMinimum: sdkMeetsMinimumValue
        ),
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
        "targetRssi": self.selectedDeviceRssi as Any,
        "displayConnectionState": self.displayConnectionState,
        "displayLastAction": self.displayLastAction as Any,
        "displayLastStatus": self.displayLastStatus as Any,
        "displayLastUpdatedAt": self.displayLastUpdatedAt as Any,
        "displayRenderPath": self.displayRenderPath as Any,
        "displayLastError": self.displayLastError as Any,
        "displayActiveWidgetId": self.displayActiveWidgetId as Any,
        "displayDescriptorCid": self.displayDescriptorCid as Any,
        "displayInterfaceCid": self.displayInterfaceCid as Any,
        "displayManifestCid": self.displayManifestCid as Any,
        "displayWidgetCid": self.displayWidgetCid as Any,
        "displayOrbReceiptCid": self.displayOrbReceiptCid as Any,
        "displayReceiptCid": self.displayOrbReceiptCid as Any,
        "displayPolicyDecision": self.displayPolicyDecision as Any,
        "displayCorrelationId": self.displayCorrelationId as Any,
        "displayRequestId": self.displayRequestId as Any,
        "displayFallback": self.displayFallback as Any,
        "displayFocusTarget": self.displayFocusTarget as Any,
        "displayUpdateCount": self.displayUpdateCount,
        "displayLifecycleStages": self.displayLifecycleStages
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
      let availability = displayActionAvailability(action: "render_display_test")
      updateDisplayState(
        action: "render_display_test",
        status: availability.supported ? "ready" : "blocked",
        connectionState: availability.supported ? "rendered" : availability.state,
        renderPath: availability.supported ? "native-dat" : "mobile-card",
        error: availability.reason,
        lifecycleStage: availability.supported ? "content_sent" : availability.state
      )
      self.mediaActionResult(
        action: "render_display_test",
        message: availability.supported ? displayActionSuccessMessage(action: "render_display_test") : availability.message,
        supported: availability.supported,
        mode: availability.supported ? "native_display" : integrationMode()
      )
    }

    AsyncFunction("clearDisplay") { () -> [String: Any] in
      let availability = displayActionAvailability(action: "clear_display")
      updateDisplayState(
        action: "clear_display",
        status: availability.supported ? "ready" : "blocked",
        connectionState: availability.supported ? "cleared" : availability.state,
        renderPath: availability.supported ? "native-dat" : "mobile-card",
        error: availability.reason,
        lifecycleStage: availability.supported ? "content_sent" : availability.state
      )
      self.mediaActionResult(
        action: "clear_display",
        message: availability.supported ? displayActionSuccessMessage(action: "clear_display") : availability.message,
        supported: availability.supported,
        mode: availability.supported ? "native_display" : integrationMode()
      )
    }

    AsyncFunction("playDisplayVideo") { (_ videoUrl: String?) -> [String: Any] in
      let availability = displayActionAvailability(
        action: "play_display_video",
        videoUrl: videoUrl,
        requiresVideoUrl: true
      )
      updateDisplayState(
        action: "play_display_video",
        status: availability.supported ? "ready" : "blocked",
        connectionState: availability.supported ? "video_playing" : availability.state,
        renderPath: availability.supported ? "native-dat" : "mobile-card",
        error: availability.reason,
        lifecycleStage: availability.supported ? "content_sent" : availability.state
      )
      self.mediaActionResult(
        action: "play_display_video",
        message: availability.supported ? displayActionSuccessMessage(action: "play_display_video") : availability.message,
        supported: availability.supported,
        mode: availability.supported ? "native_display" : integrationMode()
      )
    }

    AsyncFunction("resetDisplaySession") { () -> [String: Any] in
      let availability = displayActionAvailability(action: "reset_display_session")
      updateDisplayState(
        action: "reset_display_session",
        status: availability.supported ? "ready" : "blocked",
        connectionState: availability.supported ? "reset" : availability.state,
        renderPath: availability.supported ? "native-dat" : "mobile-card",
        error: availability.reason,
        lifecycleStage: availability.supported ? "content_sent" : availability.state
      )
      self.mediaActionResult(
        action: "reset_display_session",
        message: availability.supported ? displayActionSuccessMessage(action: "reset_display_session") : availability.message,
        supported: availability.supported,
        mode: availability.supported ? "native_display" : integrationMode()
      )
    }

    AsyncFunction("renderDisplayWidget") { (_ manifest: [String: Any], _ context: [String: Any]?) -> [String: Any] in
      let availability = displayActionAvailability(action: "render_display_widget")
      let input = displayWidgetActionInput(
        action: "render_display_widget",
        operation: "render_widget",
        input: manifest,
        context: context,
        inputKey: "manifest"
      )
      return displayWidgetActionResult(
        action: "render_display_widget",
        operation: "render_widget",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "render_display_widget") : availability.message,
        connectionState: "rendered",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }

    AsyncFunction("updateDisplayWidget") { (_ patch: [String: Any], _ context: [String: Any]?) -> [String: Any] in
      let availability = displayActionAvailability(action: "update_display_widget")
      let input = displayWidgetActionInput(
        action: "update_display_widget",
        operation: "update_widget",
        input: patch,
        context: context,
        inputKey: "patch"
      )
      return displayWidgetActionResult(
        action: "update_display_widget",
        operation: "update_widget",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "update_display_widget") : availability.message,
        connectionState: "updated",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }

    AsyncFunction("clearDisplayWidget") { (_ widgetId: String?, _ context: [String: Any]?) -> [String: Any] in
      let availability = displayActionAvailability(action: "clear_display_widget")
      let input = displayWidgetActionInput(
        action: "clear_display_widget",
        operation: "clear_widget",
        input: ["widget_id": widgetId as Any],
        context: context
      )
      return displayWidgetActionResult(
        action: "clear_display_widget",
        operation: "clear_widget",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "clear_display_widget") : availability.message,
        connectionState: "cleared",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }

    AsyncFunction("focusDisplayWidget") { (_ direction: String?, _ context: [String: Any]?) -> [String: Any] in
      let availability = displayActionAvailability(action: "focus_display_widget")
      let input = displayWidgetActionInput(
        action: "focus_display_widget",
        operation: direction == "previous" ? "focus_previous" : "focus_next",
        input: [
          "focus": ["direction": direction as Any],
          "operation": direction == "previous" ? "focus_previous" : "focus_next"
        ],
        context: context
      )
      return displayWidgetActionResult(
        action: "focus_display_widget",
        operation: direction == "previous" ? "focus_previous" : "focus_next",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "focus_display_widget") : availability.message,
        connectionState: "focused",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }

    AsyncFunction("activateDisplayWidgetAction") { (_ actionId: String?, _ context: [String: Any]?) -> [String: Any] in
      let availability = displayActionAvailability(action: "activate_display_widget_action")
      let input = displayWidgetActionInput(
        action: "activate_display_widget_action",
        operation: "activate",
        input: ["activated_action_id": actionId as Any],
        context: context
      )
      return displayWidgetActionResult(
        action: "activate_display_widget_action",
        operation: "activate",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "activate_display_widget_action") : availability.message,
        connectionState: "action_activated",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }

    AsyncFunction("resetDisplayWidgetSession") { (_ context: [String: Any]?) -> [String: Any] in
      let availability = displayActionAvailability(action: "reset_display_widget_session")
      let input = displayWidgetActionInput(
        action: "reset_display_widget_session",
        operation: "reset_session",
        context: context
      )
      return displayWidgetActionResult(
        action: "reset_display_widget_session",
        operation: "reset_session",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "reset_display_widget_session") : availability.message,
        connectionState: "reset",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }

    AsyncFunction("playDisplayWidgetVideo") { (_ video: [String: Any]?, _ context: [String: Any]?) -> [String: Any] in
      let videoInput = video ?? [:]
      let videoUrl = firstString(videoInput["uri"], videoInput["url"], videoInput["video_url"], videoInput["videoUrl"])
      let availability = displayActionAvailability(
        action: "play_display_widget_video",
        videoUrl: videoUrl,
        requiresVideoUrl: true
      )
      let input = displayWidgetActionInput(
        action: "play_display_widget_video",
        operation: "play_video",
        input: videoInput,
        context: context,
        inputKey: "video"
      )
      return displayWidgetActionResult(
        action: "play_display_widget_video",
        operation: "play_video",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "play_display_widget_video") : availability.message,
        connectionState: "video_playing",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }

    AsyncFunction("subscribeDisplayWidgetUpdates") { (_ subscription: [String: Any]?, _ context: [String: Any]?) -> [String: Any] in
      let availability = displayActionAvailability(action: "subscribe_display_widget_updates")
      let input = displayWidgetActionInput(
        action: "subscribe_display_widget_updates",
        operation: "subscribe_updates",
        input: subscription ?? [:],
        context: context,
        inputKey: "subscription"
      )
      return displayWidgetActionResult(
        action: "subscribe_display_widget_updates",
        operation: "subscribe_updates",
        input: input,
        supported: availability.supported,
        reason: availability.reason,
        message: availability.supported ? displayActionSuccessMessage(action: "subscribe_display_widget_updates") : availability.message,
        connectionState: "updates_subscribed",
        unavailableConnectionState: availability.state,
        requiredAction: availability.requiredAction
      )
    }
  }
}

private struct DisplayActionAvailability {
  let supported: Bool
  let state: String
  let reason: String?
  let message: String
  let requiredAction: String?

  static func ready(state: String) -> DisplayActionAvailability {
    return DisplayActionAvailability(
      supported: true,
      state: state,
      reason: nil,
      message: "",
      requiredAction: nil
    )
  }

  static func blocked(
    state: String,
    reason: String,
    message: String,
    requiredAction: String? = nil
  ) -> DisplayActionAvailability {
    return DisplayActionAvailability(
      supported: false,
      state: state,
      reason: reason,
      message: message,
      requiredAction: requiredAction
    )
  }
}

private struct DisplayWidgetMetadata {
  let contract: String?
  let type: String?
  let operation: String?
  let descriptorCid: String?
  let interfaceCid: String?
  let manifestCid: String?
  let widgetId: String?
  let widgetCid: String?
  let orbReceiptCid: String?
  let policyDecision: Any?
  let correlationId: String?
  let requestId: String?
  let issuedAt: String?
  let focusDirection: String?
  let activatedActionId: String?
  let fallback: [String: Any]?
}
