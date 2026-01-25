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
 */
class RestartReceiver : BroadcastReceiver() {
    
    companion object {
        const val ACTION_RESTART = "com.familyeye.agent.ACTION_RESTART"
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION_RESTART) {
            val source = intent.getStringExtra("source") ?: "unknown"
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
