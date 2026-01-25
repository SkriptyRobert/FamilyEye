package com.familyeye.agent.policy

/**
 * Policy for blocking access to Settings app.
 * 
 * Two protection levels:
 * - FULL: Block entire Settings app (maximum security, recommended)
 * - OFF: No settings blocking (parent's choice)
 */
object SettingsProtectionPolicy {
    
    enum class ProtectionLevel {
        FULL,
        OFF
    }
    
    /**
     * Check if Settings access should be blocked.
     * 
     * @param protectionLevel Current protection level
     * @param isUnlockActive Whether parent has temporarily unlocked (5 min)
     * @return true if access should be blocked
     */
    fun shouldBlockSettings(
        protectionLevel: ProtectionLevel
    ): Boolean {
        
        return when (protectionLevel) {
            ProtectionLevel.FULL -> true  // Block everything
            ProtectionLevel.OFF -> false  // Allow everything
        }
    }
    
    /**
     * Parse protection level from string (from backend).
     * Defaults to FULL for maximum security.
     */
    fun fromString(level: String?): ProtectionLevel {
        return when (level?.lowercase()) {
            "off" -> ProtectionLevel.OFF
            else -> ProtectionLevel.FULL  // Default to most secure
        }
    }
}
