package com.familyeye.agent.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import com.familyeye.agent.service.FamilyEyeService
import timber.log.Timber

/**
 * BroadcastReceiver specifically for handling restart intents from AlarmManager.
 * This is more reliable than Activity-based restart on some OEMs (especially Xiaomi).
 * 
 * Using a receiver instead of activity avoids UI permission issues and is faster.
 * 
 * Includes debounce mechanism to prevent multiple concurrent restarts.
 */
class RestartReceiver : BroadcastReceiver() {
    
    companion object {
        const val ACTION_RESTART = "com.familyeye.agent.ACTION_RESTART"
        
        // Debounce settings
        private const val DEBOUNCE_PREFS = "restart_debounce"
        private const val KEY_LAST_RESTART = "last_restart_time"
        private const val DEBOUNCE_MS = 2000L // Skip if restart was triggered within 2 seconds
        
        /**
         * Check if a restart should be debounced.
         * Returns true if restart should proceed, false if it should be skipped.
         */
        @Synchronized
        fun shouldProceedWithRestart(context: Context, source: String): Boolean {
            val prefs = context.getSharedPreferences(DEBOUNCE_PREFS, Context.MODE_PRIVATE)
            val lastRestart = prefs.getLong(KEY_LAST_RESTART, 0L)
            val now = System.currentTimeMillis()
            
            return if (now - lastRestart < DEBOUNCE_MS) {
                Timber.d("Restart debounced from '$source' (last restart ${now - lastRestart}ms ago)")
                false
            } else {
                prefs.edit().putLong(KEY_LAST_RESTART, now).apply()
                true
            }
        }
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION_RESTART) {
            val source = intent.getStringExtra("source") ?: "unknown"
            
            // Debounce check - skip if restart was triggered recently
            if (!shouldProceedWithRestart(context, source)) {
                return
            }
            
            Timber.i("RestartReceiver triggered from: $source")
            
            // Start the foreground service immediately
            try {
                FamilyEyeService.start(context)
                Timber.i("FamilyEyeService restart initiated successfully")
            } catch (e: Exception) {
                Timber.e(e, "Failed to restart FamilyEyeService")
                // Fallback: try again with explicit foreground intent
                try {
                    val serviceIntent = Intent(context, FamilyEyeService::class.java)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        context.startForegroundService(serviceIntent)
                    } else {
                        context.startService(serviceIntent)
                    }
                } catch (e2: Exception) {
                    Timber.e(e2, "Fallback restart also failed")
                }
            }
            
            // RE-SCHEDULE THE HEARTBEAT
            // This creates the infinite loop. Even if the service starts, we want the next alarm ready.
            try {
                com.familyeye.agent.service.AlarmWatchdog.scheduleHeartbeat(context)
            } catch (e: Exception) {
                Timber.e(e, "Failed to reschedule heartbeat from receiver")
            }
        }
    }
}
