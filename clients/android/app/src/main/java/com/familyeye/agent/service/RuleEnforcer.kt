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
    private val configRepository: AgentConfigRepository
) {
    // In a real app, these would come from Room DB
    private val rules = MutableStateFlow<List<RuleDTO>>(emptyList())

    suspend fun updateRules(newRules: List<RuleDTO>) {
        rules.emit(newRules)
    }

    fun isAppBlocked(packageName: String): Boolean {
        // Simple logic: Check if there is an enabled blocking rule for this package
        // Note: Backend 'app_name' might be packageName or label. Assuming packageName match for Phase 2.
        return rules.value.any { rule ->
            rule.enabled && 
            rule.ruleType == "app_block" && 
            (rule.appName == packageName || packageName.contains(rule.appName ?: ""))
        }
    }
    
    fun isAppTimeLimitExceeded(packageName: String, usageSeconds: Int): Boolean {
         return rules.value.any { rule ->
            rule.enabled && 
            rule.ruleType == "time_limit" && 
            (rule.appName == packageName) &&
            (rule.timeLimit ?: Int.MAX_VALUE) <= usageSeconds
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
