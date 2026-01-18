package com.glassesaudio

import android.os.Handler
import android.os.Looper
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule
import glasses.AudioRouteMonitor

class GlassesAudioModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext) {
    
    private var routeMonitor: AudioRouteMonitor? = null
    private var recorder: GlassesRecorderBridge? = null
    private var player: GlassesPlayerBridge? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    
    override fun getName(): String {
        return "GlassesAudioModule"
    }
    
    init {
        routeMonitor = AudioRouteMonitor(reactContext)
        recorder = GlassesRecorderBridge(reactContext)
        player = GlassesPlayerBridge(reactContext)
    }
    
    private fun sendEvent(eventName: String, params: WritableMap?) {
        reactApplicationContext
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
            .emit(eventName, params)
    }
    
    @ReactMethod
    fun startMonitoring(promise: Promise) {
        try {
            mainHandler.post {
                val currentRoute = routeMonitor?.currentRouteSummary() ?: "Unknown"
                
                // Send initial route
                val params = Arguments.createMap()
                params.putString("route", currentRoute)
                sendEvent("onRouteChange", params)
                
                promise.resolve(currentRoute)
            }
        } catch (e: Exception) {
            promise.reject("START_MONITORING_FAILED", e.message, e)
        }
    }
    
    @ReactMethod
    fun stopMonitoring(promise: Promise) {
        try {
            // Android monitoring is passive, so nothing to stop
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("STOP_MONITORING_FAILED", e.message, e)
        }
    }
    
    @ReactMethod
    fun getCurrentRoute(promise: Promise) {
        try {
            val currentRoute = routeMonitor?.currentRouteSummary() ?: "Unknown"
            promise.resolve(currentRoute)
        } catch (e: Exception) {
            promise.reject("GET_ROUTE_FAILED", e.message, e)
        }
    }
    
    @ReactMethod
    fun startRecording(durationSeconds: Double, promise: Promise) {
        try {
            recorder?.startRecording(durationSeconds.toInt()) { file, exception ->
                if (exception != null) {
                    val params = Arguments.createMap()
                    params.putString("error", exception.message)
                    sendEvent("onRecordingComplete", params)
                    promise.reject("RECORDING_FAILED", exception.message, exception)
                } else if (file != null) {
                    val fileUri = file.absolutePath
                    val params = Arguments.createMap()
                    params.putString("fileUri", fileUri)
                    sendEvent("onRecordingComplete", params)
                    promise.resolve(fileUri)
                } else {
                    val params = Arguments.createMap()
                    params.putString("error", "Recording failed")
                    sendEvent("onRecordingComplete", params)
                    promise.reject("RECORDING_FAILED", "Recording failed without error")
                }
            }
        } catch (e: Exception) {
            promise.reject("START_RECORDING_FAILED", e.message, e)
        }
    }
    
    @ReactMethod
    fun stopRecording(promise: Promise) {
        try {
            recorder?.stopRecording()
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("STOP_RECORDING_FAILED", e.message, e)
        }
    }
    
    @ReactMethod
    fun playAudio(fileUri: String, promise: Promise) {
        try {
            val file = java.io.File(fileUri)
            player?.playAudio(file) { exception ->
                if (exception != null) {
                    val params = Arguments.createMap()
                    params.putString("error", exception.message)
                    sendEvent("onPlaybackComplete", params)
                    promise.reject("PLAYBACK_FAILED", exception.message, exception)
                } else {
                    val params = Arguments.createMap()
                    sendEvent("onPlaybackComplete", params)
                    promise.resolve(null)
                }
            }
        } catch (e: Exception) {
            promise.reject("PLAY_AUDIO_FAILED", e.message, e)
        }
    }
    
    @ReactMethod
    fun stopPlayback(promise: Promise) {
        try {
            player?.stop()
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("STOP_PLAYBACK_FAILED", e.message, e)
        }
    }
}
