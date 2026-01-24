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
import androidx.work.ExistingPeriodicWorkPolicy

import androidx.work.WorkManager
import androidx.work.OneTimeWorkRequest
import androidx.work.OutOfQuotaPolicy
import com.familyeye.agent.service.RestartWorker
import com.familyeye.agent.R
import com.familyeye.agent.config.AgentConstants
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
import com.familyeye.agent.receiver.RestartReceiver
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
        
        // Cooldown to prevent strict restart loops (crash immediately after start)
        // If service runs for less than this time, we delay the restart slightly instead of firing immediately.
        private const val RESTART_COOLDOWN_MS = 3_000L  // 3 seconds (was 10s)
        
        // Prefs key for tracking last restart
        private const val PREFS_NAME = "familyeye_service_prefs"
        private const val KEY_LAST_RESTART = "last_restart_time"
        
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

    // Track when service was created to detect restart loop
    private var serviceCreatedTime = 0L

    override fun onCreate() {
        super.onCreate()
        serviceCreatedTime = System.currentTimeMillis()
        Timber.d("FamilyEyeService created at $serviceCreatedTime")
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification(), 
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC or ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            } else {
                0
            }
        )
        
        // Schedule WorkManager guardian as backup recovery mechanism
        scheduleGuardianWorker()
        
        // Start monitoring tasks
        startMonitoring()
        
        // Register screen state receiver for immediate sync on wake
        registerScreenStateReceiver()
    }

    /**
     * Schedule periodic WorkManager task as backup recovery mechanism.
     * This ensures the agent recovers even if AlarmManager fails (e.g., aggressive OEM battery management).
     */
    private fun scheduleGuardianWorker() {
        try {
            val guardianRequest = PeriodicWorkRequestBuilder<ProcessGuardianWorker>(
                AgentConstants.GUARDIAN_WORKER_INTERVAL_MIN, TimeUnit.MINUTES
            ).build()
            
            WorkManager.getInstance(this).enqueueUniquePeriodicWork(
                ProcessGuardianWorker.WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,  // Don't replace if already scheduled
                guardianRequest
            )
            Timber.i("Guardian WorkManager scheduled (every ${AgentConstants.GUARDIAN_WORKER_INTERVAL_MIN} min)")
        } catch (e: Exception) {
            Timber.e(e, "Failed to schedule guardian worker")
        }
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
     * Uses DUAL ALARM STRATEGY for maximum reliability:
     * 1. Primary: RestartReceiver at 100ms (fast, lightweight)
     * 2. Backup: KeepAliveActivity at 3000ms (fallback if receiver fails)
     */
    override fun onTaskRemoved(rootIntent: Intent?) {
        super.onTaskRemoved(rootIntent)
        
        val currentTime = System.currentTimeMillis()
        val timeSinceCreation = currentTime - serviceCreatedTime
        
        var delayMsPrimary = 100L
        var delayMsBackup = 3000L

        // COOLDOWN CHECK: If service was just created (<3s), this might be a loop or fast kill.
        // Instead of skipping restart (which leads to death), we simply DELAY it to break the loop.
        if (timeSinceCreation < RESTART_COOLDOWN_MS) {
            Timber.w("Fast kill detected (${timeSinceCreation}ms) - DELAYING restart to break loop")
            delayMsPrimary = 5000L   // 5s delay
            delayMsBackup = 8000L    // 8s delay
        } else {
             Timber.i("Normal kill detected (${timeSinceCreation}ms) - Executing IMMEDIATE restart")
        }
        
        Timber.w("Scheduling restart alarms: Primary=${delayMsPrimary}ms, Backup=${delayMsBackup}ms")
        
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as android.app.AlarmManager
        
        // PRIMARY: Fast restart via RestartReceiver
        val primaryIntent = Intent(applicationContext, RestartReceiver::class.java).apply {
            action = RestartReceiver.ACTION_RESTART
            putExtra("source", "task_removed_primary")
        }
        val primaryPendingIntent = PendingIntent.getBroadcast(
            applicationContext,
            1001,
            primaryIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )
        
        // BACKUP: Fallback via KeepAliveActivity
        val backupIntent = Intent(applicationContext, KeepAliveActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            putExtra("source", "task_removed_backup")
        }
        val backupPendingIntent = PendingIntent.getActivity(
            applicationContext,
            1002,
            backupIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            // Schedule PRIMARY
            alarmManager.setExactAndAllowWhileIdle(
                android.app.AlarmManager.RTC_WAKEUP,
                currentTime + delayMsPrimary,
                primaryPendingIntent
            )
            // Schedule BACKUP
            alarmManager.setExactAndAllowWhileIdle(
                android.app.AlarmManager.RTC_WAKEUP,
                currentTime + delayMsBackup,
                backupPendingIntent
            )
        } else {
            alarmManager.setExact(
                android.app.AlarmManager.RTC_WAKEUP,
                currentTime + delayMsPrimary,
                primaryPendingIntent
            )
            alarmManager.setExact(
                android.app.AlarmManager.RTC_WAKEUP,
                currentTime + delayMsBackup,
                backupPendingIntent
            )
        }
        
        Timber.i("Dual restart alarms scheduled: Primary=100ms, Backup=3000ms")
        
        // TRIPLE THREAT: WorkManager Backup (Expedited)
        // This is the "nuclear option" - even if Alarms fail, WorkManager will eventually run this
        try {
            val restartWork = OneTimeWorkRequest.Builder(RestartWorker::class.java)
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
                .addTag("restart_service")
                .build()
                
            WorkManager.getInstance(applicationContext)
                .enqueue(restartWork)
                
            Timber.i("Triple Threat: Expedited WorkManager restart scheduled")
        } catch (e: Exception) {
            Timber.e(e, "Failed to schedule WorkManager restart")
        }
        
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
     * Phase 3: Periodic security monitoring and health watchdog.
     * Checks for:
     * - Accessibility Service binding (zombie state detection)
     * - WebSocket connectivity
     * - System-level tampering attempts (Developer Options, ADB)
     * 
     * IMPROVED: Now runs every 10 seconds (was 60s) for faster recovery.
     */
    private fun startSecurityMonitoring() {
        serviceScope.launch {
            var selfRepairAttemptTime = 0L
            
            while (isActive) {
                try {
                    // --- Watchdog Checks ---
                    val isAccessibilityRunning = AppDetectorService.instance != null
                    val isWebSocketConnected = webSocketClient.isConnected.value
                    
                    if (!isAccessibilityRunning) {
                        val currentTime = System.currentTimeMillis()
                        
                        if (selfRepairAttemptTime == 0L) {
                            // First attempt - try soft repair
                            Timber.e("CRITICAL: Accessibility NOT running! Attempting Self-Repair...")
                            triggerSelfRepair()
                            selfRepairAttemptTime = currentTime
                        } else if (currentTime - selfRepairAttemptTime > AgentConstants.SELF_REPAIR_TIMEOUT_MS) {
                            // Self-repair didn't work - BUT DO NOT KILL PROCESS
                            // The app is better alive without Accessibility than dead in a restart loop
                            Timber.e("Self-repair timed out after ${AgentConstants.SELF_REPAIR_TIMEOUT_MS}ms - Retrying soft repair next cycle")
                            // forceNuclearRestart() // DISABLE NUCLEAR RESTART
                            selfRepairAttemptTime = 0L  // Reset for next cycle to try KeepAlive again
                        } else {
                            Timber.w("Waiting for self-repair... (${currentTime - selfRepairAttemptTime}ms elapsed)")
                        }
                    } else {
                        // Service recovered - reset timer
                        if (selfRepairAttemptTime != 0L) {
                            Timber.i("Self-repair SUCCESSFUL - Accessibility Service recovered!")
                            selfRepairAttemptTime = 0L
                        }
                    }
                    
                    Timber.d("Watchdog: AC=$isAccessibilityRunning, WS=$isWebSocketConnected")
                    
                    // --- Security Checks ---
                    val issues = selfProtectionHandler.checkSystemTampering()
                    
                    for ((issueType, _) in issues) {
                        Timber.w("Security issue detected: $issueType - reporting to backend")
                        reportSecurityAlert(issueType)
                    }
                } catch (e: Exception) {
                    Timber.e(e, "Error in security monitoring")
                }
                delay(AgentConstants.SECURITY_CHECK_INTERVAL_MS) // 10 seconds (was 60s)
            }
        }
    }

    /**
     * Nuclear restart - completely kills and restarts the process.
     * Used when soft repair (KeepAliveActivity) fails.
     */
    private fun forceNuclearRestart() {
        Timber.w("Executing NUCLEAR RESTART!")
        
        // Schedule restart via AlarmManager
        val restartIntent = Intent(applicationContext, KeepAliveActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            putExtra("source", "nuclear_restart")
        }
        
        val pendingIntent = PendingIntent.getActivity(
            applicationContext,
            System.currentTimeMillis().toInt(),  // Unique request code
            restartIntent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as android.app.AlarmManager
        alarmManager.setExactAndAllowWhileIdle(
            android.app.AlarmManager.RTC_WAKEUP,
            System.currentTimeMillis() + 1000,
            pendingIntent
        )
        
        // Kill process to force fresh start
        stopSelf()
        exitProcess(0)
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
