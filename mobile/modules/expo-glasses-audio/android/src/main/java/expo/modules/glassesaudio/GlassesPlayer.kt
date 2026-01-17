package glasses

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack

class GlassesPlayer {
    private var track: AudioTrack? = null

    fun playPcm16Mono(samples: ShortArray, sampleRate: Int = 16000) {
        stop()

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
        t.play()
        track = t
    }

    fun stop() {
        track?.stop()
        track?.release()
        track = null
    }
}
