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
    private val secureTimeProvider: SecureTimeProvider,
    private val enforcementService: com.familyeye.agent.enforcement.EnforcementService,
    private val blocker: com.familyeye.agent.enforcement.Blocker
) {
    private val trackerScope = CoroutineScope(Dispatchers.IO)
    
    // Recovery Optimization: Persist lastCheckTime to handle service restarts
    // When service dies and restarts, we want to know when we stopped tracking
    private val prefs by lazy { 
        context.getSharedPreferences(AgentConstants.PREFS_NAME, Context.MODE_PRIVATE) 
    }
    
    // BUG FIX: Cache lastCheckTime in memory to prevent re-evaluation of default on every read
    // The original bug: prefs.getLong("key", NOW) re-evaluates NOW every time, making elapsed = 0
    @Volatile
    private var _lastCheckTime: Long = -1L  // Sentinel value = not initialized
    
    private var lastCheckTime: Long
        get() {
            if (_lastCheckTime == -1L) {
                // First access: load from prefs or initialize to NOW (only once)
                val stored = prefs.getLong("last_usage_check_time", -1L)
                _lastCheckTime = if (stored == -1L) {
                    // First ever run: set to NOW and persist
                    val now = secureTimeProvider.getSecureCurrentTimeMillis()
                    prefs.edit().putLong("last_usage_check_time", now).apply()
                    Timber.d("UsageTracker: Initialized lastCheckTime to NOW = $now")
                    now
                } else {
                    Timber.d("UsageTracker: Restored lastCheckTime from prefs = $stored")
                    stored
                }
            }
            return _lastCheckTime
        }
        set(value) {
            _lastCheckTime = value
            prefs.edit().putLong("last_usage_check_time", value).apply()
        }
    
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
        
        if (elapsedSeconds <= 0) {
            Timber.v("TrackUsage: elapsedSeconds <= 0, skipping")
            return
        }

        // Skip tracking if screen is off (no phantom usage)
        if (!isScreenOn()) {
            Timber.v("TrackUsage: Screen OFF, updating lastCheckTime only")
            lastCheckTime = currentTime
            return
        }

        // Skip tracking if our own overlay is showing (avoid self-counting)
        if (blockOverlayManager.isShowing()) {
            lastCheckTime = currentTime
            
            // Critical Fix: Even if blocked, we must periodically re-check enforcement.
            // If the schedule ended or limits were raised, AppDetectorService needs to know 
            // to hide the overlay.
            Timber.v("Overlay active - requesting enforcement re-check")
            AppDetectorService.instance?.recheckEnforcement()
            
            return
        }

        // 1. Try Real-Time Tracking (Preferred)
        val realTimePackage = AppDetectorService.currentPackage
        Timber.d("TrackUsage: elapsed=${elapsedSeconds}s, screenOn=true, realTimePackage=$realTimePackage")
        
        if (realTimePackage != null) {
            // Skip our own app
            if (realTimePackage != context.packageName) {
                logUsage(realTimePackage, elapsedSeconds.toInt())
            } else {
                Timber.v("TrackUsage: Skipping own package: $realTimePackage")
            }
            lastCheckTime = currentTime
            return
        }

        // 2. Fallback to UsageStatsManager (If Accessibility is off)
        Timber.d("TrackUsage: Accessibility currentPackage null, trying UsageStatsManager fallback")
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

            if (foregroundApp != null) {
                Timber.d("TrackUsage: Fallback found foreground app: ${foregroundApp.packageName}")
                logUsage(foregroundApp.packageName, elapsedSeconds.toInt())
            } else {
                Timber.w("TrackUsage: UsageStats returned empty foreground after filter (stats count: ${stats.size})")
            }
        } else {
            Timber.w("TrackUsage: UsageStatsManager returned null/empty stats")
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

        // Enforce Rules Strategy:
        // 1. Check UNIVERSAL rules (Blacklist, Lock, Schedule) -> via EnforcementService
        // 2. Check TIME LIMITS (Requires duration) -> via EnforcementService.evaluateTimeLimits
        
        // Step 1: Structural Checks (Fast, no time limits)
        val structuralResult = enforcementService.evaluate(packageName)
        when (structuralResult) {
            is com.familyeye.agent.enforcement.EnforcementResult.Block -> {
                 Timber.w("UsageTracker: Blocking $packageName due to ${structuralResult.blockType}")
                 // Force sync if we hit a wall to ensure backend knows
                 reporter.forceSync() 
                 blocker.block(packageName, structuralResult.blockType, structuralResult.scheduleInfo)
                 return
            }
            is com.familyeye.agent.enforcement.EnforcementResult.TamperingDetected -> {
                 Timber.e("UsageTracker: Tampering detected: ${structuralResult.reason}")
                 blocker.block(packageName, com.familyeye.agent.ui.screens.BlockType.TAMPERING)
                 return
            }
            com.familyeye.agent.enforcement.EnforcementResult.Whitelisted -> {
                // Don't check limits for whitelisted apps? Or should we?
                // Usually whitelist means "System Critical" -> No limits.
                return
            }
            com.familyeye.agent.enforcement.EnforcementResult.Allow -> {
                // Proceed to time limits
            }
        }
        
        // Step 2: Time Limits (Requires duration calculation)
        val totalUsage = getTotalUsageToday()
        val appUsage = getUsageToday(packageName)
        
        val limitResult = enforcementService.evaluateTimeLimits(packageName, appUsage, totalUsage)
        
        if (limitResult is com.familyeye.agent.enforcement.EnforcementResult.Block) {
             Timber.w("UsageTracker: Blocking $packageName due to TIME LIMIT (${limitResult.blockType})")
             reporter.forceSync()
             blocker.block(packageName, limitResult.blockType)
        }
    }

    private suspend fun triggerOverlay(
        packageName: String, 
        blockType: com.familyeye.agent.ui.screens.BlockType = com.familyeye.agent.ui.screens.BlockType.GENERIC,
        scheduleInfo: String? = null
    ) {
        Timber.w("Core Limit exceeded for $packageName! Triggering block via AppDetector.")
        try {
            kotlinx.coroutines.withContext(Dispatchers.Main) {
                // Use the centralized blocking logic in AppDetectorService
                // This ensures consistency: Home Action + Delay + Overlay Protection
                AppDetectorService.instance?.blockApp(packageName, blockType, scheduleInfo) 
                    ?: run {
                        // Fallback if service instance not available (rare)
                        Timber.w("AppDetectorService instance null, falling back to direct overlay")
                        blockOverlayManager.show(packageName, blockType, scheduleInfo)
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
