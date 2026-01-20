package expo.modules.glassesaudio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import java.io.File
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

data class WavInfo(
    val sampleRate: Int,
    val channels: Int,
    val bitsPerSample: Int,
    val dataOffset: Int,
    val dataSize: Int
)

class GlassesPlayer {
    companion object {
        private const val TAG = "GlassesPlayer"
        private const val WAV_HEADER_SIZE = 44
    }
    
    private var track: AudioTrack? = null
    @Volatile
    private var isPlaying = false
    private var onPlaybackComplete: (() -> Unit)? = null
    private val playbackLock = Object()

    @Synchronized
    fun playWavFile(file: File, onComplete: (() -> Unit)? = null): WavInfo {
        stop()
        
        val wavInfo = parseWavHeader(file)
        this.onPlaybackComplete = onComplete
        
        // Read PCM data from file
        val pcmData = readPcmData(file, wavInfo)
        
        // Play the audio
        if (wavInfo.channels == 1) {
            playPcm16Mono(pcmData, wavInfo.sampleRate, onComplete)
        } else {
            throw IllegalArgumentException("Only mono audio is supported")
        }
        
        return wavInfo
    }

    @Synchronized
    fun playPcm16Mono(samples: ShortArray, sampleRate: Int = 16000, onComplete: (() -> Unit)? = null) {
        stop()
        
        // Guard against empty sample arrays
        if (samples.isEmpty()) {
            Log.w(TAG, "Cannot play empty sample array")
            onComplete?.invoke()
            return
        }
        
        this.onPlaybackComplete = onComplete

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
        track = t
        isPlaying = true
        
        // Use notification marker for completion detection
        t.setNotificationMarkerPosition(samples.size)
        t.setPlaybackPositionUpdateListener(object : AudioTrack.OnPlaybackPositionUpdateListener {
            override fun onMarkerReached(track: AudioTrack) {
                // Playback has reached the end of the buffer
                synchronized(playbackLock) {
                    if (isPlaying) {
                        isPlaying = false
                        onPlaybackComplete?.invoke()
                    }
                }
            }

            override fun onPeriodicNotification(track: AudioTrack) {
                // Not used
            }
        })
        
        try {
            t.play()
        } catch (e: Exception) {
            Log.e(TAG, "Playback failed: ${e.message}", e)
            isPlaying = false
            throw e
        }
    }

    @Synchronized
    fun stop() {
        synchronized(playbackLock) {
            isPlaying = false
            track?.stop()
            track?.release()
            track = null
            onPlaybackComplete = null
        }
    }

    private fun parseWavHeader(file: File): WavInfo {
        FileInputStream(file).use { inputStream ->
            val header = ByteArray(WAV_HEADER_SIZE)
            val bytesRead = inputStream.read(header)
            if (bytesRead < WAV_HEADER_SIZE) {
                throw IllegalArgumentException("Not a valid WAV file: file too small")
            }
            
            val buffer = ByteBuffer.wrap(header)
            buffer.order(ByteOrder.LITTLE_ENDIAN)
            
            // Verify RIFF header
            val riff = ByteArray(4)
            buffer.get(riff)
            if (String(riff) != "RIFF") {
                throw IllegalArgumentException("Not a valid WAV file: missing RIFF header")
            }
            
            buffer.getInt() // File size - 8
            
            // Verify WAVE format
            val wave = ByteArray(4)
            buffer.get(wave)
            if (String(wave) != "WAVE") {
                throw IllegalArgumentException("Not a valid WAV file: missing WAVE format")
            }
            
            // Read fmt chunk
            val fmt = ByteArray(4)
            buffer.get(fmt)
            if (String(fmt) != "fmt ") {
                throw IllegalArgumentException("Not a valid WAV file: missing fmt chunk")
            }
            
            val fmtSize = buffer.getInt()
            val audioFormat = buffer.getShort()
            if (audioFormat.toInt() != 1) {
                throw IllegalArgumentException("Only PCM format is supported")
            }
            
            val channels = buffer.getShort().toInt()
            val sampleRate = buffer.getInt()
            buffer.getInt() // Byte rate
            buffer.getShort() // Block align
            val bitsPerSample = buffer.getShort().toInt()
            
            // Read data chunk
            val data = ByteArray(4)
            buffer.get(data)
            if (String(data) != "data") {
                throw IllegalArgumentException("Not a valid WAV file: missing data chunk")
            }
            
            val dataSize = buffer.getInt()
            
            return WavInfo(
                sampleRate = sampleRate,
                channels = channels,
                bitsPerSample = bitsPerSample,
                dataOffset = WAV_HEADER_SIZE,
                dataSize = dataSize
            )
        }
    }

    private fun readPcmData(file: File, wavInfo: WavInfo): ShortArray {
        FileInputStream(file).use { inputStream ->
            inputStream.skip(wavInfo.dataOffset.toLong())
            
            val pcmBytes = ByteArray(wavInfo.dataSize)
            val totalRead = inputStream.read(pcmBytes)
            
            if (totalRead == -1) {
                throw IllegalArgumentException("No PCM data could be read from WAV file")
            }
            if (totalRead < wavInfo.dataSize) {
                Log.w(TAG, "Expected ${wavInfo.dataSize} bytes but read $totalRead bytes")
            }
            
            // Ensure we have an even number of bytes for 16-bit PCM data
            val validBytes = if (totalRead % 2 != 0) {
                Log.w(TAG, "Odd number of bytes read ($totalRead), truncating to ${totalRead - 1}")
                totalRead - 1
            } else {
                totalRead
            }
            
            // Convert bytes to shorts (PCM 16-bit), based on actual bytes read
            val pcmShorts = ShortArray(validBytes / 2)
            val buffer = ByteBuffer.wrap(pcmBytes, 0, validBytes)
            buffer.order(ByteOrder.LITTLE_ENDIAN)
            
            for (i in pcmShorts.indices) {
                pcmShorts[i] = buffer.getShort()
            }
            
            return pcmShorts
        }
    }
}
