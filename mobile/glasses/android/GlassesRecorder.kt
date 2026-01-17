package glasses

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder

class GlassesRecorder {
    private var recorder: AudioRecord? = null

    fun start(): AudioRecord {
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
