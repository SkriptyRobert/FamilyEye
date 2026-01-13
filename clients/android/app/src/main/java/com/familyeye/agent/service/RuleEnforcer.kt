package com.familyeye.agent.service

import com.familyeye.agent.data.api.dto.RuleDTO
import com.familyeye.agent.data.repository.AgentConfigRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class RuleEnforcer @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: android.content.Context,
    private val configRepository: AgentConfigRepository
) {
    // In a real app, these would come from Room DB
    private val rules = MutableStateFlow<List<RuleDTO>>(emptyList())

    suspend fun updateRules(newRules: List<RuleDTO>) {
        timber.log.Timber.d("RuleEnforcer: Updating rules: ${newRules.size}")
        newRules.forEach { timber.log.Timber.d("Rule: ${it.appName} (${it.ruleType}) Enabled:${it.enabled}") }
        rules.emit(newRules)
    }

    fun isAppBlocked(packageName: String): Boolean {
        val appLabel = getAppName(packageName)
        val currentRules = rules.value
        
        timber.log.Timber.v("Checking blocking for $packageName ($appLabel). Rules count: ${currentRules.size}")
        
        return currentRules.any { rule ->
            if (!rule.enabled || rule.ruleType != "app_block") return@any false
            
            val ruleName = rule.appName ?: return@any false
            
            // 1. Exact Package Match
            if (ruleName.equals(packageName, ignoreCase = true)) {
                timber.log.Timber.w("BLOCK MATCH (Exact): $packageName")
                return@any true
            }
            
            // 2. Partial Package Match
            if (packageName.contains(ruleName, ignoreCase = true)) {
                timber.log.Timber.w("BLOCK MATCH (Partial): $packageName contains $ruleName")
                return@any true
            }
            
            // 3. Label Match
            if (ruleName.equals(appLabel, ignoreCase = true)) {
                 timber.log.Timber.w("BLOCK MATCH (Label): $appLabel == $ruleName")
                 return@any true
            }
            
            false
        }
    }

    private fun getAppName(packageName: String): String {
        return try {
            val packageManager = context.packageManager
            val info = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: Exception) {
            packageName // Fallback
        }
    }
    
    fun isDeviceLocked(): Boolean {
        // "Lock Now" functionality
        return rules.value.any { rule ->
            rule.enabled && rule.ruleType == "lock_device"
        }
    }

    fun isDailyLimitExceeded(totalUsageSeconds: Int): Boolean {
        return rules.value.any { rule ->
            rule.enabled && 
            rule.ruleType == "daily_limit" && 
            rule.timeLimit != null &&
            (rule.timeLimit * 60) <= totalUsageSeconds
        }
    }
    
    fun isScheduleBlocked(): Boolean {
        return rules.value.any { rule ->
            if (!rule.enabled || rule.ruleType != "schedule") return@any false
            
            // Check Days (0=Mon, 6=Sun or similar? Server sends 0-6).
            // Java Calendar: 1=Sun, 2=Mon ... 7=Sat.
            // Need to match server format. Assuming Server 0=Mon, 6=Sun.
            val now = java.util.Calendar.getInstance()
            // Calendar.DAY_OF_WEEK: Sun=1, Mon=2 ... Sat=7
            // Convert to 0=Mon ... 6=Sun
            val dayOfWeek = (now.get(java.util.Calendar.DAY_OF_WEEK) + 5) % 7
            
            val days = rule.scheduleDays
            if (!days.isNullOrEmpty()) {
                val allowedDays = days.split(",").mapNotNull { it.trim().toIntOrNull() }
                if (!allowedDays.contains(dayOfWeek)) {
                    // If today is NOT in schedule_days, does it mean BLOCKED or ALLOWED?
                    // Typically 'schedule' rule defines "Blocked Times".
                    // Or "Allowed Times"?
                    // FamilyEye "schedule" usually means "Allowed Time Window" or "Downtime"?
                    // Backend: "schedule" rule usually defines "DOWNTIME" (Hours you CANNOT use).
                    // OR "Available" (valid hours).
                    // In Windows agent: Enforcer checks if "Current Time" is INSIDE "Schedule".
                    // If inside schedule -> Blocked?
                    // Let's assume schedule defines BLOCKED intervals.
                    // If today is in list, check time.
                    return@any false // If today is not in 'blocked list', then not blocked.
                }
            }

            val start = rule.scheduleStartTime ?: return@any false
            val end = rule.scheduleEndTime ?: return@any false
            
            isCurrentTimeInRange(start, end)
        }
    }
    
    fun isAppTimeLimitExceeded(packageName: String, usageSeconds: Int): Boolean {
         val appLabel = getAppName(packageName)
         
         return rules.value.any { rule ->
            if (!rule.enabled || rule.ruleType != "time_limit") return@any false
            
            val ruleName = rule.appName ?: return@any false
            val isMatch = ruleName.equals(packageName, ignoreCase = true) || 
                          packageName.contains(ruleName, ignoreCase = true) ||
                          ruleName.equals(appLabel, ignoreCase = true)
            
            isMatch && (rule.timeLimit?.times(60) ?: Int.MAX_VALUE) <= usageSeconds
        }
    }

    fun isUnlockSettingsActive(): Boolean {
        // Check for any enabled "unlock_settings" rule that is currently valid
        return rules.value.any { rule ->
            if (!rule.enabled || rule.ruleType != "unlock_settings") return@any false
            
            // If no schedule, assume valid if enabled (though usually we set schedule)
            val start = rule.scheduleStartTime ?: return@any true
            val end = rule.scheduleEndTime ?: return@any true
            
            isCurrentTimeInRange(start, end)
        }
    }

    private fun isCurrentTimeInRange(startStr: String, endStr: String): Boolean {
        try {
            val now = java.util.Calendar.getInstance()
            val currentMinutes = now.get(java.util.Calendar.HOUR_OF_DAY) * 60 + now.get(java.util.Calendar.MINUTE)
            
            fun parseMinutes(timeStr: String): Int {
                val parts = timeStr.split(":")
                return parts[0].toInt() * 60 + parts[1].toInt()
            }
            
            val startMinutes = parseMinutes(startStr)
            val endMinutes = parseMinutes(endStr)
            
            // Handle day wrapping if needed (though unlocked settings is usually short term)
            if (endMinutes < startMinutes) {
                return currentMinutes >= startMinutes || currentMinutes < endMinutes
            }
            
            return currentMinutes in startMinutes until endMinutes
        } catch (e: Exception) {
            return false
        }
    }
}
