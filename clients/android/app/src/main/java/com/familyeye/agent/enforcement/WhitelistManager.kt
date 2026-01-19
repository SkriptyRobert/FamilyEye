package com.familyeye.agent.enforcement

import android.content.Context
import com.familyeye.agent.service.RuleEnforcer
import com.familyeye.agent.utils.PackageMatcher
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Manages the whitelist of apps that should never be blocked.
 * 
 * Whitelisted apps include:
 * - Our own FamilyEye agent app
 * - System UI (to prevent crashes)
 * - Launcher apps (to prevent infinite block loops)
 * - Settings (when unlock is active)
 */
@Singleton
class WhitelistManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val ruleEnforcer: RuleEnforcer
) {
    private val ownPackageName = context.packageName

    /**
     * Check if a package should be whitelisted (never blocked).
     * 
     * @param packageName The package name to check
     * @return true if the app should be whitelisted
     */
    fun isWhitelisted(packageName: String): Boolean {
        // 1. Our own app is always whitelisted
        if (packageName == ownPackageName) {
            return true
        }

        // 2. System UI is always whitelisted to prevent crashes
        // Note: In Device Lock mode, SystemUI is handled specially (closed)
        if (PackageMatcher.isSystemUI(packageName)) {
            return true
        }

        // 3. Settings - blocked by default, allowed only when unlocked
        if (PackageMatcher.isSettings(packageName)) {
            val isUnlocked = ruleEnforcer.isUnlockSettingsActive()
            if (isUnlocked) {
                Timber.v("Settings whitelisted - unlock active")
            }
            return isUnlocked
        }

        // 4. Launcher apps are whitelisted to prevent infinite block loops
        if (PackageMatcher.isLauncher(packageName)) {
            Timber.v("Launcher whitelisted: $packageName")
            return true
        }

        return false
    }

    /**
     * Check if a package should be treated as a launcher.
     * Launchers need special handling - show overlay instead of going home.
     */
    fun isLauncher(packageName: String): Boolean {
        return PackageMatcher.isLauncher(packageName)
    }

    /**
     * Check if a package is System UI.
     * SystemUI needs special handling in Device Lock mode.
     */
    fun isSystemUI(packageName: String): Boolean {
        return PackageMatcher.isSystemUI(packageName)
    }

    /**
     * Get the agent's own package name.
     */
    fun getOwnPackageName(): String = ownPackageName
}
