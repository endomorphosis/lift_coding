import ExpoModulesCore

public class ExpoMetaWearablesDatModule: Module {
  private var sessionState = "idle"

  public func definition() -> ModuleDefinition {
    Name("ExpoMetaWearablesDat")

    Events("onDatStateChanged")

    AsyncFunction("isDatAvailable") { () -> Bool in
      false
    }

    AsyncFunction("getConfiguration") { () -> [String: Any] in
      let info = Bundle.main.infoDictionary ?? [:]
      let mwdat = info["MWDAT"] as? [String: Any]
      let analytics = mwdat?["Analytics"] as? [String: Any]
      return [
        "platform": "ios",
        "sdkLinked": false,
        "sdkConfigured": false,
        "analyticsOptOut": analytics?["OptOut"] as? Bool ?? false,
        "sdkVersion": NSNull(),
        "applicationId": mwdat?["ApplicationId"] as? String,
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
        "audio": false
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

    AsyncFunction("getDiagnostics") { () -> [String: Any] in
      let info = Bundle.main.infoDictionary ?? [:]
      let mwdat = info["MWDAT"] as? [String: Any]
      let analytics = mwdat?["Analytics"] as? [String: Any]
      return [
        "available": true,
        "platform": "ios",
        "sdkLinked": false,
        "sdkConfigured": false,
        "analyticsOptOut": analytics?["OptOut"] as? Bool ?? false,
        "sdkVersion": NSNull(),
        "applicationId": mwdat?["ApplicationId"] as? String as Any,
        "provider": "internal_bridge",
        "integrationMode": "reference_only",
        "capabilities": [
          "session": true,
          "camera": false,
          "photoCapture": false,
          "videoStream": false,
          "audio": false
        ],
        "sessionState": self.sessionState,
        "registrationState": self.sessionState,
        "deviceCount": 0,
        "activeDeviceId": NSNull()
      ]
    }

    AsyncFunction("startDeviceSession") { () -> [String: Any] in
      self.sessionState = "simulated_ready"
      self.sendEvent("onDatStateChanged", ["state": self.sessionState])
      return ["state": self.sessionState]
    }

    AsyncFunction("stopDeviceSession") { () -> [String: Any] in
      self.sessionState = "idle"
      self.sendEvent("onDatStateChanged", ["state": self.sessionState])
      return ["state": self.sessionState]
    }
  }
}
