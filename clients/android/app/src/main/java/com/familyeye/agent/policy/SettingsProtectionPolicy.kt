package com.familyeye.agent.policy

/**
 * Policy for blocking access to Settings app.
 * 
 * Three protection levels:
 * - FULL: Block entire Settings app AND notification shade (maximum security)
 * - PARTIAL: Block Settings app but ALLOW notification shade (for quick settings access)
 * - OFF: No settings blocking (parent's choice)
 */
object SettingsProtectionPolicy {
    
    enum class ProtectionLevel {
        FULL,
        PARTIAL,  // Block Settings, allow Notification Shade
        OFF
    }
    
    /**
     * Check if Settings app access should be blocked.
     * 
     * @param protectionLevel Current protection level
     * @return true if Settings app should be blocked
     */
    fun shouldBlockSettings(
        protectionLevel: ProtectionLevel
    ): Boolean {
        return when (protectionLevel) {
            ProtectionLevel.FULL -> true     // Block Settings
            ProtectionLevel.PARTIAL -> true  // Block Settings
            ProtectionLevel.OFF -> false     // Allow Settings
        }
    }
    
    /**
     * Check if SystemUI (Notification Shade / Quick Settings) should be blocked.
     * 
     * In PARTIAL mode, we allow the notification shade so the child can access
     * basic controls like brightness, WiFi, and mobile data.
     * 
     * @param protectionLevel Current protection level
     * @return true if SystemUI should be blocked
     */
    fun shouldBlockSystemUI(
        protectionLevel: ProtectionLevel
    ): Boolean {
        return when (protectionLevel) {
            ProtectionLevel.FULL -> true     // Block notification shade
            ProtectionLevel.PARTIAL -> false // Allow notification shade
            ProtectionLevel.OFF -> false     // Allow notification shade
        }
    }
    
    /**
     * Parse protection level from string (from backend).
     * Defaults to FULL for maximum security.
     */
    fun fromString(level: String?): ProtectionLevel {
        return when (level?.lowercase()) {
            "partial" -> ProtectionLevel.PARTIAL
            "off" -> ProtectionLevel.OFF
            else -> ProtectionLevel.FULL  // Default to most secure
        }
    }
}
