package glasses

import android.content.Context
import android.media.AudioDeviceInfo
import android.media.AudioManager

class AudioRouteMonitor(private val context: Context) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    fun currentRouteSummary(): String {
        val outputs = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        val inputs = audioManager.getDevices(AudioManager.GET_DEVICES_INPUTS)

        fun describe(devices: Array<AudioDeviceInfo>): String {
            if (devices.isEmpty()) return "None"
            return devices.joinToString("\n") { d ->
                val type = d.type
                val name = d.productName?.toString() ?: "(unknown)"
                "$name (type=$type)"
            }
        }

        return "Inputs:\n${describe(inputs)}\n\nOutputs:\n${describe(outputs)}\n\nMode=${audioManager.mode} SCO=${audioManager.isBluetoothScoOn}"
    }
}
