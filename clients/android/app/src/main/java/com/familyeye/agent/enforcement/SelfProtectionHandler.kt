package com.familyeye.agent.enforcement

import android.content.Context
import android.provider.Settings
import com.familyeye.agent.policy.SettingsProtectionPolicy
import com.familyeye.agent.service.RuleEnforcer
import com.familyeye.agent.utils.PackageMatcher
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber

import javax.inject.Inject
import javax.inject.Singleton

/**
 * Handles self-protection against tampering attempts.
 * 
 * Phase 3 Security Hardening:
 * Detects and reports attempts to:
 * - Deactivate Device Admin
 * - Uninstall the agent app
 * - Access protected settings screens
 * - Access Accessibility Service settings
 * - Enable Developer Options / USB Debugging
 * - Manage user accounts (to bypass restrictions)
 */
@Singleton
class SelfProtectionHandler @Inject constructor(
    @ApplicationContext private val context: Context,
    private val ruleEnforcer: RuleEnforcer
) {
    companion object {
        // Package installer patterns (uninstall detection)
        private val UNINSTALL_PATTERNS = setOf(
            "uninstall",
            "packageinstaller",
            "deletestagingdirjob"
        )

        // Recents/Overview patterns (Clear All entry point)
        private val RECENTS_PATTERNS = setOf(
            "recents",
            "recent",
            "overview"
        )
    }

    /**
     * Check if this represents a tampering attempt.
     * 
     * @param packageName The package name being accessed
     * @param className Optional class/activity name for more specific checks
     * @return true if this appears to be a tampering attempt
     */
    fun isTamperingAttempt(packageName: String, className: String?): Boolean {
        val isUnlockActive = false
        
        // ========== Settings Protection ==========
        // Binary logic: FULL blocks everything, OFF allows everything
        if (PackageMatcher.isSettings(packageName)) {
            val protectionLevel = ruleEnforcer.getSettingsProtectionLevel()
            val shouldBlock = SettingsProtectionPolicy.shouldBlockSettings(
                protectionLevel
            )
            if (shouldBlock) {
                Timber.w("Settings blocked: level=$protectionLevel")
                return true
            }
            // Protection is OFF or parent unlocked - allow access
            return false
        }

        // Block access to Recents (Clear All) when Settings protection is active.
        // This is the only reliable way without Device Owner to prevent app kill attempts.
        if (PackageMatcher.isSystemUI(packageName) && isRecentsActivity(className)) {
            val protectionLevel = ruleEnforcer.getSettingsProtectionLevel()
            val shouldBlock = SettingsProtectionPolicy.shouldBlockSettings(
                protectionLevel
            )
            if (shouldBlock) {
                Timber.w("Recents blocked: protection=$protectionLevel")
                return true
            }
        }

        // Check if this is a package installer (uninstall attempt)
        // This is ALWAYS blocked regardless of Settings protection level
        if (PackageMatcher.isPackageInstaller(packageName) || isUninstallActivity(className)) {
            if (isUnlockActive) {
                Timber.v("Package installer access allowed - unlock active")
                return false
            }
            Timber.w("Tampering detected: Uninstall attempt - $packageName / $className")
            return true
        }

        return false
    }
    
    /**
     * Check if this is an uninstall-related activity.
     */
    private fun isUninstallActivity(className: String?): Boolean {
        if (className == null) return false
        val lower = className.lowercase()
        return UNINSTALL_PATTERNS.any { lower.contains(it) }
    }

    /**
     * Check if this is the Recents/Overview activity.
     */
    private fun isRecentsActivity(className: String?): Boolean {
        if (className == null) return false
        val lower = className.lowercase()
        return RECENTS_PATTERNS.any { lower.contains(it) }
    }

    /**
     * Check if settings access should be allowed.
     * Settings are blocked by default but can be unlocked by parent.
     */
    fun isSettingsAccessAllowed(): Boolean {
        return false
    }
    
    // ==================== Phase 3: New Security Checks ====================
    
    /**
     * Check if Developer Options is enabled on the device.
     * This is a security concern as it allows ADB access and other bypasses.
     */
    fun isDeveloperOptionsEnabled(): Boolean {
        return try {
            Settings.Global.getInt(
                context.contentResolver,
                Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0
            ) != 0
        } catch (e: Exception) {
            Timber.e(e, "Error checking Developer Options")
            false
        }
    }
    
    /**
     * Check if ADB (USB Debugging) is enabled.
     * This allows command-line control which can bypass restrictions.
     */
    fun isAdbEnabled(): Boolean {
        return try {
            Settings.Global.getInt(
                context.contentResolver,
                Settings.Global.ADB_ENABLED, 0
            ) != 0
        } catch (e: Exception) {
            Timber.e(e, "Error checking ADB status")
            false
        }
    }
    
    /**
     * Perform a comprehensive system tampering check.
     * Call this periodically to detect ongoing bypass attempts.
     * 
     * @return Map of detected issues (empty if all clear)
     */
    fun checkSystemTampering(): Map<String, Boolean> {
        val issues = mutableMapOf<String, Boolean>()
        
        if (isDeveloperOptionsEnabled()) {
            issues["DEVELOPER_OPTIONS_ENABLED"] = true
            Timber.w("Security Alert: Developer Options is enabled")
        }
        
        if (isAdbEnabled()) {
            issues["ADB_DEBUGGING_ENABLED"] = true
            Timber.w("Security Alert: USB Debugging (ADB) is enabled")
        }
        
        return issues
    }

    /**
     * Get reason string for logging/reporting.
     */
    fun getTamperingReason(packageName: String, className: String?): String {
        return when {
            isUninstallActivity(className) ->
                "Attempted to uninstall FamilyEye"
            PackageMatcher.isSystemUI(packageName) && isRecentsActivity(className) ->
                "Attempted to access Recents (Clear All)"
            PackageMatcher.isPackageInstaller(packageName) -> 
                "Attempted to access package installer (uninstall attempt)"
            className?.lowercase()?.contains("accessibility") == true ->
                "Attempted to access Accessibility settings (disable protection)"
            className?.lowercase()?.contains("appinfo") == true ->
                "Attempted to access App Info (force stop/disable)"
            PackageMatcher.isSettings(packageName) && className != null ->
                "Attempted to access protected settings: $className"
            PackageMatcher.isSettings(packageName) ->
                "Attempted to access settings"
            else -> 
                "Unknown tampering attempt: $packageName"
        }
    }
}

