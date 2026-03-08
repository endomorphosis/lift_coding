import CoreBluetooth
import Foundation

final class BluetoothPeerBridge: NSObject {
  static let serviceUUID = CBUUID(string: "9F5B0010-3B1C-4A6E-8D1E-7C0B6A12F001")
  static let frameCharacteristicUUID = CBUUID(string: "9F5B0011-3B1C-4A6E-8D1E-7C0B6A12F001")

  var onPeerDiscovered: (([String: Any]) -> Void)?
  var onPeerConnected: (([String: Any]) -> Void)?
  var onPeerDisconnected: (([String: Any]) -> Void)?
  var onFrameReceived: (([String: Any]) -> Void)?

  private lazy var centralManager = CBCentralManager(delegate: self, queue: nil)
  private lazy var peripheralManager = CBPeripheralManager(delegate: self, queue: nil)

  private var advertisedIdentity: [String: Any]?
  private var discoveredPeripherals: [UUID: CBPeripheral] = [:]
  private var discoveredPeers: [String: [String: Any]] = [:]
  private var connectedPeripherals: [String: CBPeripheral] = [:]
  private var frameCharacteristics: [String: CBCharacteristic] = [:]
  private var pendingScanStopWorkItem: DispatchWorkItem?
  private var mutableFrameCharacteristic: CBMutableCharacteristic?
  private var isScanning = false

  func scanPeers(timeoutMs: Int) -> [[String: Any]] {
    guard centralManager.state == .poweredOn else {
      return Array(discoveredPeers.values)
    }

    isScanning = true
    centralManager.scanForPeripherals(
      withServices: [Self.serviceUUID],
      options: [CBCentralManagerScanOptionAllowDuplicatesKey: false]
    )

    pendingScanStopWorkItem?.cancel()
    let workItem = DispatchWorkItem { [weak self] in
      self?.isScanning = false
      self?.centralManager.stopScan()
    }
    pendingScanStopWorkItem = workItem
    DispatchQueue.main.asyncAfter(deadline: .now() + .milliseconds(max(0, timeoutMs)), execute: workItem)
    return Array(discoveredPeers.values)
  }

  func advertiseIdentity(peerId: String, displayName: String?) throws -> [String: Any] {
    guard !peerId.isEmpty else {
      throw NSError(
        domain: "ERR_INVALID_PEER_ID",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "peerId cannot be empty"]
      )
    }

    let identity: [String: Any] = [
      "peerId": peerId,
      "displayName": displayName ?? ""
    ]
    advertisedIdentity = identity
    startAdvertisingIfPossible()
    return identity
  }

  func connectPeer(_ peerRef: String) throws -> [String: Any] {
    guard !peerRef.isEmpty else {
      throw NSError(
        domain: "ERR_INVALID_PEER_REF",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "peerRef cannot be empty"]
      )
    }
    guard let peer = discoveredPeers[peerRef] else {
      throw NSError(
        domain: "ERR_PEER_NOT_FOUND",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "peerRef is not discovered"]
      )
    }
    guard let uuid = UUID(uuidString: peerRef), let peripheral = discoveredPeripherals[uuid] else {
      throw NSError(
        domain: "ERR_PEER_NOT_FOUND",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "peerRef has no matching peripheral"]
      )
    }

    centralManager.connect(peripheral, options: nil)
    return makeConnectionEvent(peerRef: peerRef, peerId: peer["peerId"] as? String)
  }

  func disconnectPeer(_ peerRef: String, reason: String?) {
    if let peripheral = connectedPeripherals[peerRef] {
      centralManager.cancelPeripheralConnection(peripheral)
    }
    connectedPeripherals.removeValue(forKey: peerRef)
    frameCharacteristics.removeValue(forKey: peerRef)
    onPeerDisconnected?([
      "peerRef": peerRef,
      "reason": reason ?? "manual"
    ])
  }

  func sendFrame(peerRef: String, payloadBase64: String) throws {
    guard !payloadBase64.isEmpty else {
      throw NSError(
        domain: "ERR_INVALID_FRAME",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "payloadBase64 cannot be empty"]
      )
    }
    guard
      let peripheral = connectedPeripherals[peerRef],
      let characteristic = frameCharacteristics[peerRef]
    else {
      throw NSError(
        domain: "ERR_PEER_NOT_CONNECTED",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "peerRef is not connected"]
      )
    }
    guard let data = Data(base64Encoded: payloadBase64) else {
      throw NSError(
        domain: "ERR_INVALID_FRAME",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "payloadBase64 is not valid base64"]
      )
    }
    peripheral.writeValue(data, for: characteristic, type: .withResponse)
  }

  func simulatePeerDiscovery(_ peer: [String: Any]) throws -> [String: Any] {
    let normalized = try normalizePeer(peer)
    discoveredPeers[normalized["peerRef"] as! String] = normalized
    onPeerDiscovered?(normalized)
    return normalized
  }

  func simulatePeerConnection(_ peerRef: String) throws -> [String: Any] {
    let peer = discoveredPeers[peerRef]
    let event = makeConnectionEvent(peerRef: peerRef, peerId: peer?["peerId"] as? String)
    onPeerConnected?(event)
    return event
  }

  func simulateFrameReceived(peerRef: String, payloadBase64: String, peerId: String?) throws {
    guard !payloadBase64.isEmpty else {
      throw NSError(
        domain: "ERR_INVALID_FRAME",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "payloadBase64 cannot be empty"]
      )
    }
    onFrameReceived?([
      "peerRef": peerRef,
      "peerId": peerId ?? (discoveredPeers[peerRef]?["peerId"] as? String) ?? "",
      "payloadBase64": payloadBase64
    ])
  }

  func resetSimulation() {
    isScanning = false
    connectedPeripherals.values.forEach { centralManager.cancelPeripheralConnection($0) }
    connectedPeripherals.removeAll()
    frameCharacteristics.removeAll()
    discoveredPeers.removeAll()
    discoveredPeripherals.removeAll()
  }

  func getAdapterState() -> [String: Any] {
    let authorizationState: CBManagerAuthorization
    if #available(iOS 13.1, *) {
      authorizationState = CBCentralManager.authorization
    } else {
      authorizationState = .allowedAlways
    }

    let permissionGranted = authorizationState == .allowedAlways
    return [
      "transport": "bluetooth",
      "adapterAvailable": true,
      "adapterEnabled": centralManager.state == .poweredOn || peripheralManager.state == .poweredOn,
      "scanPermissionGranted": permissionGranted,
      "connectPermissionGranted": permissionGranted,
      "advertisePermissionGranted": permissionGranted,
      "advertising": peripheralManager.isAdvertising,
      "scanning": isScanning,
      "state": describeState(centralManager.state)
    ]
  }

  private func startAdvertisingIfPossible() {
    guard peripheralManager.state == .poweredOn else {
      return
    }
    if mutableFrameCharacteristic == nil {
      let characteristic = CBMutableCharacteristic(
        type: Self.frameCharacteristicUUID,
        properties: [.write, .notify],
        value: nil,
        permissions: [.writeable]
      )
      let service = CBMutableService(type: Self.serviceUUID, primary: true)
      service.characteristics = [characteristic]
      mutableFrameCharacteristic = characteristic
      peripheralManager.removeAllServices()
      peripheralManager.add(service)
    }

    guard let identity = advertisedIdentity else {
      return
    }

    let peerId = identity["peerId"] as? String ?? ""
    let displayName = identity["displayName"] as? String ?? ""
    let resolvedName = displayName.isEmpty ? peerId : displayName
    peripheralManager.stopAdvertising()
    peripheralManager.startAdvertising([
      CBAdvertisementDataServiceUUIDsKey: [Self.serviceUUID],
      CBAdvertisementDataLocalNameKey: resolvedName,
      CBAdvertisementDataServiceDataKey: [Self.serviceUUID: Data(resolvedName.utf8)]
    ])
  }

  private func normalizePeer(_ peer: [String: Any]) throws -> [String: Any] {
    guard let peerRef = peer["peerRef"] as? String, !peerRef.isEmpty else {
      throw NSError(
        domain: "ERR_INVALID_PEER_REF",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "peerRef cannot be empty"]
      )
    }
    guard let peerId = peer["peerId"] as? String, !peerId.isEmpty else {
      throw NSError(
        domain: "ERR_INVALID_PEER_ID",
        code: 0,
        userInfo: [NSLocalizedDescriptionKey: "peerId cannot be empty"]
      )
    }
    var normalized: [String: Any] = [
      "peerRef": peerRef,
      "peerId": peerId,
      "transport": (peer["transport"] as? String) ?? "simulated"
    ]
    if let displayName = peer["displayName"] as? String {
      normalized["displayName"] = displayName
    }
    if let rssi = peer["rssi"] as? Int {
      normalized["rssi"] = rssi
    }
    return normalized
  }

  private func makeConnectionEvent(peerRef: String, peerId: String?) -> [String: Any] {
    [
      "peerRef": peerRef,
      "peerId": peerId ?? "",
      "transport": "bluetooth",
      "connectedAt": Int(Date().timeIntervalSince1970 * 1000)
    ]
  }

  private func describeState(_ state: CBManagerState) -> String {
    switch state {
    case .unknown:
      return "unknown"
    case .resetting:
      return "resetting"
    case .unsupported:
      return "unsupported"
    case .unauthorized:
      return "unauthorized"
    case .poweredOff:
      return "powered_off"
    case .poweredOn:
      return "powered_on"
    @unknown default:
      return "unknown"
    }
  }
}

extension BluetoothPeerBridge: CBCentralManagerDelegate {
  func centralManagerDidUpdateState(_ central: CBCentralManager) {
    if central.state == .poweredOn {
      startAdvertisingIfPossible()
    } else if central.state != .resetting {
      isScanning = false
    }
  }

  func centralManager(
    _ central: CBCentralManager,
    didDiscover peripheral: CBPeripheral,
    advertisementData: [String: Any],
    rssi RSSI: NSNumber
  ) {
    discoveredPeripherals[peripheral.identifier] = peripheral
    let peerRef = peripheral.identifier.uuidString
    let serviceData = advertisementData[CBAdvertisementDataServiceDataKey] as? [CBUUID: Data]
    let advertisedName = serviceData?[Self.serviceUUID]
      .flatMap { String(data: $0, encoding: .utf8) }
      ?.trimmingCharacters(in: .whitespacesAndNewlines)
    let displayName = advertisedName
      ?? (advertisementData[CBAdvertisementDataLocalNameKey] as? String)
      ?? peripheral.name
      ?? ""
    let peerId = displayName.isEmpty ? peerRef : displayName
    let peer: [String: Any] = [
      "peerRef": peerRef,
      "peerId": peerId,
      "displayName": displayName,
      "transport": "bluetooth",
      "rssi": RSSI.intValue
    ]
    discoveredPeers[peerRef] = peer
    onPeerDiscovered?(peer)
  }

  func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
    let peerRef = peripheral.identifier.uuidString
    connectedPeripherals[peerRef] = peripheral
    peripheral.delegate = self
    peripheral.discoverServices([Self.serviceUUID])
    let peerId = discoveredPeers[peerRef]?["peerId"] as? String
    onPeerConnected?(makeConnectionEvent(peerRef: peerRef, peerId: peerId))
  }

  func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
    onPeerDisconnected?([
      "peerRef": peripheral.identifier.uuidString,
      "reason": error?.localizedDescription ?? "connect_failed"
    ])
  }

  func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
    let peerRef = peripheral.identifier.uuidString
    connectedPeripherals.removeValue(forKey: peerRef)
    frameCharacteristics.removeValue(forKey: peerRef)
    onPeerDisconnected?([
      "peerRef": peerRef,
      "reason": error?.localizedDescription ?? "disconnected"
    ])
  }
}

extension BluetoothPeerBridge: CBPeripheralDelegate {
  func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
    guard error == nil else { return }
    peripheral.services?
      .filter { $0.uuid == Self.serviceUUID }
      .forEach { peripheral.discoverCharacteristics([Self.frameCharacteristicUUID], for: $0) }
  }

  func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
    guard error == nil else { return }
    for characteristic in service.characteristics ?? [] where characteristic.uuid == Self.frameCharacteristicUUID {
      frameCharacteristics[peripheral.identifier.uuidString] = characteristic
      if characteristic.properties.contains(.notify) {
        peripheral.setNotifyValue(true, for: characteristic)
      }
    }
  }

  func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
    guard error == nil, characteristic.uuid == Self.frameCharacteristicUUID, let value = characteristic.value else {
      return
    }
    onFrameReceived?([
      "peerRef": peripheral.identifier.uuidString,
      "peerId": (discoveredPeers[peripheral.identifier.uuidString]?["peerId"] as? String) ?? "",
      "payloadBase64": value.base64EncodedString()
    ])
  }
}

extension BluetoothPeerBridge: CBPeripheralManagerDelegate {
  func peripheralManagerDidUpdateState(_ peripheral: CBPeripheralManager) {
    if peripheral.state == .poweredOn {
      startAdvertisingIfPossible()
    }
  }

  func peripheralManager(_ peripheral: CBPeripheralManager, didReceiveWrite requests: [CBATTRequest]) {
    for request in requests where request.characteristic.uuid == Self.frameCharacteristicUUID {
      let payload = request.value?.base64EncodedString() ?? ""
      let peerRef = request.central.identifier.uuidString
      onFrameReceived?([
        "peerRef": peerRef,
        "peerId": peerRef,
        "payloadBase64": payload
      ])
      peripheral.respond(to: request, withResult: .success)
    }
  }
}
