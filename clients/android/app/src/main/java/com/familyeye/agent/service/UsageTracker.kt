package com.familyeye.agent.service

import android.app.usage.UsageStatsManager
import android.content.Context
import com.familyeye.agent.data.local.UsageLogDao
import com.familyeye.agent.data.local.UsageLogEntity
import com.familyeye.agent.data.repository.AgentConfigRepository
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

@Singleton
class UsageTracker @Inject constructor(
    @ApplicationContext private val context: Context,
    private val usageLogDao: UsageLogDao,
    private val configRepository: AgentConfigRepository,
    private val ruleEnforcer: RuleEnforcer,
    private val blockOverlayManager: BlockOverlayManager
) {
    private val trackerScope = CoroutineScope(Dispatchers.IO)
    private var lastCheckTime = System.currentTimeMillis()

    fun start() {
        trackerScope.launch {
            while (isActive) {
                try {
                    trackUsage()
                } catch (e: Exception) {
                    Timber.e(e, "Error in UsageTracker")
                }
                delay(5000) // Poll every 5 seconds
            }
        }
    }

    private suspend fun trackUsage() {
        val currentTime = System.currentTimeMillis()
        val elapsedSeconds = (currentTime - lastCheckTime) / 1000
        
        if (elapsedSeconds <= 0) return

        // 1. Try Real-Time Tracking (Preferred)
        val realTimePackage = AppDetectorService.currentPackage
        if (realTimePackage != null) {
            // Log usage for the current real-time app
            logUsage(realTimePackage, elapsedSeconds.toInt())
            lastCheckTime = currentTime
            return
        }

        // 2. Fallback to UsageStatsManager (If Accessibility is off)
        val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        
        // Get stats since last check
        val stats = usageStatsManager.queryUsageStats(
            UsageStatsManager.INTERVAL_DAILY,
            lastCheckTime,
            currentTime
        )

        if (!stats.isNullOrEmpty()) {
             val foregroundApp = stats
                .filter { it.totalTimeInForeground > 0 }
                .maxByOrNull { it.lastTimeUsed }

            foregroundApp?.let { app ->
                if (app.lastTimeUsed > lastCheckTime) {
                    logUsage(app.packageName, elapsedSeconds.toInt())
                }
            }
        }
        
        lastCheckTime = currentTime
    }

    private suspend fun logUsage(packageName: String, durationSeconds: Int) {
        val appName = getAppName(packageName)
        Timber.d("Tracked: $appName ($packageName) for ${durationSeconds}s")
        
        usageLogDao.insert(
            UsageLogEntity(
                appName = appName,
                packageName = packageName,
                durationSeconds = durationSeconds,
                timestamp = System.currentTimeMillis()
            )
        )

        // Enforce Time Limit immediately
        val totalUsage = getTotalUsageToday()
        // 1. Global Daily Limit
        if (ruleEnforcer.isDailyLimitExceeded(totalUsage)) {
             triggerOverlay(packageName)
             return
        }
        
        // 2. Global Schedule
        if (ruleEnforcer.isScheduleBlocked()) {
             triggerOverlay(packageName)
             return
        }
        
        // 3. App Time Limit
        if (ruleEnforcer.isAppTimeLimitExceeded(packageName, getUsageToday(packageName))) {
            triggerOverlay(packageName)
        }
    }

    private suspend fun triggerOverlay(packageName: String) {
        Timber.w("Core Limit exceeded for $packageName! Showing overlay.")
        try {
            kotlinx.coroutines.withContext(Dispatchers.Main) {
                blockOverlayManager.show(packageName)
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to trigger overlay from tracker")
        }
    }

    private fun getAppName(packageName: String): String {
        return try {
            val packageManager = context.packageManager
            val info = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: Exception) {
            packageName.split(".").last()
        }
    }

    suspend fun getUsageToday(packageName: String): Int {
        val startOfDay = getStartOfDay()
        return usageLogDao.getUsageDurationForPackage(packageName, startOfDay) ?: 0
    }

    suspend fun getTotalUsageToday(): Int {
        val startOfDay = getStartOfDay()
        // Dao returns Flow, we need single value. But Dao also likely supports suspend fun if we change it?
        // UsageLogDao.getTotalUsageToday returns Flow<Int?>.
        // We can capture the first value.
        return usageLogDao.getTotalUsageToday(startOfDay).firstOrNull() ?: 0
    }

    private fun getStartOfDay(): Long {
        val calendar = java.util.Calendar.getInstance()
        calendar.set(java.util.Calendar.HOUR_OF_DAY, 0)
        calendar.set(java.util.Calendar.MINUTE, 0)
        calendar.set(java.util.Calendar.SECOND, 0)
        calendar.set(java.util.Calendar.MILLISECOND, 0)
        return calendar.timeInMillis
    }
}
