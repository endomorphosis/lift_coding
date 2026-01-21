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
    val sizeBytes: Long,
    val durationSeconds: Int,
)

class GlassesRecorder {
    companion object {
        private const val TAG = "GlassesRecorder"
        private const val WAV_HEADER_SIZE = 44
        private const val RECORDING_THREAD_JOIN_TIMEOUT_MS = 3000L
    }
    
    private var recorder: AudioRecord? = null
    private var recordingThread: Thread? = null
    @Volatile
    private var isRecording = false
    private var outputFile: File? = null
    private var totalBytesWritten = 0L
    private var startedAtMs: Long? = null

    @Synchronized
    fun start(outputFile: File, audioSource: AudioSource = AudioSource.AUTO) {
        if (isRecording || recorder != null) {
            throw IllegalStateException("Recorder is already running")
        }

        val sampleRate = 16000
        val channel = AudioFormat.CHANNEL_IN_MONO
        val encoding = AudioFormat.ENCODING_PCM_16BIT
        val minBufferSize = AudioRecord.getMinBufferSize(sampleRate, channel, encoding)
        if (minBufferSize == AudioRecord.ERROR || minBufferSize == AudioRecord.ERROR_BAD_VALUE) {
            throw IllegalStateException("AudioRecord.getMinBufferSize failed: $minBufferSize")
        }

        val bufferSize = minBufferSize.coerceAtLeast(2048)

        outputFile.parentFile?.mkdirs()
        this.outputFile = outputFile
        totalBytesWritten = 0L
        startedAtMs = System.currentTimeMillis()

        // Select audio source based on preference
        val androidAudioSource = when (audioSource) {
            AudioSource.PHONE -> MediaRecorder.AudioSource.MIC // Built-in mic
            AudioSource.GLASSES -> MediaRecorder.AudioSource.VOICE_COMMUNICATION // Bluetooth/Headset mic
            AudioSource.AUTO -> MediaRecorder.AudioSource.VOICE_COMMUNICATION // Default to voice comm
        }

        val r = AudioRecord(
            androidAudioSource,
            sampleRate,
            channel,
            encoding,
            bufferSize
        )

        if (r.state != AudioRecord.STATE_INITIALIZED) {
            r.release()
            throw IllegalStateException("AudioRecord failed to initialize (state=${r.state})")
        }

        // Write initial WAV header (will be updated with correct sizes on stop)
        writeWavHeader(outputFile, sampleRate, 1, 16)
        
        r.startRecording()
        recorder = r
        isRecording = true
        
        // Start background thread to read and write audio data
        recordingThread = Thread {
            writeAudioData(r, outputFile, bufferSize)
        }.apply { name = "GlassesRecorderThread" }
        recordingThread?.start()
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

    @Synchronized
    fun stop(): RecordingResult? {
        val file = outputFile

        if (!isRecording && recorder == null) {
            return file?.takeIf { it.exists() }?.let {
                RecordingResult(
                    file = it,
                    sizeBytes = it.length(),
                    durationSeconds = 0,
                )
            }
        }

        // Signal the writer loop to finish, then stop AudioRecord to unblock read().
        isRecording = false
        try {
            recorder?.stop()
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping AudioRecord: ${e.message}")
        }

        recordingThread?.join(RECORDING_THREAD_JOIN_TIMEOUT_MS)
        if (recordingThread?.isAlive == true) {
            recordingThread?.interrupt()
        }
        recordingThread = null

        try {
            recorder?.release()
        } catch (e: Exception) {
            Log.w(TAG, "Error releasing AudioRecord: ${e.message}")
        }
        recorder = null

        // Update WAV header with actual data size
        if (file != null && file.exists()) {
            try {
                updateWavHeader(file)
            } catch (e: Exception) {
                Log.e(TAG, "Error updating WAV header: ${e.message}", e)
            }
        }

        val durationSeconds = startedAtMs?.let { startMs ->
            ((System.currentTimeMillis() - startMs) / 1000L).toInt().coerceAtLeast(0)
        } ?: 0

        startedAtMs = null
        outputFile = null

        return file?.takeIf { it.exists() }?.let {
            RecordingResult(
                file = it,
                sizeBytes = it.length(),
                durationSeconds = durationSeconds,
            )
        }
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
