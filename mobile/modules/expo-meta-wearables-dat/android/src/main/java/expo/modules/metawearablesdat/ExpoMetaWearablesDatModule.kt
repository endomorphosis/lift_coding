package expo.modules.metawearablesdat

import android.app.Activity
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import java.lang.reflect.Method
import java.lang.reflect.Modifier

class ExpoMetaWearablesDatModule : Module() {
  private var sessionState: String = "idle"

  override fun definition() = ModuleDefinition {
    Name("ExpoMetaWearablesDat")

    Events("onDatStateChanged")

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
      mapOf(
        "platform" to "android",
        "sdkLinked" to snapshot.sdkLinked,
        "sdkConfigured" to BuildConfig.META_WEARABLES_DAT_SDK_ENABLED,
        "applicationId" to metadata?.getString(METADATA_APPLICATION_ID),
        "deviceId" to snapshot.activeDeviceId,
        "registrationState" to snapshot.registrationState,
        "deviceName" to snapshot.activeDeviceId,
        "deviceModel" to Build.MODEL
      )
    }

    AsyncFunction("getSessionState") {
      sessionState
    }

    AsyncFunction("getDiagnostics") {
      val metadata = manifestMetadata()
      val snapshot = getWearablesSnapshot()
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
        "activeDeviceId" to snapshot.activeDeviceId
      )
    }

    AsyncFunction("startDeviceSession") {
      val result = if (BuildConfig.META_WEARABLES_DAT_SDK_ENABLED && isDatSdkLinked()) {
        startRegistration()
      } else {
        sessionState = "simulated_ready"
        emitStateChanged()
        mapOf("state" to sessionState, "mode" to "simulated")
      }
      result
    }

    AsyncFunction("stopDeviceSession") {
      val result = if (BuildConfig.META_WEARABLES_DAT_SDK_ENABLED && isDatSdkLinked()) {
        startUnregistration()
      } else {
        sessionState = "idle"
        emitStateChanged()
        mapOf("state" to sessionState, "mode" to "simulated")
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
      return DatSnapshot(
        sdkLinked = false,
        registrationState = sessionState,
        deviceCount = 0,
        activeDeviceId = null
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
    sendEvent("onDatStateChanged", mapOf("state" to sessionState))
  }

  private fun integrationMode(sdkLinked: Boolean): String =
    if (sdkLinked) "sdk_reflection" else "reference_only"

  private data class DatSnapshot(
    val sdkLinked: Boolean,
    val registrationState: String,
    val deviceCount: Int,
    val activeDeviceId: String?
  )

  private companion object {
    const val WEARABLES_CLASS_NAME = "com.meta.wearable.dat.core.Wearables"
    const val METADATA_APPLICATION_ID = "com.meta.wearable.mwdat.APPLICATION_ID"
    const val METADATA_ANALYTICS_OPT_OUT = "com.meta.wearable.mwdat.ANALYTICS_OPT_OUT"
  }
}
