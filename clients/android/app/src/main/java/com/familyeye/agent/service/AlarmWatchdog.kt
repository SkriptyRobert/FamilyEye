package com.familyeye.agent.service

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import com.familyeye.agent.receiver.RestartReceiver
import timber.log.Timber

/**
 * Aggressive Watchdog using AlarmManager.
 * Schedules a "Heartbeat" that fires every minute (or as fast as OS allows).
 * This acts as an external pulse: if the app is alive, it just resets the timer.
 * If the app is dead, this alarm will wake up the system and trigger RestartReceiver.
 */
object AlarmWatchdog {

    private const val HEARTBEAT_INTERVAL_MS = 60_000L // 1 minute
    private const val REQUEST_CODE = 777

    fun scheduleHeartbeat(context: Context) {
        try {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
            
            val intent = Intent(context, RestartReceiver::class.java).apply {
                action = RestartReceiver.ACTION_RESTART
                putExtra("source", "alarm_heartbeat")
            }
            
            // FLAG_UPDATE_CURRENT so we don't spawn multiple pending intents
            val pendingIntent = PendingIntent.getBroadcast(
                context,
                REQUEST_CODE,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            
            val triggerTime = System.currentTimeMillis() + HEARTBEAT_INTERVAL_MS
            
            // Use aggressive scheduling
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                if (alarmManager.canScheduleExactAlarms()) {
                    alarmManager.setExactAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP,
                        triggerTime,
                        pendingIntent
                    )
                } else {
                    // Fallback to inexact alarm if permission revoked (e.g. by user)
                    Timber.w("AlarmWatchdog: Exact alarm permission missing, using inexact")
                    alarmManager.setAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP,
                        triggerTime,
                        pendingIntent
                    )
                }
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    triggerTime,
                    pendingIntent
                )
            } else {
                alarmManager.setExact(
                    AlarmManager.RTC_WAKEUP,
                    triggerTime,
                    pendingIntent
                )
            }
            
            Timber.v("AlarmWatchdog: Heartbeat scheduled for +${HEARTBEAT_INTERVAL_MS}ms")
            
        } catch (e: Exception) {
            Timber.e(e, "AlarmWatchdog: Failed to schedule heartbeat")
        }
    }
    
    fun cancel(context: Context) {
        // We arguably DON'T want to cancel this if we want true immortality.
        // But for "official" stopping of the service (e.g. uninstall), we might need to.
        // For now, let's allow cancelling only if explicitly requested.
        try {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
            val intent = Intent(context, RestartReceiver::class.java).apply {
                action = RestartReceiver.ACTION_RESTART
            }
            val pendingIntent = PendingIntent.getBroadcast(
                context,
                REQUEST_CODE,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            alarmManager.cancel(pendingIntent)
            Timber.i("AlarmWatchdog: Heartbeat cancelled")
        } catch (e: Exception) {
            Timber.e(e, "AlarmWatchdog: Failed to cancel heartbeat")
        }
    }
}
