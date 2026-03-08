package expo.modules.glassesaudio

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import expo.modules.kotlin.Promise
import android.content.Context
import android.net.Uri
import android.media.AudioManager
import android.os.Handler
import android.os.Looper
import expo.modules.glassesaudio.AudioRouteMonitor
import expo.modules.glassesaudio.AudioSource
import expo.modules.glassesaudio.GlassesRecorder
import expo.modules.glassesaudio.GlassesPlayer
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class ExpoGlassesAudioModule : Module() {
  companion object {
    private const val PLAYBACK_TIMEOUT_MS = 5 * 60 * 1000L // 5 minutes timeout for playback
  }
  
  private lateinit var context: Context
  private lateinit var routeMonitor: AudioRouteMonitor
  private lateinit var recorder: GlassesRecorder
  private lateinit var player: GlassesPlayer
  private lateinit var peerBridge: BluetoothPeerBridge
  private val handler = Handler(Looper.getMainLooper())
  private var playbackTimeoutRunnable: Runnable? = null
  private var recordingStopRunnable: Runnable? = null

  override fun definition() = ModuleDefinition {
    Name("ExpoGlassesAudio")

    Events(
      "onAudioRouteChange",
      "onRecordingProgress",
      "onPlaybackStatus",
      "peerDiscovered",
      "peerConnected",
      "peerDisconnected",
      "frameReceived"
    )

    OnCreate {
      context = appContext.reactContext ?: throw IllegalStateException("React context is null")
      routeMonitor = AudioRouteMonitor(context)
      recorder = GlassesRecorder()
      player = GlassesPlayer()
      peerBridge = BluetoothPeerBridge(context) { eventName, payload ->
        sendEvent(eventName, payload)
      }
    }

    Function("getAudioRoute") {
      val route = routeMonitor.getCurrentRoute()
      val inputs = route["inputs"] as? List<*>
      val outputs = route["outputs"] as? List<*>

      val firstInput = inputs?.firstOrNull() as? Map<*, *>
      val firstOutput = outputs?.firstOrNull() as? Map<*, *>

      val inputDevice = (firstInput?.get("productName") as? String)
        ?: (firstInput?.get("typeName") as? String)
        ?: "Unknown"
      val outputDevice = (firstOutput?.get("productName") as? String)
        ?: (firstOutput?.get("typeName") as? String)
        ?: "Unknown"

      val isBluetoothConnected = route["isBluetoothConnected"] as? Boolean
        ?: (inputDevice.contains("Bluetooth", ignoreCase = true) || outputDevice.contains("Bluetooth", ignoreCase = true))

      mapOf(
        "inputDevice" to inputDevice,
        "outputDevice" to outputDevice,
        "sampleRate" to 16000,
        "isBluetoothConnected" to isBluetoothConnected
      )
    }

    AsyncFunction("startRecording") { durationSeconds: Int, audioSourceString: String?, promise: Promise ->
      try {
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

        val audioSource = when (audioSourceString) {
          "phone" -> AudioSource.PHONE
          "glasses" -> AudioSource.GLASSES
          else -> AudioSource.AUTO
        }

        when (audioSource) {
          AudioSource.GLASSES -> {
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            audioManager.startBluetoothSco()
          }
          AudioSource.PHONE -> {
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
          }
          AudioSource.AUTO -> {
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            if (audioManager.isBluetoothScoAvailableOffCall) {
              audioManager.startBluetoothSco()
            }
          }
        }

        val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
        val timestamp = dateFormat.format(Date())
        val filename = "glasses_recording_$timestamp.wav"
        val outputDir = context.getExternalFilesDir(null) ?: context.filesDir
        val outputFile = File(outputDir, filename)
        outputFile.parentFile?.mkdirs()

        recorder.start(outputFile, audioSource)
        sendEvent("onRecordingProgress", mapOf("isRecording" to true, "duration" to 0))

        recordingStopRunnable?.let { handler.removeCallbacks(it) }
        recordingStopRunnable = Runnable {
          val result = this@ExpoGlassesAudioModule.recorder.stop()
          audioManager.stopBluetoothSco()
          audioManager.mode = AudioManager.MODE_NORMAL

          if (result != null) {
            sendEvent(
              "onRecordingProgress",
              mapOf("isRecording" to false, "duration" to result.durationSeconds)
            )
            promise.resolve(
              mapOf(
                "uri" to Uri.fromFile(result.file).toString(),
                "duration" to result.durationSeconds,
                "size" to result.sizeBytes.toInt()
              )
            )
          } else {
            sendEvent(
              "onRecordingProgress",
              mapOf("isRecording" to false, "duration" to durationSeconds)
            )
            promise.reject("ERR_RECORDING_RESULT", "Recording stopped but no result available", null)
          }
        }
        handler.postDelayed(recordingStopRunnable!!, (durationSeconds * 1000).toLong())
      } catch (e: Exception) {
        promise.reject("ERR_START_RECORDING", "Failed to start recording: ${e.message}", e)
      }
    }

    AsyncFunction("stopRecording") { promise: Promise ->
      try {
        recordingStopRunnable?.let { handler.removeCallbacks(it) }
        recordingStopRunnable = null

        val result = this@ExpoGlassesAudioModule.recorder.stop()
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.stopBluetoothSco()
        audioManager.mode = AudioManager.MODE_NORMAL

        val uri = if (result != null) Uri.fromFile(result.file).toString() else ""
        val size = result?.sizeBytes?.toInt() ?: 0
        val duration = result?.durationSeconds ?: 0

        sendEvent("onRecordingProgress", mapOf("isRecording" to false, "duration" to duration))
        promise.resolve(
          mapOf(
            "uri" to uri,
            "duration" to duration,
            "size" to size
          )
        )
      } catch (e: Exception) {
        promise.reject("ERR_STOP_RECORDING", "Failed to stop recording: ${e.message}", e)
      }
    }

    AsyncFunction("playAudio") { fileUri: String, promise: Promise ->
      try {
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        
        // Enable Bluetooth SCO for playback
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        audioManager.startBluetoothSco()
        
        val file = if (fileUri.startsWith("file://")) {
          val path = Uri.parse(fileUri).path
          if (path.isNullOrEmpty()) {
            promise.reject("ERR_INVALID_URI", "Invalid file URI: $fileUri", null)
            return@AsyncFunction
          }
          File(path)
        } else {
          File(fileUri)
        }
        if (!file.exists()) {
          promise.reject("ERR_FILE_NOT_FOUND", "Audio file not found: $fileUri", null)
          return@AsyncFunction
        }
        
        // Emit playback started event
        sendEvent("onPlaybackStatus", mapOf(
          "isPlaying" to true
        ))
        
        // Track if promise has been resolved/rejected
        var promiseSettled = false
        
        // Setup timeout to prevent promise from hanging indefinitely
        synchronized(this@ExpoGlassesAudioModule) {
          val timeoutRunnable = Runnable {
            synchronized(this@ExpoGlassesAudioModule) {
              if (!promiseSettled) {
                promiseSettled = true
                this@ExpoGlassesAudioModule.player.stop()
                audioManager.stopBluetoothSco()
                audioManager.mode = AudioManager.MODE_NORMAL
                
                sendEvent("onPlaybackStatus", mapOf(
                  "isPlaying" to false,
                  "error" to "Playback timeout after ${PLAYBACK_TIMEOUT_MS / 60000} minutes"
                ))
                
                promise.reject("ERR_PLAYBACK_TIMEOUT", "Playback did not complete within ${PLAYBACK_TIMEOUT_MS / 60000} minutes", null)
              }
            }
          }
          playbackTimeoutRunnable = timeoutRunnable
          handler.postDelayed(timeoutRunnable, PLAYBACK_TIMEOUT_MS)
        }
        
        try {
          // Parse and play WAV file
          val wavInfo = player.playWavFile(file) {
            // Playback completed callback
            handler.post {
              synchronized(this@ExpoGlassesAudioModule) {
                if (!promiseSettled) {
                  promiseSettled = true
                  
                  // Cancel timeout
                  playbackTimeoutRunnable?.let { handler.removeCallbacks(it) }
                  playbackTimeoutRunnable = null
                  
                  audioManager.stopBluetoothSco()
                  audioManager.mode = AudioManager.MODE_NORMAL
                  
                  // Emit playback ended event
                  sendEvent("onPlaybackStatus", mapOf(
                    "isPlaying" to false
                  ))
                  
                  // Resolve promise when playback completes
                  promise.resolve(null)
                }
              }
            }
          }
          
          // Don't resolve here - wait for completion callback
        } catch (e: Exception) {
          synchronized(this@ExpoGlassesAudioModule) {
            if (!promiseSettled) {
              promiseSettled = true
              
              // Cancel timeout
              playbackTimeoutRunnable?.let { handler.removeCallbacks(it) }
              playbackTimeoutRunnable = null
              
              audioManager.stopBluetoothSco()
              audioManager.mode = AudioManager.MODE_NORMAL
              
              // Emit playback error event
              sendEvent("onPlaybackStatus", mapOf(
                "isPlaying" to false,
                "error" to e.message
              ))
              
              promise.reject("ERR_PLAY_AUDIO", "Failed to play WAV file: ${e.message}", e)
            }
          }
        }
      } catch (e: Exception) {
        promise.reject("ERR_PLAY_AUDIO", "Failed to play audio: ${e.message}", e)
      }
    }

    AsyncFunction("stopPlayback") { promise: Promise ->
      try {
        this@ExpoGlassesAudioModule.player.stop()
        
        // Cancel any pending timeout
        playbackTimeoutRunnable?.let { handler.removeCallbacks(it) }
        playbackTimeoutRunnable = null
        
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.stopBluetoothSco()
        audioManager.mode = AudioManager.MODE_NORMAL
        
        promise.resolve(null)
      } catch (e: Exception) {
        promise.reject("ERR_STOP_PLAYBACK", "Failed to stop playback: ${e.message}", e)
      }
    }

    AsyncFunction("scanPeers") { timeoutMs: Int ->
      peerBridge.scanPeers(timeoutMs)
    }

    Function("getPeerAdapterState") {
      peerBridge.getAdapterState()
    }

    AsyncFunction("advertiseIdentity") { peerId: String, displayName: String? ->
      peerBridge.advertiseIdentity(peerId, displayName)
    }

    AsyncFunction("connectPeer") { peerRef: String ->
      peerBridge.connectPeer(peerRef)
    }

    AsyncFunction("disconnectPeer") { peerRef: String, reason: String? ->
      peerBridge.disconnectPeer(peerRef, reason)
      null
    }

    AsyncFunction("sendFrame") { peerRef: String, payloadBase64: String ->
      peerBridge.sendFrame(peerRef, payloadBase64)
      null
    }

    AsyncFunction("simulatePeerDiscovery") { peer: Map<String, Any?> ->
      peerBridge.simulatePeerDiscovery(peer)
    }

    AsyncFunction("simulatePeerConnection") { peerRef: String ->
      peerBridge.simulatePeerConnection(peerRef)
    }

    AsyncFunction("simulateFrameReceived") { peerRef: String, payloadBase64: String, peerId: String? ->
      peerBridge.simulateFrameReceived(peerRef, payloadBase64, peerId)
      null
    }

    AsyncFunction("resetPeerSimulation") {
      peerBridge.resetSimulation()
      null
    }

    OnDestroy {
      playbackTimeoutRunnable?.let { handler.removeCallbacks(it) }
      playbackTimeoutRunnable = null
      recordingStopRunnable?.let { handler.removeCallbacks(it) }
      recordingStopRunnable = null
      peerBridge.resetSimulation()
      this@ExpoGlassesAudioModule.recorder.stop()
      this@ExpoGlassesAudioModule.player.stop()
    }
  }
}
