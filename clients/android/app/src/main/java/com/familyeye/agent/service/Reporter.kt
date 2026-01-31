package com.familyeye.agent.service

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import com.familyeye.agent.config.AgentConstants
import com.familyeye.agent.data.api.FamilyEyeApi
import com.familyeye.agent.data.api.dto.AgentReportRequest
import com.familyeye.agent.data.api.dto.AgentUsageLogCreate
import com.familyeye.agent.data.api.dto.ShieldKeyword
import com.familyeye.agent.data.local.UsageLogDao
import com.familyeye.agent.time.SecureTimeProvider
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import com.familyeye.agent.data.repository.AgentConfigRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import timber.log.Timber
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Syncs local usage logs to the backend with retry logic and connectivity awareness.
 * 
 * Features:
 * - Exponential backoff for failed sync attempts
 * - Automatic sync on network reconnection
 * - Configurable retention period for old logs
 * - Server time synchronization
 */
@Singleton
class Reporter @Inject constructor(
    private val api: FamilyEyeApi,
    private val usageLogDao: UsageLogDao,
    private val configRepository: AgentConfigRepository,
    private val keywordManager: com.familyeye.agent.scanner.KeywordManager,
    private val secureTimeProvider: SecureTimeProvider,
    private val webSocketClient: com.familyeye.agent.data.api.WebSocketClient, // Phase 1 Optimization
    private val ruleRepository: com.familyeye.agent.data.repository.RuleRepository, // Rule sync fix
    private val deviceOwnerEnforcer: com.familyeye.agent.device.DeviceOwnerPolicyEnforcer,
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: android.content.Context
) {
    private val reporterScope = CoroutineScope(Dispatchers.IO)
    private val isoFormat = SimpleDateFormat(AgentConstants.ISO_DATE_FORMAT, Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    // Retry state
    private var consecutiveFailures = 0
    private var lastSyncAttempt = 0L
    
    // Network connectivity
    private val connectivityManager by lazy {
        context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    }
    private var networkCallback: ConnectivityManager.NetworkCallback? = null

    // Screen state for battery-friendly sync interval (screen on -> longer interval)
    private val powerManager by lazy {
        context.getSystemService(Context.POWER_SERVICE) as? android.os.PowerManager
    }
    
    // Sync state
    @Volatile
    private var isSyncing = false

    fun start() {
        registerNetworkCallback()
        
        reporterScope.launch {
            while (isActive) {
                try {
                    doSync()
                    // Sync keywords periodically
                    keywordManager.syncKeywords()
                    // Sync rules periodically (fix for startRuleFetching Flow issue)
                    ruleRepository.refreshRules()
                } catch (e: Exception) {
                    Timber.e(e, "Error in Reporter loop")
                }
                // Phase 4: Adaptive sync interval based on battery
                delay(getSyncInterval())
            }
        }
    }

    /**
     * Adaptive sync interval: screen on -> 60s (battery-friendly); else battery/data-saver aware.
     */
    private suspend fun getSyncInterval(): Long {
        if (powerManager?.isInteractive == true) {
            return AgentConstants.SYNC_INTERVAL_SCREEN_ON_MS
        }
        val batteryLevel = getBatteryLevel()
        val isDataSaver = configRepository.dataSaverEnabled.first()
        return when {
            batteryLevel < AgentConstants.BATTERY_LOW_THRESHOLD -> {
                Timber.v("Battery low ($batteryLevel%) - using extended sync interval")
                AgentConstants.SYNC_INTERVAL_BATTERY_LOW_MS
            }
            isDataSaver && !isWifiConnected() -> {
                Timber.v("Data Saver active, no WiFi - using extended sync interval")
                AgentConstants.SYNC_INTERVAL_BATTERY_LOW_MS
            }
            else -> AgentConstants.SYNC_INTERVAL_MS
        }
    }

    /**
     * Get current battery level as percentage (0-100).
     */
    private fun getBatteryLevel(): Int {
        val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as? android.os.BatteryManager
        return batteryManager?.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: 100
    }

    /**
     * Register for network connectivity changes to auto-sync on reconnection.
     */
    private fun registerNetworkCallback() {
        try {
            val request = NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build()

            networkCallback = object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    Timber.i("Network available - triggering sync")
                    // Reset failure count on new network
                    consecutiveFailures = 0
                    forceSync()
                }

                override fun onLost(network: Network) {
                    Timber.i("Network lost")
                }
            }

            connectivityManager.registerNetworkCallback(request, networkCallback!!)
        } catch (e: Exception) {
            Timber.e(e, "Failed to register network callback")
        }
    }

    fun forceSync() {
        reporterScope.launch {
            try {
                doSync()
            } catch (e: Exception) {
                Timber.e(e, "Error in Force Sync")
            }
        }
    }

    private suspend fun doSync() {
        // Prevent concurrent syncs
        if (isSyncing) {
            Timber.v("Sync already in progress, skipping")
            return
        }

        if (!configRepository.isPaired.first()) {
            return
        }

        // Check exponential backoff
        if (!shouldAttemptSync()) {
            Timber.v("Backoff active, skipping sync attempt")
            return
        }

        val isDataSaver = configRepository.dataSaverEnabled.first()
        
        if (isDataSaver && !isWifiConnected()) {
            Timber.d("Data Saver active & NO Wi-Fi - skipping sync")
            return
        }

        isSyncing = true
        try {
            syncLogs()
        } finally {
            isSyncing = false
        }
    }

    /**
     * Check if we should attempt sync based on exponential backoff.
     */
    private fun shouldAttemptSync(): Boolean {
        if (consecutiveFailures == 0) return true

        val backoffMs = calculateBackoff()
        val timeSinceLastAttempt = System.currentTimeMillis() - lastSyncAttempt

        return timeSinceLastAttempt >= backoffMs
    }

    /**
     * Calculate exponential backoff delay based on consecutive failures.
     * Max backoff is 5 minutes.
     */
    private fun calculateBackoff(): Long {
        // Base: 5 seconds, doubles each failure, max 5 minutes
        val baseMs = 5_000L
        val maxMs = 5 * 60 * 1000L // 5 minutes
        val backoff = baseMs * (1L shl minOf(consecutiveFailures, 6))
        return minOf(backoff, maxMs)
    }

    private suspend fun syncLogs() {
        val deviceId = configRepository.getDeviceId() ?: return
        val apiKey = configRepository.getApiKey() ?: return
        
        val unsyncedLogs = usageLogDao.getUnsyncedLogs(limit = AgentConstants.MAX_UNSYNCED_LOGS_PER_BATCH)
        
        // Phase 1 Optimization: Skip HTTP heartbeat if WebSocket is connected and no logs to send
        // WebSocket ping/pong already handles presence detection
        if (unsyncedLogs.isEmpty() && webSocketClient.isConnected.value) {
            Timber.v("WebSocket connected, no logs to sync - skipping HTTP heartbeat")
            return
        }
        
        Timber.d("Syncing ${unsyncedLogs.size} logs to backend (Heartbeat)...")

        val reportItems = unsyncedLogs.map { log ->
            AgentUsageLogCreate(
                appName = log.appName,
                duration = log.durationSeconds,
                isFocused = true,
                timestamp = isoFormat.format(Date(log.timestamp))
            )
        }

        val request = AgentReportRequest(
            deviceId = deviceId,
            apiKey = apiKey,
            usageLogs = reportItems,
            clientTimestamp = isoFormat.format(Date(secureTimeProvider.getSecureCurrentTimeMillis())),
            protectionLevel = deviceOwnerEnforcer.getProtectionLevel()
        )

        lastSyncAttempt = System.currentTimeMillis()

        try {
            val response = api.reportUsage(request)
            if (response.isSuccessful) {
                // Success - reset failure count
                consecutiveFailures = 0

                if (unsyncedLogs.isNotEmpty()) {
                    Timber.i("Successfully synced ${unsyncedLogs.size} logs")
                    usageLogDao.markAsSynced(unsyncedLogs.map { it.id })
                    
                    // Cleanup old logs
                    val retentionThreshold = System.currentTimeMillis() - AgentConstants.SYNCED_LOG_RETENTION_MS
                    usageLogDao.deleteSyncedLogsOlderThan(retentionThreshold)
                } else {
                    Timber.i("Heartbeat sent successfully")
                }

                // Try to extract server time from response for sync
                syncServerTime(response)
            } else {
                handleSyncFailure("HTTP ${response.code()}")
            }
        } catch (e: Exception) {
            handleSyncFailure(e.message ?: "Unknown error")
            Timber.e(e, "Network error during sync")
        }
    }

    /**
     * Handle sync failure with exponential backoff.
     */
    private fun handleSyncFailure(reason: String) {
        consecutiveFailures++
        val nextAttemptMs = calculateBackoff()
        Timber.w("Sync failed ($reason). Failures: $consecutiveFailures, next attempt in ${nextAttemptMs}ms")
    }

    /**
     * Extract and sync server time from response headers.
     */
    private fun syncServerTime(response: retrofit2.Response<*>) {
        try {
            val dateHeader = response.headers()["Date"]
            if (dateHeader != null) {
                val serverDate = java.text.SimpleDateFormat(
                    "EEE, dd MMM yyyy HH:mm:ss zzz", 
                    Locale.US
                ).parse(dateHeader)
                serverDate?.let {
                    secureTimeProvider.syncWithServerTime(it.time)
                }
            }
        } catch (e: Exception) {
            Timber.v("Could not parse server date header: ${e.message}")
        }
    }

    fun reportShieldAlert(keyword: ShieldKeyword, packageName: String, contextText: String, bitmap: android.graphics.Bitmap?) {
        reporterScope.launch {
            try {
                val deviceId = configRepository.getDeviceId() ?: return@launch
                val apiKey = configRepository.getApiKey() ?: return@launch

                var screenshotUrl: String? = null

                // Upload screenshot if present
                if (bitmap != null) {
                    val file = saveBitmapToFile(bitmap)
                    if (file != null) {
                        screenshotUrl = uploadScreenshot(file, deviceId, apiKey)
                        file.delete() // Cleanup
                    }
                }

                val request = com.familyeye.agent.data.api.dto.ShieldAlertRequest(
                    device_id = deviceId,
                    keyword = keyword.keyword,
                    app_name = packageName,
                    detected_text = contextText.take(AgentConstants.MAX_CONTEXT_TEXT_LENGTH),
                    screenshot_url = screenshotUrl,
                    severity = keyword.severity
                )

                val response = api.reportShieldAlert(request)
                if (response.isSuccessful) {
                    Timber.i("Smart Shield Alert sent for: ${keyword.keyword}")
                } else {
                    Timber.e("Failed to send Shield Alert: ${response.code()}")
                }

            } catch (e: Exception) {
                Timber.e(e, "Error sending Shield Alert")
            }
        }
    }

    private suspend fun uploadScreenshot(file: java.io.File, deviceId: String, apiKey: String): String? {
        try {
            val requestFile = okhttp3.RequestBody.create("image/jpeg".toMediaTypeOrNull(), file)
            val body = okhttp3.MultipartBody.Part.createFormData("file", file.name, requestFile)
            
            val response = api.uploadScreenshot(deviceId, apiKey, body)
            if (response.isSuccessful) {
                return response.body()?.url
            }
        } catch (e: Exception) {
            Timber.e(e, "Screenshot upload failed")
        }
        return null
    }

    private fun saveBitmapToFile(bitmap: android.graphics.Bitmap): java.io.File? {
        return try {
            val file = java.io.File(context.cacheDir, "shield_alert_${System.currentTimeMillis()}.jpg")
            val fos = java.io.FileOutputStream(file)
            bitmap.compress(
                android.graphics.Bitmap.CompressFormat.JPEG, 
                AgentConstants.SCREENSHOT_JPEG_QUALITY, 
                fos
            )
            fos.flush()
            fos.close()
            file
        } catch (e: Exception) {
            Timber.e(e, "Failed to save bitmap")
            null
        }
    }

    private fun isWifiConnected(): Boolean {
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
    }

    /**
     * Get sync diagnostic information.
     */
    fun getDiagnostics(): Map<String, Any> {
        return mapOf(
            "consecutiveFailures" to consecutiveFailures,
            "lastSyncAttempt" to lastSyncAttempt,
            "isSyncing" to isSyncing,
            "nextBackoffMs" to calculateBackoff(),
            "isWifiConnected" to isWifiConnected()
        )
    }

    /**
     * Clean up resources.
     */
    fun stop() {
        networkCallback?.let {
            try {
                connectivityManager.unregisterNetworkCallback(it)
            } catch (e: Exception) {
                Timber.e(e, "Failed to unregister network callback")
            }
        }
        networkCallback = null
    }
}
