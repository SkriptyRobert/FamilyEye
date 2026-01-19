package com.familyeye.agent.enforcement

import android.content.Context
import com.familyeye.agent.service.RuleEnforcer
import com.familyeye.agent.utils.PackageMatcher
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Handles self-protection against tampering attempts.
 * 
 * Detects and reports attempts to:
 * - Deactivate Device Admin
 * - Uninstall the agent app
 * - Access protected settings screens
 * - Manage user accounts (to bypass restrictions)
 */
@Singleton
class SelfProtectionHandler @Inject constructor(
    @ApplicationContext private val context: Context,
    private val ruleEnforcer: RuleEnforcer
) {
    companion object {
        // Dangerous activity class names that should be blocked
        private val DANGEROUS_ACTIVITIES = setOf(
            "deviceadminadd",
            "deviceadminsettings",
            "usersettings",
            "usermanagement",
            "deviceadministratorsettings"
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
        // Check if this is a settings app accessing dangerous screens
        if (PackageMatcher.isSettings(packageName)) {
            if (className != null && isDangerousActivity(className)) {
                // Check if parent has unlocked access
                if (ruleEnforcer.isUnlockSettingsActive()) {
                    Timber.v("Settings access allowed - unlock active")
                    return false
                }
                Timber.w("Tampering detected: Settings accessing $className")
                return true
            }
        }

        // Check if this is a package installer (uninstall attempt)
        if (PackageMatcher.isPackageInstaller(packageName)) {
            // Check if parent has unlocked access
            if (ruleEnforcer.isUnlockSettingsActive()) {
                Timber.v("Package installer access allowed - unlock active")
                return false
            }
            Timber.w("Tampering detected: Package installer accessed")
            return true
        }

        return false
    }

    /**
     * Check if a class name matches any dangerous activity patterns.
     */
    private fun isDangerousActivity(className: String): Boolean {
        val lowerClassName = className.lowercase()
        return DANGEROUS_ACTIVITIES.any { lowerClassName.contains(it) }
    }

    /**
     * Check if settings access should be allowed.
     * Settings are blocked by default but can be unlocked by parent.
     */
    fun isSettingsAccessAllowed(): Boolean {
        return ruleEnforcer.isUnlockSettingsActive()
    }

    /**
     * Get reason string for logging/reporting.
     */
    fun getTamperingReason(packageName: String, className: String?): String {
        return when {
            PackageMatcher.isPackageInstaller(packageName) -> 
                "Attempted to access package installer (uninstall attempt)"
            PackageMatcher.isSettings(packageName) && className != null ->
                "Attempted to access protected settings: $className"
            PackageMatcher.isSettings(packageName) ->
                "Attempted to access settings"
            else -> 
                "Unknown tampering attempt: $packageName"
        }
    }
}
