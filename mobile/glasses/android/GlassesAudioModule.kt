package glasses

import android.content.Context
import android.os.Environment
import com.facebook.react.bridge.*
import com.facebook.react.modules.core.DeviceEventManagerModule
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class GlassesAudioModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext) {
    
    private var recorder: GlassesRecorder? = null
    private var player: GlassesPlayer? = null
    private var audioRouteMonitor: AudioRouteMonitor? = null
    private var lastRecordingFile: File? = null

    override fun getName(): String {
        return "GlassesAudioModule"
    }

    /**
     * Get current audio route information
     */
    @ReactMethod
    fun getAudioRoute(promise: Promise) {
        try {
            if (audioRouteMonitor == null) {
                audioRouteMonitor = AudioRouteMonitor(reactApplicationContext)
            }
            val route = audioRouteMonitor!!.currentRouteSummary()
            promise.resolve(route)
        } catch (e: Exception) {
            promise.reject("AUDIO_ROUTE_ERROR", e.message, e)
        }
    }

    /**
     * Start recording audio to a WAV file
     * @param durationMs Recording duration in milliseconds (0 = unlimited)
     */
    @ReactMethod
    fun startRecording(durationMs: Int, promise: Promise) {
        try {
            if (recorder?.isRecording() == true) {
                promise.reject("RECORDING_ERROR", "Recording already in progress")
                return
            }

            // Create output file
            val outputFile = createAudioFile()
            
            // Initialize recorder if needed
            if (recorder == null) {
                recorder = GlassesRecorder(reactApplicationContext)
            }

            // Start recording
            recorder!!.startRecording(outputFile, durationMs.toLong()) { file, error ->
                if (error != null) {
                    promise.reject("RECORDING_ERROR", error.message, error)
                } else {
                    lastRecordingFile = file
                    val result = Arguments.createMap().apply {
                        putString("filePath", file?.absolutePath)
                        putDouble("duration", durationMs.toDouble())
                    }
                    promise.resolve(result)
                }
            }
        } catch (e: Exception) {
            promise.reject("RECORDING_ERROR", e.message, e)
        }
    }

    /**
     * Stop recording
     */
    @ReactMethod
    fun stopRecording(promise: Promise) {
        try {
            recorder?.stopRecording()
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("STOP_RECORDING_ERROR", e.message, e)
        }
    }

    /**
     * Check if currently recording
     */
    @ReactMethod
    fun isRecording(promise: Promise) {
        try {
            val recording = recorder?.isRecording() ?: false
            promise.resolve(recording)
        } catch (e: Exception) {
            promise.reject("IS_RECORDING_ERROR", e.message, e)
        }
    }

    /**
     * Play audio from a file
     * @param filePath Path to audio file (WAV format)
     */
    @ReactMethod
    fun playAudio(filePath: String, promise: Promise) {
        try {
            if (player?.isPlaying() == true) {
                promise.reject("PLAYBACK_ERROR", "Playback already in progress")
                return
            }

            val file = File(filePath)
            if (!file.exists()) {
                promise.reject("PLAYBACK_ERROR", "File not found: $filePath")
                return
            }

            // Initialize player if needed
            if (player == null) {
                player = GlassesPlayer(reactApplicationContext)
            }

            // Start playback
            player!!.playAudio(file) { error ->
                if (error != null) {
                    promise.reject("PLAYBACK_ERROR", error.message, error)
                } else {
                    promise.resolve(null)
                }
            }
        } catch (e: Exception) {
            promise.reject("PLAYBACK_ERROR", e.message, e)
        }
    }

    /**
     * Play last recording
     */
    @ReactMethod
    fun playLastRecording(promise: Promise) {
        try {
            if (lastRecordingFile == null || !lastRecordingFile!!.exists()) {
                promise.reject("PLAYBACK_ERROR", "No recording available")
                return
            }

            playAudio(lastRecordingFile!!.absolutePath, promise)
        } catch (e: Exception) {
            promise.reject("PLAYBACK_ERROR", e.message, e)
        }
    }

    /**
     * Stop playback
     */
    @ReactMethod
    fun stopPlayback(promise: Promise) {
        try {
            player?.stop()
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("STOP_PLAYBACK_ERROR", e.message, e)
        }
    }

    /**
     * Pause playback
     */
    @ReactMethod
    fun pausePlayback(promise: Promise) {
        try {
            player?.pause()
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("PAUSE_PLAYBACK_ERROR", e.message, e)
        }
    }

    /**
     * Resume playback
     */
    @ReactMethod
    fun resumePlayback(promise: Promise) {
        try {
            player?.resume()
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("RESUME_PLAYBACK_ERROR", e.message, e)
        }
    }

    /**
     * Check if currently playing
     */
    @ReactMethod
    fun isPlaying(promise: Promise) {
        try {
            val playing = player?.isPlaying() ?: false
            promise.resolve(playing)
        } catch (e: Exception) {
            promise.reject("IS_PLAYING_ERROR", e.message, e)
        }
    }

    /**
     * Get last recording file path
     */
    @ReactMethod
    fun getLastRecordingPath(promise: Promise) {
        try {
            if (lastRecordingFile != null && lastRecordingFile!!.exists()) {
                promise.resolve(lastRecordingFile!!.absolutePath)
            } else {
                promise.resolve(null)
            }
        } catch (e: Exception) {
            promise.reject("GET_PATH_ERROR", e.message, e)
        }
    }

    /**
     * List all recording files
     */
    @ReactMethod
    fun listRecordings(promise: Promise) {
        try {
            val dir = getAudioDirectory()
            val files = dir.listFiles { file -> file.extension == "wav" }
            
            val recordings = Arguments.createArray()
            files?.sortedByDescending { it.lastModified() }?.forEach { file ->
                val info = Arguments.createMap().apply {
                    putString("path", file.absolutePath)
                    putString("name", file.name)
                    putDouble("size", file.length().toDouble())
                    putDouble("timestamp", file.lastModified().toDouble())
                }
                recordings.pushMap(info)
            }
            
            promise.resolve(recordings)
        } catch (e: Exception) {
            promise.reject("LIST_RECORDINGS_ERROR", e.message, e)
        }
    }

    /**
     * Delete a recording file
     */
    @ReactMethod
    fun deleteRecording(filePath: String, promise: Promise) {
        try {
            val file = File(filePath)
            if (file.exists() && file.delete()) {
                promise.resolve(true)
            } else {
                promise.reject("DELETE_ERROR", "Failed to delete file")
            }
        } catch (e: Exception) {
            promise.reject("DELETE_ERROR", e.message, e)
        }
    }

    private fun createAudioFile(): File {
        val dir = getAudioDirectory()
        if (!dir.exists()) {
            dir.mkdirs()
        }
        
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        return File(dir, "glasses_recording_$timestamp.wav")
    }

    private fun getAudioDirectory(): File {
        return File(
            reactApplicationContext.getExternalFilesDir(Environment.DIRECTORY_MUSIC),
            "audio_diagnostics"
        )
    }

    override fun onCatalystInstanceDestroy() {
        super.onCatalystInstanceDestroy()
        recorder?.stopRecording()
        player?.stop()
    }
}
