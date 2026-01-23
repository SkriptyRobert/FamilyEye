package com.familyeye.agent.ui

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.core.app.NotificationCompat
import com.familyeye.agent.R
import com.familyeye.agent.service.AppDetectorService
import com.familyeye.agent.service.FamilyEyeService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import timber.log.Timber

/**
 * Transparent Activity used to "kick" the application process back to life
 * with high priority after a "Clear All" or crash.
 * 
 * Starting an Activity forces the Android system to recognize the app as 
 * "Foreground" / User-Interactive for a moment, which dramatically increases
 * the chance that the System will re-bind the Accessibility Service (AppDetector).
 * 
 * IMPROVED: Now waits briefly to verify service health and logs recovery source.
 */
class KeepAliveActivity : Activity() {

    companion object {
        private const val RECOVERY_NOTIFICATION_ID = 9999
        private const val RECOVERY_CHANNEL_ID = "familyeye_recovery_channel"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val source = intent.getStringExtra("source") ?: "unknown"
        Timber.d("KeepAliveActivity: Recovery triggered from '$source'")

        // 1. Ensure Service is running first
        try {
            FamilyEyeService.start(this)
            Timber.i("FamilyEyeService.start() called")
        } catch (e: Exception) {
            Timber.e(e, "Failed to start service from KeepAlive")
        }

        // 2. Wait and verify service health before closing
        CoroutineScope(Dispatchers.Main).launch {
            verifyAndFinish()
        }
    }

    /**
     * Wait briefly for Accessibility Service to bind, then verify health.
     * If not recovered, create notification for parent awareness.
     */
    private suspend fun verifyAndFinish() {
        // Give system time to bind Accessibility Service
        delay(2000)
        
        val isAccessibilityBound = AppDetectorService.instance != null
        
        if (isAccessibilityBound) {
            Timber.i("KeepAliveActivity: Recovery SUCCESSFUL - Accessibility bound!")
        } else {
            Timber.e("KeepAliveActivity: Recovery PARTIAL - Accessibility NOT bound!")
            
            // Check if Accessibility is even enabled in settings
            if (!isAccessibilityServiceEnabled()) {
                Timber.e("Accessibility Service is DISABLED in system settings!")
                showRecoveryNotification(
                    title = "FamilyEye needs attention",
                    message = "Protection service was disabled. Please re-enable in Settings."
                )
            } else {
                // Accessibility is enabled but not bound - system issue, will retry
                Timber.w("Accessibility enabled but not bound - waiting for system rebind...")
            }
        }
        
        // Finish immediately without animation
        finish()
        overridePendingTransition(0, 0)
    }

    /**
     * Check if our Accessibility Service is enabled in system settings.
     */
    private fun isAccessibilityServiceEnabled(): Boolean {
        return try {
            val enabledServices = android.provider.Settings.Secure.getString(
                contentResolver,
                android.provider.Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            ) ?: return false
            
            val ourServiceName = "${packageName}/${AppDetectorService::class.java.name}"
            enabledServices.contains(ourServiceName, ignoreCase = true)
        } catch (e: Exception) {
            Timber.e(e, "Failed to check accessibility status")
            false
        }
    }

    /**
     * Show notification to parent that agent needs attention.
     * This is a last resort when automatic recovery fails.
     */
    private fun showRecoveryNotification(title: String, message: String) {
        try {
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            
            // Create channel for Android O+
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val channel = NotificationChannel(
                    RECOVERY_CHANNEL_ID,
                    "Recovery Alerts",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Alerts when FamilyEye needs manual intervention"
                }
                notificationManager.createNotificationChannel(channel)
            }
            
            val notification = NotificationCompat.Builder(this, RECOVERY_CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText(message)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                // Tap to open settings
                .setContentIntent(
                    android.app.PendingIntent.getActivity(
                        this,
                        0,
                        Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS),
                        android.app.PendingIntent.FLAG_IMMUTABLE
                    )
                )
                .build()
            
            notificationManager.notify(RECOVERY_NOTIFICATION_ID, notification)
            Timber.i("Recovery notification shown")
        } catch (e: Exception) {
            Timber.e(e, "Failed to show recovery notification")
        }
    }
}
