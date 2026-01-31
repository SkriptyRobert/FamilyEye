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
    private val blocker: com.familyeye.agent.enforcement.Blocker,
    private val usageRepository: com.familyeye.agent.data.repository.UsageRepository
) {
    private val trackerScope = CoroutineScope(Dispatchers.IO)
    
    // Recovery Optimization: Persist lastCheckTime to handle service restarts
    // When service dies and restarts, we want to know when we stopped tracking
    private val prefs by lazy { 
        context.getSharedPreferences(AgentConstants.PREFS_NAME, Context.MODE_PRIVATE) 
    }
    
    // Cache lastCheckTime; prefs.getLong("key", NOW) re-evaluates NOW each read -> elapsed=0 bug
    @Volatile
    private var _lastCheckTime: Long = -1L  // Sentinel value = not initialized
    
    private var lastCheckTime: Long
        get() {
            if (_lastCheckTime == -1L) {
                // First access: load from prefs or initialize to NOW (only once)
                val stored = prefs.getLong("last_usage_check_time", -1L)
                val now = secureTimeProvider.getSecureCurrentTimeMillis()
                
                _lastCheckTime = if (stored == -1L) {
                    // First ever run: set to NOW and persist
                    prefs.edit().putLong("last_usage_check_time", now).apply()
                    Timber.d("UsageTracker: Initialized lastCheckTime to NOW = $now")
                    now
                } else {
                    // Check if stored time is too old (app was killed/restarted)
                    // If gap > 60 seconds, reset to NOW to prevent phantom usage
                    val gapSeconds = (now - stored) / 1000
                    if (gapSeconds > 60) {
                        Timber.w("UsageTracker: Large gap detected (${gapSeconds}s). Resetting lastCheckTime to NOW to prevent phantom usage.")
                        prefs.edit().putLong("last_usage_check_time", now).apply()
                        now
                    } else {
                        Timber.d("UsageTracker: Restored lastCheckTime from prefs = $stored (gap: ${gapSeconds}s)")
                        stored
                    }
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

    // In-memory buffer for usage logs; flushed every USAGE_FLUSH_INTERVAL_MS or on screen off (battery-friendly)
    private val usageBuffer = mutableListOf<UsageLogEntity>()
    private var lastFlushTime: Long = 0L

    fun start() {
        trackerScope.launch {
            Timber.i("UsageTracker: Starting fresh tracking (no reconciliation)")
            lastFlushTime = secureTimeProvider.getSecureCurrentTimeMillis()
            while (isActive) {
                try {
                    trackUsage()
                    if (isScreenOn()) {
                        val now = secureTimeProvider.getSecureCurrentTimeMillis()
                        if (now - lastFlushTime >= AgentConstants.USAGE_FLUSH_INTERVAL_MS) {
                            flushBuffer()
                            lastFlushTime = now
                        }
                    }
                } catch (e: Exception) {
                    Timber.e(e, "Error in UsageTracker")
                }
                val delayMs = if (isScreenOn()) AgentConstants.USAGE_TRACK_INTERVAL_MS else AgentConstants.USAGE_TRACK_INTERVAL_SCREEN_OFF_MS
                delay(delayMs)
            }
        }
    }

    /**
     * Reconcile local logs with system UsageStatsManager.
     * 
     * This fills in gaps created when the Agent service was killed or stopped,
     * ensuring 100% accuracy even when offline.
     */
    suspend fun reconcileWithSystemStats() {
        try {
            Timber.i("UsageTracker: Starting local reconciliation...")
            val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            
            val startOfDay = secureTimeProvider.getSecureStartOfDay()
            val endTime = System.currentTimeMillis()
            
            // Query stats for the entire current day using INTERVAL_DAILY
            val stats = usageStatsManager.queryUsageStats(
                UsageStatsManager.INTERVAL_DAILY,
                startOfDay, 
                endTime
            )
            
            if (stats.isNullOrEmpty()) {
                Timber.v("UsageTracker: No UsageStats available for reconciliation")
                return
            }

            stats.forEach { stat ->
                val pkg = stat.packageName
                val systemSeconds = (stat.totalTimeInForeground / 1000).toInt()
                
                // Skip noise, ourselves, and launchers
                if (systemSeconds <= 10 || pkg == context.packageName) return@forEach
                if (com.familyeye.agent.utils.PackageMatcher.isLauncher(pkg)) return@forEach
                
                // Get our local count
                val localSeconds = usageLogDao.getUsageDurationForPackage(pkg, startOfDay) ?: 0
                
                // If system has significantly more, it means we missed a chunk while dead
                if (systemSeconds > localSeconds + 30) { // 30s tolerance for overlapping sessions
                    val delta = systemSeconds - localSeconds
                    
                    // BUGFIX: Limit reconciliation to max 5 minutes per app
                    // Large deltas usually indicate stale system stats, not real gaps
                    val cappedDelta = minOf(delta, 300)  // Max 5 minutes
                    
                    if (cappedDelta > 0) {
                        Timber.w("UsageTracker: GAP detected for $pkg! System=$systemSeconds, Local=$localSeconds. Reconciliation adding ${cappedDelta}s (capped from ${delta}s)")
                        logUsage(pkg, cappedDelta)
                    }
                }
            }
            Timber.i("UsageTracker: Reconciliation complete")
        } catch (e: Exception) {
            Timber.e(e, "Error during usage reconciliation")
        }
    }

    private suspend fun trackUsage() {
        // Use secure time for tamper-resistant tracking
        val currentTime = secureTimeProvider.getSecureCurrentTimeMillis()
        
        // Handle negative time jumps (server sync) gracefullly
        if (lastCheckTime > currentTime) {
            Timber.w("Time jump detected (backwards). Resetting lastCheckTime.")
            lastCheckTime = currentTime
            return // Skip this tick
        }

        val elapsedSeconds = (currentTime - lastCheckTime) / 1000
        
        if (elapsedSeconds <= 0) {
            // Wait for enough time to pass
            return
        }

        // Skip tracking if screen is off (no phantom usage); flush buffer before sleep
        if (!isScreenOn()) {
            Timber.v("TrackUsage: Screen OFF, flushing buffer and updating lastCheckTime")
            flushBuffer()
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
        val appName = AppInfoResolver.getAppName(context, packageName)
        Timber.d("Tracked: $appName ($packageName) for ${durationSeconds}s")
        val secureTimestamp = secureTimeProvider.getSecureCurrentTimeMillis()
        val entity = UsageLogEntity(
            appName = appName,
            packageName = packageName,
            durationSeconds = durationSeconds,
            timestamp = secureTimestamp
        )
        synchronized(usageBuffer) { usageBuffer.add(entity) }

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

    private fun isScreenOn(): Boolean = powerManager.isInteractive

    private suspend fun flushBuffer() {
        val toInsert = synchronized(usageBuffer) {
            if (usageBuffer.isEmpty()) return
            usageBuffer.toList().also { usageBuffer.clear() }
        }
        if (toInsert.isNotEmpty()) {
            usageLogDao.insertAll(toInsert)
            Timber.v("UsageTracker: Flushed ${toInsert.size} usage entries to DB")
        }
    }

    suspend fun getUsageToday(packageName: String): Int {
        val startOfDay = secureTimeProvider.getSecureStartOfDay()
        val localUsage = usageLogDao.getUsageDurationForPackage(packageName, startOfDay) ?: 0
        val bufferSum = synchronized(usageBuffer) {
            usageBuffer.filter { it.packageName == packageName }.sumOf { it.durationSeconds }
        }
        val appName = AppInfoResolver.getAppName(context, packageName)
        val remoteUsage = usageRepository.getRemoteAppUsage(appName)
        return maxOf(localUsage + bufferSum, remoteUsage)
    }

    suspend fun getTotalUsageToday(): Int {
        val startOfDay = secureTimeProvider.getSecureStartOfDay()
        val localTotal = usageLogDao.getTotalUsageToday(startOfDay).firstOrNull() ?: 0
        val bufferSum = synchronized(usageBuffer) { usageBuffer.sumOf { it.durationSeconds } }
        val remoteTotal = usageRepository.getRemoteDailyUsage()
        return maxOf(localTotal + bufferSum, remoteTotal)
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
