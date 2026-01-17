// Android Kotlin: Push Notification Receive Handler with TTS Playback
//
// This example demonstrates how to handle incoming FCM push notifications
// and play the notification message using TTS audio from the backend.
//
// Usage:
// 1. Add to your Android app as a service
// 2. Register service in AndroidManifest.xml
// 3. Ensure INTERNET permission is granted

package com.example.handsfree

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream

class MyFirebaseMessagingService : FirebaseMessagingService() {
    private val backendURL = "http://localhost:8080" // Change to production URL
    private val userID = "00000000-0000-0000-0000-000000000001" // Get from auth
    private val httpClient = OkHttpClient()
    private var mediaPlayer: MediaPlayer? = null
    
    companion object {
        private const val TAG = "FCMService"
        private const val CHANNEL_ID = "handsfree_notifications"
        private const val CHANNEL_NAME = "HandsFree Dev Notifications"
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }
    
    // MARK: - Notification Channel
    
    /**
     * Create notification channel (Android 8.0+)
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications from HandsFree Dev Companion"
                enableVibration(true)
                enableLights(true)
            }
            
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    // MARK: - Message Handling
    
    /**
     * Handle incoming FCM message
     */
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        
        Log.d(TAG, "Message received from: ${remoteMessage.from}")
        
        // Handle notification payload
        remoteMessage.notification?.let { notification ->
            Log.d(TAG, "Notification title: ${notification.title}")
            Log.d(TAG, "Notification body: ${notification.body}")
            
            showNotification(
                title = notification.title ?: "HandsFree Dev",
                body = notification.body ?: ""
            )
        }
        
        // Handle data payload
        if (remoteMessage.data.isNotEmpty()) {
            Log.d(TAG, "Data payload: ${remoteMessage.data}")
            
            val notificationID = remoteMessage.data["notification_id"]
            val eventType = remoteMessage.data["event_type"]
            val message = remoteMessage.data["message"] ?: remoteMessage.notification?.body
            
            if (message != null) {
                speakNotification(message, notificationID)
            } else if (notificationID != null) {
                // If no message in payload, fetch from backend
                fetchNotificationDetails(notificationID)
            }
            
            Log.d(TAG, "Event type: $eventType")
        }
    }
    
    /**
     * Handle token refresh
     */
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New FCM token: $token")
        
        // Re-register token with backend
        registerTokenWithBackend(token, "fcm")
    }
    
    // MARK: - Notification Display
    
    /**
     * Show system notification
     */
    private fun showNotification(title: String, body: String) {
        val notificationBuilder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
        
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(System.currentTimeMillis().toInt(), notificationBuilder.build())
    }
    
    // MARK: - Backend Integration
    
    /**
     * Register token with backend
     */
    private fun registerTokenWithBackend(token: String, platform: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val json = JSONObject().apply {
                    put("endpoint", token)
                    put("platform", platform)
                }
                
                val requestBody = json.toString()
                    .toRequestBody("application/json".toMediaType())
                
                val request = Request.Builder()
                    .url("$backendURL/v1/notifications/subscriptions")
                    .post(requestBody)
                    .addHeader("Content-Type", "application/json")
                    .addHeader("X-User-ID", userID)
                    .build()
                
                val response = httpClient.newCall(request).execute()
                
                if (response.isSuccessful) {
                    Log.d(TAG, "Token re-registered successfully")
                } else {
                    Log.e(TAG, "Token re-registration failed: ${response.code}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Token re-registration error", e)
            }
        }
    }
    
    /**
     * Fetch notification details from backend
     */
    private fun fetchNotificationDetails(notificationID: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val request = Request.Builder()
                    .url("$backendURL/v1/notifications")
                    .addHeader("X-User-ID", userID)
                    .build()
                
                val response = httpClient.newCall(request).execute()
                
                if (response.isSuccessful) {
                    val responseBody = response.body?.string()
                    val json = JSONObject(responseBody ?: "{}")
                    val notifications = json.optJSONArray("notifications")
                    
                    // Find notification by ID
                    if (notifications != null) {
                        for (i in 0 until notifications.length()) {
                            val notification = notifications.getJSONObject(i)
                            if (notification.optString("id") == notificationID) {
                                val message = notification.optString("message")
                                speakNotification(message, notificationID)
                                break
                            }
                        }
                    }
                } else {
                    Log.e(TAG, "Failed to fetch notification: ${response.code}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Fetch notification error", e)
            }
        }
    }
    
    // MARK: - TTS Playback
    
    /**
     * Fetch TTS audio and play it
     */
    private fun speakNotification(message: String, notificationID: String?) {
        Log.d(TAG, "Speaking notification: $message")
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val audioData = fetchTTS(message)
                if (audioData != null) {
                    withContext(Dispatchers.Main) {
                        playAudio(audioData)
                    }
                } else {
                    Log.e(TAG, "Failed to fetch TTS audio")
                }
            } catch (e: Exception) {
                Log.e(TAG, "TTS playback error", e)
            }
        }
    }
    
    /**
     * Fetch TTS audio from backend
     */
    private suspend fun fetchTTS(text: String): ByteArray? {
        return withContext(Dispatchers.IO) {
            try {
                val json = JSONObject().apply {
                    put("text", text)
                    put("format", "mp3")
                    put("voice", "default")
                }
                
                val requestBody = json.toString()
                    .toRequestBody("application/json".toMediaType())
                
                val request = Request.Builder()
                    .url("$backendURL/v1/tts")
                    .post(requestBody)
                    .addHeader("Content-Type", "application/json")
                    .addHeader("X-User-ID", userID)
                    .build()
                
                val response = httpClient.newCall(request).execute()
                
                if (response.isSuccessful) {
                    val audioData = response.body?.bytes()
                    Log.d(TAG, "TTS audio fetched successfully (${audioData?.size ?: 0} bytes)")
                    audioData
                } else {
                    Log.e(TAG, "TTS request failed: ${response.code}")
                    null
                }
            } catch (e: Exception) {
                Log.e(TAG, "TTS fetch error", e)
                null
            }
        }
    }
    
    /**
     * Play audio data using MediaPlayer
     */
    private fun playAudio(audioData: ByteArray) {
        try {
            // Write audio to temporary file
            val tempFile = File.createTempFile("tts", ".mp3", cacheDir)
            FileOutputStream(tempFile).use { fos ->
                fos.write(audioData)
            }
            
            // Release previous player if exists
            mediaPlayer?.release()
            
            // Create and configure MediaPlayer
            mediaPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                        .build()
                )
                
                setDataSource(tempFile.absolutePath)
                prepare()
                start()
                
                setOnCompletionListener {
                    // Clean up after playback
                    release()
                    tempFile.delete()
                    Log.d(TAG, "TTS playback completed")
                }
                
                setOnErrorListener { _, what, extra ->
                    Log.e(TAG, "MediaPlayer error: what=$what, extra=$extra")
                    release()
                    tempFile.delete()
                    true
                }
            }
            
            Log.d(TAG, "Playing TTS audio")
        } catch (e: Exception) {
            Log.e(TAG, "Audio playback error", e)
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        mediaPlayer?.release()
    }
}

// MARK: - AndroidManifest.xml Configuration

// Add to AndroidManifest.xml:
/*
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

<application>
    <service
        android:name=".MyFirebaseMessagingService"
        android:exported="false">
        <intent-filter>
            <action android:name="com.google.firebase.MESSAGING_EVENT" />
        </intent-filter>
    </service>
</application>
*/
