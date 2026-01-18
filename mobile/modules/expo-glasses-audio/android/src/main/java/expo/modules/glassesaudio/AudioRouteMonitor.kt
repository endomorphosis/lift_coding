package expo.modules.glassesaudio

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build

/**
 * Monitors Android audio routing state and provides real-time updates.
 * Detects Bluetooth headset/SCO availability, connection state, and device changes.
 */
class AudioRouteMonitor(private val context: Context) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private var routeChangeCallback: AudioManager.AudioDeviceCallback? = null
    private var scoStateReceiver: BroadcastReceiver? = null
    private var isMonitoring = false

    /**
     * Get current audio route information as a formatted string.
     */
    fun currentRouteSummary(): String {
        val outputs = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        val inputs = audioManager.getDevices(AudioManager.GET_DEVICES_INPUTS)

        val inputsDesc = describeDevices(inputs)
        val outputsDesc = describeDevices(outputs)
        
        val mode = getAudioModeName(audioManager.mode)
        val scoStatus = if (audioManager.isBluetoothScoOn) "ON" else "OFF"
        val scoAvailable = if (audioManager.isBluetoothScoAvailableOffCall) "Available" else "Not Available"
        
        return buildString {
            append("📱 Inputs:\n$inputsDesc\n\n")
            append("🔊 Outputs:\n$outputsDesc\n\n")
            append("🎛️ Audio Mode: $mode\n")
            append("📡 Bluetooth SCO: $scoStatus ($scoAvailable)")
        }
    }

    /**
     * Get current audio route information as a structured map for JSON serialization.
     */
    fun getCurrentRoute(): Map<String, Any> {
        val outputs = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        val inputs = audioManager.getDevices(AudioManager.GET_DEVICES_INPUTS)

        return mapOf(
            "inputs" to inputs.map { deviceToMap(it) },
            "outputs" to outputs.map { deviceToMap(it) },
            "audioMode" to audioManager.mode,
            "audioModeName" to getAudioModeName(audioManager.mode),
            "isScoOn" to audioManager.isBluetoothScoOn,
            "isScoAvailable" to audioManager.isBluetoothScoAvailableOffCall,
            "isBluetoothConnected" to isBluetoothDeviceConnected(),
            "timestamp" to System.currentTimeMillis()
        )
    }

    /**
     * Start monitoring audio route changes and SCO state changes.
     * @param callback Function to call when route changes are detected.
     */
    fun startMonitoring(callback: (Map<String, Any>) -> Unit) {
        if (isMonitoring) {
            stopMonitoring()
        }

        isMonitoring = true

        // Register audio device callback (API 23+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            routeChangeCallback = object : AudioManager.AudioDeviceCallback() {
                override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>?) {
                    callback(getCurrentRoute())
                }

                override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>?) {
                    callback(getCurrentRoute())
                }
            }
            audioManager.registerAudioDeviceCallback(routeChangeCallback, null)
        }

        // Register SCO state broadcast receiver
        scoStateReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                when (intent?.action) {
                    AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED -> {
                        val state = intent.getIntExtra(
                            AudioManager.EXTRA_SCO_AUDIO_STATE,
                            AudioManager.SCO_AUDIO_STATE_DISCONNECTED
                        )
                        callback(getCurrentRoute())
                    }
                    AudioManager.ACTION_AUDIO_BECOMING_NOISY -> {
                        callback(getCurrentRoute())
                    }
                }
            }
        }

        val filter = IntentFilter().apply {
            addAction(AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED)
            addAction(AudioManager.ACTION_AUDIO_BECOMING_NOISY)
            addAction(AudioManager.ACTION_HEADSET_PLUG)
        }
        context.registerReceiver(scoStateReceiver, filter)
    }

    /**
     * Stop monitoring audio route changes.
     */
    fun stopMonitoring() {
        if (!isMonitoring) return

        isMonitoring = false

        // Unregister audio device callback
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            routeChangeCallback?.let {
                audioManager.unregisterAudioDeviceCallback(it)
            }
            routeChangeCallback = null
        }

        // Unregister broadcast receiver
        scoStateReceiver?.let {
            try {
                context.unregisterReceiver(it)
            } catch (e: IllegalArgumentException) {
                // Receiver was not registered, ignore
            }
        }
        scoStateReceiver = null
    }

    /**
     * Check if any Bluetooth device is currently connected.
     */
    fun isBluetoothDeviceConnected(): Boolean {
        val devices = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        return devices.any { 
            it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP ||
            it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO
        }
    }

    /**
     * Check if Bluetooth SCO is currently connected.
     */
    fun isScoConnected(): Boolean {
        return audioManager.isBluetoothScoOn
    }

    // Private helper methods

    private fun describeDevices(devices: Array<AudioDeviceInfo>): String {
        if (devices.isEmpty()) return "  None"
        return devices.joinToString("\n") { device ->
            val typeName = getDeviceTypeName(device.type)
            val name = device.productName?.toString()?.takeIf { it.isNotEmpty() } 
                ?: typeName
            val address = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                device.address.takeIf { it.isNotEmpty() }?.let { " [$it]" } ?: ""
            } else {
                ""
            }
            "  • $name$address"
        }
    }

    private fun deviceToMap(device: AudioDeviceInfo): Map<String, Any> {
        val address = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            device.address
        } else {
            "N/A"
        }
        
        return mapOf(
            "id" to device.id,
            "type" to device.type,
            "typeName" to getDeviceTypeName(device.type),
            "productName" to (device.productName?.toString() ?: "Unknown"),
            "address" to address
        )
    }

    private fun getDeviceTypeName(type: Int): String = when (type) {
        AudioDeviceInfo.TYPE_BUILTIN_EARPIECE -> "Built-in Earpiece"
        AudioDeviceInfo.TYPE_BUILTIN_SPEAKER -> "Built-in Speaker"
        AudioDeviceInfo.TYPE_WIRED_HEADSET -> "Wired Headset"
        AudioDeviceInfo.TYPE_WIRED_HEADPHONES -> "Wired Headphones"
        AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "Bluetooth SCO (Headset)"
        AudioDeviceInfo.TYPE_BLUETOOTH_A2DP -> "Bluetooth A2DP"
        AudioDeviceInfo.TYPE_USB_DEVICE -> "USB Device"
        AudioDeviceInfo.TYPE_USB_HEADSET -> "USB Headset"
        AudioDeviceInfo.TYPE_BUILTIN_MIC -> "Built-in Mic"
        AudioDeviceInfo.TYPE_LINE_ANALOG -> "Line Analog"
        AudioDeviceInfo.TYPE_LINE_DIGITAL -> "Line Digital"
        else -> "Unknown (type=$type)"
    }

    private fun getAudioModeName(mode: Int): String = when (mode) {
        AudioManager.MODE_NORMAL -> "Normal"
        AudioManager.MODE_RINGTONE -> "Ringtone"
        AudioManager.MODE_IN_CALL -> "In Call"
        AudioManager.MODE_IN_COMMUNICATION -> "In Communication"
        else -> "Unknown ($mode)"
    }
}
