package com.familyeye.agent.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import timber.log.Timber
import kotlinx.coroutines.*

/**
 * Lightweight service running in a separate process (:watchdog).
 * Its sole purpose is to ensure FamilyEyeService is running.
 */
class WatchdogService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var monitoringJob: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Timber.i("WatchdogService created in process: ${android.os.Process.myPid()}")
        startForegroundService()
    }

    private fun startForegroundService() {
        val channelId = "familyeye_watchdog_v2" // Changed ID to force update
        val channelName = "Security Watchdog"
        
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            // ERROR FIX: Use IMPORTANCE_LOW (2) so it appears in status bar but doesn't ding
            // MIUI treats IMPORTANCE_MIN (0/1) as "junk" to be killed.
            val chan = android.app.NotificationChannel(channelId, channelName, android.app.NotificationManager.IMPORTANCE_LOW)
            chan.lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
            chan.setShowBadge(false)
            val manager = getSystemService(android.app.NotificationManager::class.java)
            manager.createNotificationChannel(chan)
        }

        val notification = androidx.core.app.NotificationCompat.Builder(this, channelId)
            .setOngoing(true)
            .setSmallIcon(android.R.drawable.ic_secure)
            .setContentTitle("FamilyEye Security")
            .setContentText("Active Device Protection")
            // Priority LOW ensures it shows up but isn't annoying
            .setPriority(androidx.core.app.NotificationCompat.PRIORITY_LOW)
            .setCategory(androidx.core.app.NotificationCompat.CATEGORY_SERVICE)
            .build()
            
        // Use a different ID than the main service
        startForeground(2001, notification)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Timber.d("WatchdogService started")
        startMonitoring()
        return START_STICKY
    }

    private fun startMonitoring() {
        if (monitoringJob?.isActive == true) return

        monitoringJob = serviceScope.launch {
            while (isActive) {
                checkMainService()
                delay(5000) // Check every 5 seconds
            }
        }
    }

    private fun checkMainService() {
        // We use a simple check: can we start the service? 
        // Calling startService on an already running service is safe and inexpensive.
        try {
            FamilyEyeService.start(this)
        } catch (e: Exception) {
            Timber.e(e, "Watchdog failed to ping FamilyEyeService")
        }
    }

    override fun onDestroy() {
        Timber.w("WatchdogService destroyed!")
        serviceScope.cancel()
        // Try to revive ourself via the main service if possible
        super.onDestroy()
    }
}
