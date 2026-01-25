package com.familyeye.agent.service

import com.familyeye.agent.data.api.dto.RuleDTO
import com.familyeye.agent.policy.AppBlockPolicy
import com.familyeye.agent.policy.DeviceLockPolicy
import com.familyeye.agent.policy.LimitPolicy
import com.familyeye.agent.policy.SchedulePolicy
import com.familyeye.agent.policy.SettingsProtectionPolicy

import com.familyeye.agent.utils.AppInfoResolver
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Facade for rule enforcement that delegates to specialized policy classes.
 * 
 * This class maintains the same public API for backward compatibility
 * while internally using the modular policy classes.
 */
@Singleton
class RuleEnforcer @Inject constructor(
    @ApplicationContext private val context: android.content.Context,
    private val ruleRepository: com.familyeye.agent.data.repository.RuleRepository,
    private val configRepository: com.familyeye.agent.data.repository.AgentConfigRepository
) {
    // Cache rules in memory for synchronous access (volatile for thread safety)
    @Volatile
    private var cachedRules: List<RuleDTO> = emptyList()

    init {
        // Observe rules from repository immediately
        CoroutineScope(Dispatchers.IO).launch {
            ruleRepository.getRules().collect { newRules ->
                Timber.d("RuleEnforcer: Rules updated from DB: ${newRules.size}")
                cachedRules = newRules
            }
        }
    }

    private fun getRules(): List<RuleDTO> = cachedRules

    /**
     * Check if an app is blocked by any app_block rule.
     */
    fun isAppBlocked(packageName: String): Boolean {
        val appLabel = getAppName(packageName)
        val isBlocked = AppBlockPolicy.isBlocked(packageName, appLabel, getRules())
        if (isBlocked) {
            Timber.w("App blocked: $packageName ($appLabel)")
        }
        return isBlocked
    }

    /**
     * Get the human-readable name for an app.
     */
    fun getAppName(packageName: String): String {
        return AppInfoResolver.getAppName(context, packageName)
    }

    /**
     * Check if the device is currently locked.
     */
    fun isDeviceLocked(): Boolean {
        return DeviceLockPolicy.isLocked(getRules())
    }

    /**
     * Check if the daily limit is exceeded.
     */
    fun isDailyLimitExceeded(totalUsageSeconds: Int): Boolean {
        val exceeded = LimitPolicy.isDailyLimitExceeded(totalUsageSeconds, getRules())
        if (exceeded) {
            Timber.w("Daily limit exceeded: $totalUsageSeconds seconds")
        }
        return exceeded
    }

    /**
     * Check if the device is currently in a blocked schedule period.
     */
    fun isDeviceScheduleBlocked(): Boolean {
        return SchedulePolicy.isDeviceScheduleBlocked(getRules())
    }

    /**
     * Check if an app is currently in a blocked schedule period.
     */
    fun isAppScheduleBlocked(packageName: String): Boolean {
        val appLabel = getAppName(packageName)
        return SchedulePolicy.isAppScheduleBlocked(packageName, appLabel, getRules())
    }

    /**
     * Get the active app schedule rule for a package.
     */
    fun getActiveAppScheduleRule(packageName: String): RuleDTO? {
        val appLabel = getAppName(packageName)
        return SchedulePolicy.getActiveAppScheduleRule(packageName, appLabel, getRules())
    }

    /**
     * Get the active device schedule rule.
     */
    fun getActiveDeviceScheduleRule(): RuleDTO? {
        return SchedulePolicy.getActiveDeviceScheduleRule(getRules())
    }

    /**
     * Check if an app's time limit is exceeded.
     */
    fun isAppTimeLimitExceeded(packageName: String, usageSeconds: Int): Boolean {
        val appLabel = getAppName(packageName)
        val rules = getRules()
        
        val exceeded = LimitPolicy.isAppTimeLimitExceeded(packageName, appLabel, usageSeconds, rules)
        if (exceeded) {
            Timber.w("App time limit exceeded: $packageName ($usageSeconds seconds)")
        }
        return exceeded
    }



    /**
     * Get remaining daily limit time in seconds.
     * @return Remaining seconds, or null if no limit
     */
    fun getRemainingDailyTime(totalUsageSeconds: Int): Int? {
        val rule = getRules().find { 
            it.enabled && it.ruleType == "daily_limit" && it.timeLimit != null 
        } ?: return null
        val limitSeconds = rule.timeLimit!! * 60
        return maxOf(0, limitSeconds - totalUsageSeconds)
    }

    /**
     * Get remaining app time limit in seconds.
     * @return Remaining seconds, or null if no limit
     */
    fun getRemainingAppTime(packageName: String, usageSeconds: Int): Int? {
        val appLabel = getAppName(packageName)
        return LimitPolicy.getRemainingAppTime(packageName, appLabel, usageSeconds, getRules())
    }

    /**
     * Get current rule count for diagnostics.
     */
    fun getRuleCount(): Int = cachedRules.size

    /**
     * Get diagnostic information.
     */
    fun getDiagnostics(): Map<String, Any> {
        return mapOf(
            "ruleCount" to cachedRules.size,
            "deviceLocked" to isDeviceLocked(),
            "deviceScheduleBlocked" to isDeviceScheduleBlocked(),
            "unlockActive" to isUnlockSettingsActive(),
            "settingsProtection" to getSettingsProtectionLevel().name
        )
    }
    
    /**
     * Get the current settings protection level.
     * Reads directly from configRepository to ensure latest value.
     * Default is FULL for maximum security.
     */
    fun getSettingsProtectionLevel(): SettingsProtectionPolicy.ProtectionLevel {
        // Always read fresh from config to ensure immediate updates
        val level = configRepository.getSettingsProtection()
        return SettingsProtectionPolicy.fromString(level)
    }
}
