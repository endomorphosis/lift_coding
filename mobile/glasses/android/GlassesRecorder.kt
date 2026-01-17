package glasses

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile
import kotlin.concurrent.thread

class GlassesRecorder(private val context: Context) {
    private var recorder: AudioRecord? = null
    private var audioManager: AudioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private var isRecording = false
    private var recordingThread: Thread? = null
    private var scoReceiver: BroadcastReceiver? = null
    private var scoConnected = false
    
    companion object {
        const val SAMPLE_RATE = 16000
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        const val BITS_PER_SAMPLE = 16
        const val NUM_CHANNELS = 1
    }

    /**
     * Start recording audio to a WAV file
     * @param outputFile File to write WAV data to
     * @param durationMs Optional recording duration in milliseconds (0 = unlimited)
     * @param callback Callback when recording completes or errors
     */
    fun startRecording(
        outputFile: File, 
        durationMs: Long = 0,
        callback: (File?, Exception?) -> Unit
    ) {
        if (isRecording) {
            callback(null, Exception("Recording already in progress"))
            return
        }

        try {
            // Setup Bluetooth SCO
            setupBluetoothSco()
            
            // Wait a moment for SCO to connect
            Thread.sleep(500)

            val bufferSize = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT
            )

            if (bufferSize == AudioRecord.ERROR || bufferSize == AudioRecord.ERROR_BAD_VALUE) {
                callback(null, Exception("Invalid buffer size: $bufferSize"))
                return
            }

            recorder = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize * 2
            )

            if (recorder?.state != AudioRecord.STATE_INITIALIZED) {
                callback(null, Exception("AudioRecord failed to initialize"))
                return
            }

            recorder?.startRecording()
            isRecording = true

            // Record in background thread
            recordingThread = thread {
                try {
                    val buffer = ShortArray(bufferSize / 2)
                    val outputStream = FileOutputStream(outputFile)
                    
                    // Write placeholder WAV header (will update later with actual size)
                    writeWAVHeader(outputStream, 0)
                    
                    var totalSamplesWritten = 0
                    val startTime = System.currentTimeMillis()
                    
                    while (isRecording) {
                        val samplesRead = recorder?.read(buffer, 0, buffer.size) ?: 0
                        
                        if (samplesRead > 0) {
                            // Convert shorts to bytes (little-endian)
                            val byteBuffer = ByteArray(samplesRead * 2)
                            for (i in 0 until samplesRead) {
                                val sample = buffer[i]
                                byteBuffer[i * 2] = (sample.toInt() and 0xFF).toByte()
                                byteBuffer[i * 2 + 1] = (sample.toInt() shr 8 and 0xFF).toByte()
                            }
                            outputStream.write(byteBuffer)
                            totalSamplesWritten += samplesRead
                        }
                        
                        // Check duration limit
                        if (durationMs > 0 && System.currentTimeMillis() - startTime >= durationMs) {
                            break
                        }
                    }
                    
                    outputStream.close()
                    
                    // Update WAV header with actual data size
                    updateWAVHeader(outputFile, totalSamplesWritten * 2)
                    
                    callback(outputFile, null)
                } catch (e: Exception) {
                    callback(null, e)
                } finally {
                    cleanup()
                }
            }
        } catch (e: Exception) {
            cleanup()
            callback(null, e)
        }
    }

    /**
     * Stop recording
     */
    fun stopRecording() {
        isRecording = false
        recordingThread?.join(1000)
    }

    /**
     * Check if currently recording
     */
    fun isRecording(): Boolean = isRecording

    /**
     * Get current recording level (0.0 to 1.0)
     */
    fun getRecordingLevel(): Float {
        // This would require maintaining a running calculation of amplitude
        // For now, return a placeholder
        return 0.5f
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
        recorder?.stop()
        recorder?.release()
        recorder = null
        teardownBluetoothSco()
    }

    private fun writeWAVHeader(outputStream: FileOutputStream, dataSize: Int) {
        val header = ByteArray(44)
        val channels = NUM_CHANNELS
        val bitsPerSample = BITS_PER_SAMPLE
        val byteRate = SAMPLE_RATE * channels * bitsPerSample / 8
        val blockAlign = channels * bitsPerSample / 8
        
        // RIFF header
        header[0] = 'R'.code.toByte()
        header[1] = 'I'.code.toByte()
        header[2] = 'F'.code.toByte()
        header[3] = 'F'.code.toByte()
        writeInt(header, 4, dataSize + 36)
        header[8] = 'W'.code.toByte()
        header[9] = 'A'.code.toByte()
        header[10] = 'V'.code.toByte()
        header[11] = 'E'.code.toByte()
        
        // fmt chunk
        header[12] = 'f'.code.toByte()
        header[13] = 'm'.code.toByte()
        header[14] = 't'.code.toByte()
        header[15] = ' '.code.toByte()
        writeInt(header, 16, 16)  // Subchunk1 size (16 for PCM)
        writeShort(header, 20, 1) // Audio format (1 = PCM)
        writeShort(header, 22, channels)
        writeInt(header, 24, SAMPLE_RATE)
        writeInt(header, 28, byteRate)
        writeShort(header, 32, blockAlign.toShort())
        writeShort(header, 34, bitsPerSample.toShort())
        
        // data chunk
        header[36] = 'd'.code.toByte()
        header[37] = 'a'.code.toByte()
        header[38] = 't'.code.toByte()
        header[39] = 'a'.code.toByte()
        writeInt(header, 40, dataSize)
        
        outputStream.write(header)
    }

    private fun updateWAVHeader(file: File, dataSize: Int) {
        val raf = RandomAccessFile(file, "rw")
        try {
            // Update file size in RIFF header (offset 4)
            raf.seek(4)
            raf.write(intToByteArray(dataSize + 36))
            
            // Update data size in data chunk (offset 40)
            raf.seek(40)
            raf.write(intToByteArray(dataSize))
        } finally {
            raf.close()
        }
    }

    private fun writeInt(buffer: ByteArray, offset: Int, value: Int) {
        buffer[offset] = (value and 0xff).toByte()
        buffer[offset + 1] = (value shr 8 and 0xff).toByte()
        buffer[offset + 2] = (value shr 16 and 0xff).toByte()
        buffer[offset + 3] = (value shr 24 and 0xff).toByte()
    }

    private fun writeShort(buffer: ByteArray, offset: Int, value: Short) {
        buffer[offset] = (value.toInt() and 0xff).toByte()
        buffer[offset + 1] = (value.toInt() shr 8 and 0xff).toByte()
    }

    private fun intToByteArray(value: Int): ByteArray {
        return byteArrayOf(
            (value and 0xff).toByte(),
            (value shr 8 and 0xff).toByte(),
            (value shr 16 and 0xff).toByte(),
            (value shr 24 and 0xff).toByte()
        )
    }
}
