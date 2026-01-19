package glasses

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
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
    private var track: AudioTrack? = null
    private var playbackThread: Thread? = null
    private var isPlaying = false
    private var onPlaybackComplete: (() -> Unit)? = null

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

    fun playPcm16Mono(samples: ShortArray, sampleRate: Int = 16000, onComplete: (() -> Unit)? = null) {
        stop()
        
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
        
        // Start playback in background thread
        playbackThread = Thread {
            t.play()
            
            // Wait for playback to complete
            while (isPlaying && t.playState == AudioTrack.PLAYSTATE_PLAYING) {
                Thread.sleep(100)
            }
            
            // Check if we reached the end
            if (isPlaying && t.playbackHeadPosition >= samples.size) {
                isPlaying = false
                onPlaybackComplete?.invoke()
            }
        }
        playbackThread?.start()
    }

    fun stop() {
        isPlaying = false
        playbackThread?.interrupt()
        playbackThread = null
        track?.stop()
        track?.release()
        track = null
        onPlaybackComplete = null
    }

    private fun parseWavHeader(file: File): WavInfo {
        val inputStream = FileInputStream(file)
        val header = ByteArray(44)
        inputStream.read(header)
        inputStream.close()
        
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
            dataOffset = 44,
            dataSize = dataSize
        )
    }

    private fun readPcmData(file: File, wavInfo: WavInfo): ShortArray {
        val inputStream = FileInputStream(file)
        inputStream.skip(wavInfo.dataOffset.toLong())
        
        val pcmBytes = ByteArray(wavInfo.dataSize)
        inputStream.read(pcmBytes)
        inputStream.close()
        
        // Convert bytes to shorts (PCM 16-bit)
        val pcmShorts = ShortArray(pcmBytes.size / 2)
        val buffer = ByteBuffer.wrap(pcmBytes)
        buffer.order(ByteOrder.LITTLE_ENDIAN)
        
        for (i in pcmShorts.indices) {
            pcmShorts[i] = buffer.getShort()
        }
        
        return pcmShorts
    }
}
