package expo.modules.glassesaudio

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

enum class AudioSource(val value: String) {
    PHONE("phone"),
    GLASSES("glasses"),
    AUTO("auto")
}

data class RecordingResult(
    val file: File,
    val durationSeconds: Int,
    val sizeBytes: Long
)

class GlassesRecorder {
    companion object {
        private const val TAG = "GlassesRecorder"
        private const val WAV_HEADER_SIZE = 44
        private const val RECORDING_THREAD_JOIN_TIMEOUT_MS = 3000L
        private const val SAMPLE_RATE = 16000
        private const val CHANNELS = 1 // MONO
        private const val BYTES_PER_SAMPLE = 2 // 16-bit = 2 bytes per sample
    }
    
    private var recorder: AudioRecord? = null
    private var recordingThread: Thread? = null
    @Volatile
    private var isRecording = false
    private var outputFile: File? = null
    private var totalBytesWritten = 0L
    private var recordingStartedAtMs: Long = 0L
    private var sampleRate: Int = 0
    private var channels: Int = 0
    private var bytesPerSample: Int = 0

    fun start(outputFile: File, audioSource: AudioSource = AudioSource.AUTO): AudioRecord {
        val channel = AudioFormat.CHANNEL_IN_MONO
        val encoding = AudioFormat.ENCODING_PCM_16BIT
        val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, channel, encoding)
        val bufferSize = if (minBufferSize > 0) minBufferSize else (SAMPLE_RATE * 2)

        // Select audio source based on preference
        val androidAudioSource = when (audioSource) {
            AudioSource.PHONE -> MediaRecorder.AudioSource.MIC // Built-in mic
            AudioSource.GLASSES -> MediaRecorder.AudioSource.VOICE_COMMUNICATION // Bluetooth/Headset mic
            AudioSource.AUTO -> MediaRecorder.AudioSource.VOICE_COMMUNICATION // Default to voice comm
        }

        val r = AudioRecord(
            androidAudioSource,
            SAMPLE_RATE,
            channel,
            encoding,
            bufferSize
        )

        // Ensure destination exists
        outputFile.parentFile?.mkdirs()
        this.outputFile = outputFile
        totalBytesWritten = 0L
        recordingStartedAtMs = System.currentTimeMillis()
        
        // Store audio format parameters for duration calculation
        this.sampleRate = SAMPLE_RATE
        this.channels = CHANNELS
        this.bytesPerSample = BYTES_PER_SAMPLE

        // Write initial WAV header (will be updated with correct sizes on stop)
        writeWavHeader(outputFile, SAMPLE_RATE, CHANNELS, BYTES_PER_SAMPLE * 8)
        
        r.startRecording()
        recorder = r
        isRecording = true
        
        // Start background thread to read and write audio data
        recordingThread = Thread {
            writeAudioData(r, outputFile, bufferSize)
        }
        recordingThread?.start()
        
        return r
    }

    private fun writeAudioData(recorder: AudioRecord, file: File, bufferSize: Int) {
        val buffer = ByteArray(bufferSize)
        
        try {
            FileOutputStream(file, true).use { outputStream ->
                while (isRecording) {
                    val bytesRead = recorder.read(buffer, 0, buffer.size)
                    
                    // Handle error codes from AudioRecord.read()
                    when {
                        bytesRead > 0 -> {
                            outputStream.write(buffer, 0, bytesRead)
                            totalBytesWritten += bytesRead
                        }
                        bytesRead == AudioRecord.ERROR_INVALID_OPERATION -> {
                            Log.e(TAG, "AudioRecord.read() returned ERROR_INVALID_OPERATION")
                            break
                        }
                        bytesRead == AudioRecord.ERROR_BAD_VALUE -> {
                            Log.e(TAG, "AudioRecord.read() returned ERROR_BAD_VALUE")
                            break
                        }
                        bytesRead == AudioRecord.ERROR_DEAD_OBJECT -> {
                            Log.e(TAG, "AudioRecord.read() returned ERROR_DEAD_OBJECT")
                            break
                        }
                        bytesRead == AudioRecord.ERROR -> {
                            Log.e(TAG, "AudioRecord.read() returned ERROR")
                            break
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error writing audio data: ${e.message}", e)
        }
    }

    fun stop(): RecordingResult? {
        val file = outputFile

        // Stop the recorder first to unblock the read() call
        try {
            recorder?.stop()
        } catch (e: IllegalStateException) {
            Log.w(TAG, "AudioRecord.stop() failed: ${e.message}")
        }
        
        // Then signal the thread to finish
        isRecording = false
        recordingThread?.join(RECORDING_THREAD_JOIN_TIMEOUT_MS)
        recordingThread = null
        
        recorder?.release()
        recorder = null
        
        // Update WAV header with actual data size
        if (file != null && file.exists()) {
            try {
                updateWavHeader(file)
            } catch (e: Exception) {
                Log.e(TAG, "Error updating WAV header: ${e.message}", e)
            }

            // Calculate duration based on actual audio data written
            // duration = totalBytesWritten / (sampleRate * channels * bytesPerSample)
            val durationSeconds = if (sampleRate > 0 && channels > 0 && bytesPerSample > 0) {
                kotlin.math.max(
                    0,
                    (totalBytesWritten / (sampleRate * channels * bytesPerSample)).toInt()
                )
            } else {
                // Fallback to wall-clock time if format parameters are not available
                kotlin.math.max(
                    0,
                    ((System.currentTimeMillis() - recordingStartedAtMs) / 1000L).toInt()
                )
            }
            val sizeBytes = file.length()

            outputFile = null
            recordingStartedAtMs = 0L
            sampleRate = 0
            channels = 0
            bytesPerSample = 0
            return RecordingResult(file = file, durationSeconds = durationSeconds, sizeBytes = sizeBytes)
        }

        outputFile = null
        recordingStartedAtMs = 0L
        sampleRate = 0
        channels = 0
        bytesPerSample = 0
        return null
    }

    private fun writeWavHeader(file: File, sampleRate: Int, channels: Int, bitsPerSample: Int) {
        FileOutputStream(file).use { outputStream ->
            val header = ByteBuffer.allocate(WAV_HEADER_SIZE)
            header.order(ByteOrder.LITTLE_ENDIAN)
            
            // RIFF header
            header.put("RIFF".toByteArray())
            header.putInt(36) // Will be updated later
            header.put("WAVE".toByteArray())
            
            // fmt chunk
            header.put("fmt ".toByteArray())
            header.putInt(16) // Chunk size
            header.putShort(1.toShort()) // Audio format (PCM)
            header.putShort(channels.toShort())
            header.putInt(sampleRate)
            header.putInt(sampleRate * channels * bitsPerSample / 8) // Byte rate
            header.putShort((channels * bitsPerSample / 8).toShort()) // Block align
            header.putShort(bitsPerSample.toShort())
            
            // data chunk
            header.put("data".toByteArray())
            header.putInt(0) // Will be updated later
            
            outputStream.write(header.array())
        }
    }

    private fun updateWavHeader(file: File) {
        RandomAccessFile(file, "rw").use { randomAccessFile ->
            val fileSize = randomAccessFile.length()
            val dataSize = fileSize - WAV_HEADER_SIZE
            
            // Update RIFF chunk size (file size - 8)
            randomAccessFile.seek(4)
            val fileSizeBuffer = ByteBuffer.allocate(4)
            fileSizeBuffer.order(ByteOrder.LITTLE_ENDIAN)
            fileSizeBuffer.putInt((fileSize - 8).toInt())
            randomAccessFile.write(fileSizeBuffer.array())
            
            // Update data chunk size
            randomAccessFile.seek(40)
            val dataSizeBuffer = ByteBuffer.allocate(4)
            dataSizeBuffer.order(ByteOrder.LITTLE_ENDIAN)
            dataSizeBuffer.putInt(dataSize.toInt())
            randomAccessFile.write(dataSizeBuffer.array())
        }
    }
}
