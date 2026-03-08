package expo.modules.glassesaudio

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattService
import android.bluetooth.BluetoothManager
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.BluetoothLeAdvertiser
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.ParcelUuid
import android.util.Log
import androidx.core.content.ContextCompat
import java.util.UUID

class BluetoothPeerBridge(
  private val context: Context,
  private val sendEvent: (name: String, payload: Map<String, Any>) -> Unit,
) {
  companion object {
    private const val TAG = "BluetoothPeerBridge"
    private val SERVICE_UUID: UUID = UUID.fromString("9F5B0010-3B1C-4A6E-8D1E-7C0B6A12F001")
    private val FRAME_CHARACTERISTIC_UUID: UUID = UUID.fromString("9F5B0011-3B1C-4A6E-8D1E-7C0B6A12F001")
  }

  private val bluetoothManager =
    context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
  private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager.adapter
  private val bluetoothLeAdvertiser: BluetoothLeAdvertiser?
    get() = bluetoothAdapter?.bluetoothLeAdvertiser
  private val bluetoothLeScanner: BluetoothLeScanner?
    get() = bluetoothAdapter?.bluetoothLeScanner

  private var advertisedPeerId: String? = null
  private var advertisedDisplayName: String? = null
  private val discoveredPeers = linkedMapOf<String, Map<String, Any>>()
  private val connectedGatts = linkedMapOf<String, BluetoothGatt>()
  private val writableCharacteristics = linkedMapOf<String, BluetoothGattCharacteristic>()
  private var activeScanCallback: ScanCallback? = null
  private var activeAdvertiseCallback: AdvertiseCallback? = null
  private var isScanning = false
  private var isAdvertising = false

  @SuppressLint("MissingPermission")
  fun scanPeers(timeoutMs: Int): List<Map<String, Any>> {
    val timeout = timeoutMs
    if (!canScan()) {
      Log.w(TAG, "scanPeers skipped: adapter unavailable or scan permission missing")
      return discoveredPeers.values.toList()
    }

    Log.d(TAG, "Starting BLE scan for ${maxOf(0, timeout)}ms")
    activeScanCallback?.let { bluetoothLeScanner?.stopScan(it) }
    isScanning = true

    val callback = object : ScanCallback() {
      override fun onScanResult(callbackType: Int, result: ScanResult) {
        val device = result.device ?: return
        val peer = scanResultToPeer(device, result)
        Log.d(TAG, "Discovered peer ${peer["peerRef"]} (${peer["peerId"]})")
        discoveredPeers[peer["peerRef"] as String] = peer
        sendEvent("peerDiscovered", mapOf("peer" to peer))
      }
    }
    activeScanCallback = callback

    val filters = listOf(
      ScanFilter.Builder()
        .setServiceUuid(ParcelUuid(SERVICE_UUID))
        .build()
    )
    val settings = ScanSettings.Builder()
      .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
      .build()
    bluetoothLeScanner?.startScan(filters, settings, callback)

    android.os.Handler(context.mainLooper).postDelayed({
      activeScanCallback?.let { bluetoothLeScanner?.stopScan(it) }
      activeScanCallback = null
      isScanning = false
      Log.d(TAG, "BLE scan finished with ${discoveredPeers.size} discovered peers")
    }, maxOf(0, timeout).toLong())

    bluetoothAdapter?.bondedDevices?.forEach { device ->
      val peer = deviceToPeer(device, null)
      discoveredPeers.putIfAbsent(peer["peerRef"] as String, peer)
    }

    return discoveredPeers.values.toList()
  }

  fun advertiseIdentity(peerId: String, displayName: String?): Map<String, Any> {
    require(peerId.isNotBlank()) { "peerId cannot be empty" }
    advertisedPeerId = peerId
    advertisedDisplayName = displayName
    Log.d(TAG, "Advertising identity peerId=$peerId displayName=${displayName ?: ""}")
    startAdvertisingIfPossible()
    return mapOf(
      "peerId" to peerId,
      "displayName" to (displayName ?: "")
    )
  }

  fun getAdapterState(): Map<String, Any> {
    val adapterAvailable = bluetoothAdapter != null
    val adapterEnabled = bluetoothAdapter?.isEnabled == true
    return mapOf(
      "transport" to "bluetooth",
      "adapterAvailable" to adapterAvailable,
      "adapterEnabled" to adapterEnabled,
      "scanPermissionGranted" to canScanPermission(),
      "connectPermissionGranted" to canConnectPermission(),
      "advertisePermissionGranted" to canAdvertisePermission(),
      "advertising" to isAdvertising,
      "scanning" to isScanning,
      "state" to when {
        !adapterAvailable -> "unavailable"
        !adapterEnabled -> "powered_off"
        else -> "powered_on"
      }
    )
  }

  @SuppressLint("MissingPermission")
  fun connectPeer(peerRef: String): Map<String, Any> {
    require(peerRef.isNotBlank()) { "peerRef cannot be empty" }
    val device = bluetoothAdapter?.getRemoteDevice(peerRef)
      ?: throw IllegalStateException("peerRef is not discoverable")
    if (canConnect()) {
      Log.d(TAG, "Connecting to peer $peerRef")
      connectedGatts[peerRef]?.close()
      connectedGatts[peerRef] = device.connectGatt(context, false, gattCallback)
    }
    val event = connectionEvent(peerRef, discoveredPeers[peerRef]?.get("peerId") as? String)
    sendEvent("peerConnected", event)
    return event
  }

  @SuppressLint("MissingPermission")
  fun disconnectPeer(peerRef: String, reason: String?) {
    Log.d(TAG, "Disconnecting peer $peerRef reason=${reason ?: "manual"}")
    connectedGatts.remove(peerRef)?.let { gatt ->
      writableCharacteristics.remove(peerRef)
      gatt.disconnect()
      gatt.close()
    }
    sendEvent(
      "peerDisconnected",
      mapOf(
        "peerRef" to peerRef,
        "reason" to (reason ?: "manual")
      )
    )
  }

  @SuppressLint("MissingPermission")
  fun sendFrame(peerRef: String, payloadBase64: String) {
    require(peerRef.isNotBlank()) { "peerRef cannot be empty" }
    require(payloadBase64.isNotBlank()) { "payloadBase64 cannot be empty" }
    val characteristic = writableCharacteristics[peerRef]
      ?: throw IllegalStateException("peerRef is not connected")
    val gatt = connectedGatts[peerRef]
      ?: throw IllegalStateException("peerRef is not connected")
    val payload = android.util.Base64.decode(payloadBase64, android.util.Base64.DEFAULT)
    Log.d(TAG, "Sending frame to $peerRef bytes=${payload.size}")
    characteristic.value = payload
    gatt.writeCharacteristic(characteristic)
  }

  fun simulatePeerDiscovery(peer: Map<String, Any?>): Map<String, Any> {
    val normalized = normalizePeer(peer)
    Log.d(TAG, "Simulating peer discovery ${normalized["peerRef"]}")
    discoveredPeers[normalized["peerRef"] as String] = normalized
    sendEvent("peerDiscovered", mapOf("peer" to normalized))
    return normalized
  }

  fun simulatePeerConnection(peerRef: String): Map<String, Any> {
    Log.d(TAG, "Simulating peer connection $peerRef")
    val event = connectionEvent(peerRef, discoveredPeers[peerRef]?.get("peerId") as? String, "simulated")
    sendEvent("peerConnected", event)
    return event
  }

  fun simulateFrameReceived(peerRef: String, payloadBase64: String, peerId: String?) {
    require(payloadBase64.isNotBlank()) { "payloadBase64 cannot be empty" }
    Log.d(TAG, "Simulating inbound frame from $peerRef")
    sendEvent(
      "frameReceived",
      mapOf(
        "peerRef" to peerRef,
        "peerId" to (peerId ?: discoveredPeers[peerRef]?.get("peerId") ?: ""),
        "payloadBase64" to payloadBase64
      )
    )
  }

  @SuppressLint("MissingPermission")
  fun resetSimulation() {
    Log.d(TAG, "Resetting Bluetooth peer bridge state")
    isScanning = false
    stopAdvertising()
    connectedGatts.values.forEach {
      it.disconnect()
      it.close()
    }
    connectedGatts.clear()
    writableCharacteristics.clear()
    discoveredPeers.clear()
    activeScanCallback?.let { bluetoothLeScanner?.stopScan(it) }
    activeScanCallback = null
  }

  private val gattCallback = object : BluetoothGattCallback() {
    override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
      val peerRef = gatt.device.address
      Log.d(TAG, "Connection state changed peer=$peerRef status=$status state=$newState")
      if (newState == android.bluetooth.BluetoothProfile.STATE_CONNECTED) {
        gatt.discoverServices()
      } else if (newState == android.bluetooth.BluetoothProfile.STATE_DISCONNECTED) {
        connectedGatts.remove(peerRef)
        writableCharacteristics.remove(peerRef)
        sendEvent(
          "peerDisconnected",
          mapOf("peerRef" to peerRef, "reason" to "disconnected")
        )
      }
    }

    override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
      Log.d(TAG, "Services discovered peer=${gatt.device.address} status=$status")
      val service: BluetoothGattService = gatt.getService(SERVICE_UUID) ?: return
      val characteristic = service.getCharacteristic(FRAME_CHARACTERISTIC_UUID) ?: return
      writableCharacteristics[gatt.device.address] = characteristic
    }

    override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
      if (characteristic.uuid != FRAME_CHARACTERISTIC_UUID) return
      Log.d(TAG, "Received frame from peer=${gatt.device.address} bytes=${characteristic.value?.size ?: 0}")
      sendEvent(
        "frameReceived",
        mapOf(
          "peerRef" to gatt.device.address,
          "peerId" to (discoveredPeers[gatt.device.address]?.get("peerId") ?: ""),
          "payloadBase64" to android.util.Base64.encodeToString(characteristic.value, android.util.Base64.NO_WRAP)
        )
      )
    }
  }

  private fun normalizePeer(peer: Map<String, Any?>): Map<String, Any> {
    val peerRef = (peer["peerRef"] as? String)?.takeIf { it.isNotBlank() }
      ?: throw IllegalArgumentException("peerRef cannot be empty")
    val peerId = (peer["peerId"] as? String)?.takeIf { it.isNotBlank() }
      ?: throw IllegalArgumentException("peerId cannot be empty")
    val normalized = linkedMapOf<String, Any>(
      "peerRef" to peerRef,
      "peerId" to peerId,
      "transport" to ((peer["transport"] as? String) ?: "simulated")
    )
    (peer["displayName"] as? String)?.let { normalized["displayName"] = it }
    when (val rssi = peer["rssi"]) {
      is Int -> normalized["rssi"] = rssi
      is Double -> normalized["rssi"] = rssi.toInt()
    }
    return normalized
  }

  private fun deviceToPeer(device: BluetoothDevice, rssi: Int?): Map<String, Any> {
    val displayName = device.name ?: ""
    return buildMap {
      put("peerRef", device.address)
      put("peerId", if (displayName.isBlank()) device.address else displayName)
      put("displayName", displayName)
      put("transport", "bluetooth")
      if (rssi != null) {
        put("rssi", rssi)
      }
    }
  }

  private fun scanResultToPeer(device: BluetoothDevice, result: ScanResult): Map<String, Any> {
    val scanRecord = result.scanRecord
    val serviceData = scanRecord?.getServiceData(ParcelUuid(SERVICE_UUID))
    val advertisedName = serviceData
      ?.takeIf { it.isNotEmpty() }
      ?.toString(Charsets.UTF_8)
      ?.trim()
      ?.takeIf { it.isNotEmpty() }
    val localName = scanRecord?.deviceName?.takeIf { it.isNotBlank() }
    val resolvedName = advertisedName ?: localName ?: device.name ?: ""
    return buildMap {
      put("peerRef", device.address)
      put("peerId", if (resolvedName.isBlank()) device.address else resolvedName)
      put("displayName", resolvedName)
      put("transport", "bluetooth")
      put("rssi", result.rssi)
    }
  }

  private fun connectionEvent(peerRef: String, peerId: String?, transport: String = "bluetooth"): Map<String, Any> {
    return mapOf(
      "peerRef" to peerRef,
      "peerId" to (peerId ?: ""),
      "transport" to transport,
      "connectedAt" to System.currentTimeMillis()
    )
  }

  private fun canScan(): Boolean {
    val adapter = bluetoothAdapter ?: return false
    if (!adapter.isEnabled) return false
    return canScanPermission()
  }

  private fun canConnect(): Boolean {
    val adapter = bluetoothAdapter ?: return false
    if (!adapter.isEnabled) return false
    return canConnectPermission()
  }

  private fun canScanPermission(): Boolean {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED
    } else {
      true
    }
  }

  private fun canConnectPermission(): Boolean {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
    } else {
      true
    }
  }

  private fun canAdvertise(): Boolean {
    val adapter = bluetoothAdapter ?: return false
    if (!adapter.isEnabled) return false
    if (!canAdvertisePermission()) return false
    return bluetoothLeAdvertiser != null && adapter.isMultipleAdvertisementSupported
  }

  private fun canAdvertisePermission(): Boolean {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_ADVERTISE) == PackageManager.PERMISSION_GRANTED
    } else {
      true
    }
  }

  @SuppressLint("MissingPermission")
  private fun startAdvertisingIfPossible() {
    if (!canAdvertise()) {
      isAdvertising = false
      return
    }

    stopAdvertising()

    val localName = advertisedDisplayName?.takeIf { it.isNotBlank() } ?: advertisedPeerId ?: return
    val settings = AdvertiseSettings.Builder()
      .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
      .setConnectable(true)
      .setTimeout(0)
      .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_MEDIUM)
      .build()
    val data = AdvertiseData.Builder()
      .setIncludeDeviceName(false)
      .addServiceUuid(ParcelUuid(SERVICE_UUID))
      .addServiceData(ParcelUuid(SERVICE_UUID), localName.toByteArray(Charsets.UTF_8))
      .build()
    val scanResponse = AdvertiseData.Builder()
      .setIncludeDeviceName(true)
      .build()

    bluetoothAdapter?.name = localName

    val callback = object : AdvertiseCallback() {
      override fun onStartSuccess(settingsInEffect: AdvertiseSettings) {
        isAdvertising = true
      }

      override fun onStartFailure(errorCode: Int) {
        isAdvertising = false
      }
    }
    activeAdvertiseCallback = callback
    bluetoothLeAdvertiser?.startAdvertising(settings, data, scanResponse, callback)
  }

  @SuppressLint("MissingPermission")
  private fun stopAdvertising() {
    activeAdvertiseCallback?.let { callback ->
      bluetoothLeAdvertiser?.stopAdvertising(callback)
    }
    activeAdvertiseCallback = null
    isAdvertising = false
  }
}
