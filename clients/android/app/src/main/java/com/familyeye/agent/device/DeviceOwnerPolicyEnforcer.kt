package com.familyeye.agent.device

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
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
    companion object {
        /**
         * Factory method for creating instance without Hilt DI.
         * Used in DeviceAdminReceiver which doesn't support Hilt injection.
         */
        fun create(context: Context): DeviceOwnerPolicyEnforcer {
            return DeviceOwnerPolicyEnforcer(context.applicationContext)
        }
        
        // Re-export constants for backward compatibility
        val RESTRICTION_MAP = DeviceRestrictions.RESTRICTION_MAP
    }

    private val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val admin = ComponentName(context, FamilyEyeDeviceAdmin::class.java)
    private var lastSettingsBlock: Boolean? = null
    private var protectionsActive: Boolean = true

    // Delegate managers for cleaner code
    private val restrictionManager = RestrictionManager(context, dpm, admin)
    private val permissionManager = PermissionManager(context, dpm, admin)

    // ==================== Status Methods ====================

    fun isDeviceOwner(): Boolean = dpm.isDeviceOwnerApp(context.packageName)

    fun areProtectionsActive(): Boolean = protectionsActive && isDeviceOwner()

    fun getProtectionLevel(): String {
        if (!isDeviceOwner()) return "NONE"
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            "GOD_MODE"
        } else {
            "RESURRECTION_MODE"
        }
    }

    // ==================== Baseline Restrictions ====================

    /**
     * Apply baseline OS restrictions for child devices.
     * Safe to call repeatedly (idempotent).
     */
    fun applyBaselineRestrictions() {
        if (!isDeviceOwner()) return
        try {
            restrictionManager.applyBaselineRestrictions()
            
            // Prevent Force Stop on Android 11+
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                safeSetControlDisabledPackages(listOf(context.packageName))
            }
            
            Timber.i("DeviceOwner: Baseline restrictions and control disabling applied")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to apply baseline restrictions")
        }
    }

    // ==================== Settings Protection ====================

    /**
     * Block or allow Settings-like apps at OS level using package suspension.
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
            Timber.e(e, "DeviceOwner: Failed to apply settings protection")
        }
    }

    // ==================== Uninstall Blocking ====================

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

    // ==================== Kiosk Mode ====================

    fun enableKioskMode(packages: Array<String>) {
        if (!isDeviceOwner()) return
        try {
            dpm.setLockTaskPackages(admin, packages)
            Timber.i("DeviceOwner: Kiosk mode enabled for ${packages.size} packages")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to enable kiosk mode")
        }
    }

    fun disableKioskMode() {
        if (!isDeviceOwner()) return
        try {
            dpm.setLockTaskPackages(admin, emptyArray())
            Timber.i("DeviceOwner: Kiosk mode disabled")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to disable kiosk mode")
        }
    }

    // ==================== Activation / Deactivation ====================

    /**
     * Called after Device Owner provisioning is complete.
     */
    fun onDeviceOwnerActivated() {
        if (!isDeviceOwner()) {
            Timber.w("onDeviceOwnerActivated called but not Device Owner")
            return
        }
        
        Timber.i("Device Owner activated - applying full protection")
        applyBaselineRestrictions()
        setUninstallBlocked(true)
        whitelistFromBatteryOptimizations()
    }

    /**
     * Deactivate ALL Device Owner protections.
     * Allows parent to remove FamilyEye from child's device.
     */
    fun deactivateAllProtections(): Boolean {
        if (!isDeviceOwner()) return false
        
        return try {
            Timber.i("DeviceOwner: Deactivating all protections...")
            
            restrictionManager.clearBaselineRestrictions()
            setUninstallBlocked(false)
            
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                safeSetControlDisabledPackages(emptyList())
            }
            
            applySettingsProtection(false)
            disableKioskMode()
            protectionsActive = false
            
            // Relinquish Device Owner status
            try {
                @Suppress("DEPRECATION")
                dpm.clearDeviceOwnerApp(context.packageName)
                Timber.i("DeviceOwner: Relinquished Device Owner status")
            } catch (e: Exception) {
                Timber.e(e, "DeviceOwner: Failed to relinquish DO status")
            }
            
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to deactivate all protections")
            false
        }
    }

    /**
     * Reactivate all Device Owner protections.
     */
    fun reactivateAllProtections(): Boolean {
        if (!isDeviceOwner()) return false
        
        return try {
            Timber.i("DeviceOwner: Reactivating all protections...")
            applyBaselineRestrictions()
            setUninstallBlocked(true)
            protectionsActive = true
            Timber.i("DeviceOwner: All protections reactivated")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to reactivate protections")
            false
        }
    }

    // ==================== Restriction Management (Delegated) ====================

    fun removeRestriction(restrictionName: String): Boolean {
        if (!isDeviceOwner()) return false
        return restrictionManager.removeRestriction(restrictionName)
    }

    fun setRestriction(restrictionName: String, enabled: Boolean): Boolean {
        if (!isDeviceOwner()) return false
        return restrictionManager.setRestriction(restrictionName, enabled)
    }

    fun getActiveRestrictions(): List<String> {
        if (!isDeviceOwner()) return emptyList()
        return restrictionManager.getActiveRestrictions()
    }

    fun applyRestrictions(restrictions: Map<String, Boolean>): Boolean {
        if (!isDeviceOwner()) return false
        return restrictionManager.applyRestrictions(restrictions)
    }

    // ==================== Permission Management (Delegated) ====================

    fun grantRuntimePermission(packageName: String, permission: String): Boolean {
        if (!isDeviceOwner()) return false
        return permissionManager.grantPermission(packageName, permission)
    }

    fun grantAllRequiredPermissions(): Boolean {
        if (!isDeviceOwner()) return false
        return permissionManager.grantAllRequiredPermissions()
    }

    // ==================== Device Controls ====================

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

    fun setCameraDisabled(disabled: Boolean): Boolean {
        if (!isDeviceOwner()) return false
        return try {
            dpm.setCameraDisabled(admin, disabled)
            Timber.i("DeviceOwner: Camera ${if (disabled) "disabled" else "enabled"}")
            true
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to set camera disabled")
            false
        }
    }

    // ==================== Private Helpers ====================

    private fun whitelistFromBatteryOptimizations() {
        if (!isDeviceOwner()) return
        try {
            dpm.setPackagesSuspended(admin, arrayOf(context.packageName), false)
            grantRuntimePermission(context.packageName, android.Manifest.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            Timber.i("DeviceOwner: Whitelisted from battery optimizations")
        } catch (e: Exception) {
            Timber.e(e, "DeviceOwner: Failed to whitelist from battery optimizations")
        }
    }

    private fun getInstalledSettingsPackages(): List<String> {
        val pm = context.packageManager
        return PackageMatcher.getSettingsPackages().filter { pkg ->
            isPackageInstalled(pm, pkg)
        }
    }

    private fun isPackageInstalled(pm: PackageManager, packageName: String): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                pm.getPackageInfo(packageName, PackageManager.PackageInfoFlags.of(0))
            } else {
                @Suppress("DEPRECATION")
                pm.getPackageInfo(packageName, 0)
            }
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun safeSetControlDisabledPackages(packages: List<String>) {
        try {
            val method = DevicePolicyManager::class.java.getMethod(
                "setControlDisabledPackages", 
                ComponentName::class.java, 
                List::class.java
            )
            method.invoke(dpm, admin, packages)
            Timber.i("DeviceOwner: setControlDisabledPackages applied to ${packages.size} packages")
        } catch (e: NoSuchMethodException) {
            Timber.d("DeviceOwner: setControlDisabledPackages not available")
        } catch (e: Exception) {
            Timber.w(e, "DeviceOwner: Failed to call setControlDisabledPackages")
        }
    }
}
