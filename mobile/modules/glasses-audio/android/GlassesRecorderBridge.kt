package com.glassesaudio

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Handler
import android.os.Looper
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

class GlassesRecorderBridge(private val context: Context) {
    private var recorder: AudioRecord? = null
    private var isRecording = false
    private var recordingThread: Thread? = null
    
    fun startRecording(durationSeconds: Int, callback: (File?, Exception?) -> Unit) {
        try {
            val sampleRate = 16000
            val channel = AudioFormat.CHANNEL_IN_MONO
            val encoding = AudioFormat.ENCODING_PCM_16BIT
            val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channel, encoding)
            
            val audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                sampleRate,
                channel,
                encoding,
                bufferSize
            )
            
            // Create output file
            val audioDir = File(context.filesDir, "audio_diagnostics")
            audioDir.mkdirs()
            val timestamp = System.currentTimeMillis() / 1000
            val outputFile = File(audioDir, "glasses_$timestamp.wav")
            
            recorder = audioRecord
            isRecording = true
            audioRecord.startRecording()
            
            // Record in background thread
            recordingThread = Thread {
                try {
                    val buffer = ByteArray(bufferSize)
                    val fileOutputStream = FileOutputStream(outputFile)
                    
                    // Write WAV header (will update later with actual size)
                    writeWavHeader(fileOutputStream, sampleRate, 1, 16, 0)
                    
                    val startTime = System.currentTimeMillis()
                    val durationMs = durationSeconds * 1000L
                    var totalBytes = 0
                    
                    while (isRecording && (System.currentTimeMillis() - startTime) < durationMs) {
                        val bytesRead = audioRecord.read(buffer, 0, buffer.size)
                        if (bytesRead > 0) {
                            fileOutputStream.write(buffer, 0, bytesRead)
                            totalBytes += bytesRead
                        }
                    }
                    
                    // Stop recording
                    audioRecord.stop()
                    audioRecord.release()
                    
                    // Update WAV header with actual size
                    fileOutputStream.close()
                    updateWavHeader(outputFile, totalBytes)
                    
                    // Call callback on main thread
                    Handler(Looper.getMainLooper()).post {
                        callback(outputFile, null)
                    }
                } catch (e: Exception) {
                    Handler(Looper.getMainLooper()).post {
                        callback(null, e)
                    }
                } finally {
                    isRecording = false
                    recorder = null
                }
            }
            recordingThread?.start()
            
        } catch (e: Exception) {
            callback(null, e)
        }
    }
    
    fun stopRecording() {
        isRecording = false
        recorder?.stop()
        recorder?.release()
        recorder = null
    }
    
    private fun writeWavHeader(out: FileOutputStream, sampleRate: Int, channels: Int, bitDepth: Int, dataSize: Int) {
        val header = ByteArray(44)
        val buffer = ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN)
        
        // RIFF header
        buffer.put("RIFF".toByteArray())
        buffer.putInt(36 + dataSize) // File size - 8
        buffer.put("WAVE".toByteArray())
        
        // fmt chunk
        buffer.put("fmt ".toByteArray())
        buffer.putInt(16) // fmt chunk size
        buffer.putShort(1) // Audio format (1 = PCM)
        buffer.putShort(channels.toShort())
        buffer.putInt(sampleRate)
        buffer.putInt(sampleRate * channels * bitDepth / 8) // Byte rate
        buffer.putShort((channels * bitDepth / 8).toShort()) // Block align
        buffer.putShort(bitDepth.toShort())
        
        // data chunk
        buffer.put("data".toByteArray())
        buffer.putInt(dataSize)
        
        out.write(header)
    }
    
    private fun updateWavHeader(file: File, dataSize: Int) {
        val randomAccessFile = java.io.RandomAccessFile(file, "rw")
        randomAccessFile.seek(4)
        randomAccessFile.write(intToByteArrayLE(36 + dataSize))
        randomAccessFile.seek(40)
        randomAccessFile.write(intToByteArrayLE(dataSize))
        randomAccessFile.close()
    }
    
    private fun intToByteArrayLE(value: Int): ByteArray {
        return byteArrayOf(
            (value and 0xFF).toByte(),
            ((value shr 8) and 0xFF).toByte(),
            ((value shr 16) and 0xFF).toByte(),
            ((value shr 24) and 0xFF).toByte()
        )
    }
}
