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
import java.lang.reflect.InvocationTargetException
import java.lang.reflect.Method
import java.lang.reflect.Modifier
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException
import kotlin.coroutines.Continuation
import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.coroutines.intrinsics.COROUTINE_SUSPENDED

class ExpoMetaWearablesDatModule : Module() {
  private var sessionState: String = "idle"
  private var selectedDeviceId: String? = null
  private var selectedDeviceLastSeenAt: Long? = null
  private var selectedDeviceRssi: Int? = null
  private var lastCandidateDevices: List<Map<String, Any?>> = emptyList()
  private var displayConnectionState: String = "idle"
  private var displayLastAction: String? = null
  private var displayLastStatus: String? = null
  private var displayLastUpdatedAt: Long? = null
  private var displayRenderPath: String? = null
  private var displayLastError: String? = null
  private var displayActiveWidgetId: String? = null
  private var displayDescriptorCid: String? = null
  private var displayInterfaceCid: String? = null
  private var displayManifestCid: String? = null
  private var displayWidgetCid: String? = null
  private var displayOrbReceiptCid: String? = null
  private var displayPolicyDecision: Any? = null
  private var displayCorrelationId: String? = null
  private var displayRequestId: String? = null
  private var displayFallback: Map<String, Any?>? = null
  private var displayFocusTarget: String? = null
  private var displayUpdateCount: Int = 0
  private var displayLifecycleStages: List<String> = emptyList()
  private val nativeDisplayLock = Any()
  private var nativeDisplaySession: Any? = null
  private var nativeDisplay: Any? = null
  private var nativeDisplayDeviceId: String? = null

  override fun definition() = ModuleDefinition {
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
      selectedDeviceId = preferences().getString(PREF_SELECTED_DEVICE_ID, null)
    }

    AsyncFunction("isDatAvailable") {
      isDatSdkLinked()
    }

    AsyncFunction("getConfiguration") {
      val metadata = manifestMetadata()
      val damEnabled = metadata?.getBoolean(METADATA_DAM_ENABLED) ?: false
      val sdkMeetsMinimum = isDatVersionAtLeast(
        BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
        MINIMUM_DAT_SDK_VERSION
      )
      mapOf(
        "platform" to "android",
        "sdkLinked" to isDatSdkLinked(),
        "sdkConfigured" to BuildConfig.META_WEARABLES_DAT_SDK_ENABLED,
        "sdkMeetsMinimum" to sdkMeetsMinimum,
        "analyticsOptOut" to (metadata?.getBoolean(METADATA_ANALYTICS_OPT_OUT) ?: false),
        "sdkVersion" to BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
        "sdkVersionTarget" to MINIMUM_DAT_SDK_VERSION,
        "datAppModelEnabled" to damEnabled,
        "displayDamRequired" to true,
        "displayDamEnabled" to damEnabled,
        "applicationId" to metadata?.getString(METADATA_APPLICATION_ID),
        "provider" to "internal_bridge",
        "integrationMode" to integrationMode(isDatSdkLinked())
      )
    }

    AsyncFunction("getCapabilities") {
      val realSdkActive = isDatSdkLinked() && BuildConfig.META_WEARABLES_DAT_SDK_ENABLED
      buildCapabilitiesMap(
        realSdkActive = realSdkActive,
        damEnabled = (manifestMetadata()?.getBoolean(METADATA_DAM_ENABLED) ?: false),
        sdkMeetsMinimum = isDatVersionAtLeast(
          BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
          MINIMUM_DAT_SDK_VERSION
        ),
        displaySdkLinked = realSdkActive && isDisplaySdkLinked()
      )
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
      val damEnabled = metadata?.getBoolean(METADATA_DAM_ENABLED) ?: false
      val sdkMeetsMinimum = isDatVersionAtLeast(
        BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
        MINIMUM_DAT_SDK_VERSION
      )
      val realSdkActive = snapshot.sdkLinked && BuildConfig.META_WEARABLES_DAT_SDK_ENABLED
      val displaySdkLinked = realSdkActive && isDisplaySdkLinked()
      val displayReady = realSdkActive && displaySdkLinked && sdkMeetsMinimum && damEnabled
      val adapterState = getBluetoothAdapterState()
      val knownDevices = getKnownDevicesSnapshot()
      val selectedTarget = getSelectedDeviceTarget()
      val configWarnings = mutableListOf<String>()
      if (!sdkMeetsMinimum) {
        configWarnings.add(
          "Configured DAT SDK ${BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION} is below required ${MINIMUM_DAT_SDK_VERSION} for display."
        )
      }
      if (!damEnabled) {
        configWarnings.add("DAM app-model is disabled; display capability remains unavailable.")
      }
      if (!BuildConfig.META_WEARABLES_DAT_SDK_ENABLED) {
        configWarnings.add("DAT SDK integration is disabled for this build flavor.")
      }
      if (realSdkActive && !displaySdkLinked) {
        configWarnings.add("DAT display SDK classes are not linked into this Android build.")
      }
      mapOf(
        "available" to true,
        "platform" to "android",
        "sdkLinked" to snapshot.sdkLinked,
        "sdkConfigured" to BuildConfig.META_WEARABLES_DAT_SDK_ENABLED,
        "sdkMeetsMinimum" to sdkMeetsMinimum,
        "analyticsOptOut" to (metadata?.getBoolean(METADATA_ANALYTICS_OPT_OUT) ?: false),
        "sdkVersion" to BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
        "sdkVersionTarget" to MINIMUM_DAT_SDK_VERSION,
        "datAppModelEnabled" to damEnabled,
        "displayDamRequired" to true,
        "displayDamEnabled" to damEnabled,
        "displayReady" to displayReady,
        "configWarnings" to configWarnings,
        "applicationId" to metadata?.getString(METADATA_APPLICATION_ID),
        "provider" to "internal_bridge",
        "integrationMode" to integrationMode(snapshot.sdkLinked),
        "capabilities" to buildCapabilitiesMap(
          realSdkActive = realSdkActive,
          damEnabled = damEnabled,
          sdkMeetsMinimum = sdkMeetsMinimum,
          displaySdkLinked = displaySdkLinked
        ),
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
        "targetRssi" to selectedTarget?.get("rssi"),
        "displayConnectionState" to displayConnectionState,
        "displayLastAction" to displayLastAction,
        "displayLastStatus" to displayLastStatus,
        "displayLastUpdatedAt" to displayLastUpdatedAt,
        "displayRenderPath" to displayRenderPath,
        "displayLastError" to displayLastError,
        "displayActiveWidgetId" to displayActiveWidgetId,
        "displayDescriptorCid" to displayDescriptorCid,
        "displayInterfaceCid" to displayInterfaceCid,
        "displayManifestCid" to displayManifestCid,
        "displayWidgetCid" to displayWidgetCid,
        "displayOrbReceiptCid" to displayOrbReceiptCid,
        "displayReceiptCid" to displayOrbReceiptCid,
        "displayPolicyDecision" to displayPolicyDecision,
        "displayCorrelationId" to displayCorrelationId,
        "displayRequestId" to displayRequestId,
        "displayFallback" to displayFallback,
        "displayFocusTarget" to displayFocusTarget,
        "displayUpdateCount" to displayUpdateCount,
        "displayLifecycleStages" to displayLifecycleStages
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

    AsyncFunction("capturePhoto") {
      mediaActionResult(
        action = "capture_photo",
        message = "Photo capture is not implemented in the Android DAT bridge yet."
      )
    }

    AsyncFunction("startVideoStream") {
      mediaActionResult(
        action = "start_video_stream",
        message = "Video streaming is not implemented in the Android DAT bridge yet."
      )
    }

    AsyncFunction("stopVideoStream") {
      mediaActionResult(
        action = "stop_video_stream",
        message = "Video streaming is not implemented in the Android DAT bridge yet."
      )
    }

    AsyncFunction("renderDisplayTest") {
      val displayEnabled = canExecuteDisplayAction()
      updateDisplayState(
        action = "render_display_test",
        status = if (displayEnabled) "ready" else "blocked",
        connectionState = if (displayEnabled) "rendered" else fallbackDisplayConnectionState(),
      )
      mediaActionResult(
        action = "render_display_test",
        message = if (displayEnabled) {
          "Display test card queued by the Android DAT bridge lifecycle."
        } else {
          "Display test rendering requires DAM enablement, SDK compatibility, and a selected target."
        },
        supported = displayEnabled
      )
    }

    AsyncFunction("clearDisplay") {
      val displayEnabled = canExecuteDisplayAction()
      updateDisplayState(
        action = "clear_display",
        status = if (displayEnabled) "ready" else "blocked",
        connectionState = if (displayEnabled) "cleared" else fallbackDisplayConnectionState(),
      )
      mediaActionResult(
        action = "clear_display",
        message = if (displayEnabled) {
          "Display clear queued by the Android DAT bridge lifecycle."
        } else {
          "Display clear requires DAM enablement, SDK compatibility, and a selected target."
        },
        supported = displayEnabled
      )
    }

    AsyncFunction("playDisplayVideo") { videoUrl: String? ->
      val displayEnabled = canExecuteDisplayAction()
      val canPlayVideo = displayEnabled && !videoUrl.isNullOrBlank()
      updateDisplayState(
        action = "play_display_video",
        status = if (canPlayVideo) "ready" else "blocked",
        connectionState = if (canPlayVideo) "video_playing" else fallbackDisplayConnectionState(),
      )
      mediaActionResult(
        action = "play_display_video",
        message = if (!displayEnabled) {
          "Display video playback requires DAM enablement, SDK compatibility, and a selected target."
        } else if (videoUrl.isNullOrBlank()) {
          "Display video playback requires an MP4 URL and DAM app-model support."
        } else {
          "Display video playback queued by the Android DAT bridge lifecycle."
        },
        supported = canPlayVideo
      )
    }

    AsyncFunction("resetDisplaySession") {
      val displayEnabled = canExecuteDisplayAction()
      updateDisplayState(
        action = "reset_display_session",
        status = if (displayEnabled) "ready" else "blocked",
        connectionState = if (displayEnabled) "reset" else fallbackDisplayConnectionState(),
      )
      mediaActionResult(
        action = "reset_display_session",
        message = if (displayEnabled) {
          "Display session reset queued by the Android DAT bridge lifecycle."
        } else {
          "Display session reset requires DAM enablement, SDK compatibility, and a selected target."
        },
        supported = displayEnabled
      )
    }

    AsyncFunction("renderDisplayWidget") { manifest: Map<String, Any?>, context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_RENDER,
        displayWidgetActionInput(DISPLAY_WIDGET_RENDER, manifest, context, "manifest")
      )
    }

    AsyncFunction("updateDisplayWidget") { patch: Map<String, Any?>, context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_UPDATE,
        displayWidgetActionInput(DISPLAY_WIDGET_UPDATE, patch, context, "patch")
      )
    }

    AsyncFunction("clearDisplayWidget") { widgetId: String?, context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_CLEAR,
        displayWidgetActionInput(
          DISPLAY_WIDGET_CLEAR,
          mapOf("widget_id" to widgetId),
          context
        )
      )
    }

    AsyncFunction("focusDisplayWidget") { direction: String?, context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_FOCUS,
        displayWidgetActionInput(
          DISPLAY_WIDGET_FOCUS,
          mapOf(
          "focus" to mapOf("direction" to direction),
          "operation" to if (direction == "previous") "focus_previous" else "focus_next"
          ),
          context
        )
      )
    }

    AsyncFunction("activateDisplayWidgetAction") { actionId: String?, context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_ACTIVATE,
        displayWidgetActionInput(
          DISPLAY_WIDGET_ACTIVATE,
          mapOf("activated_action_id" to actionId),
          context
        )
      )
    }

    AsyncFunction("resetDisplayWidgetSession") { context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_RESET,
        displayWidgetActionInput(DISPLAY_WIDGET_RESET, emptyMap(), context)
      )
    }

    AsyncFunction("playDisplayWidgetVideo") { video: Map<String, Any?>?, context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_PLAY_VIDEO,
        displayWidgetActionInput(DISPLAY_WIDGET_PLAY_VIDEO, video ?: emptyMap(), context, "video")
      )
    }

    AsyncFunction("subscribeDisplayWidgetUpdates") { subscription: Map<String, Any?>?, context: Map<String, Any?>? ->
      executeDisplayWidgetAction(
        DISPLAY_WIDGET_SUBSCRIBE_UPDATES,
        displayWidgetActionInput(DISPLAY_WIDGET_SUBSCRIBE_UPDATES, subscription ?: emptyMap(), context, "subscription")
      )
    }
  }

  private fun buildCapabilitiesMap(
    realSdkActive: Boolean,
    damEnabled: Boolean = false,
    sdkMeetsMinimum: Boolean = false,
    displaySdkLinked: Boolean = realSdkActive
  ): Map<String, Boolean> =
    mapOf(
      "session" to true,
      "camera" to realSdkActive,
      "photoCapture" to realSdkActive,
      "videoStream" to realSdkActive,
      "audio" to false,
      "display" to (realSdkActive && displaySdkLinked && damEnabled && sdkMeetsMinimum),
      "displayVideo" to (realSdkActive && displaySdkLinked && damEnabled && sdkMeetsMinimum)
    )

  private fun mediaActionResult(
    action: String,
    message: String,
    supported: Boolean = false
  ): Map<String, Any?> =
    mapOf(
      "state" to if (supported) "ready" else "not_supported",
      "mode" to integrationMode(isDatSdkLinked()),
      "supported" to supported,
      "action" to action,
      "message" to message,
      "deviceId" to selectedDeviceId,
      "targetConnectionState" to targetConnectionState(null, getSelectedDeviceTarget()),
      "assetUri" to null,
      "mimeType" to null,
      "displayConnectionState" to displayConnectionState,
      "displayLastAction" to displayLastAction,
      "displayLastStatus" to displayLastStatus,
      "displayLastUpdatedAt" to displayLastUpdatedAt
    )

  private fun canExecuteDisplayAction(): Boolean {
    val damEnabled = manifestMetadata()?.getBoolean(METADATA_DAM_ENABLED) ?: false
    val sdkMeetsMinimum = isDatVersionAtLeast(
      BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
      MINIMUM_DAT_SDK_VERSION
    )
    val hasSelectedTarget = getSelectedDeviceTarget() != null
    val realSdkActive = isDatSdkLinked() && BuildConfig.META_WEARABLES_DAT_SDK_ENABLED
    // When SDK integration is disabled for the build flavor, we still allow
    // bridge-lifecycle simulation for diagnostics and contract validation.
    val bridgeSimulationMode = !BuildConfig.META_WEARABLES_DAT_SDK_ENABLED
    return damEnabled && sdkMeetsMinimum && hasSelectedTarget && (realSdkActive || bridgeSimulationMode)
  }

  private fun executeDisplayWidgetAction(
    config: DisplayActionConfig,
    input: Map<String, Any?>
  ): Map<String, Any?> {
    if (config.action == "render_display_widget") {
      displayLifecycleStages = emptyList()
    }
    val metadata = displayWidgetMetadata(input)
    val lifecycle = prepareDisplayLifecycle(config, metadata)
    var supported = lifecycle.supported
    var reason = lifecycle.reason
    var message = lifecycle.message
    var displayState = lifecycle.state
    var renderPath = lifecycle.renderPath

    if (supported && config.sendsContent && lifecycle.display != null) {
      val sendResult = try {
        sendNativeDisplayContent(lifecycle.display, config, metadata)
      } catch (error: Throwable) {
        val nativeError = unwrapDatError(error)
        DatCallResult.failure(
          description = datErrorDescription(nativeError) ?: "DAT display content send failed.",
          error = nativeError
        )
      }
      if (!sendResult.success) {
        supported = false
        reason = datErrorReason(sendResult.error)
        message = sendResult.description ?: "DAT display content send failed."
        displayState = "display_send_failed"
        renderPath = "mobile-card"
        recordDisplayLifecycleStage("content_send_failed")
      } else {
        message = nativeDisplayContentSentMessage(config)
        recordDisplayLifecycleStage("content_sent")
      }
    }

    applyDisplayWidgetState(config, metadata, supported, reason, displayState, renderPath, message)

    val result = displayWidgetActionResult(
      config = config,
      metadata = metadata,
      supported = supported,
      state = if (supported) "ready" else "not_supported",
      reason = reason,
      message = message,
      requiredAction = lifecycle.requiredAction
    )
    emitDisplayWidgetEvent(config, supported, result)
    return result
  }

  private fun prepareDisplayLifecycle(
    config: DisplayActionConfig,
    metadata: DisplayWidgetMetadata
  ): DisplayLifecycleResult {
    val damEnabled = manifestMetadata()?.getBoolean(METADATA_DAM_ENABLED) ?: false
    val sdkMeetsMinimum = isDatVersionAtLeast(
      BuildConfig.META_WEARABLES_DAT_ANDROID_VERSION,
      MINIMUM_DAT_SDK_VERSION
    )
    if (!BuildConfig.META_WEARABLES_DAT_SDK_ENABLED) {
      return DisplayLifecycleResult.blocked(
        state = "native_display_unavailable",
        reason = "dat_native_display_unavailable",
        message = "DAT native display is unavailable in this bridge-only Android build."
      )
    }
    if (!damEnabled) {
      return DisplayLifecycleResult.blocked(
        state = "dam_disabled",
        reason = "dam_disabled",
        message = "DAT display actions require DAM app-model enablement."
      )
    }
    if (!sdkMeetsMinimum) {
      return DisplayLifecycleResult.blocked(
        state = "sdk_version_unsupported",
        reason = "sdk_version_unsupported",
        message = "DAT display actions require Android DAT SDK $MINIMUM_DAT_SDK_VERSION or newer."
      )
    }
    if (!isDatSdkLinked()) {
      return DisplayLifecycleResult.blocked(
        state = "sdk_unlinked",
        reason = "dat_sdk_unlinked",
        message = "DAT SDK classes are not linked into this Android build."
      )
    }
    if (!isDisplaySdkLinked()) {
      return DisplayLifecycleResult.blocked(
        state = "display_sdk_unlinked",
        reason = "display_sdk_unlinked",
        message = "DAT display SDK classes are not linked into this Android build."
      )
    }
    if (config.action == DISPLAY_WIDGET_RESET.action) {
      synchronized(nativeDisplayLock) {
        detachNativeDisplayLocked()
      }
      sessionState = if (selectedDeviceId == null) "idle" else "target_ready"
      emitStateChanged()
      recordDisplayLifecycleStage("display_session_reset")
      return DisplayLifecycleResult.ready(
        state = config.successConnectionState,
        message = "DAT display widget session reset.",
        display = null,
        renderPath = "native-dat"
      )
    }

    return try {
      initializeWearables()
      val registrationState = normalizedStateName(readFlowValue(invokeWearablesMethod("getRegistrationState")))
      if (registrationState != null && registrationState != "REGISTERED") {
        DisplayLifecycleResult.blocked(
          state = "registration_required",
          reason = "registration_required",
          message = "Register with Meta AI before starting a DAT display session."
        )
      } else {
        val target = resolveDisplayDeviceTarget()
        if (target == null) {
          DisplayLifecycleResult.blocked(
            state = "awaiting_target",
            reason = "target_required",
            message = "Select a display-capable glasses target before rendering a DAT display widget."
          )
        } else {
          selectedDeviceId = target.deviceId
          recordDisplayLifecycleStage("target_selected")
          val deviceGate = displayDeviceGate(target)
          if (deviceGate != null) {
            deviceGate
          } else {
            synchronized(nativeDisplayLock) {
              ensureNativeDisplayReadyLocked(target, metadata)
            }
          }
        }
      }
    } catch (error: Throwable) {
      val nativeError = unwrapDatError(error)
      synchronized(nativeDisplayLock) {
        detachNativeDisplayLocked()
      }
      DisplayLifecycleResult.blocked(
        state = "native_display_error",
        reason = datErrorReason(nativeError),
        message = datErrorDescription(nativeError) ?: "DAT display lifecycle failed.",
        requiredAction = requiredActionForError(nativeError)
      )
    }
  }

  private fun ensureNativeDisplayReadyLocked(
    target: DisplayDeviceTarget,
    metadata: DisplayWidgetMetadata
  ): DisplayLifecycleResult {
    if (nativeDisplaySession != null && nativeDisplayDeviceId != null && nativeDisplayDeviceId != target.deviceId) {
      detachNativeDisplayLocked()
      recordDisplayLifecycleStage("target_changed_session_reset")
    }

    var session = nativeDisplaySession
    if (session == null) {
      updateDisplayState(
        action = DISPLAY_WIDGET_RENDER.action,
        status = "starting_session",
        connectionState = "session_starting",
        renderPath = "native-dat",
        lifecycleStage = "starting_session"
      )
      val selector = createSpecificDeviceSelector(target.nativeIdentifier)
        ?: return DisplayLifecycleResult.blocked(
          state = "selector_unavailable",
          reason = "selector_unavailable",
          message = "DAT SpecificDeviceSelector is unavailable for display session creation."
        )
      val sessionResult = unwrapDatResult(invokeWearablesMethod("createSession", selector))
      if (!sessionResult.success || sessionResult.value == null) {
        return DisplayLifecycleResult.blocked(
          state = "session_create_failed",
          reason = datErrorReason(sessionResult.error),
          message = sessionResult.description ?: "DAT display device session creation failed.",
          requiredAction = requiredActionForError(sessionResult.error)
        )
      }
      session = sessionResult.value
      nativeDisplaySession = session
      nativeDisplayDeviceId = target.deviceId
      sessionState = "display_session_starting"
      val startResult = unwrapDatResult(invokeInstanceMethod(session, "start"))
      if (!startResult.success) {
        detachNativeDisplayLocked()
        return DisplayLifecycleResult.blocked(
          state = "session_start_failed",
          reason = datErrorReason(startResult.error),
          message = startResult.description ?: "DAT display device session start failed.",
          requiredAction = requiredActionForError(startResult.error)
        )
      }
      val sessionStarted = waitForOwnerState(session, "STARTED", DISPLAY_SESSION_TIMEOUT_MS)
      if (sessionStarted != "STARTED") {
        latestDatOwnerError(session)?.let { error ->
          detachNativeDisplayLocked()
          return DisplayLifecycleResult.blocked(
            state = datErrorReason(error),
            reason = datErrorReason(error),
            message = datErrorDescription(error) ?: "DAT display device session failed before STARTED.",
            requiredAction = requiredActionForError(error)
          )
        }
        detachNativeDisplayLocked()
        return DisplayLifecycleResult.blocked(
          state = "session_start_timeout",
          reason = "session_start_timeout",
          message = "DAT display device session did not reach STARTED before timeout."
        )
      }
      sessionState = "target_ready"
      recordDisplayLifecycleStage("session_started")
      emitStateChanged()
    }

    var display = nativeDisplay
    if (display == null) {
      updateDisplayState(
        action = DISPLAY_WIDGET_RENDER.action,
        status = "attaching_display",
        connectionState = "display_attaching",
        renderPath = "native-dat",
        lifecycleStage = "attaching_display"
      )
      val displayResult = addDisplayToSession(session)
      if (!displayResult.success || displayResult.value == null) {
        detachNativeDisplayLocked()
        return DisplayLifecycleResult.blocked(
          state = "display_attach_failed",
          reason = datErrorReason(displayResult.error),
          message = displayResult.description ?: "DAT display capability attach failed.",
          requiredAction = requiredActionForError(displayResult.error)
        )
      }
      display = displayResult.value
      nativeDisplay = display
      recordDisplayLifecycleStage("display_attached")
      recordDisplayLifecycleStage("display_starting")
      val displayStarted = waitForOwnerState(display, "STARTED", DISPLAY_SESSION_TIMEOUT_MS)
      if (displayStarted != "STARTED") {
        latestDatOwnerError(display)?.let { error ->
          detachNativeDisplayLocked()
          return DisplayLifecycleResult.blocked(
            state = datErrorReason(error),
            reason = datErrorReason(error),
            message = datErrorDescription(error) ?: "DAT display capability failed before STARTED.",
            requiredAction = requiredActionForError(error)
          )
        }
        detachNativeDisplayLocked()
        return DisplayLifecycleResult.blocked(
          state = "display_start_timeout",
          reason = "display_start_timeout",
          message = "DAT display capability did not reach STARTED before timeout."
        )
      }
      recordDisplayLifecycleStage("display_started")
    }

    recordDisplayLifecycleStage("display_ready")
    return DisplayLifecycleResult.ready(
      state = "display_ready",
      message = "DAT display lifecycle is ready for ${metadata.widgetId ?: "widget"} content.",
      display = display,
      renderPath = "native-dat"
    )
  }

  private fun sendNativeDisplayContent(
    display: Any,
    config: DisplayActionConfig,
    metadata: DisplayWidgetMetadata
  ): DatCallResult {
    val contentBuilder: (Any) -> Unit = { scope ->
      renderNativeDisplayScope(scope, config, metadata)
    }
    val result = invokeInstanceMethod(display, "sendContent", contentBuilder)
      ?: invokeTopLevelDisplayFunction("sendContent", display, contentBuilder)
      ?: invokeSuspendInstanceMethod(display, "sendContent", contentBuilder)
      ?: invokeSuspendTopLevelDisplayFunction("sendContent", display, contentBuilder)
      ?: return DatCallResult.failure("DAT display sendContent API is unavailable.")
    return unwrapDatResult(result)
  }

  private fun renderNativeDisplayScope(
    scope: Any,
    config: DisplayActionConfig,
    metadata: DisplayWidgetMetadata
  ) {
    val title = when (config.action) {
      "clear_display_widget" -> "Display cleared"
      "reset_display_widget_session" -> "Display session reset"
      else -> metadata.title ?: "HandsFree widget"
    }
    val detail = when (config.action) {
      "focus_display_widget" -> "Focus: ${metadata.focusDirection ?: displayFocusTarget ?: "next"}"
      "activate_display_widget_action" -> "Action: ${metadata.activatedActionId ?: "selected"}"
      "update_display_widget" -> metadata.subtitle ?: "Widget updated"
      else -> metadata.subtitle ?: metadata.widgetId ?: config.operation
    }
    val footer = listOfNotNull(
      metadata.widgetId,
      metadata.manifestCid ?: metadata.descriptorCid
    ).joinToString(" | ").ifBlank { config.operation }

    val rendered = invokeDisplayDslMethod(scope, "flexBox") { box ->
      invokeDisplayText(box, title, "HEADING", null)
      invokeDisplayText(box, detail, "BODY", "SECONDARY")
      invokeDisplayText(box, footer, "META", "SECONDARY")
    }
    if (!rendered && !invokeDisplayText(scope, title, "HEADING", null)) {
      throw IllegalStateException("DAT display ContentScope did not expose supported text/flexBox builders")
    }
  }

  private fun applyDisplayWidgetState(
    config: DisplayActionConfig,
    metadata: DisplayWidgetMetadata,
    supported: Boolean,
    reason: String?,
    connectionState: String,
    renderPath: String?,
    message: String
  ) {
    if (supported || config.clearsLocalWidgetState) {
      when (config.action) {
        "render_display_widget" -> {
          displayActiveWidgetId = metadata.widgetId
          displayUpdateCount = 0
        }
        "update_display_widget" -> {
          displayActiveWidgetId = metadata.widgetId ?: displayActiveWidgetId
          displayUpdateCount += 1
        }
        "clear_display_widget" -> {
          displayActiveWidgetId = null
          displayFocusTarget = null
        }
        "focus_display_widget" -> {
          displayFocusTarget = metadata.focusDirection
        }
        "reset_display_widget_session" -> {
          displayActiveWidgetId = null
          displayFocusTarget = null
          displayUpdateCount = 0
        }
      }
    }
    displayDescriptorCid = metadata.descriptorCid ?: displayDescriptorCid
    displayInterfaceCid = metadata.interfaceCid ?: displayInterfaceCid
    displayManifestCid = metadata.manifestCid ?: displayManifestCid
    displayWidgetCid = metadata.widgetCid ?: displayWidgetCid
    displayOrbReceiptCid = metadata.orbReceiptCid ?: displayOrbReceiptCid
    displayPolicyDecision = metadata.policyDecision ?: displayPolicyDecision
    displayCorrelationId = metadata.correlationId ?: displayCorrelationId
    displayRequestId = metadata.requestId ?: displayRequestId
    displayFallback = metadata.fallback ?: if (supported) null else displayWidgetFallback(metadata, reason, message)
    updateDisplayState(
      action = config.action,
      status = if (supported) "ready" else "blocked",
      connectionState = if (supported) config.successConnectionState else connectionState,
      renderPath = if (supported) renderPath ?: "native-dat" else fallbackRenderPath(metadata),
      error = reason
    )
  }

  private fun nativeDisplayContentSentMessage(config: DisplayActionConfig): String =
    when (config.action) {
      "render_display_widget" -> "DAT display widget sent."
      "update_display_widget" -> "DAT display widget updated."
      "clear_display_widget" -> "DAT display widget cleared."
      "focus_display_widget" -> "DAT display widget focused."
      "activate_display_widget_action" -> "DAT display widget action activated."
      "play_display_widget_video" -> "DAT display widget video playback queued."
      "subscribe_display_widget_updates" -> "DAT display widget update subscription queued."
      else -> "DAT display content sent."
    }

  private fun displayWidgetActionResult(
    config: DisplayActionConfig,
    metadata: DisplayWidgetMetadata,
    supported: Boolean,
    state: String,
    reason: String?,
    message: String,
    requiredAction: String?
  ): Map<String, Any?> =
    mapOf(
      "state" to state,
      "mode" to if (supported && displayRenderPath == "native-dat") "native_display" else integrationMode(isDatSdkLinked()),
      "supported" to supported,
      "action" to config.action,
      "operation" to metadata.operation.orEmpty().ifBlank { config.operation },
      "reason" to reason,
      "message" to message,
      "renderPath" to if (supported) displayRenderPath.orEmpty().ifBlank { "native-dat" } else fallbackRenderPath(metadata),
      "requiredAction" to requiredAction,
      "deviceId" to selectedDeviceId,
      "targetConnectionState" to targetConnectionState(selectedDeviceId, getSelectedDeviceTarget()),
      "assetUri" to null,
      "mimeType" to null,
      "displayConnectionState" to displayConnectionState,
      "displayLastAction" to displayLastAction,
      "displayLastStatus" to displayLastStatus,
      "displayLastUpdatedAt" to displayLastUpdatedAt,
      "displayRenderPath" to displayRenderPath,
      "displayLastError" to displayLastError,
      "displayUpdateCount" to displayUpdateCount,
      "displayLifecycleStages" to displayLifecycleStages,
      "widgetId" to metadata.widgetId,
      "widgetCid" to metadata.widgetCid,
      "descriptorCid" to metadata.descriptorCid,
      "interfaceCid" to metadata.interfaceCid,
      "manifestCid" to metadata.manifestCid,
      "orbReceiptCid" to metadata.orbReceiptCid,
      "policyDecision" to metadata.policyDecision,
      "correlationId" to metadata.correlationId,
      "requestId" to metadata.requestId,
      "issuedAt" to metadata.issuedAt,
      "focusDirection" to metadata.focusDirection,
      "activatedActionId" to metadata.activatedActionId,
      "fallback" to if (supported) null else displayWidgetFallback(metadata, reason, message)
    )

  private fun emitDisplayWidgetEvent(
    config: DisplayActionConfig,
    supported: Boolean,
    payload: Map<String, Any?>
  ) {
    sendEvent(displayWidgetEventName(config, supported), payload)
  }

  private fun displayWidgetEventName(config: DisplayActionConfig, supported: Boolean): String {
    if (!supported) {
      return "display_widget_error"
    }
    return when (config.action) {
      "render_display_widget" -> "display_widget_rendered"
      "update_display_widget" -> "display_widget_updated"
      "clear_display_widget" -> "display_widget_cleared"
      "reset_display_widget_session" -> "display_widget_session_reset"
      else -> "display_widget_action"
    }
  }

  private fun displayWidgetPayload(context: Map<String, Any?>?): Map<String, Any?>? {
    if (context == null) {
      return null
    }
    return mapValue(context["display_widget_action"])
      ?: mapValue(context["mobile_payload"])
      ?: context
  }

  private fun displayWidgetActionInput(
    config: DisplayActionConfig,
    input: Map<String, Any?>,
    context: Map<String, Any?>?,
    inputKey: String? = null
  ): Map<String, Any?> {
    val contextPayload = displayWidgetPayload(context)
    val inputPayload = if (contextPayload == null) displayWidgetPayload(input) else null
    val payload = (contextPayload ?: inputPayload ?: input).toMutableMap()
    if (inputKey != null && !payload.containsKey(inputKey)) {
      payload[inputKey] = input
    }
    if (!payload.containsKey("operation")) {
      payload["operation"] = config.operation
    }
    if (!payload.containsKey("action")) {
      payload["action"] = config.action
    }
    return payload
  }

  private fun fallbackRenderPath(metadata: DisplayWidgetMetadata): String =
    firstString(metadata.fallback?.get("renderPath"), metadata.fallback?.get("render_path")) ?: "mobile-card"

  private fun displayWidgetFallback(
    metadata: DisplayWidgetMetadata,
    reason: String?,
    message: String
  ): Map<String, Any?> {
    val fallback = metadata.fallback?.toMutableMap() ?: mutableMapOf()
    if (firstString(fallback["reason"]) == null) {
      fallback["reason"] = reason ?: "dat_native_display_unavailable"
    }
    if (firstString(fallback["renderPath"]) == null) {
      fallback["renderPath"] = firstString(fallback["render_path"]) ?: "mobile-card"
    }
    if (firstString(fallback["message"]) == null) {
      fallback["message"] = message
    }
    return fallback
  }

  private fun displayWidgetMetadata(input: Map<String, Any?>): DisplayWidgetMetadata {
    val manifest = mapValue(input["manifest"]) ?: input
    val focus = mapValue(input["focus"])
    return DisplayWidgetMetadata(
      contract = stringValue(input["contract"]),
      type = stringValue(input["type"]),
      operation = firstString(input["operation"], manifest["operation"]),
      descriptorCid = firstString(input["descriptor_cid"], input["descriptorCid"], manifest["descriptor_cid"], manifest["descriptorCid"]),
      interfaceCid = firstString(input["interface_cid"], input["interfaceCid"], manifest["interface_cid"], manifest["interfaceCid"]),
      manifestCid = firstString(input["manifest_cid"], input["manifestCid"], manifest["manifest_cid"], manifest["manifestCid"]),
      widgetId = firstString(
        input["widget_id"],
        input["widgetId"],
        manifest["widget_id"],
        manifest["widgetId"],
        manifest["id"],
        displayActiveWidgetId
      ),
      widgetCid = firstString(input["widget_cid"], input["widgetCid"], manifest["widget_cid"], manifest["widgetCid"], manifest["cid"]),
      orbReceiptCid = firstString(input["orb_receipt_cid"], input["orbReceiptCid"], input["receipt_cid"], input["receiptCid"]),
      policyDecision = firstValue(input["policy_decision"], input["policyDecision"]),
      correlationId = firstString(input["correlation_id"], input["correlationId"]),
      requestId = firstString(input["request_id"], input["requestId"]),
      issuedAt = firstString(input["issued_at"], input["issuedAt"]),
      title = firstString(manifest["title"], manifest["name"], manifest["label"], input["title"], input["name"]),
      subtitle = firstString(manifest["summary"], manifest["description"], input["summary"], input["description"]),
      focusDirection = firstString(focus?.get("direction"), input["direction"]),
      activatedActionId = firstString(input["activated_action_id"], input["activatedActionId"], input["action_id"], input["actionId"]),
      fallback = mapValue(input["fallback"])
    )
  }

  private fun resolveDisplayDeviceTarget(): DisplayDeviceTarget? {
    val targets = getWearablesDeviceTargets()
    val selectedId = selectedDeviceId
    if (selectedId != null && targets.isEmpty()) {
      return DisplayDeviceTarget(selectedId, selectedId)
    }
    targets.firstOrNull { it.deviceId == selectedId }?.let { return it }
    return targets.firstOrNull { target ->
      val metadata = getWearablesDeviceMetadata(target)
      isDisplayCapableDevice(metadata) != false && normalizedPropertyState(metadata, "getLinkState") != "DISCONNECTED"
    } ?: targets.firstOrNull() ?: selectedId?.let { DisplayDeviceTarget(it, it) }
  }

  private fun displayDeviceGate(target: DisplayDeviceTarget): DisplayLifecycleResult? {
    val metadata = getWearablesDeviceMetadata(target) ?: return null
    val compatibility = normalizedToken(normalizedPropertyState(metadata, "getCompatibility"))
    if ("DEVICE_UPDATE_REQUIRED" in compatibility) {
      return DisplayLifecycleResult.blocked(
        state = "firmware_update_required",
        reason = "firmware_update_required",
        message = "Glasses firmware update is required before DAT display rendering.",
        requiredAction = "open_firmware_update"
      )
    }
    if ("DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED" in compatibility) {
      return DisplayLifecycleResult.blocked(
        state = "dat_app_update_required",
        reason = "dat_app_update_required",
        message = "DAT glasses app update is required before display rendering.",
        requiredAction = "open_dat_glasses_app_update"
      )
    }
    val linkState = normalizedPropertyState(metadata, "getLinkState")
    if (linkState != null && linkState != "CONNECTED") {
      return DisplayLifecycleResult.blocked(
        state = "device_not_connected",
        reason = "device_not_connected",
        message = "Selected glasses must be connected before starting a DAT display session."
      )
    }
    if (isDisplayCapableDevice(metadata) == false) {
      return DisplayLifecycleResult.blocked(
        state = "device_display_unsupported",
        reason = "device_display_unsupported",
        message = "Selected glasses do not report DAT display capability."
      )
    }
    return null
  }

  private fun getWearablesDeviceIds(): List<String> {
    return getWearablesDeviceTargets().map { it.deviceId }
  }

  private fun getWearablesDeviceTargets(): List<DisplayDeviceTarget> {
    val devicesFlow = invokeWearablesMethod("getDevices")
    val devicesValue = readFlowValue(devicesFlow)
    return (devicesValue as? Collection<*>)
      ?.mapNotNull { identifier ->
        deviceIdentifierKey(identifier)?.takeIf { it.isNotBlank() }?.let { deviceId ->
          DisplayDeviceTarget(deviceId, identifier ?: deviceId)
        }
      }
      ?: emptyList()
  }

  private fun getWearablesDeviceMetadata(target: DisplayDeviceTarget): Any? {
    val metadataMap = invokeWearablesMethod("getDevicesMetadata") as? Map<*, *> ?: return null
    metadataMap[target.nativeIdentifier]?.let { return readFlowValue(it) }
    val matchedEntry = metadataMap.entries.firstOrNull { (key, _) ->
      deviceIdentifierKey(key) == target.deviceId
    }
    return readFlowValue(matchedEntry?.value)
  }

  private fun isDisplayCapableDevice(device: Any?): Boolean? {
    if (device == null) {
      return null
    }
    invokeInstanceMethod(device, "isDisplayCapable")?.let { value ->
      return value as? Boolean
    }
    val deviceType = invokeInstanceMethod(device, "getDeviceType")
    invokeInstanceMethod(deviceType ?: return null, "isDisplayCapable")?.let { value ->
      return value as? Boolean
    }
    return null
  }

  private fun createSpecificDeviceSelector(deviceIdentifier: Any): Any? =
    try {
      val clazz = Class.forName(SPECIFIC_DEVICE_SELECTOR_CLASS_NAME)
      listOfNotNull(deviceIdentifier, deviceIdentifierKey(deviceIdentifier))
        .distinct()
        .firstNotNullOfOrNull { candidate ->
          val constructor = clazz.constructors.firstOrNull { ctor ->
            ctor.parameterTypes.size == 1 && isArgumentCompatible(ctor.parameterTypes[0], candidate)
          }
          constructor?.newInstance(candidate)
        }
    } catch (_: Throwable) {
      null
    }

  private fun addDisplayToSession(session: Any): DatCallResult {
    invokeInstanceMethod(session, "addDisplay")?.let { return unwrapDatResult(it) }
    invokeTopLevelDisplayFunction("addDisplay", session)?.let { return unwrapDatResult(it) }

    val config = instantiateNoArg(DISPLAY_CONFIGURATION_CLASS_NAME)
    if (config != null) {
      invokeInstanceMethod(session, "addDisplay", config)?.let { return unwrapDatResult(it) }
      invokeTopLevelDisplayFunction("addDisplay", session, config)?.let { return unwrapDatResult(it) }
    }

    invokeTopLevelDisplayFunction("addDisplay\$default", session, null, 1, null)
      ?.let { return unwrapDatResult(it) }

    return DatCallResult.failure("DAT display addDisplay API is unavailable.")
  }

  private fun detachNativeDisplayLocked() {
    val session = nativeDisplaySession
    if (session != null) {
      try {
        invokeInstanceMethod(session, "removeDisplay")
          ?: invokeTopLevelDisplayFunction("removeDisplay", session)
      } catch (_: Throwable) {
        // Best-effort cleanup; session stop below is the recovery path.
      }
      try {
        invokeInstanceMethod(session, "stop")
      } catch (_: Throwable) {
        // Best-effort cleanup.
      }
    }
    nativeDisplay = null
    nativeDisplaySession = null
    nativeDisplayDeviceId = null
  }

  private fun waitForOwnerState(owner: Any, expected: String, timeoutMs: Long): String? {
    val deadline = System.currentTimeMillis() + timeoutMs
    var lastState: String? = null
    while (System.currentTimeMillis() <= deadline) {
      lastState = normalizedStateName(readFlowValue(invokeInstanceMethod(owner, "getState")))
        ?: normalizedStateName(invokeInstanceMethod(owner, "getState"))
      if (lastState == expected) {
        return lastState
      }
      Thread.sleep(DISPLAY_STATE_POLL_MS)
    }
    return lastState
  }

  private fun isDisplaySdkLinked(): Boolean =
    classExists(DISPLAY_INTERFACE_CLASS_NAME) && (
      displayExtensionClass() != null || classExists(DISPLAY_CONFIGURATION_CLASS_NAME)
    )

  private fun displayExtensionClass(): Class<*>? =
    DISPLAY_EXTENSION_CLASS_NAMES.firstNotNullOfOrNull { className ->
      try {
        Class.forName(className)
      } catch (_: ClassNotFoundException) {
        null
      }
    }

  private fun invokeTopLevelDisplayFunction(name: String, vararg args: Any?): Any? {
    val method = DISPLAY_EXTENSION_CLASS_NAMES.firstNotNullOfOrNull { className ->
      try {
        val clazz = Class.forName(className)
        findMethod(clazz, name, args)
      } catch (_: Throwable) {
        null
      }
    } ?: return null
    return method.invoke(null, *args)
  }

  private fun invokeSuspendTopLevelDisplayFunction(name: String, vararg args: Any?): Any? {
    val continuation = BlockingContinuation()
    val invocationArgs = args.toMutableList().apply { add(continuation) }.toTypedArray()
    val method = DISPLAY_EXTENSION_CLASS_NAMES.firstNotNullOfOrNull { className ->
      try {
        val clazz = Class.forName(className)
        findMethod(clazz, name, invocationArgs)
      } catch (_: Throwable) {
        null
      }
    } ?: return null
    return continuation.resolve(method.invoke(null, *invocationArgs))
  }

  private fun invokeSuspendInstanceMethod(target: Any?, name: String, vararg args: Any?): Any? {
    if (target == null) {
      return null
    }
    val continuation = BlockingContinuation()
    val invocationArgs = args.toMutableList().apply { add(continuation) }.toTypedArray()
    val method = findMethod(target.javaClass, name, invocationArgs) ?: return null
    return continuation.resolve(method.invoke(target, *invocationArgs))
  }

  private fun invokeInstanceMethod(target: Any?, name: String, vararg args: Any?): Any? {
    if (target == null) {
      return null
    }
    val method = findMethod(target.javaClass, name, args) ?: return null
    return method.invoke(target, *args)
  }

  private fun unwrapDatResult(result: Any?): DatCallResult {
    if (result == null) {
      return DatCallResult.success(null)
    }
    val resultClass = result.javaClass
    if (resultClass.name.startsWith("com.meta.wearable") || resultClass.methods.any { it.name == "fold" }) {
      var successValue: Any? = null
      var failureValue: Any? = null
      val onSuccess: (Any?) -> Any? = { value ->
        successValue = value
        value
      }
      val onFailure: (Any?, Any?) -> Any? = { error, _ ->
        failureValue = error
        null
      }
      findMethod(resultClass, "fold", arrayOf(onSuccess, onFailure))?.let { method ->
        method.invoke(result, onSuccess, onFailure)
        return if (failureValue == null) {
          DatCallResult.success(successValue)
        } else {
          DatCallResult.failure(error = failureValue)
        }
      }

      var fallbackError: Any? = null
      val fallback: (Any?) -> Any? = { error ->
        fallbackError = error
        null
      }
      findMethod(resultClass, "getOrElse", arrayOf(fallback))?.let { method ->
        val value = method.invoke(result, fallback)
        return if (fallbackError == null) {
          DatCallResult.success(value)
        } else {
          DatCallResult.failure(error = fallbackError)
        }
      }

      invokeInstanceMethod(result, "exceptionOrNull")?.let { error ->
        return DatCallResult.failure(error = error)
      }
      invokeInstanceMethod(result, "getOrNull")?.let { value ->
        return DatCallResult.success(value)
      }
    }
    return DatCallResult.success(result)
  }

  private fun invokeDisplayText(
    target: Any,
    text: String,
    style: String?,
    color: String?
  ): Boolean =
    invokeDisplayDslMethod(
      target = target,
      name = "text",
      text = text,
      enumHints = mapOf(
        "TextStyle" to (style ?: "BODY"),
        "TextColor" to (color ?: "PRIMARY")
      )
    )

  private fun invokeDisplayDslMethod(
    target: Any,
    name: String,
    text: String? = null,
    enumHints: Map<String, String> = emptyMap(),
    block: ((Any) -> Unit)? = null
  ): Boolean {
    val methods = target.javaClass.methods
      .filter { it.name == name }
      .sortedBy { it.parameterTypes.size }

    for (method in methods) {
      val args = buildDisplayDslArgs(method.parameterTypes, text, enumHints, block) ?: continue
      try {
        method.invoke(target, *args)
        return true
      } catch (_: Throwable) {
        // Try the next overload; DAT display DSL signatures can differ across preview SDK drops.
      }
    }
    return false
  }

  private fun buildDisplayDslArgs(
    parameterTypes: Array<Class<*>>,
    text: String?,
    enumHints: Map<String, String>,
    block: ((Any) -> Unit)?
  ): Array<Any?>? {
    var textUsed = false
    return parameterTypes.map { parameterType ->
      when {
        parameterType == String::class.java -> {
          textUsed = true
          text ?: ""
        }
        parameterType.isEnum -> enumConstant(parameterType, enumHints[parameterType.simpleName])
        parameterType == Integer.TYPE || parameterType == Int::class.javaObjectType -> 12
        parameterType == java.lang.Float.TYPE || parameterType == Float::class.javaObjectType -> 1f
        parameterType == java.lang.Boolean.TYPE || parameterType == Boolean::class.javaObjectType -> false
        parameterType.name == "kotlin.jvm.functions.Function1" -> ({ child: Any ->
          block?.invoke(child)
          Unit
        })
        parameterType.name == "kotlin.jvm.functions.Function0" -> ({
          Unit
        })
        !parameterType.isPrimitive -> null
        else -> return null
      }
    }.toTypedArray().also {
      if (text != null && !textUsed) {
        return null
      }
    }
  }

  private fun enumConstant(enumClass: Class<*>, preferredName: String?): Any? {
    val constants = enumClass.enumConstants ?: return null
    val names = listOfNotNull(preferredName, "COLUMN", "CARD", "CENTER", "PRIMARY", "BODY", "NONE")
    return names.firstNotNullOfOrNull { name ->
      constants.firstOrNull { constant -> normalizedStateName(constant) == name }
    } ?: constants.firstOrNull()
  }

  private fun instantiateNoArg(className: String): Any? =
    try {
      Class.forName(className).constructors.firstOrNull { it.parameterCount == 0 }?.newInstance()
    } catch (_: Throwable) {
      null
    }

  private fun classExists(className: String): Boolean =
    try {
      Class.forName(className)
      true
    } catch (_: ClassNotFoundException) {
      false
    }

  private fun normalizedPropertyState(target: Any?, getter: String): String? =
    normalizedStateName(invokeInstanceMethod(target, getter))

  private fun normalizedStateName(value: Any?): String? {
    if (value == null) {
      return null
    }
    if (value is Enum<*>) {
      return value.name.uppercase()
    }
    val text = value.toString().substringAfterLast(".")
    if (text.isNotBlank() && "@" !in text) {
      return text.uppercase()
    }
    return value.javaClass.simpleName?.uppercase()
  }

  private fun latestDatOwnerError(owner: Any?): Any? =
    readFlowLatestValue(invokeInstanceMethod(owner, "getErrors"))
      ?: readFlowLatestValue(invokeInstanceMethod(owner, "getErrorStream"))

  private fun readFlowLatestValue(flowLike: Any?): Any? =
    readFlowValue(flowLike)
      ?: (invokeInstanceMethod(flowLike, "getReplayCache") as? List<*>)?.lastOrNull()

  private fun unwrapDatError(error: Any?): Any? =
    when (error) {
      is InvocationTargetException -> unwrapDatError(error.targetException ?: error.cause ?: error)
      else -> error
    }

  private fun datErrorDescription(error: Any?): String? {
    val actual = unwrapDatError(error) ?: return null
    val description = try {
      actual.javaClass.methods.firstOrNull { method ->
        method.name == "getDescription" && method.parameterCount == 0
      }?.invoke(actual) as? String
    } catch (_: Throwable) {
      null
    }
    return description
      ?: (actual as? Throwable)?.message?.takeIf { it.isNotBlank() }
      ?: actual.toString().takeIf { it.isNotBlank() }
  }

  private fun datErrorReason(error: Any?): String {
    val normalized = normalizedErrorToken(error)
    return when {
      "DEVICE_UPDATE_REQUIRED" in normalized -> "firmware_update_required"
      "DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED" in normalized -> "dat_app_update_required"
      "TIMEOUT" in normalized -> "display_timeout"
      "UNAVAILABLE" in normalized -> "display_unavailable"
      normalized.isNotBlank() -> normalized.lowercase()
      else -> "native_display_error"
    }
  }

  private fun requiredActionForError(error: Any?): String? {
    val normalized = normalizedErrorToken(error)
    return when {
      "DEVICE_UPDATE_REQUIRED" in normalized -> "open_firmware_update"
      "DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED" in normalized -> "open_dat_glasses_app_update"
      else -> null
    }
  }

  private fun normalizedErrorToken(error: Any?): String {
    val actual = unwrapDatError(error)
    val stateName = normalizedStateName(actual).orEmpty()
    val description = datErrorDescription(actual).orEmpty()
    return normalizedToken(listOf(stateName, description).joinToString("_"))
  }

  private fun normalizedToken(value: String?): String =
    value.orEmpty()
      .uppercase()
      .replace(Regex("[^A-Z0-9]+"), "_")

  private fun mapValue(value: Any?): Map<String, Any?>? =
    (value as? Map<*, *>)?.mapNotNull { (key, mapValue) ->
      (key as? String)?.let { it to mapValue }
    }?.toMap()

  private fun firstString(vararg values: Any?): String? =
    values.firstNotNullOfOrNull { stringValue(it)?.takeIf { value -> value.isNotBlank() } }

  private fun firstValue(vararg values: Any?): Any? =
    values.firstOrNull { it != null }

  private fun stringValue(value: Any?): String? =
    when (value) {
      null -> null
      is String -> value
      else -> value.toString()
    }

  private fun deviceIdentifierKey(identifier: Any?): String? =
    firstString(
      invokeInstanceMethod(identifier, "getValue"),
      invokeInstanceMethod(identifier, "getId"),
      invokeInstanceMethod(identifier, "getIdentifier"),
      identifier
    )?.takeUnless { it.contains("@") && it.contains(".") }

  private fun fallbackDisplayConnectionState(): String =
    if (getSelectedDeviceTarget() == null) "awaiting_target" else "blocked"

  private fun updateDisplayState(
    action: String,
    status: String,
    connectionState: String,
    renderPath: String? = displayRenderPath,
    error: String? = displayLastError,
    lifecycleStage: String? = null
  ) {
    displayLastAction = action
    displayLastStatus = status
    displayConnectionState = connectionState
    displayLastUpdatedAt = System.currentTimeMillis()
    displayRenderPath = renderPath
    displayLastError = error
    lifecycleStage?.let { recordDisplayLifecycleStage(it) }
  }

  private fun recordDisplayLifecycleStage(stage: String) {
    if (stage.isBlank()) {
      return
    }
    val stages = displayLifecycleStages.toMutableList()
    if (stages.lastOrNull() != stage) {
      stages.add(stage)
    }
    displayLifecycleStages = stages.takeLast(MAX_DISPLAY_LIFECYCLE_STAGES)
  }

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

  private fun invokeWearablesMethod(name: String, vararg args: Any?): Any? {
    val clazz = wearablesClass() ?: return null
    val method = findMethod(clazz, name, args) ?: return null
    val target = if (Modifier.isStatic(method.modifiers)) null else wearablesInstance(clazz)
    return method.invoke(target, *args)
  }

  private fun invokeWearablesMethodOrThrow(name: String, vararg args: Any?) {
    val clazz = wearablesClass()
      ?: throw IllegalStateException("Wearables SDK class is unavailable")
    val method = findMethod(clazz, name, args)
      ?: throw IllegalStateException("Wearables.$name is unavailable")
    val target = if (Modifier.isStatic(method.modifiers)) null else wearablesInstance(clazz)
    method.invoke(target, *args)
  }

  private fun findMethod(clazz: Class<*>, name: String, args: Array<out Any?>): Method? =
    clazz.methods.firstOrNull { method ->
      method.name == name &&
        method.parameterTypes.size == args.size &&
        method.parameterTypes.indices.all { index ->
          isArgumentCompatible(method.parameterTypes[index], args[index])
        }
    }

  private fun isArgumentCompatible(parameterType: Class<*>, arg: Any?): Boolean {
    if (arg == null) {
      return !parameterType.isPrimitive
    }
    if (parameterType.isAssignableFrom(arg.javaClass)) {
      return true
    }
    return when (parameterType) {
      java.lang.Boolean.TYPE -> arg is Boolean
      java.lang.Integer.TYPE -> arg is Int
      java.lang.Long.TYPE -> arg is Long
      java.lang.Float.TYPE -> arg is Float
      java.lang.Double.TYPE -> arg is Double
      else -> false
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
    invokeWearablesMethodOrThrow("initialize", reactContextOrThrow())
  }

  private fun startRegistration(): Map<String, String> {
    initializeWearables()
    invokeWearablesMethodOrThrow("startRegistration", currentActivityOrThrow())
    sessionState = "registering"
    emitStateChanged()
    return mapOf("state" to sessionState, "mode" to "sdk")
  }

  private fun startUnregistration(): Map<String, String> {
    initializeWearables()
    invokeWearablesMethodOrThrow("startUnregistration", currentActivityOrThrow())
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

  private fun isDatVersionAtLeast(current: String?, minimum: String): Boolean {
    // Missing version segments are treated as zeros so that, for example,
    // "0.7" compares equal to "0.7.0" and "0.7.0.0". This is a lenient
    // vendor-version comparison, not a strict semver parser.
    fun parse(version: String?): List<Int> =
      (version ?: "")
        .split(".")
        .map { token -> token.toIntOrNull() ?: 0 }
    val left = parse(current)
    val right = parse(minimum)
    val max = maxOf(left.size, right.size)
    for (index in 0 until max) {
      val lhs = left.getOrElse(index) { 0 }
      val rhs = right.getOrElse(index) { 0 }
      if (lhs > rhs) return true
      if (lhs < rhs) return false
    }
    return true
  }

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

  private data class DisplayActionConfig(
    val action: String,
    val operation: String,
    val successConnectionState: String,
    val unavailableMessage: String,
    val sendsContent: Boolean = true,
    val clearsLocalWidgetState: Boolean = false
  )

  private data class DisplayWidgetMetadata(
    val contract: String?,
    val type: String?,
    val operation: String?,
    val descriptorCid: String?,
    val interfaceCid: String?,
    val manifestCid: String?,
    val widgetId: String?,
    val widgetCid: String?,
    val orbReceiptCid: String?,
    val policyDecision: Any?,
    val correlationId: String?,
    val requestId: String?,
    val issuedAt: String?,
    val title: String?,
    val subtitle: String?,
    val focusDirection: String?,
    val activatedActionId: String?,
    val fallback: Map<String, Any?>?
  )

  private data class DisplayDeviceTarget(
    val deviceId: String,
    val nativeIdentifier: Any
  )

  private class BlockingContinuation : Continuation<Any?> {
    override val context: CoroutineContext = EmptyCoroutineContext
    private val latch = CountDownLatch(1)
    private var value: Any? = null
    private var error: Throwable? = null

    override fun resumeWith(result: Result<Any?>) {
      result.fold(
        onSuccess = { value = it },
        onFailure = { error = it }
      )
      latch.countDown()
    }

    fun resolve(invocationResult: Any?): Any? {
      if (invocationResult !== COROUTINE_SUSPENDED) {
        return invocationResult
      }
      if (!latch.await(DISPLAY_SESSION_TIMEOUT_MS, TimeUnit.MILLISECONDS)) {
        throw TimeoutException("DAT display suspend call did not complete before timeout.")
      }
      error?.let { throw it }
      return value
    }
  }

  private data class DisplayLifecycleResult(
    val supported: Boolean,
    val state: String,
    val reason: String?,
    val message: String,
    val display: Any?,
    val renderPath: String?,
    val requiredAction: String?
  ) {
    companion object {
      fun ready(
        state: String,
        message: String,
        display: Any?,
        renderPath: String
      ): DisplayLifecycleResult =
        DisplayLifecycleResult(
          supported = true,
          state = state,
          reason = null,
          message = message,
          display = display,
          renderPath = renderPath,
          requiredAction = null
        )

      fun blocked(
        state: String,
        reason: String,
        message: String,
        requiredAction: String? = null
      ): DisplayLifecycleResult =
        DisplayLifecycleResult(
          supported = false,
          state = state,
          reason = reason,
          message = message,
          display = null,
          renderPath = null,
          requiredAction = requiredAction
        )
    }
  }

  private data class DatCallResult(
    val success: Boolean,
    val value: Any?,
    val error: Any?,
    val description: String?
  ) {
    companion object {
      fun success(value: Any?): DatCallResult =
        DatCallResult(success = true, value = value, error = null, description = null)

      fun failure(description: String? = null, error: Any? = null): DatCallResult =
        DatCallResult(
          success = false,
          value = null,
          error = error,
          description = description ?: errorDescription(error)
        )

      private fun errorDescription(error: Any?): String? {
        if (error == null) {
          return null
        }
        return try {
          error.javaClass.methods.firstOrNull { method ->
            method.name == "getDescription" && method.parameterCount == 0
          }?.invoke(error) as? String
        } catch (_: Throwable) {
          null
        } ?: error.toString()
      }
    }
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
    const val METADATA_DAM_ENABLED = "com.meta.wearable.mwdat.DAM_ENABLED"
    const val MINIMUM_DAT_SDK_VERSION = "0.7.0"
    const val SPECIFIC_DEVICE_SELECTOR_CLASS_NAME = "com.meta.wearable.dat.core.selectors.SpecificDeviceSelector"
    const val DISPLAY_INTERFACE_CLASS_NAME = "com.meta.wearable.dat.display.Display"
    const val DISPLAY_CONFIGURATION_CLASS_NAME = "com.meta.wearable.dat.display.DisplayConfiguration"
    const val DISPLAY_SESSION_TIMEOUT_MS = 5_000L
    const val DISPLAY_STATE_POLL_MS = 100L
    const val MAX_DISPLAY_LIFECYCLE_STAGES = 16
    val DISPLAY_EXTENSION_CLASS_NAMES = listOf(
      "com.meta.wearable.dat.display.DisplayKt",
      "com.meta.wearable.dat.display.DisplayExtensionsKt",
      "com.meta.wearable.dat.display.DisplayCapabilityKt",
      "com.meta.wearable.dat.display.DeviceSessionDisplayKt",
      "com.meta.wearable.dat.display.DeviceSessionExtensionsKt"
    )
    val DISPLAY_WIDGET_RENDER = DisplayActionConfig(
      action = "render_display_widget",
      operation = "render_widget",
      successConnectionState = "rendered",
      unavailableMessage = "Display widget rendering requires DAT SDK linkage, DAM enablement, and a selected target."
    )
    val DISPLAY_WIDGET_UPDATE = DisplayActionConfig(
      action = "update_display_widget",
      operation = "update_widget",
      successConnectionState = "updated",
      unavailableMessage = "Display widget updates require an active DAT display session."
    )
    val DISPLAY_WIDGET_CLEAR = DisplayActionConfig(
      action = "clear_display_widget",
      operation = "clear_widget",
      successConnectionState = "cleared",
      unavailableMessage = "Display widget clearing requires an active DAT display session.",
      clearsLocalWidgetState = true
    )
    val DISPLAY_WIDGET_FOCUS = DisplayActionConfig(
      action = "focus_display_widget",
      operation = "focus_next",
      successConnectionState = "focused",
      unavailableMessage = "Display widget focus requires an active DAT display session."
    )
    val DISPLAY_WIDGET_ACTIVATE = DisplayActionConfig(
      action = "activate_display_widget_action",
      operation = "activate",
      successConnectionState = "action_activated",
      unavailableMessage = "Display widget actions require an active DAT display session."
    )
    val DISPLAY_WIDGET_RESET = DisplayActionConfig(
      action = "reset_display_widget_session",
      operation = "reset_session",
      successConnectionState = "reset",
      unavailableMessage = "Display widget session reset requires DAT display lifecycle availability.",
      sendsContent = false,
      clearsLocalWidgetState = true
    )
    val DISPLAY_WIDGET_PLAY_VIDEO = DisplayActionConfig(
      action = "play_display_widget_video",
      operation = "play_video",
      successConnectionState = "video_playing",
      unavailableMessage = "Display widget video playback requires an active DAT display session."
    )
    val DISPLAY_WIDGET_SUBSCRIBE_UPDATES = DisplayActionConfig(
      action = "subscribe_display_widget_updates",
      operation = "subscribe_updates",
      successConnectionState = "updates_subscribed",
      unavailableMessage = "Display widget update subscriptions require an active DAT display session.",
      sendsContent = false
    )
  }
}
