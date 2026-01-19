package com.familyeye.agent.service

import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.PowerManager
import com.familyeye.agent.config.AgentConstants
import com.familyeye.agent.data.local.UsageLogDao
import com.familyeye.agent.data.local.UsageLogEntity
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.familyeye.agent.time.SecureTimeProvider
import com.familyeye.agent.utils.AppInfoResolver
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.firstOrNull
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext

/**
 * Tracks app usage and enforces time limits.
 * 
 * Uses SecureTimeProvider for tamper-resistant time tracking to prevent
 * children from bypassing limits by manipulating device time.
 */
@Singleton
class UsageTracker @Inject constructor(
    @ApplicationContext private val context: Context,
    private val usageLogDao: UsageLogDao,
    private val configRepository: AgentConfigRepository,
    private val ruleEnforcer: RuleEnforcer,
    private val blockOverlayManager: BlockOverlayManager,
    private val reporter: Reporter,
    private val secureTimeProvider: SecureTimeProvider
) {
    private val trackerScope = CoroutineScope(Dispatchers.IO)
    private var lastCheckTime = secureTimeProvider.getSecureCurrentTimeMillis()
    
    // Track screen state to avoid phantom usage when screen is off
    private val powerManager by lazy {
        context.getSystemService(Context.POWER_SERVICE) as PowerManager
    }

    fun start() {
        trackerScope.launch {
            while (isActive) {
                try {
                    trackUsage()
                } catch (e: Exception) {
                    Timber.e(e, "Error in UsageTracker")
                }
                delay(AgentConstants.USAGE_TRACK_INTERVAL_MS)
            }
        }
    }

    private suspend fun trackUsage() {
        // Use secure time for tamper-resistant tracking
        val currentTime = secureTimeProvider.getSecureCurrentTimeMillis()
        val elapsedSeconds = (currentTime - lastCheckTime) / 1000
        
        if (elapsedSeconds <= 0) return

        // Skip tracking if screen is off (no phantom usage)
        if (!isScreenOn()) {
            lastCheckTime = currentTime
            return
        }

        // Skip tracking if our own overlay is showing (avoid self-counting)
        if (blockOverlayManager.isShowing()) {
            lastCheckTime = currentTime
            return
        }

        // 1. Try Real-Time Tracking (Preferred)
        val realTimePackage = AppDetectorService.currentPackage
        if (realTimePackage != null) {
            // Skip our own app
            if (realTimePackage != context.packageName) {
                logUsage(realTimePackage, elapsedSeconds.toInt())
            }
            lastCheckTime = currentTime
            return
        }

        // 2. Fallback to UsageStatsManager (If Accessibility is off)
        val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        
        // Get stats since last check (use device time for this API)
        val deviceCurrentTime = System.currentTimeMillis()
        val deviceLastCheck = deviceCurrentTime - (elapsedSeconds * 1000)
        
        val stats = usageStatsManager.queryUsageStats(
            UsageStatsManager.INTERVAL_DAILY,
            deviceLastCheck,
            deviceCurrentTime
        )

        if (!stats.isNullOrEmpty()) {
            val foregroundApp = stats
                .filter { it.totalTimeInForeground > 0 && it.packageName != context.packageName }
                .maxByOrNull { it.lastTimeUsed }

            foregroundApp?.let { app ->
                logUsage(app.packageName, elapsedSeconds.toInt())
            }
        }
        
        lastCheckTime = currentTime
    }

    private suspend fun logUsage(packageName: String, durationSeconds: Int) {
        // Use cached app name resolution
        val appName = AppInfoResolver.getAppName(context, packageName)
        Timber.d("Tracked: $appName ($packageName) for ${durationSeconds}s")
        
        // Use secure time for timestamp
        val secureTimestamp = secureTimeProvider.getSecureCurrentTimeMillis()
        
        usageLogDao.insert(
            UsageLogEntity(
                appName = appName,
                packageName = packageName,
                durationSeconds = durationSeconds,
                timestamp = secureTimestamp
            )
        )

        // Enforce Time Limit immediately
        val totalUsage = getTotalUsageToday()
        
        // 1. Global Daily Limit
        if (ruleEnforcer.isDailyLimitExceeded(totalUsage)) {
            reporter.forceSync() // Force immediate sync on block!
            triggerOverlay(packageName, com.familyeye.agent.ui.screens.BlockType.DEVICE_LIMIT)
            return
        }
        
        // 2. Device Lock
        if (ruleEnforcer.isDeviceLocked()) {
            triggerOverlay(packageName, com.familyeye.agent.ui.screens.BlockType.DEVICE_LOCK)
            return
        }

        // 3. Global Schedule
        if (ruleEnforcer.isDeviceScheduleBlocked()) {
            triggerOverlay(packageName, com.familyeye.agent.ui.screens.BlockType.DEVICE_SCHEDULE)
            return
        }
        
        // 4. App Schedule
        if (ruleEnforcer.isAppScheduleBlocked(packageName)) {
            triggerOverlay(packageName, com.familyeye.agent.ui.screens.BlockType.APP_SCHEDULE)
            return
        }
        
        // 5. App Time Limit
        if (ruleEnforcer.isAppTimeLimitExceeded(packageName, getUsageToday(packageName))) {
            reporter.forceSync() // Force immediate sync on block!
            triggerOverlay(packageName, com.familyeye.agent.ui.screens.BlockType.APP_LIMIT)
        }
    }

    private suspend fun triggerOverlay(
        packageName: String, 
        blockType: com.familyeye.agent.ui.screens.BlockType = com.familyeye.agent.ui.screens.BlockType.GENERIC
    ) {
        Timber.w("Core Limit exceeded for $packageName! Triggering block via AppDetector.")
        try {
            kotlinx.coroutines.withContext(Dispatchers.Main) {
                // Use the centralized blocking logic in AppDetectorService
                // This ensures consistency: Home Action + Delay + Overlay Protection
                AppDetectorService.instance?.blockApp(packageName, blockType) 
                    ?: run {
                        // Fallback if service instance not available (rare)
                        Timber.w("AppDetectorService instance null, falling back to direct overlay")
                        blockOverlayManager.show(packageName, blockType)
                    }
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to trigger overlay from tracker")
        }
    }

    /**
     * Check if the screen is currently on.
     */
    private fun isScreenOn(): Boolean {
        return powerManager.isInteractive
    }

    suspend fun getUsageToday(packageName: String): Int {
        val startOfDay = secureTimeProvider.getSecureStartOfDay()
        return usageLogDao.getUsageDurationForPackage(packageName, startOfDay) ?: 0
    }

    suspend fun getTotalUsageToday(): Int {
        val startOfDay = secureTimeProvider.getSecureStartOfDay()
        return usageLogDao.getTotalUsageToday(startOfDay).firstOrNull() ?: 0
    }

    /**
     * Get diagnostic info for debugging time-related issues.
     */
    fun getDiagnostics(): Map<String, Any> {
        return mapOf(
            "lastCheckTime" to lastCheckTime,
            "isScreenOn" to isScreenOn(),
            "currentPackage" to (AppDetectorService.currentPackage ?: "null"),
            "timeProvider" to secureTimeProvider.getDiagnostics()
        )
    }
}
