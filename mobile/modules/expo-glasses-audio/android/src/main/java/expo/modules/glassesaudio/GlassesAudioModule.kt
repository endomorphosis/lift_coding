package expo.modules.glassesaudio

import android.content.Context
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

/**
 * Expo module that bridges AudioRouteMonitor to React Native.
 * Provides methods to get current audio route and monitor changes in real-time.
 */
class GlassesAudioModule : Module() {
    private var audioRouteMonitor: AudioRouteMonitor? = null

    override fun definition() = ModuleDefinition {
        Name("GlassesAudio")

        Events("onAudioRouteChange")

        // Module lifecycle
        OnCreate {
            audioRouteMonitor = AudioRouteMonitor(appContext.reactContext ?: return@OnCreate)
        }

        OnDestroy {
            audioRouteMonitor?.stopMonitoring()
            audioRouteMonitor = null
        }

        /**
         * Get the current audio route information as a map.
         * Returns inputs, outputs, Bluetooth connection status, SCO status, etc.
         */
        AsyncFunction("getCurrentRoute") {
            val monitor = audioRouteMonitor ?: throw Exception("AudioRouteMonitor not initialized")
            return@AsyncFunction monitor.getCurrentRoute()
        }

        /**
         * Get the current audio route as a formatted string summary.
         */
        AsyncFunction("getCurrentRouteSummary") {
            val monitor = audioRouteMonitor ?: throw Exception("AudioRouteMonitor not initialized")
            return@AsyncFunction monitor.currentRouteSummary()
        }

        /**
         * Check if a Bluetooth device is connected.
         */
        AsyncFunction("isBluetoothConnected") {
            val monitor = audioRouteMonitor ?: throw Exception("AudioRouteMonitor not initialized")
            return@AsyncFunction monitor.isBluetoothDeviceConnected()
        }

        /**
         * Check if Bluetooth SCO is currently connected.
         */
        AsyncFunction("isScoConnected") {
            val monitor = audioRouteMonitor ?: throw Exception("AudioRouteMonitor not initialized")
            return@AsyncFunction monitor.isScoConnected()
        }

        /**
         * Start monitoring audio route changes.
         * Emits "onAudioRouteChange" events when the route changes.
         */
        Function("startMonitoring") {
            val monitor = audioRouteMonitor ?: throw Exception("AudioRouteMonitor not initialized")
            
            monitor.startMonitoring { routeInfo ->
                sendEvent("onAudioRouteChange", mapOf(
                    "route" to routeInfo
                ))
            }
        }

        /**
         * Stop monitoring audio route changes.
         */
        Function("stopMonitoring") {
            val monitor = audioRouteMonitor ?: return@Function
            monitor.stopMonitoring()
        }
    }

    private val Context.reactContext: Context?
        get() = this
}
