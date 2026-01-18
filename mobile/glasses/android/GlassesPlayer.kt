package glasses

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.os.Build
import java.io.File
import java.io.RandomAccessFile
import kotlin.concurrent.thread

class GlassesPlayer(private val context: Context) {
    private var track: AudioTrack? = null
    private var audioManager: AudioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private var isPlaying = false
    private var playbackThread: Thread? = null
    private var scoReceiver: BroadcastReceiver? = null
    private var scoConnected = false
    
    companion object {
        const val SAMPLE_RATE = 16000
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_OUT_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        const val WAV_HEADER_SIZE = 44
        const val SCO_CONNECTION_DELAY_MS = 500L
    }

    /**
     * Play PCM audio samples
     * @param samples Audio samples as ShortArray
     * @param sampleRate Sample rate (default 16000)
     */
    fun playPcm16Mono(samples: ShortArray, sampleRate: Int = 16000) {
        stop()

        setupBluetoothSco()

        val bufferBytes = samples.size * 2
        val t = AudioTrack(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build(),
            AudioFormat.Builder()
                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                .setSampleRate(sampleRate)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                .build(),
            bufferBytes,
            AudioTrack.MODE_STATIC,
            AudioTrack.AUDIO_SESSION_ID_GENERATE
        )

        t.write(samples, 0, samples.size)
        t.play()
        track = t
        isPlaying = true
    }

    /**
     * Play audio from a WAV file
     * @param file WAV file to play
     * @param callback Callback when playback completes or errors
     */
    fun playAudio(file: File, callback: (Exception?) -> Unit) {
        if (isPlaying) {
            callback(Exception("Playback already in progress"))
            return
        }

        try {
            // Setup Bluetooth SCO
            setupBluetoothSco()
            
            // Note: SCO connection delay should be handled by caller on background thread
            // to avoid ANR. This is a known limitation for synchronous API.
            Thread.sleep(SCO_CONNECTION_DELAY_MS)

            // Read WAV file
            val wavData = readWAVFile(file)
            
            val bufferSize = AudioTrack.getMinBufferSize(
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT
            )

            if (bufferSize == AudioTrack.ERROR || bufferSize == AudioTrack.ERROR_BAD_VALUE) {
                callback(Exception("Invalid buffer size: $bufferSize"))
                return
            }

            val audioAttributes = AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build()

            val audioFormat = AudioFormat.Builder()
                .setSampleRate(SAMPLE_RATE)
                .setEncoding(AUDIO_FORMAT)
                .setChannelMask(CHANNEL_CONFIG)
                .build()

            track = AudioTrack.Builder()
                .setAudioAttributes(audioAttributes)
                .setAudioFormat(audioFormat)
                .setBufferSizeInBytes(bufferSize * 2)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build()

            if (track?.state != AudioTrack.STATE_INITIALIZED) {
                callback(Exception("AudioTrack failed to initialize"))
                return
            }

            track?.play()
            isPlaying = true

            // Play in background thread
            playbackThread = thread {
                try {
                    val buffer = ByteArray(bufferSize)
                    var offset = 0
                    
                    while (isPlaying && offset < wavData.size) {
                        val remaining = wavData.size - offset
                        val toWrite = minOf(remaining, buffer.size)
                        
                        System.arraycopy(wavData, offset, buffer, 0, toWrite)
                        val written = track?.write(buffer, 0, toWrite) ?: 0
                        
                        if (written > 0) {
                            offset += written
                        } else {
                            break
                        }
                    }
                    
                    // Wait for playback to complete
                    Thread.sleep(100)
                    
                    callback(null)
                } catch (e: Exception) {
                    callback(e)
                } finally {
                    cleanup()
                }
            }
        } catch (e: Exception) {
            cleanup()
            callback(e)
        }
    }

    /**
     * Stop playback
     * Note: This method blocks briefly to ensure clean shutdown.
     * Consider calling from a background thread to avoid ANR in UI code.
     */
    fun stop() {
        isPlaying = false
        playbackThread?.join(1000)
    }

    /**
     * Pause playback
     */
    fun pause() {
        track?.pause()
        isPlaying = false
    }

    /**
     * Resume playback
     */
    fun resume() {
        track?.play()
        isPlaying = true
    }

    /**
     * Check if currently playing
     */
    fun isPlaying(): Boolean = isPlaying

    /**
     * Get playback progress (0.0 to 1.0)
     */
    fun getPlaybackProgress(): Double {
        // This would require tracking total samples and current position
        // For now, return a placeholder
        return 0.5
    }

    private fun setupBluetoothSco() {
        // Register SCO state receiver
        scoReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                val state = intent.getIntExtra(AudioManager.EXTRA_SCO_AUDIO_STATE, -1)
                scoConnected = state == AudioManager.SCO_AUDIO_STATE_CONNECTED
            }
        }
        
        val filter = IntentFilter(AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.registerReceiver(scoReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            context.registerReceiver(scoReceiver, filter)
        }

        // Set audio mode for voice communication
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        
        // Start Bluetooth SCO if available
        if (audioManager.isBluetoothScoAvailableOffCall) {
            audioManager.startBluetoothSco()
            audioManager.isBluetoothScoOn = true
        }
    }

    private fun teardownBluetoothSco() {
        try {
            audioManager.stopBluetoothSco()
            audioManager.isBluetoothScoOn = false
            audioManager.mode = AudioManager.MODE_NORMAL
            
            scoReceiver?.let {
                context.unregisterReceiver(it)
            }
            scoReceiver = null
        } catch (e: Exception) {
            // Ignore errors during cleanup
        }
    }

    private fun cleanup() {
        track?.stop()
        track?.release()
        track = null
        teardownBluetoothSco()
    }

    private fun readWAVFile(file: File): ByteArray {
        val raf = RandomAccessFile(file, "r")
        try {
            // Skip WAV header
            raf.seek(WAV_HEADER_SIZE.toLong())
            
            // Read remaining data
            val dataSize = (file.length() - WAV_HEADER_SIZE).toInt()
            val data = ByteArray(dataSize)
            raf.readFully(data)
            
            return data
        } finally {
            raf.close()
        }
    }
}
