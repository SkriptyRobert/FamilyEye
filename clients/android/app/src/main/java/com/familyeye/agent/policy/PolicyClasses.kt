package com.familyeye.agent.policy

import com.familyeye.agent.data.api.dto.RuleDTO
import com.familyeye.agent.utils.PackageMatcher
import com.familyeye.agent.utils.TimeUtils

/**
 * Sealed class representing the result of a policy evaluation.
 */
sealed class PolicyResult {
    object Allow : PolicyResult()
    data class Block(val reason: String, val rule: RuleDTO? = null) : PolicyResult()
}

/**
 * Policy for checking app blocking rules.
 */
object AppBlockPolicy {
    
    /**
     * Check if an app is blocked by any app_block rule.
     * 
     * @param packageName The package name to check
     * @param appLabel The display name of the app
     * @param rules All current rules
     * @return true if the app is blocked
     */
    fun isBlocked(packageName: String, appLabel: String, rules: List<RuleDTO>): Boolean {
        return rules.any { rule ->
            if (!rule.enabled || rule.ruleType != "app_block") return@any false
            val ruleName = rule.appName ?: return@any false
            PackageMatcher.matches(packageName, ruleName, appLabel)
        }
    }

    /**
     * Get the blocking rule for an app, if any.
     */
    fun getBlockingRule(packageName: String, appLabel: String, rules: List<RuleDTO>): RuleDTO? {
        return rules.find { rule ->
            rule.enabled && 
            rule.ruleType == "app_block" && 
            rule.appName != null &&
            PackageMatcher.matches(packageName, rule.appName!!, appLabel)
        }
    }
}

/**
 * Policy for checking device and app schedules.
 */
object SchedulePolicy {
    
    /**
     * Check if the device is currently in a blocked schedule period.
     * Device schedules have null or empty appName.
     * 
     * @param rules All current rules
     * @return true if device is currently schedule-blocked
     */
    fun isDeviceScheduleBlocked(rules: List<RuleDTO>): Boolean {
        return rules.any { rule ->
            if (!rule.enabled || rule.ruleType != "schedule") return@any false
            if (!rule.appName.isNullOrEmpty()) return@any false // Skip app-specific schedules
            isRuleActiveNow(rule)
        }
    }

    /**
     * Get the active device schedule rule, if any.
     */
    fun getActiveDeviceScheduleRule(rules: List<RuleDTO>): RuleDTO? {
        return rules.find { rule ->
            rule.enabled && 
            rule.ruleType == "schedule" && 
            rule.appName.isNullOrEmpty() &&
            isRuleActiveNow(rule)
        }
    }

    /**
     * Check if an app is currently in a blocked schedule period.
     * 
     * @param packageName The package name to check
     * @param appLabel The display name of the app
     * @param rules All current rules
     * @return true if app is currently schedule-blocked
     */
    fun isAppScheduleBlocked(packageName: String, appLabel: String, rules: List<RuleDTO>): Boolean {
        return rules.any { rule ->
            if (!rule.enabled || rule.ruleType != "schedule") return@any false
            val ruleName = rule.appName ?: return@any false
            if (!PackageMatcher.matches(packageName, ruleName, appLabel)) return@any false
            isRuleActiveNow(rule)
        }
    }

    /**
     * Get the active app schedule rule, if any.
     */
    fun getActiveAppScheduleRule(packageName: String, appLabel: String, rules: List<RuleDTO>): RuleDTO? {
        return rules.find { rule ->
            rule.enabled && 
            rule.ruleType == "schedule" && 
            rule.appName != null &&
            PackageMatcher.matches(packageName, rule.appName!!, appLabel) &&
            isRuleActiveNow(rule)
        }
    }

    /**
     * Check if a schedule rule is currently active (day and time match).
     */
    private fun isRuleActiveNow(rule: RuleDTO): Boolean {
        // Check day of week
        val currentDay = TimeUtils.getCurrentDayOfWeek()
        val days = rule.scheduleDays
        if (!days.isNullOrEmpty()) {
            val allowedDays = days.split(",").mapNotNull { it.trim().toIntOrNull() }
            if (!allowedDays.contains(currentDay)) {
                return false
            }
        }

        // Check time range
        val start = rule.scheduleStartTime ?: return false
        val end = rule.scheduleEndTime ?: return false
        
        return TimeUtils.isCurrentTimeInRange(start, end)
    }
}

/**
 * Policy for checking time limits (daily and per-app).
 */
object LimitPolicy {
    
    /**
     * Check if the daily device limit is exceeded.
     * 
     * @param totalUsageSeconds Total usage time today in seconds
     * @param rules All current rules
     * @return true if daily limit is exceeded
     */
    fun isDailyLimitExceeded(totalUsageSeconds: Int, rules: List<RuleDTO>): Boolean {
        return rules.any { rule ->
            if (!rule.enabled || rule.ruleType != "daily_limit") return@any false
            val limitMinutes = rule.timeLimit ?: return@any false
            val limitSeconds = limitMinutes * 60
            totalUsageSeconds >= limitSeconds
        }
    }

    /**
     * Get the daily limit rule if one exists and is exceeded.
     */
    fun getExceededDailyLimitRule(totalUsageSeconds: Int, rules: List<RuleDTO>): RuleDTO? {
        return rules.find { rule ->
            rule.enabled && 
            rule.ruleType == "daily_limit" && 
            rule.timeLimit != null &&
            totalUsageSeconds >= (rule.timeLimit!! * 60)
        }
    }

    /**
     * Check if an app's time limit is exceeded.
     * 
     * @param packageName The package name to check
     * @param appLabel The display name of the app
     * @param appUsageSeconds Usage time for this app today in seconds
     * @param rules All current rules
     * @return true if app time limit is exceeded
     */
    fun isAppTimeLimitExceeded(
        packageName: String, 
        appLabel: String, 
        appUsageSeconds: Int, 
        rules: List<RuleDTO>
    ): Boolean {
        return rules.any { rule ->
            if (!rule.enabled || rule.ruleType != "time_limit") return@any false
            val ruleName = rule.appName ?: return@any false
            if (!PackageMatcher.matches(packageName, ruleName, appLabel)) return@any false
            val limitMinutes = rule.timeLimit ?: return@any false
            appUsageSeconds >= (limitMinutes * 60)
        }
    }

    /**
     * Get remaining time for an app's limit.
     * 
     * @return Remaining seconds, or null if no limit exists
     */
    fun getRemainingAppTime(
        packageName: String,
        appLabel: String,
        appUsageSeconds: Int,
        rules: List<RuleDTO>
    ): Int? {
        val rule = rules.find { r ->
            r.enabled && 
            r.ruleType == "time_limit" && 
            r.appName != null &&
            PackageMatcher.matches(packageName, r.appName!!, appLabel)
        } ?: return null

        val limitSeconds = (rule.timeLimit ?: return null) * 60
        return maxOf(0, limitSeconds - appUsageSeconds)
    }
}

/**
 * Policy for device lock functionality.
 */
object DeviceLockPolicy {
    
    /**
     * Check if the device is currently locked.
     * 
     * @param rules All current rules
     * @return true if device is locked
     */
    fun isLocked(rules: List<RuleDTO>): Boolean {
        return rules.any { rule ->
            rule.enabled && rule.ruleType == "lock_device"
        }
    }

    /**
     * Get the active lock rule, if any.
     */
    fun getLockRule(rules: List<RuleDTO>): RuleDTO? {
        return rules.find { rule ->
            rule.enabled && rule.ruleType == "lock_device"
        }
    }
}

/**
 * Policy for unlock settings (temporary parent access).
 */
object UnlockPolicy {
    
    /**
     * Check if settings unlock is currently active.
     * 
     * @param rules All current rules  
     * @return true if unlock is active
     */
    fun isUnlockActive(rules: List<RuleDTO>): Boolean {
        return rules.any { rule ->
            if (!rule.enabled || rule.ruleType != "unlock_settings") return@any false
            
            // If no schedule, assume valid if enabled
            val start = rule.scheduleStartTime ?: return@any true
            val end = rule.scheduleEndTime ?: return@any true
            
            TimeUtils.isCurrentTimeInRange(start, end)
        }
    }
}
