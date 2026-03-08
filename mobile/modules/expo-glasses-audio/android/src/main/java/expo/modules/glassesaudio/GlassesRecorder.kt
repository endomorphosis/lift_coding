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
        private const val CHANNELS = 1
        private const val BYTES_PER_SAMPLE = 2
        private const val BITS_PER_SAMPLE = 16
    }

    private var recorder: AudioRecord? = null
    private var recordingThread: Thread? = null
    @Volatile
    private var isRecording = false
    private var outputFile: File? = null
    @Volatile
    private var totalBytesWritten = 0L

    @Synchronized
    fun start(outputFile: File, audioSource: AudioSource = AudioSource.AUTO) {
        if (isRecording || recorder != null) {
            throw IllegalStateException("Recorder is already running")
        }

        val channel = AudioFormat.CHANNEL_IN_MONO
        val encoding = AudioFormat.ENCODING_PCM_16BIT
        val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, channel, encoding)
        val bufferSize = if (minBufferSize > 0) minBufferSize else SAMPLE_RATE * BYTES_PER_SAMPLE

        val androidAudioSource = when (audioSource) {
            AudioSource.PHONE -> MediaRecorder.AudioSource.MIC
            AudioSource.GLASSES -> MediaRecorder.AudioSource.VOICE_COMMUNICATION
            AudioSource.AUTO -> MediaRecorder.AudioSource.VOICE_COMMUNICATION
        }

        val audioRecord = AudioRecord(
            androidAudioSource,
            SAMPLE_RATE,
            channel,
            encoding,
            bufferSize
        )

        if (audioRecord.state != AudioRecord.STATE_INITIALIZED) {
            audioRecord.release()
            throw IllegalStateException("AudioRecord failed to initialize")
        }

        outputFile.parentFile?.mkdirs()
        writeWavHeader(outputFile, SAMPLE_RATE, CHANNELS, BITS_PER_SAMPLE)

        this.outputFile = outputFile
        totalBytesWritten = 0L
        recorder = audioRecord
        isRecording = true

        audioRecord.startRecording()
        recordingThread = Thread({
            writeAudioData(audioRecord, outputFile, bufferSize)
        }, "GlassesRecorderThread").also { it.start() }
    }

    @Synchronized
    fun stop(): RecordingResult? {
        val file = outputFile

        isRecording = false

        try {
            recorder?.stop()
        } catch (e: IllegalStateException) {
            Log.w(TAG, "AudioRecord.stop() failed: ${e.message}")
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

        if (file != null && file.exists()) {
            try {
                updateWavHeader(file)
            } catch (e: Exception) {
                Log.e(TAG, "Error updating WAV header: ${e.message}", e)
            }

            val durationSeconds =
                (totalBytesWritten / (SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE)).toInt()
            val sizeBytes = file.length()
            outputFile = null
            totalBytesWritten = 0L
            return RecordingResult(file, durationSeconds, sizeBytes)
        }

        outputFile = null
        totalBytesWritten = 0L
        return null
    }

    private fun writeAudioData(audioRecord: AudioRecord, file: File, bufferSize: Int) {
        val buffer = ByteArray(bufferSize)

        try {
            FileOutputStream(file, true).use { outputStream ->
                while (isRecording && !Thread.currentThread().isInterrupted) {
                    val bytesRead = audioRecord.read(buffer, 0, buffer.size)
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

    private fun writeWavHeader(file: File, sampleRate: Int, channels: Int, bitsPerSample: Int) {
        FileOutputStream(file).use { outputStream ->
            val header = ByteBuffer.allocate(WAV_HEADER_SIZE).order(ByteOrder.LITTLE_ENDIAN)
            header.put("RIFF".toByteArray())
            header.putInt(36)
            header.put("WAVE".toByteArray())
            header.put("fmt ".toByteArray())
            header.putInt(16)
            header.putShort(1.toShort())
            header.putShort(channels.toShort())
            header.putInt(sampleRate)
            header.putInt(sampleRate * channels * bitsPerSample / 8)
            header.putShort((channels * bitsPerSample / 8).toShort())
            header.putShort(bitsPerSample.toShort())
            header.put("data".toByteArray())
            header.putInt(0)
            outputStream.write(header.array())
        }
    }

    private fun updateWavHeader(file: File) {
        RandomAccessFile(file, "rw").use { randomAccessFile ->
            val fileSize = randomAccessFile.length()
            val dataSize = fileSize - WAV_HEADER_SIZE

            val fileSizeBuffer = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN)
            fileSizeBuffer.putInt((fileSize - 8).toInt())
            randomAccessFile.seek(4)
            randomAccessFile.write(fileSizeBuffer.array())

            val dataSizeBuffer = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN)
            dataSizeBuffer.putInt(dataSize.toInt())
            randomAccessFile.seek(40)
            randomAccessFile.write(dataSizeBuffer.array())
        }
    }
}
