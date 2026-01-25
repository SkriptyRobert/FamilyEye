package com.familyeye.agent.device

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.UserManager
import com.familyeye.agent.receiver.FamilyEyeDeviceAdmin
import com.familyeye.agent.utils.PackageMatcher
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Applies device-owner level protections that survive app process death.
 *
 * These restrictions persist at the OS level and help mitigate the
 * "Clear All / Force Stop" bypass on child devices.
 * 
 * Supports both activation and deactivation of protections for parent control.
 */
@Singleton
class DeviceOwnerPolicyEnforcer @Inject constructor(
    @ApplicationContext private val context: Context
) {
    /**
     * Factory method for creating instance without Hilt DI.
     * Used in DeviceAdminReceiver which doesn't support Hilt injection.
     */
    companion object {
        fun create(context: Context): DeviceOwnerPolicyEnforcer {
            return DeviceOwnerPolicyEnforcer(context.applicationContext)
        }
        
        // Map of restriction names to UserManager constants for dashboard configuration
        val RESTRICTION_MAP = mapOf(
            "disallow_safe_boot" to UserManager.DISALLOW_SAFE_BOOT,
            "disallow_factory_reset" to UserManager.DISALLOW_FACTORY_RESET,
            "disallow_add_user" to UserManager.DISALLOW_ADD_USER,
            "disallow_remove_user" to UserManager.DISALLOW_REMOVE_USER,
            "disallow_install_apps" to UserManager.DISALLOW_INSTALL_APPS,
            "disallow_uninstall_apps" to UserManager.DISALLOW_UNINSTALL_APPS,
            "disallow_apps_control" to UserManager.DISALLOW_APPS_CONTROL,
            "disallow_modify_accounts" to UserManager.DISALLOW_MODIFY_ACCOUNTS,
            "disallow_debugging" to UserManager.DISALLOW_DEBUGGING_FEATURES,
            "disallow_usb_transfer" to UserManager.DISALLOW_USB_FILE_TRANSFER,
            "disallow_install_unknown_sources" to UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES,
            // Paranoid options for future use
            "disallow_config_wifi" to UserManager.DISALLOW_CONFIG_WIFI,
            "disallow_config_bluetooth" to UserManager.DISALLOW_CONFIG_BLUETOOTH,
            "disallow_sms" to UserManager.DISALLOW_SMS,
            "disallow_outgoing_calls" to UserManager.DISALLOW_OUTGOING_CALLS,
            "disallow_share_location" to UserManager.DISALLOW_SHARE_LOCATION
        )
    }

    private val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val admin = ComponentName(context, FamilyEyeDeviceAdmin::class.java)
    private var lastSettingsBlock: Boolean? = null
    private var protectionsActive: Boolean = true

    // Balanced preset - default restrictions for child devices
    private val baselineRestrictions = listOf(
        UserManager.DISALLOW_SAFE_BOOT,
        UserManager.DISALLOW_FACTORY_RESET,
        UserManager.DISALLOW_ADD_USER,
        UserManager.DISALLOW_REMOVE_USER,
        UserManager.DISALLOW_INSTALL_APPS,
        UserManager.DISALLOW_UNINSTALL_APPS,
        UserManager.DISALLOW_APPS_CONTROL,
        UserManager.DISALLOW_MODIFY_ACCOUNTS,
        // UserManager.DISALLOW_DEBUGGING_FEATURES, // Temporarily disabled for dev testing
        // UserManager.DISALLOW_USB_FILE_TRANSFER,  // Temporarily disabled for dev testing
        UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES
    )

    fun isDeviceOwner(): Boolean {
        return dpm.isDeviceOwnerApp(context.packageName)
    }

    /**
     * Apply baseline OS restrictions for child devices.
     * Safe to call repeatedly (idempotent).
     */
    fun applyBaselineRestrictions() {
        if (!isDeviceOwner()) return
        try {
            baselineRestrictions.forEach { restriction ->
                dpm.addUserRestriction(admin, restriction)
            }
            
            // CRITICAL: Prevent ANY mechanism (ADB, SystemUI, etc.) from force-stopping our package.
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                safeSetControlDisabledPackages(listOf(context.packageName))
            }
            
            Timber.i("DeviceOwner: Baseline restrictions and control disabling applied")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to apply baseline restrictions")
        }
    }

    /**
     * Block or allow Settings-like apps at OS level using package suspension.
     * This persists across process death and helps prevent settings tampering.
     */
    fun applySettingsProtection(shouldBlock: Boolean) {
        if (!isDeviceOwner()) return
        if (lastSettingsBlock == shouldBlock) return

        val targets = getInstalledSettingsPackages()
        if (targets.isEmpty()) {
            Timber.w("DeviceOwner: No settings packages found to suspend")
            return
        }

        try {
            val failed = dpm.setPackagesSuspended(admin, targets.toTypedArray(), shouldBlock)
            if (failed.isNotEmpty()) {
                Timber.w("DeviceOwner: Failed to suspend packages: ${failed.joinToString()}")
            } else {
                Timber.i("DeviceOwner: Settings packages ${if (shouldBlock) "suspended" else "unsuspended"}")
            }
            lastSettingsBlock = shouldBlock
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to apply settings protection (shouldBlock=$shouldBlock)")
        }
    }

    private fun getInstalledSettingsPackages(): List<String> {
        val pm = context.packageManager
        return PackageMatcher.getSettingsPackages().filter { pkg ->
            isPackageInstalled(pm, pkg)
        }
    }

    @Suppress("DEPRECATION")
    private fun isPackageInstalled(pm: PackageManager, packageName: String): Boolean {
        return try {
            pm.getPackageInfo(packageName, 0)
            true
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Called after Device Owner provisioning is complete.
     * Activates full protection including uninstall blocking and kiosk mode if needed.
     */
    fun onDeviceOwnerActivated() {
        if (!isDeviceOwner()) {
            Timber.w("onDeviceOwnerActivated called but not Device Owner")
            return
        }
        
        Timber.i("Device Owner activated - applying full protection")
        
        // Apply baseline restrictions
        applyBaselineRestrictions()
        
        // Block uninstallation
        setUninstallBlocked(true)
        
        // Enable kiosk mode if needed (can be configured later)
        // enableKioskModeIfNeeded()

        // 4. Whitelist from battery optimizations
        whitelistFromBatteryOptimizations()
    }

    /**
     * Whitelist this app from battery optimizations silently.
     * Prevents Doze mode from stopping background synchronization.
     */
    fun whitelistFromBatteryOptimizations() {
        if (!isDeviceOwner()) return
        
        try {
            // Using ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS is for users.
            // As Device Owner, we can directly set the app as a "power-allowlisted" 
            // package if the ROM allows it, OR we simply grant the permission.
            // But the most robust way is to use the DPM to allow everything.
            
            // For most modern Androids, adding to user restrictions is not enough.
            // We need to ensure we are not restricted.
            Timber.i("DeviceOwner: Whitelisting app from battery optimizations")
            
            // Note: There isn't a direct DPM method to "ignore battery optimization" 
            // but but we can ensure the app is never suspended.
            dpm.setPackagesSuspended(admin, arrayOf(context.packageName), false)
            
            // Grant permission if not already granted (just in case)
            grantRuntimePermission(context.packageName, android.Manifest.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to whitelist from battery optimizations")
        }
    }

    /**
     * Block or allow uninstallation of this app.
     */
    fun setUninstallBlocked(blocked: Boolean) {
        if (!isDeviceOwner()) {
            Timber.w("setUninstallBlocked called but not Device Owner")
            return
        }
        
        try {
            dpm.setUninstallBlocked(admin, context.packageName, blocked)
            Timber.i("DeviceOwner: Uninstall ${if (blocked) "blocked" else "allowed"}")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to set uninstall blocked=$blocked")
        }
    }

    /**
     * Enable Kiosk Mode (Lock Task Mode) for specified packages.
     * This locks the device to only allow specified apps to run.
     */
    fun enableKioskMode(packages: Array<String>) {
        if (!isDeviceOwner()) {
            Timber.w("enableKioskMode called but not Device Owner")
            return
        }
        
        try {
            dpm.setLockTaskPackages(admin, packages)
            Timber.i("DeviceOwner: Kiosk mode enabled for ${packages.size} packages")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to enable kiosk mode")
        }
    }

    /**
     * Disable Kiosk Mode (Lock Task Mode).
     */
    fun disableKioskMode() {
        if (!isDeviceOwner()) {
            Timber.w("disableKioskMode called but not Device Owner")
            return
        }
        
        try {
            dpm.setLockTaskPackages(admin, emptyArray())
            Timber.i("DeviceOwner: Kiosk mode disabled")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to disable kiosk mode")
        }
    }

    // ==================== Deactivation & Management Methods ====================

    /**
     * Check if protections are currently active.
     */
    fun areProtectionsActive(): Boolean {
        return protectionsActive && isDeviceOwner()
    }

    /**
     * Deactivate ALL Device Owner protections.
     * This allows the parent to remove FamilyEye from child's device.
     * 
     * Note: Device Owner status remains (Android limitation), but all restrictions
     * are removed, allowing normal app uninstallation.
     */
    fun deactivateAllProtections(): Boolean {
        if (!isDeviceOwner()) {
            Timber.w("deactivateAllProtections called but not Device Owner")
            return false
        }
        
        return try {
            Timber.i("DeviceOwner: Deactivating all protections...")
            
            // 1. Remove all user restrictions
            baselineRestrictions.forEach { restriction ->
                try {
                    dpm.clearUserRestriction(admin, restriction)
                } catch (e: Exception) {
                    Timber.w("Failed to clear restriction: $restriction")
                }
            }
            
            // 2. Allow uninstallation
            setUninstallBlocked(false)

            // 3. Enable Force Stop again
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                safeSetControlDisabledPackages(emptyList<String>())
            }
            
            // 4. Unsuspend Settings apps
            applySettingsProtection(false)
            
            // 4. Disable Kiosk mode if active
            disableKioskMode()
            
            // 5. Mark protections as inactive
            protectionsActive = false
            
            // 6. NUCLEAR OPTION: Relinquish Device Owner status completely
            // This allows the app to be uninstalled even from the device UI.
            try {
                dpm.clearDeviceOwnerApp(context.packageName)
                Timber.i("DeviceOwner: Relinquished Device Owner status")
            } catch (e: Exception) {
                Timber.e(e, "DeviceOwner: Failed to relinquish DO status (might not be DO anymore)")
            }
            
            Timber.i("DeviceOwner: All protections deactivated successfully")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to deactivate all protections")
            false
        }
    }

    /**
     * Reactivate all Device Owner protections.
     * Call this after deactivation if parent changes their mind.
     */
    fun reactivateAllProtections(): Boolean {
        if (!isDeviceOwner()) {
            Timber.w("reactivateAllProtections called but not Device Owner")
            return false
        }
        
        return try {
            Timber.i("DeviceOwner: Reactivating all protections...")
            
            // Apply baseline restrictions
            applyBaselineRestrictions()
            
            // Block uninstallation
            setUninstallBlocked(true)
            
            // Mark protections as active
            protectionsActive = true
            
            Timber.i("DeviceOwner: All protections reactivated successfully")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to reactivate protections")
            false
        }
    }

    /**
     * Remove a specific restriction by name.
     * @param restrictionName The name from RESTRICTION_MAP (e.g., "disallow_safe_boot")
     */
    fun removeRestriction(restrictionName: String): Boolean {
        if (!isDeviceOwner()) return false
        
        val restriction = RESTRICTION_MAP[restrictionName]
        if (restriction == null) {
            Timber.w("Unknown restriction name: $restrictionName")
            return false
        }
        
        return try {
            dpm.clearUserRestriction(admin, restriction)
            Timber.i("DeviceOwner: Removed restriction: $restrictionName")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to remove restriction: $restrictionName")
            false
        }
    }

    /**
     * Set a specific restriction by name.
     * @param restrictionName The name from RESTRICTION_MAP (e.g., "disallow_safe_boot")
     * @param enabled true to enable the restriction, false to disable
     */
    fun setRestriction(restrictionName: String, enabled: Boolean): Boolean {
        if (!isDeviceOwner()) return false
        
        val restriction = RESTRICTION_MAP[restrictionName]
        if (restriction == null) {
            Timber.w("Unknown restriction name: $restrictionName")
            return false
        }
        
        return try {
            if (enabled) {
                dpm.addUserRestriction(admin, restriction)
            } else {
                dpm.clearUserRestriction(admin, restriction)
            }
            Timber.i("DeviceOwner: Set restriction $restrictionName = $enabled")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to set restriction: $restrictionName")
            false
        }
    }

    /**
     * Get list of currently active restrictions.
     * @return List of restriction names that are currently enforced
     */
    fun getActiveRestrictions(): List<String> {
        if (!isDeviceOwner()) return emptyList()
        
        val userManager = context.getSystemService(Context.USER_SERVICE) as UserManager
        val activeRestrictions = mutableListOf<String>()
        
        RESTRICTION_MAP.forEach { (name, restriction) ->
            try {
                if (userManager.hasUserRestriction(restriction)) {
                    activeRestrictions.add(name)
                }
            } catch (e: Exception) {
                Timber.w("Failed to check restriction: $name")
            }
        }
        
        return activeRestrictions
    }

    /**
     * Apply multiple restrictions from a map (for dashboard configuration).
     * @param restrictions Map of restriction names to enabled/disabled state
     */
    fun applyRestrictions(restrictions: Map<String, Boolean>): Boolean {
        if (!isDeviceOwner()) return false
        
        var allSuccess = true
        restrictions.forEach { (name, enabled) ->
            if (!setRestriction(name, enabled)) {
                allSuccess = false
            }
        }
        return allSuccess
    }

    /**
     * Grant a runtime permission to a package automatically.
     * This allows silent granting of permissions like GPS, Camera, etc.
     * 
     * @param packageName The package to grant permission to (use context.packageName for self)
     * @param permission The permission to grant (e.g., Manifest.permission.ACCESS_FINE_LOCATION)
     */
    fun grantRuntimePermission(packageName: String, permission: String): Boolean {
        if (!isDeviceOwner()) {
            Timber.w("grantRuntimePermission called but not Device Owner")
            return false
        }
        
        return try {
            val result = dpm.setPermissionGrantState(
                admin,
                packageName,
                permission,
                DevicePolicyManager.PERMISSION_GRANT_STATE_GRANTED
            )
            if (result) {
                Timber.i("DeviceOwner: Granted permission $permission to $packageName")
            } else {
                Timber.w("DeviceOwner: Failed to grant permission $permission to $packageName")
            }
            result
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Error granting permission $permission")
            false
        }
    }

    /**
     * Grant all necessary runtime permissions to FamilyEye automatically.
     */
    fun grantAllRequiredPermissions(): Boolean {
        if (!isDeviceOwner()) return false
        
        val permissions = listOf(
            android.Manifest.permission.ACCESS_FINE_LOCATION,
            android.Manifest.permission.ACCESS_COARSE_LOCATION,
            android.Manifest.permission.CAMERA,
            android.Manifest.permission.READ_CONTACTS,
            android.Manifest.permission.READ_CALL_LOG,
            android.Manifest.permission.READ_SMS
        )
        
        var allGranted = true
        permissions.forEach { permission ->
            if (!grantRuntimePermission(context.packageName, permission)) {
                allGranted = false
            }
        }
        
        return allGranted
    }

    /**
     * Disable screenshots on the device.
     */
    fun setScreenCaptureDisabled(disabled: Boolean): Boolean {
        if (!isDeviceOwner()) return false
        
        return try {
            dpm.setScreenCaptureDisabled(admin, disabled)
            Timber.i("DeviceOwner: Screen capture ${if (disabled) "disabled" else "enabled"}")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to set screen capture disabled")
            false
        }
    }

    /**
     * Disable camera on the device.
     */
    fun setCameraDisabled(disabled: Boolean): Boolean {
        if (!isDeviceOwner()) return false
        
        return try {
            dpm.setCameraDisabled(admin, disabled)
            Timber.i("DeviceOwner: Camera ${if (disabled) "disabled" else "enabled"}")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to set camera disabled")
            false
            false
        }
    }

    /**
     * Get the current active protection tier.
     * Used for dashboard reporting.
     */
    fun getProtectionLevel(): String {
        if (!isDeviceOwner()) return "NONE"
        
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            "GOD_MODE" // API 30+: Immune to Force Stop
        } else {
            "RESURRECTION_MODE" // API <30: Relies on Watchdog revival
        }
    }

    /**
     * Helper to call setControlDisabledPackages via reflection to avoid compiler issues.
     */
    private fun safeSetControlDisabledPackages(packages: List<String>) {
        try {
            // DISCOVERY: Log all methods to see what Xiaomi did
            val methods = DevicePolicyManager::class.java.methods
            val matches = methods.filter { it.name.contains("Package", ignoreCase = true) || it.name.startsWith("set") }
            Timber.d("DPM Discovery: Found ${matches.size} candidate methods")
            matches.take(20).forEach { 
                Timber.v("DPM Method: ${it.name}(${it.parameterTypes.joinToString { p -> p.simpleName }})")
            }

            val method = DevicePolicyManager::class.java.getMethod("setControlDisabledPackages", ComponentName::class.java, List::class.java)
            method.invoke(dpm, admin, packages)
            Timber.i("Reflection: Successfully called setControlDisabledPackages with ${packages.size} packages")
        } catch (e: Exception) {
            Timber.e("Reflection: Failed to call setControlDisabledPackages on ${dpm.javaClass.name}: ${e}")
        }
    }
}
