// Android Kotlin: Push Notification Token Registration
//
// This example demonstrates how to request notification permissions,
// obtain an FCM device token, and register it with the backend.
//
// Usage:
// 1. Add Firebase dependencies to build.gradle
// 2. Add google-services.json to app/
// 3. Call registerForPushNotifications() during app initialization

package com.example.handsfree

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class PushManager(private val context: Context) {
    private val backendURL = "http://localhost:8080" // Change to production URL
    private val userID = "00000000-0000-0000-0000-000000000001" // Get from auth
    private val httpClient = OkHttpClient()
    
    companion object {
        private const val TAG = "PushManager"
        private const val NOTIFICATION_PERMISSION_REQUEST_CODE = 1001
        private const val PREFS_NAME = "handsfree_prefs"
        private const val KEY_SUBSCRIPTION_ID = "push_subscription_id"
    }
    
    // MARK: - Permission Request
    
    /**
     * Request notification permission (Android 13+) and register for FCM token
     */
    fun registerForPushNotifications() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // Android 13+ requires runtime permission
            if (ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                // Permission already granted
                obtainFCMToken()
            } else {
                // Request permission
                ActivityCompat.requestPermissions(
                    context as Activity,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    NOTIFICATION_PERMISSION_REQUEST_CODE
                )
            }
        } else {
            // Pre-Android 13: no runtime permission needed
            obtainFCMToken()
        }
    }
    
    /**
     * Handle permission result from Activity
     */
    fun onPermissionResult(requestCode: Int, grantResults: IntArray) {
        if (requestCode == NOTIFICATION_PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Log.d(TAG, "Notification permission granted")
                obtainFCMToken()
            } else {
                Log.w(TAG, "Notification permission denied")
            }
        }
    }
    
    // MARK: - Token Registration
    
    /**
     * Obtain FCM token from Firebase
     */
    private fun obtainFCMToken() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.w(TAG, "Fetching FCM token failed", task.exception)
                return@addOnCompleteListener
            }
            
            val token = task.result
            Log.d(TAG, "FCM token: $token")
            
            // Register with backend
            registerTokenWithBackend(token, "fcm")
        }
    }
    
    /**
     * Register FCM token with backend
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
                    val responseBody = response.body?.string()
                    val responseJson = JSONObject(responseBody ?: "{}")
                    val subscriptionID = responseJson.optString("id")
                    
                    // Store subscription ID for later deletion
                    context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                        .edit()
                        .putString(KEY_SUBSCRIPTION_ID, subscriptionID)
                        .apply()
                    
                    Log.d(TAG, "Token registered successfully. Subscription ID: $subscriptionID")
                } else {
                    Log.e(TAG, "Token registration failed: ${response.code}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Token registration error", e)
            }
        }
    }
    
    // MARK: - Unregistration
    
    /**
     * Delete push subscription from backend
     */
    fun unregisterFromBackend() {
        val subscriptionID = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_SUBSCRIPTION_ID, null)
        
        if (subscriptionID == null) {
            Log.w(TAG, "No subscription to delete")
            return
        }
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val request = Request.Builder()
                    .url("$backendURL/v1/notifications/subscriptions/$subscriptionID")
                    .delete()
                    .addHeader("X-User-ID", userID)
                    .build()
                
                val response = httpClient.newCall(request).execute()
                
                if (response.isSuccessful || response.code == 204) {
                    Log.d(TAG, "Successfully unregistered from push notifications")
                    
                    // Clear stored subscription ID
                    context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                        .edit()
                        .remove(KEY_SUBSCRIPTION_ID)
                        .apply()
                } else {
                    Log.e(TAG, "Unregistration failed: ${response.code}")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Unregistration error", e)
            }
        }
    }
}

// MARK: - MainActivity Integration

// Add to your MainActivity.kt:
/*
class MainActivity : AppCompatActivity() {
    private lateinit var pushManager: PushManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        pushManager = PushManager(this)
        pushManager.registerForPushNotifications()
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        pushManager.onPermissionResult(requestCode, grantResults)
    }
}
*/

// MARK: - Gradle Configuration

// Add to app/build.gradle:
/*
dependencies {
    implementation 'com.google.firebase:firebase-messaging:23.0.0'
    implementation 'com.squareup.okhttp3:okhttp:4.12.0'
}

apply plugin: 'com.google.gms.google-services'
*/

// Add to project-level build.gradle:
/*
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.3.15'
    }
}
*/
