package com.glassesaudio

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.os.Handler
import android.os.Looper
import java.io.File
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

class GlassesPlayerBridge(private val context: Context) {
    private var track: AudioTrack? = null
    private var playbackThread: Thread? = null
    private var isPlaying = false
    
    fun playAudio(file: File, callback: (Exception?) -> Unit) {
        try {
            stop()
            
            // Read WAV file
            val fileInputStream = FileInputStream(file)
            
            // Skip WAV header (44 bytes)
            val header = ByteArray(44)
            fileInputStream.read(header)
            
            // Parse WAV header to get sample rate
            val sampleRate = ByteBuffer.wrap(header, 24, 4).order(ByteOrder.LITTLE_ENDIAN).int
            
            // Read audio data
            val audioData = fileInputStream.readBytes()
            fileInputStream.close()
            
            // Convert bytes to shorts
            val audioBuffer = ByteBuffer.wrap(audioData).order(ByteOrder.LITTLE_ENDIAN)
            val samples = ShortArray(audioData.size / 2)
            audioBuffer.asShortBuffer().get(samples)
            
            // Create AudioTrack
            val bufferSize = samples.size * 2
            val audioTrack = AudioTrack(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build(),
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(sampleRate)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build(),
                bufferSize,
                AudioTrack.MODE_STATIC,
                AudioTrack.AUDIO_SESSION_ID_GENERATE
            )
            
            audioTrack.write(samples, 0, samples.size)
            track = audioTrack
            isPlaying = true
            
            // Play in background thread
            playbackThread = Thread {
                audioTrack.play()
                
                // Wait for playback to complete
                while (isPlaying && audioTrack.playState == AudioTrack.PLAYSTATE_PLAYING) {
                    Thread.sleep(100)
                }
                
                // Call callback on main thread
                Handler(Looper.getMainLooper()).post {
                    callback(null)
                }
                
                isPlaying = false
            }
            playbackThread?.start()
            
        } catch (e: Exception) {
            callback(e)
        }
    }
    
    fun stop() {
        isPlaying = false
        track?.stop()
        track?.release()
        track = null
    }
}
