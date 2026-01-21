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
  private val handler = Handler(Looper.getMainLooper())
  private var playbackTimeoutRunnable: Runnable? = null
  private var recordingStopRunnable: Runnable? = null

  override fun definition() = ModuleDefinition {
    Name("ExpoGlassesAudio")

    Events("onAudioRouteChange", "onRecordingProgress", "onPlaybackStatus")

    OnCreate {
      context = appContext.reactContext ?: throw IllegalStateException("React context is null")
      routeMonitor = AudioRouteMonitor(context)
      recorder = GlassesRecorder()
      player = GlassesPlayer()
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
        
        // Parse audio source
        val audioSource = when (audioSourceString) {
          "phone" -> AudioSource.PHONE
          "glasses" -> AudioSource.GLASSES
          else -> AudioSource.AUTO
        }
        
        // Configure Bluetooth SCO based on audio source
        when (audioSource) {
          AudioSource.GLASSES -> {
            // Enable Bluetooth SCO for glasses/Bluetooth mic
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            audioManager.startBluetoothSco()
          }
          AudioSource.PHONE -> {
            // Use phone mic - don't enable Bluetooth SCO
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
          }
          AudioSource.AUTO -> {
            // Auto mode - enable SCO if available
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            if (audioManager.isBluetoothScoAvailableOffCall) {
              audioManager.startBluetoothSco()
            }
          }
        }
        
        // Create output file
        val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
        val timestamp = dateFormat.format(Date())
        val filename = "glasses_recording_$timestamp.wav"
        val outputDir = context.getExternalFilesDir(null) ?: context.filesDir
        val outputFile = File(outputDir, filename)
        outputFile.parentFile?.mkdirs()
        
        // Start recording with specified audio source
        recorder.start(outputFile, audioSource)
        
        // Schedule stop after duration
        handler.postDelayed({
          val result = recorder.stop()
          audioManager.stopBluetoothSco()
          audioManager.mode = AudioManager.MODE_NORMAL
          
          if (result != null) {
            // Emit recording stopped event with actual recorded duration
            sendEvent("onRecordingProgress", mapOf("isRecording" to false, "duration" to result.durationSeconds))
            
            promise.resolve(
              mapOf(
                "uri" to result.file.absolutePath,
                "duration" to result.durationSeconds,
                "size" to result.sizeBytes.toInt()
              )
          val finalFile = result?.file ?: outputFile
          val fileSize = if (finalFile.exists()) finalFile.length() else 0L
          val uri = Uri.fromFile(finalFile).toString()
          
          // Emit recording stopped event
          sendEvent("onRecordingProgress", mapOf("isRecording" to false, "duration" to durationSeconds))
          
          promise.resolve(
            mapOf(
              "uri" to uri,
              "duration" to durationSeconds,
              "size" to fileSize.toInt()
            )
          } else {
            // Emit recording stopped event with scheduled duration as fallback
            sendEvent("onRecordingProgress", mapOf("isRecording" to false, "duration" to durationSeconds))
            promise.reject("ERR_RECORDING_RESULT", "Recording stopped but no result available")
          }
        }, (durationSeconds * 1000).toLong())
        
      } catch (e: Exception) {
        promise.reject("ERR_START_RECORDING", "Failed to start recording: ${e.message}", e)
      }
    }

    AsyncFunction("stopRecording") { promise: Promise ->
      try {
        val result = recorder.stop()
        
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.stopBluetoothSco()
        audioManager.mode = AudioManager.MODE_NORMAL

        val uri = result?.file?.let { Uri.fromFile(it).toString() } ?: ""
        val size = result?.sizeBytes?.toInt() ?: 0
        val duration = result?.durationSeconds ?: 0
        
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
            promise.reject("ERR_INVALID_URI", "Invalid file URI: $fileUri")
            return@AsyncFunction
          }
          File(path)
        } else {
          File(fileUri)
        }
        if (!file.exists()) {
          promise.reject("ERR_FILE_NOT_FOUND", "Audio file not found: $fileUri")
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
                player.stop()
                audioManager.stopBluetoothSco()
                audioManager.mode = AudioManager.MODE_NORMAL
                
                sendEvent("onPlaybackStatus", mapOf(
                  "isPlaying" to false,
                  "error" to "Playback timeout after ${PLAYBACK_TIMEOUT_MS / 60000} minutes"
                ))
                
                promise.reject("ERR_PLAYBACK_TIMEOUT", "Playback did not complete within ${PLAYBACK_TIMEOUT_MS / 60000} minutes")
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
        player.stop()
        
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

    OnDestroy {
      playbackTimeoutRunnable?.let { handler.removeCallbacks(it) }
      playbackTimeoutRunnable = null
      recordingStopRunnable?.let { handler.removeCallbacks(it) }
      recordingStopRunnable = null
      recorder.stop()
      player.stop()
    }
  }
}
