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

/**
 * Core Foreground Service for FamilyEye Agent.
 * This service keeps the app alive and orchestrates monitoring tasks.
 */
@AndroidEntryPoint
class FamilyEyeService : Service() {

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
        webSocketClient.stop()
        serviceScope.cancel()
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

    private fun startRuleFetching() {
        serviceScope.launch {
            while (isActive) {
                try {
                    fetchRules()
                } catch (e: Exception) {
                    Timber.e(e, "Error fetching rules")
                }
                delay(30_000) // Fetch every 30 seconds
            }
        }
    }

    @Inject
    lateinit var ruleRepository: com.familyeye.agent.data.repository.RuleRepository

    private suspend fun fetchRules() {
        try {
             ruleRepository.refreshRules()
        } catch (e: Exception) {
            Timber.e(e, "Exception in fetchRules")
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = getString(R.string.service_notification_title)
            val descriptionText = getString(R.string.service_notification_text)
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
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
