package expo.modules.metawearablesdat

import android.Manifest
import android.app.Activity
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import androidx.core.content.ContextCompat
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.lang.reflect.Method
import java.lang.reflect.Modifier
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class ExpoMetaWearablesDatModule : Module() {
  private var sessionState: String = "idle"
  private var selectedDeviceId: String? = null
  private var selectedDeviceLastSeenAt: Long? = null
  private var selectedDeviceRssi: Int? = null
  private var lastCandidateDevices: List<Map<String, Any?>> = emptyList()

  override fun definition() = ModuleDefinition {
    Name("ExpoMetaWearablesDat")

    Events("onDatStateChanged")

    OnCreate {
      selectedDeviceId = preferences().getString(PREF_SELECTED_DEVICE_ID, null)
    }

    AsyncFunction("isDatAvailable") {
      isDatSdkLinked()
    }

    AsyncFunction("getConfiguration") {
      val metadata = manifestMetadata()
      mapOf(
        "platform" to "android",
        "sdkLinked" to isDatSdkLinked(),
        "sdkConfigured" to BuildConfig.META_WEARABLES_DAT_SDK_ENABLED,
        "analyticsOptOut" to (metadata?.getBoolean(METADATA_ANALYTICS_OPT_OUT) ?: false),
        "sdkVersion" to BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
        "applicationId" to metadata?.getString(METADATA_APPLICATION_ID),
        "provider" to "internal_bridge",
        "integrationMode" to integrationMode(isDatSdkLinked())
      )
    }

    AsyncFunction("getCapabilities") {
      buildCapabilitiesMap(isDatSdkLinked() && BuildConfig.META_WEARABLES_DAT_SDK_ENABLED)
    }

    AsyncFunction("getConnectedDevice") {
      val metadata = manifestMetadata()
      val snapshot = getWearablesSnapshot()
      val knownDevices = getKnownDevicesSnapshot()
      val primaryDevice = knownDevices.firstOrNull()
      mapOf(
        "platform" to "android",
        "sdkLinked" to snapshot.sdkLinked,
        "sdkConfigured" to BuildConfig.META_WEARABLES_DAT_SDK_ENABLED,
        "applicationId" to metadata?.getString(METADATA_APPLICATION_ID),
        "deviceId" to (snapshot.activeDeviceId ?: primaryDevice?.get("deviceId")),
        "registrationState" to snapshot.registrationState,
        "deviceName" to (primaryDevice?.get("deviceName") ?: snapshot.activeDeviceId),
        "deviceModel" to (primaryDevice?.get("deviceClassName") ?: Build.MODEL)
      )
    }

    AsyncFunction("getSessionState") {
      sessionState
    }

    AsyncFunction("getAdapterState") {
      getBluetoothAdapterState()
    }

    AsyncFunction("getKnownDevices") {
      getKnownDevicesSnapshot()
    }

    AsyncFunction("scanKnownAndNearbyDevices") { timeoutMs: Int ->
      scanKnownAndNearbyDevices(timeoutMs)
    }

    AsyncFunction("getSelectedDeviceTarget") {
      getSelectedDeviceTarget()
    }

    AsyncFunction("selectDeviceTarget") { deviceId: String ->
      selectDeviceTarget(deviceId)
    }

    AsyncFunction("clearDeviceTarget") {
      clearDeviceTarget()
    }

    AsyncFunction("reconnectSelectedDeviceTarget") {
      reconnectSelectedDeviceTarget()
    }

    AsyncFunction("connectSelectedDeviceTarget") {
      connectSelectedDeviceTarget()
    }

    AsyncFunction("getDiagnostics") {
      val metadata = manifestMetadata()
      val snapshot = getWearablesSnapshot()
      val adapterState = getBluetoothAdapterState()
      val knownDevices = getKnownDevicesSnapshot()
      val selectedTarget = getSelectedDeviceTarget()
      mapOf(
        "available" to true,
        "platform" to "android",
        "sdkLinked" to snapshot.sdkLinked,
        "sdkConfigured" to BuildConfig.META_WEARABLES_DAT_SDK_ENABLED,
        "analyticsOptOut" to (metadata?.getBoolean(METADATA_ANALYTICS_OPT_OUT) ?: false),
        "sdkVersion" to BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
        "applicationId" to metadata?.getString(METADATA_APPLICATION_ID),
        "provider" to "internal_bridge",
        "integrationMode" to integrationMode(snapshot.sdkLinked),
        "capabilities" to buildCapabilitiesMap(snapshot.sdkLinked && BuildConfig.META_WEARABLES_DAT_SDK_ENABLED),
        "sessionState" to sessionState,
        "registrationState" to snapshot.registrationState,
        "deviceCount" to snapshot.deviceCount,
        "activeDeviceId" to snapshot.activeDeviceId,
        "adapterState" to adapterState,
        "knownDeviceCount" to knownDevices.size,
        "selectedDeviceId" to selectedTarget?.get("deviceId"),
        "selectedDeviceName" to selectedTarget?.get("deviceName"),
        "targetConnectionState" to targetConnectionState(snapshot.activeDeviceId, selectedTarget),
        "targetLastSeenAt" to selectedTarget?.get("lastSeenAt"),
        "targetRssi" to selectedTarget?.get("rssi")
      )
    }

    AsyncFunction("startDeviceSession") {
      val result = if (BuildConfig.META_WEARABLES_DAT_SDK_ENABLED && isDatSdkLinked()) {
        startRegistration()
      } else {
        val selectedTarget = getSelectedDeviceTarget()
        sessionState = if (selectedTarget == null) "awaiting_target" else "target_ready"
        emitStateChanged()
        mapOf(
          "state" to sessionState,
          "mode" to "reference_only",
          "deviceId" to selectedTarget?.get("deviceId"),
          "targetConnectionState" to targetConnectionState(selectedTarget?.get("deviceId") as? String, selectedTarget)
        )
      }
      result
    }

    AsyncFunction("stopDeviceSession") {
      val result = if (BuildConfig.META_WEARABLES_DAT_SDK_ENABLED && isDatSdkLinked()) {
        startUnregistration()
      } else {
        sessionState = "idle"
        emitStateChanged()
        mapOf(
          "state" to sessionState,
          "mode" to "reference_only",
          "deviceId" to selectedDeviceId,
          "targetConnectionState" to targetConnectionState(null, getSelectedDeviceTarget())
        )
      }
      result
    }
  }

  private fun buildCapabilitiesMap(realSdkActive: Boolean): Map<String, Boolean> =
    mapOf(
      "session" to true,
      "camera" to realSdkActive,
      "photoCapture" to realSdkActive,
      "videoStream" to realSdkActive,
      "audio" to false
    )

  private fun manifestMetadata() =
    reactContextOrThrow()
      .packageManager
      .getApplicationInfo(reactContextOrThrow().packageName, PackageManager.GET_META_DATA)
      .metaData

  private fun reactContextOrThrow(): Context =
    appContext.reactContext ?: throw IllegalStateException("React context is null")

  private fun currentActivityOrThrow(): Activity =
    appContext.currentActivity ?: throw IllegalStateException("Current activity is null")

  private fun preferences() =
    reactContextOrThrow().getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

  private fun bluetoothAdapter(): BluetoothAdapter? =
    (reactContextOrThrow().getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter

  private fun isDatSdkLinked(): Boolean = wearablesClass() != null

  private fun wearablesClass(): Class<*>? =
    try {
      Class.forName(WEARABLES_CLASS_NAME)
    } catch (_: ClassNotFoundException) {
      null
    }

  private fun wearablesInstance(clazz: Class<*>): Any? =
    try {
      clazz.getDeclaredField("INSTANCE").get(null)
    } catch (_: Throwable) {
      null
    }

  private fun invokeWearablesMethod(name: String, vararg args: Any): Any? {
    val clazz = wearablesClass() ?: return null
    val method = findMethod(clazz, name, args) ?: return null
    val target = if (Modifier.isStatic(method.modifiers)) null else wearablesInstance(clazz)
    return method.invoke(target, *args)
  }

  private fun findMethod(clazz: Class<*>, name: String, args: Array<out Any>): Method? =
    clazz.methods.firstOrNull { method ->
      method.name == name &&
        method.parameterTypes.size == args.size &&
        method.parameterTypes.indices.all { index ->
          method.parameterTypes[index].isAssignableFrom(args[index].javaClass)
        }
    }

  private fun readFlowValue(flowLike: Any?): Any? {
    if (flowLike == null) {
      return null
    }
    return try {
      flowLike.javaClass.methods.firstOrNull { it.name == "getValue" && it.parameterCount == 0 }
        ?.invoke(flowLike)
    } catch (_: Throwable) {
      null
    }
  }

  private fun getWearablesSnapshot(): DatSnapshot {
    if (!isDatSdkLinked()) {
      val activeDeviceId =
        if (sessionState == "target_ready" || sessionState == "simulated_ready") selectedDeviceId else null
      return DatSnapshot(
        sdkLinked = false,
        registrationState = sessionState,
        deviceCount = if (activeDeviceId == null) 0 else 1,
        activeDeviceId = activeDeviceId
      )
    }

    val registrationFlow = invokeWearablesMethod("getRegistrationState")
    val registrationState = readFlowValue(registrationFlow)
    val devicesFlow = invokeWearablesMethod("getDevices")
    val devicesValue = readFlowValue(devicesFlow)
    val deviceIds = (devicesValue as? Collection<*>)?.map { it.toString() }?.filter { it.isNotBlank() } ?: emptyList()
    val normalizedRegistrationState = registrationState?.javaClass?.simpleName
      ?: registrationState?.toString()
      ?: sessionState

    return DatSnapshot(
      sdkLinked = true,
      registrationState = normalizedRegistrationState,
      deviceCount = deviceIds.size,
      activeDeviceId = deviceIds.firstOrNull()
    )
  }

  private fun initializeWearables() {
    invokeWearablesMethod("initialize", reactContextOrThrow())
      ?: throw IllegalStateException("Wearables.initialize(Context) is unavailable")
  }

  private fun startRegistration(): Map<String, String> {
    initializeWearables()
    invokeWearablesMethod("startRegistration", currentActivityOrThrow())
      ?: throw IllegalStateException("Wearables.startRegistration(Activity) is unavailable")
    sessionState = "registering"
    emitStateChanged()
    return mapOf("state" to sessionState, "mode" to "sdk")
  }

  private fun startUnregistration(): Map<String, String> {
    initializeWearables()
    invokeWearablesMethod("startUnregistration", currentActivityOrThrow())
      ?: throw IllegalStateException("Wearables.startUnregistration(Activity) is unavailable")
    sessionState = "unregistering"
    emitStateChanged()
    return mapOf("state" to sessionState, "mode" to "sdk")
  }

  private fun emitStateChanged() {
    val selectedTarget = getSelectedDeviceTarget()
    sendEvent(
      "onDatStateChanged",
      mapOf(
        "state" to sessionState,
        "sessionState" to sessionState,
        "deviceId" to selectedTarget?.get("deviceId"),
        "deviceName" to selectedTarget?.get("deviceName"),
        "targetConnectionState" to targetConnectionState(null, selectedTarget),
        "targetLastSeenAt" to selectedTarget?.get("lastSeenAt"),
        "targetRssi" to selectedTarget?.get("rssi")
      )
    )
  }

  private fun integrationMode(sdkLinked: Boolean): String =
    if (sdkLinked) "sdk_reflection" else "reference_only"

  private fun getBluetoothAdapterState(): Map<String, Any> {
    val adapter = bluetoothAdapter()
    val adapterAvailable = adapter != null
    val adapterEnabled = adapter?.isEnabled == true
    return mapOf(
      "transport" to "bluetooth",
      "adapterAvailable" to adapterAvailable,
      "adapterEnabled" to adapterEnabled,
      "scanPermissionGranted" to canScanPermission(),
      "connectPermissionGranted" to canConnectPermission(),
      "advertisePermissionGranted" to canAdvertisePermission(),
      "state" to when {
        !adapterAvailable -> "unavailable"
        !adapterEnabled -> "powered_off"
        else -> "powered_on"
      }
    )
  }

  private fun getKnownDevicesSnapshot(): List<Map<String, Any?>> {
    val adapter = bluetoothAdapter() ?: return emptyList()
    if (!canConnectPermission()) {
      return emptyList()
    }

    return adapter.bondedDevices
      ?.sortedBy { it.name ?: it.address }
      ?.map { device ->
        val lastSeenAt = System.currentTimeMillis()
        mapOf(
          "deviceId" to device.address,
          "deviceName" to (device.name ?: device.address),
          "deviceClassName" to device.bluetoothClass?.majorDeviceClass?.toString(),
          "bondState" to bondStateLabel(device.bondState),
          "type" to deviceTypeLabel(device.type),
          "lastSeenAt" to lastSeenAt
        )
      }
      ?: emptyList()
  }

  private fun scanKnownAndNearbyDevices(timeoutMs: Int): List<Map<String, Any?>> {
    val merged = linkedMapOf<String, Map<String, Any?>>()
    getKnownDevicesSnapshot().forEach { device ->
      val deviceId = device["deviceId"] as? String ?: return@forEach
      merged[deviceId] = device + mapOf("source" to "bonded")
    }

    val adapter = bluetoothAdapter() ?: return merged.values.toList()
    if (!adapter.isEnabled || !canScanPermission()) {
      return merged.values.toList()
    }

    val scanner = adapter.bluetoothLeScanner ?: return merged.values.toList()
    val latch = CountDownLatch(1)
    val timeout = timeoutMs.coerceIn(0, 10_000)
    val handler = Handler(Looper.getMainLooper())

    val callback = object : ScanCallback() {
      override fun onScanResult(callbackType: Int, result: ScanResult) {
        val device = result.device ?: return
        val deviceId = device.address ?: return
        val existing = merged[deviceId] ?: emptyMap()
        merged[deviceId] =
          existing + mapOf(
            "deviceId" to deviceId,
            "deviceName" to (device.name ?: existing["deviceName"] ?: deviceId),
            "deviceClassName" to existing["deviceClassName"],
            "bondState" to bondStateLabel(device.bondState),
            "type" to deviceTypeLabel(device.type),
            "source" to if (existing.isEmpty()) "scan" else "bonded+scan",
            "rssi" to result.rssi,
            "lastSeenAt" to System.currentTimeMillis()
          )
      }

      override fun onScanFailed(errorCode: Int) {
        latch.countDown()
      }
    }

    try {
      scanner.startScan(callback)
      handler.postDelayed({
        try {
          scanner.stopScan(callback)
        } catch (_: Throwable) {
          // ignore
        } finally {
          latch.countDown()
        }
      }, timeout.toLong())
      latch.await((timeout + 500).toLong(), TimeUnit.MILLISECONDS)
    } catch (_: Throwable) {
      // keep bonded snapshot best-effort
    } finally {
      try {
        scanner.stopScan(callback)
      } catch (_: Throwable) {
        // ignore
      }
    }

    lastCandidateDevices = merged.values.toList()
    refreshSelectedTargetMetadata(lastCandidateDevices)
    return lastCandidateDevices
  }

  private fun getSelectedDeviceTarget(): Map<String, Any?>? {
    val deviceId = selectedDeviceId ?: return null
    val candidates = if (lastCandidateDevices.isNotEmpty()) lastCandidateDevices else getKnownDevicesSnapshot()
    return candidates.firstOrNull { it["deviceId"] == deviceId }
      ?: mapOf(
        "deviceId" to deviceId,
        "deviceName" to deviceId,
        "source" to "selected_only",
        "lastSeenAt" to selectedDeviceLastSeenAt,
        "rssi" to selectedDeviceRssi
      )
  }

  private fun selectDeviceTarget(deviceId: String): Map<String, Any?> {
    require(deviceId.isNotBlank()) { "deviceId cannot be empty" }
    selectedDeviceId = deviceId
    selectedDeviceLastSeenAt = System.currentTimeMillis()
    selectedDeviceRssi = null
    preferences().edit().putString(PREF_SELECTED_DEVICE_ID, deviceId).apply()
    return getSelectedDeviceTarget()
      ?: mapOf(
        "deviceId" to deviceId,
        "deviceName" to deviceId,
        "source" to "selected_only",
        "lastSeenAt" to selectedDeviceLastSeenAt,
        "rssi" to selectedDeviceRssi
      )
  }

  private fun clearDeviceTarget(): Map<String, Any?> {
    val previous = getSelectedDeviceTarget()
    selectedDeviceId = null
    selectedDeviceLastSeenAt = null
    selectedDeviceRssi = null
    preferences().edit().remove(PREF_SELECTED_DEVICE_ID).apply()
    return previous ?: emptyMap()
  }

  private fun reconnectSelectedDeviceTarget(): Map<String, Any?> {
    if (selectedDeviceId == null) {
      selectedDeviceId = preferences().getString(PREF_SELECTED_DEVICE_ID, null)
    }
    val selectedId = selectedDeviceId
    if (selectedId == null) {
      sessionState = "awaiting_target"
      emitStateChanged()
      return mapOf(
        "state" to sessionState,
        "mode" to "reference_only",
        "deviceId" to null,
        "targetConnectionState" to "unselected"
      )
    }

    val previousSessionState = sessionState
    sessionState = "reconnecting_target"
    emitStateChanged()

    val candidates = scanKnownAndNearbyDevices(2000)
    val matchedTarget = candidates.firstOrNull { it["deviceId"] == selectedId }
    if (matchedTarget != null) {
      selectedDeviceLastSeenAt = (matchedTarget["lastSeenAt"] as? Number)?.toLong() ?: System.currentTimeMillis()
      selectedDeviceRssi = (matchedTarget["rssi"] as? Number)?.toInt()
      sessionState = if (previousSessionState == "target_ready") "target_ready" else "target_discovered"
    }

    val selectedTarget = matchedTarget ?: getSelectedDeviceTarget()
    if (matchedTarget == null) {
      sessionState = "reconnecting_target"
    }
    emitStateChanged()
    return mapOf(
      "state" to sessionState,
      "mode" to "reference_only",
      "deviceId" to selectedTarget?.get("deviceId"),
      "targetConnectionState" to targetConnectionState(null, selectedTarget),
      "targetLastSeenAt" to selectedTarget?.get("lastSeenAt"),
      "targetRssi" to selectedTarget?.get("rssi")
    )
  }

  private fun connectSelectedDeviceTarget(): Map<String, Any?> {
    if (selectedDeviceId == null) {
      selectedDeviceId = preferences().getString(PREF_SELECTED_DEVICE_ID, null)
    }
    val selectedTarget = getSelectedDeviceTarget()
    if (selectedTarget == null) {
      sessionState = "awaiting_target"
      emitStateChanged()
      return mapOf(
        "state" to sessionState,
        "mode" to "reference_only",
        "deviceId" to null,
        "targetConnectionState" to "unselected"
      )
    }

    selectedDeviceLastSeenAt = (selectedTarget["lastSeenAt"] as? Number)?.toLong() ?: System.currentTimeMillis()
    selectedDeviceRssi = (selectedTarget["rssi"] as? Number)?.toInt() ?: selectedDeviceRssi
    sessionState = "target_connected"
    emitStateChanged()
    return mapOf(
      "state" to sessionState,
      "mode" to "reference_only",
      "deviceId" to selectedTarget["deviceId"],
      "targetConnectionState" to "connected",
      "targetLastSeenAt" to selectedDeviceLastSeenAt,
      "targetRssi" to selectedDeviceRssi
    )
  }

  private fun refreshSelectedTargetMetadata(candidates: List<Map<String, Any?>>) {
    val deviceId = selectedDeviceId ?: return
    val selected = candidates.firstOrNull { it["deviceId"] == deviceId } ?: return
    selectedDeviceLastSeenAt = (selected["lastSeenAt"] as? Number)?.toLong() ?: selectedDeviceLastSeenAt
    selectedDeviceRssi = (selected["rssi"] as? Number)?.toInt() ?: selectedDeviceRssi
  }

  private fun targetConnectionState(
    activeDeviceId: String?,
    selectedTarget: Map<String, Any?>?
  ): String {
    val selectedId = selectedTarget?.get("deviceId") as? String ?: return "unselected"
    if (activeDeviceId != null && activeDeviceId == selectedId) {
      return "active"
    }
    return when (sessionState) {
      "target_connected" -> "connected"
      "target_ready", "simulated_ready" -> "ready"
      "target_discovered" -> "discovered"
      "reconnecting_target" -> "reconnecting"
      "registering" -> "connecting"
      "awaiting_target" -> "unselected"
      else -> when (selectedTarget["source"] as? String) {
        "selected_only" -> "selected"
        else -> "discovered"
      }
    }
  }

  private fun canScanPermission(): Boolean =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      ContextCompat.checkSelfPermission(reactContextOrThrow(), Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED
    } else {
      true
    }

  private fun canConnectPermission(): Boolean =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      ContextCompat.checkSelfPermission(reactContextOrThrow(), Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
    } else {
      true
    }

  private fun canAdvertisePermission(): Boolean =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
      ContextCompat.checkSelfPermission(reactContextOrThrow(), Manifest.permission.BLUETOOTH_ADVERTISE) == PackageManager.PERMISSION_GRANTED
    } else {
      true
    }

  private fun bondStateLabel(bondState: Int): String =
    when (bondState) {
      BluetoothDevice.BOND_BONDED -> "bonded"
      BluetoothDevice.BOND_BONDING -> "bonding"
      else -> "none"
    }

  private fun deviceTypeLabel(deviceType: Int): String =
    when (deviceType) {
      BluetoothDevice.DEVICE_TYPE_CLASSIC -> "classic"
      BluetoothDevice.DEVICE_TYPE_DUAL -> "dual"
      BluetoothDevice.DEVICE_TYPE_LE -> "le"
      else -> "unknown"
    }

  private data class DatSnapshot(
    val sdkLinked: Boolean,
    val registrationState: String,
    val deviceCount: Int,
    val activeDeviceId: String?
  )

  private companion object {
    const val PREFS_NAME = "expo_meta_wearables_dat"
    const val PREF_SELECTED_DEVICE_ID = "selected_device_id"
    const val WEARABLES_CLASS_NAME = "com.meta.wearable.dat.core.Wearables"
    const val METADATA_APPLICATION_ID = "com.meta.wearable.mwdat.APPLICATION_ID"
    const val METADATA_ANALYTICS_OPT_OUT = "com.meta.wearable.mwdat.ANALYTICS_OPT_OUT"
  }
}
