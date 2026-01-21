package com.familyeye.agent.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.familyeye.agent.R
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.familyeye.agent.ui.MainActivity
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import timber.log.Timber
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.isActive
import javax.inject.Inject
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.asRequestBody
import com.familyeye.agent.ui.KeepAliveActivity
import kotlin.system.exitProcess


/**
 * Core Foreground Service for FamilyEye Agent.
 * This service keeps the app alive and orchestrates monitoring tasks.
 */
@AndroidEntryPoint
class FamilyEyeService : Service(), ScreenStateListener {

    @Inject
    lateinit var configRepository: AgentConfigRepository

    @Inject
    lateinit var usageTracker: UsageTracker

    @Inject
    lateinit var reporter: Reporter

    @Inject
    lateinit var ruleEnforcer: RuleEnforcer

    @Inject
    lateinit var api: com.familyeye.agent.data.api.FamilyEyeApi

    @Inject
    lateinit var blockOverlayManager: BlockOverlayManager

    @Inject
    lateinit var webSocketClient: com.familyeye.agent.data.api.WebSocketClient

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    
    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "familyeye_monitor_channel"
        
        fun start(context: Context) {
            val intent = Intent(context, FamilyEyeService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }
        
        fun stop(context: Context) {
            val intent = Intent(context, FamilyEyeService::class.java)
            context.stopService(intent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        Timber.d("FamilyEyeService created")
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification(), 
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC or ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            } else {
                0
            }
        )
        
        // Start monitoring tasks
        startMonitoring()
        
        // Register screen state receiver for immediate sync on wake
        registerScreenStateReceiver()
    }

    private fun registerScreenStateReceiver() {
        try {
            val filter = android.content.IntentFilter().apply {
                addAction(Intent.ACTION_SCREEN_ON)
                addAction(Intent.ACTION_SCREEN_OFF)
            }
            registerReceiver(screenReceiver, filter)
            Timber.d("Screen state receiver registered")
        } catch (e: Exception) {
            Timber.e(e, "Failed to register screen receiver")
        }
    }

    private val screenReceiver = object : android.content.BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                Intent.ACTION_SCREEN_ON -> onScreenOn()
                Intent.ACTION_SCREEN_OFF -> onScreenOff()
            }
        }
    }

    override fun onScreenOn() {
        Timber.i("Screen ON - triggering immediate sync and WebSocket reconnect")
        serviceScope.launch {
            try {
                // Force WebSocket reconnect
                webSocketClient.stop()
                webSocketClient.start()
                // Force immediate sync
                reporter.forceSync()
            } catch (e: Exception) {
                Timber.e(e, "Error during screen-on sync")
            }
        }
    }

    override fun onScreenOff() {
        Timber.d("Screen OFF - monitoring continues in background")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Timber.d("FamilyEyeService started")
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    override fun onDestroy() {
        super.onDestroy()
        Timber.d("FamilyEyeService destroyed")
        try {
            unregisterReceiver(screenReceiver)
        } catch (e: Exception) {
            Timber.e(e, "Failed to unregister screen receiver")
        }
        webSocketClient.stop()
        serviceScope.cancel()
    }

    /**
     * Called when user swipes away the app from recent apps.
     * Restart the service to ensure continuous monitoring.
     */
    override fun onTaskRemoved(rootIntent: Intent?) {
        super.onTaskRemoved(rootIntent)
        Timber.w("FamilyEyeService task removed - performing HARD RESTART")
        
        // Schedule restart via KeepAliveActivity to force process priority upgrade
        // and trigger Accessibility re-bind
        val restartIntent = Intent(applicationContext, KeepAliveActivity::class.java)
        restartIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        
        val pendingIntent = PendingIntent.getActivity(
            applicationContext,
            1,
            restartIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as android.app.AlarmManager
        alarmManager.set(
            android.app.AlarmManager.RTC_WAKEUP,
            System.currentTimeMillis() + 500, // 500ms delay
            pendingIntent
        )
        
        // Suicide to ensure fresh start
        stopSelf()
        exitProcess(0)
    }

    private fun startMonitoring() {
        serviceScope.launch {
            configRepository.isPaired.collect { isPaired ->
                if (isPaired) {
                    Timber.i("Device is paired, starting monitoring loops...")
                    usageTracker.start()
                    reporter.start()
                    webSocketClient.start()
                    startRuleFetching()
                    startCommandListening()
                    startSecurityMonitoring() // Phase 3: Security checks
                } else {
                    Timber.i("Device not paired, waiting for pairing...")
                    webSocketClient.stop()
                }
            }
        }
    }

    private fun startCommandListening() {
        serviceScope.launch {
             webSocketClient.commands.collect { command ->
                 Timber.i("Received WebSocket Command: ${command.command}")
                 when (command.command) {
                     "LOCK_NOW", "UNLOCK_NOW", "REFRESH_RULES" -> {
                         Timber.i("Immediate Rule Refresh Requested")
                         fetchRules()
                         // Critical Fix for Remote Unlock:
                         // UsageTracker pauses when overlay is showing. If we unlock, we MUST explicitly hide the overlay
                         // to allow the user to continue usage. If a different block is still active, UsageTracker will 
                         // re-show it in the next tick.
                         launch(Dispatchers.Main) {
                             blockOverlayManager.hide()
                         }
                     }
                     "SCREENSHOT_NOW" -> {
                         Timber.i("Screenshot Requested")
                         captureAndUploadScreenshot()
                     }
                     else -> {
                         if (command.command.startsWith("RESET_PIN:")) {
                             val newPin = command.command.substringAfter("RESET_PIN:")
                             Timber.i("PIN Reset Command Received. New PIN: $newPin")
                             configRepository.savePin(newPin)
                         }
                     }
                 }
             }
        }
    }

    private fun captureAndUploadScreenshot() {
        val detector = AppDetectorService.instance
        if (detector == null) {
            Timber.e("AppDetectorService is not running, cannot take screenshot")
            return
        }

        detector.requestScreenshot { bitmap ->
            if (bitmap != null) {
                serviceScope.launch(Dispatchers.IO) {
                    try {
                         val file = saveBitmapToFile(bitmap)
                         uploadScreenshot(file)
                         file.delete() // Clean up
                    } catch (e: Exception) {
                        Timber.e(e, "Failed to upload screenshot")
                    }
                }
            } else {
                Timber.e("Screenshot capture returned null")
            }
        }
    }

    private fun saveBitmapToFile(bitmap: android.graphics.Bitmap): java.io.File {
        val file = java.io.File(cacheDir, "screenshot_${System.currentTimeMillis()}.jpg")
        val stream = java.io.FileOutputStream(file)
        bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG, 70, stream)
        stream.close()
        return file
    }



// ... inside class ...

    private suspend fun uploadScreenshot(file: java.io.File) {
        val deviceId = configRepository.deviceId.firstOrNull() ?: return
        val apiKey = configRepository.apiKey.firstOrNull() ?: return

        val requestFile = file.asRequestBody("image/jpeg".toMediaTypeOrNull())
        val body = okhttp3.MultipartBody.Part.createFormData("file", file.name, requestFile)

        val response = api.uploadScreenshot(deviceId, apiKey, body)
        if (response.isSuccessful) {
            Timber.i("Screenshot uploaded successfully: ${response.body()?.url}")
        } else {
            Timber.e("Screenshot upload failed: ${response.code()}")
        }
    }

    /**
     * Phase 1 Optimization: Event-driven rule fetching instead of 30s polling.
     * Rules are fetched:
     * 1. Once on startup
     * 2. When WebSocket reconnects (to catch up with missed changes)
     * 3. When REFRESH_RULES command is received (handled in startCommandListening)
     */
    private fun startRuleFetching() {
        serviceScope.launch {
            // Initial fetch on startup
            Timber.i("Initial rule fetch on startup")
            fetchRules()
            
            // Re-fetch when WebSocket reconnects (indicates we might have missed updates)
            webSocketClient.isConnected.collect { connected ->
                if (connected) {
                    Timber.i("WebSocket reconnected - refreshing rules to catch up")
                    fetchRules()
                }
            }
        }
    }

    @Inject
    lateinit var ruleRepository: com.familyeye.agent.data.repository.RuleRepository

    @Inject
    lateinit var selfProtectionHandler: com.familyeye.agent.enforcement.SelfProtectionHandler

    private suspend fun fetchRules() {
        try {
             ruleRepository.refreshRules()
        } catch (e: Exception) {
            Timber.e(e, "Exception in fetchRules")
        }
    }

    /**
     * Phase 3: Periodic security monitoring.
     * Checks for system-level tampering attempts like Developer Options or ADB.
     */
    private fun startSecurityMonitoring() {
        serviceScope.launch {
            while (isActive) {
                try {
                    // --- Watchdog Checks ---
                    val isAccessibilityRunning = AppDetectorService.instance != null
                    val isWebSocketConnected = webSocketClient.isConnected.value
                    
                    if (!isAccessibilityRunning) {
                         Timber.e("CRITICAL: Accessibility Service (AppDetector) is NOT running! Attempting Self-Repair.")
                         triggerSelfRepair()
                    }
                    
                    Timber.d("Watchdog: AC=$isAccessibilityRunning, WS=$isWebSocketConnected")
                    
                    // --- Security Checks ---
                    val issues = selfProtectionHandler.checkSystemTampering()
                    
                    for ((issueType, _) in issues) {
                        // Report each security issue to backend
                        Timber.w("Security issue detected: $issueType - reporting to backend")
                        reportSecurityAlert(issueType)
                    }
                } catch (e: Exception) {
                    Timber.e(e, "Error in security monitoring")
                }
                delay(60_000) // Check every 60 seconds
            }
        }
    }

    /**
     * Attempts to repair broken service bindings by launching a transparent activity.
     * This moves the app to the foreground, prompting the system to re-evaluate bindings.
     */
    private fun triggerSelfRepair() {
        try {
            val intent = Intent(this, KeepAliveActivity::class.java)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            Timber.i("Self-Repair triggered: KeepAliveActivity launched")
        } catch (e: Exception) {
            Timber.e(e, "Failed to trigger self-repair")
        }
    }

    private suspend fun reportSecurityAlert(issueType: String) {
        try {
            val deviceId = configRepository.getDeviceId() ?: return
            
            val alertMessage = when (issueType) {
                "DEVELOPER_OPTIONS_ENABLED" -> "Developer Options is enabled on device"
                "ADB_DEBUGGING_ENABLED" -> "USB Debugging (ADB) is enabled on device"
                else -> "Security issue detected: $issueType"
            }
            
            val request = com.familyeye.agent.data.api.dto.ShieldAlertRequest(
                device_id = deviceId,
                keyword = "TAMPERING:$issueType",
                app_name = "System Settings",
                detected_text = alertMessage,
                screenshot_url = null,
                severity = "critical"
            )
            
            api.reportShieldAlert(request)
            Timber.i("Security alert reported: $issueType")
        } catch (e: Exception) {
            Timber.e(e, "Failed to report security alert")
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = getString(R.string.service_notification_title)
            val descriptionText = getString(R.string.service_notification_text)
            // Use IMPORTANCE_DEFAULT instead of LOW to ensure notifications are visible
            val importance = NotificationManager.IMPORTANCE_DEFAULT
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
                // Disable sound for foreground service notification (still visible)
                setSound(null, null)
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        val pendingIntent: PendingIntent = Intent(this, MainActivity::class.java).let { notificationIntent ->
            PendingIntent.getActivity(this, 0, notificationIntent, PendingIntent.FLAG_IMMUTABLE)
        }

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.service_notification_title))
            .setContentText(getString(R.string.service_notification_text))
            .setSmallIcon(R.mipmap.ic_launcher) // TODO: Use dedicated persistent icon
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }
}
