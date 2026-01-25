package com.familyeye.agent.device

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
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
    }

    private val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val admin = ComponentName(context, FamilyEyeDeviceAdmin::class.java)
    private var lastSettingsBlock: Boolean? = null

    private val baselineRestrictions = listOf(
        UserManager.DISALLOW_SAFE_BOOT,
        UserManager.DISALLOW_FACTORY_RESET,
        UserManager.DISALLOW_ADD_USER,
        UserManager.DISALLOW_REMOVE_USER,
        UserManager.DISALLOW_INSTALL_APPS,
        UserManager.DISALLOW_UNINSTALL_APPS,
        UserManager.DISALLOW_APPS_CONTROL,
        UserManager.DISALLOW_MODIFY_ACCOUNTS,
        UserManager.DISALLOW_DEBUGGING_FEATURES,
        UserManager.DISALLOW_USB_FILE_TRANSFER
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
            Timber.i("DeviceOwner: Baseline restrictions applied")
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
}
