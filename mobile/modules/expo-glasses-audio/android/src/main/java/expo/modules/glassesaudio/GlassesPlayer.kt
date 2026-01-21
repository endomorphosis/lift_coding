package expo.modules.glassesaudio

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import java.io.File
import java.io.FileInputStream
import java.io.RandomAccessFile
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
            try {
                track?.stop()
            } catch (e: Exception) {
                Log.w(TAG, "AudioTrack.stop() failed: ${e.message}")
            }
            try {
                track?.release()
            } catch (e: Exception) {
                Log.w(TAG, "AudioTrack.release() failed: ${e.message}")
            }
            track = null
            onPlaybackComplete = null
        }
    }

    private fun parseWavHeader(file: File): WavInfo {
        RandomAccessFile(file, "r").use { raf ->
            fun readFourCC(): String {
                val b = ByteArray(4)
                raf.readFully(b)
                return String(b)
            }

            fun readLEInt(): Int {
                val b = ByteArray(4)
                raf.readFully(b)
                return ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).int
            }

            fun readLEShort(): Short {
                val b = ByteArray(2)
                raf.readFully(b)
                return ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).short
            }

            if (raf.length() < 12) {
                throw IllegalArgumentException("Not a valid WAV file: file too small")
            }

            val riff = readFourCC()
            if (riff != "RIFF") {
                throw IllegalArgumentException("Not a valid WAV file: missing RIFF header")
            }

            readLEInt() // file size - 8

            val wave = readFourCC()
            if (wave != "WAVE") {
                throw IllegalArgumentException("Not a valid WAV file: missing WAVE format")
            }

            var sampleRate: Int? = null
            var channels: Int? = null
            var bitsPerSample: Int? = null
            var dataOffset: Int? = null
            var dataSize: Int? = null

            while (raf.filePointer + 8 <= raf.length()) {
                val chunkId = readFourCC()
                val chunkSize = readLEInt()
                val chunkDataStart = raf.filePointer

                // Validate chunk size to prevent issues with malformed WAV files
                if (chunkSize < 0) {
                    throw IllegalArgumentException("Invalid chunk size: $chunkSize for chunk $chunkId")
                }

                when (chunkId) {
                    "fmt " -> {
                        if (chunkSize < 16) {
                            throw IllegalArgumentException("Invalid WAV fmt chunk size: $chunkSize")
                        }
                        val audioFormat = readLEShort().toInt()
                        if (audioFormat != 1) {
                            throw IllegalArgumentException("Only PCM WAV is supported (format=$audioFormat)")
                        }

                        channels = readLEShort().toInt()
                        sampleRate = readLEInt()
                        readLEInt() // byte rate
                        readLEShort() // block align
                        bitsPerSample = readLEShort().toInt()
                    }
                    "data" -> {
                        dataOffset = raf.filePointer.toInt()
                        dataSize = chunkSize
                        break
                    }
                }

                // Move to end of chunk (chunks are word-aligned; pad to even)
                // This applies to all chunks except "data" which breaks out of the loop
                if (chunkId != "data") {
                    val chunkEnd = chunkDataStart + chunkSize
                    raf.seek(chunkEnd + (chunkSize % 2))
                }
            }

            val finalSampleRate = sampleRate ?: throw IllegalArgumentException("WAV missing fmt chunk")
            val finalChannels = channels ?: throw IllegalArgumentException("WAV missing fmt chunk")
            val finalBits = bitsPerSample ?: throw IllegalArgumentException("WAV missing fmt chunk")
            val finalOffset = dataOffset ?: throw IllegalArgumentException("WAV missing data chunk")
            val finalSize = dataSize ?: throw IllegalArgumentException("WAV missing data chunk")

            return WavInfo(
                sampleRate = finalSampleRate,
                channels = finalChannels,
                bitsPerSample = finalBits,
                dataOffset = finalOffset,
                dataSize = finalSize,
            )
        }
    }

    private fun readPcmData(file: File, wavInfo: WavInfo): ShortArray {
        FileInputStream(file).use { inputStream ->
            inputStream.skip(wavInfo.dataOffset.toLong())
            
            val pcmBytes = ByteArray(wavInfo.dataSize)
            val totalRead = inputStream.read(pcmBytes)
            
            if (totalRead == -1) {
                throw IllegalArgumentException("WAV file contains no PCM data - reached end of stream")
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
            
            // At least 2 bytes are required for a single 16-bit PCM sample
            if (validBytes < 2) {
                throw IllegalArgumentException(
                    "WAV file too small to contain valid 16-bit PCM data: read $totalRead byte(s)"
                )
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
