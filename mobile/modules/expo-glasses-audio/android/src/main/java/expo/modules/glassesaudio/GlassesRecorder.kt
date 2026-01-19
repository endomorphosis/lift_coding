package expo.modules.glassesaudio

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

class GlassesRecorder {
    companion object {
        private const val WAV_HEADER_SIZE = 44
    }
    
    private var recorder: AudioRecord? = null
    private var recordingThread: Thread? = null
    @Volatile
    private var isRecording = false
    private var outputFile: File? = null
    private var totalBytesWritten = 0L

    fun start(outputFile: File): AudioRecord {
        this.outputFile = outputFile
        this.totalBytesWritten = 0L
        
        val sampleRate = 16000
        val channel = AudioFormat.CHANNEL_IN_MONO
        val encoding = AudioFormat.ENCODING_PCM_16BIT
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channel, encoding)

        val r = AudioRecord(
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            sampleRate,
            channel,
            encoding,
            bufferSize
        )

        // Write initial WAV header (will be updated with correct sizes on stop)
        writeWavHeader(outputFile, sampleRate, 1, 16)
        
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
        val outputStream = FileOutputStream(file, true)
        
        try {
            while (isRecording) {
                val bytesRead = recorder.read(buffer, 0, buffer.size)
                if (bytesRead > 0) {
                    outputStream.write(buffer, 0, bytesRead)
                    totalBytesWritten += bytesRead
                }
            }
        } finally {
            outputStream.close()
        }
    }

    fun stop() {
        isRecording = false
        recordingThread?.join(1000)
        recordingThread = null
        
        recorder?.stop()
        recorder?.release()
        recorder = null
        
        // Update WAV header with actual data size
        outputFile?.let { file ->
            if (file.exists()) {
                updateWavHeader(file)
            }
        }
        outputFile = null
    }

    private fun writeWavHeader(file: File, sampleRate: Int, channels: Int, bitsPerSample: Int) {
        val outputStream = FileOutputStream(file)
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
        outputStream.close()
    }

    private fun updateWavHeader(file: File) {
        val randomAccessFile = RandomAccessFile(file, "rw")
        val fileSize = randomAccessFile.length()
        val dataSize = fileSize - WAV_HEADER_SIZE
        
        // Update RIFF chunk size (file size - 8)
        randomAccessFile.seek(4)
        randomAccessFile.write(intToByteArray((fileSize - 8).toInt()))
        
        // Update data chunk size
        randomAccessFile.seek(40)
        randomAccessFile.write(intToByteArray(dataSize.toInt()))
        
        randomAccessFile.close()
    }

    private fun intToByteArray(value: Int): ByteArray {
        return byteArrayOf(
            (value and 0xFF).toByte(),
            ((value shr 8) and 0xFF).toByte(),
            ((value shr 16) and 0xFF).toByte(),
            ((value shr 24) and 0xFF).toByte()
        )
    }
}
