package glasses

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder

enum class AudioSource(val value: String) {
    PHONE("phone"),
    GLASSES("glasses"),
    AUTO("auto")
}

class GlassesRecorder {
    private var recorder: AudioRecord? = null

    fun start(audioSource: AudioSource = AudioSource.AUTO): AudioRecord {
        val sampleRate = 16000
        val channel = AudioFormat.CHANNEL_IN_MONO
        val encoding = AudioFormat.ENCODING_PCM_16BIT
        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channel, encoding)

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

        r.startRecording()
        recorder = r
        return r
    }

    fun stop() {
        recorder?.stop()
        recorder?.release()
        recorder = null
    }
}
