package expo.modules.glassesaudio

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition
import expo.modules.kotlin.Promise
import android.content.Context
import android.media.AudioManager
import android.os.Handler
import android.os.Looper
import glasses.AudioRouteMonitor
import glasses.GlassesRecorder
import glasses.GlassesPlayer
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class ExpoGlassesAudioModule : Module() {
  private lateinit var context: Context
  private lateinit var routeMonitor: AudioRouteMonitor
  private lateinit var recorder: GlassesRecorder
  private lateinit var player: GlassesPlayer
  private val handler = Handler(Looper.getMainLooper())

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
      val summary = routeMonitor.currentRouteSummary()
      val lines = summary.split("\n")
      
      var inputDevice = "Unknown"
      var outputDevice = "Unknown"
      
      for (line in lines) {
        when {
          line.startsWith("Inputs:") -> {
            val inputIndex = lines.indexOf(line)
            if (inputIndex + 1 < lines.size) {
              inputDevice = lines[inputIndex + 1].trim()
            }
          }
          line.startsWith("Outputs:") -> {
            val outputIndex = lines.indexOf(line)
            if (outputIndex + 1 < lines.size) {
              outputDevice = lines[outputIndex + 1].trim()
            }
          }
        }
      }
      
      val isBluetoothConnected = summary.contains("SCO=true") || 
                                 outputDevice.contains("Bluetooth", ignoreCase = true) ||
                                 inputDevice.contains("Bluetooth", ignoreCase = true)
      
      mapOf(
        "inputDevice" to inputDevice,
        "outputDevice" to outputDevice,
        "sampleRate" to 16000,
        "isBluetoothConnected" to isBluetoothConnected
      )
    }

    AsyncFunction("startRecording") { durationSeconds: Int, promise: Promise ->
      try {
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        
        // Enable Bluetooth SCO if available
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        audioManager.startBluetoothSco()
        
        // Create output file
        val dateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
        val timestamp = dateFormat.format(Date())
        val filename = "glasses_recording_$timestamp.wav"
        val outputDir = context.getExternalFilesDir(null)
        val outputFile = File(outputDir, filename)
        
        // Start recording with WAV file output
        val audioRecord = recorder.start(outputFile)
        
        // Emit recording started event
        sendEvent("onRecordingProgress", mapOf("isRecording" to true, "duration" to 0))
        
        // Schedule stop after duration
        handler.postDelayed({
          recorder.stop()
          audioManager.stopBluetoothSco()
          audioManager.mode = AudioManager.MODE_NORMAL
          
          val fileSize = if (outputFile.exists()) outputFile.length() else 0L
          
          // Emit recording stopped event
          sendEvent("onRecordingProgress", mapOf("isRecording" to false, "duration" to durationSeconds))
          
          promise.resolve(
            mapOf(
              "uri" to outputFile.absolutePath,
              "duration" to durationSeconds,
              "size" to fileSize.toInt()
            )
          )
        }, (durationSeconds * 1000).toLong())
        
      } catch (e: Exception) {
        promise.reject("ERR_START_RECORDING", "Failed to start recording: ${e.message}", e)
      }
    }

    AsyncFunction("stopRecording") { promise: Promise ->
      try {
        recorder.stop()
        
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.stopBluetoothSco()
        audioManager.mode = AudioManager.MODE_NORMAL
        
        promise.resolve(
          mapOf(
            "uri" to "",
            "duration" to 0,
            "size" to 0
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
        
        val file = File(fileUri)
        if (!file.exists()) {
          promise.reject("ERR_FILE_NOT_FOUND", "Audio file not found: $fileUri")
          return@AsyncFunction
        }
        
        // Emit playback started event
        sendEvent("onPlaybackStatus", mapOf(
          "isPlaying" to true,
          "position" to 0,
          "duration" to 0
        ))
        
        try {
          // Parse and play WAV file
          val wavInfo = player.playWavFile(file) {
            // Playback completed callback
            handler.post {
              audioManager.stopBluetoothSco()
              audioManager.mode = AudioManager.MODE_NORMAL
              
              // Emit playback ended event
              sendEvent("onPlaybackStatus", mapOf(
                "isPlaying" to false,
                "position" to 0,
                "duration" to 0
              ))
            }
          }
          
          promise.resolve(null)
        } catch (e: Exception) {
          audioManager.stopBluetoothSco()
          audioManager.mode = AudioManager.MODE_NORMAL
          
          // Emit playback error event
          sendEvent("onPlaybackStatus", mapOf(
            "isPlaying" to false,
            "position" to 0,
            "duration" to 0,
            "error" to e.message
          ))
          
          promise.reject("ERR_PLAY_AUDIO", "Failed to play WAV file: ${e.message}", e)
        }
      } catch (e: Exception) {
        promise.reject("ERR_PLAY_AUDIO", "Failed to play audio: ${e.message}", e)
      }
    }

    AsyncFunction("stopPlayback") { promise: Promise ->
      try {
        player.stop()
        
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.stopBluetoothSco()
        audioManager.mode = AudioManager.MODE_NORMAL
        
        promise.resolve(null)
      } catch (e: Exception) {
        promise.reject("ERR_STOP_PLAYBACK", "Failed to stop playback: ${e.message}", e)
      }
    }

    OnDestroy {
      recorder.stop()
      player.stop()
    }
  }
}
