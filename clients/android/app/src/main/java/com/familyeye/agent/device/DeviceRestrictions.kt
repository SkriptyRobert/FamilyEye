package com.familyeye.agent.device

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.os.UserManager
import com.familyeye.agent.receiver.FamilyEyeDeviceAdmin
import timber.log.Timber

/**
 * Constants and helper functions for Device Owner restrictions.
 * Extracted from DeviceOwnerPolicyEnforcer for better modularity.
 */
object DeviceRestrictions {
    
    /**
     * Map of restriction names (for API/dashboard) to UserManager constants.
     * Used for dynamic restriction management from the dashboard.
     */
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
        "disallow_config_date_time" to UserManager.DISALLOW_CONFIG_DATE_TIME,
        "disallow_mount_physical_media" to UserManager.DISALLOW_MOUNT_PHYSICAL_MEDIA,
        "disallow_config_wifi" to UserManager.DISALLOW_CONFIG_WIFI,
        "disallow_config_bluetooth" to UserManager.DISALLOW_CONFIG_BLUETOOTH,
        "disallow_sms" to UserManager.DISALLOW_SMS,
        "disallow_outgoing_calls" to UserManager.DISALLOW_OUTGOING_CALLS,
        "disallow_share_location" to UserManager.DISALLOW_SHARE_LOCATION
    )
    
    /**
     * Balanced preset - default restrictions for child devices.
     * These are applied automatically when Device Owner is activated.
     */
    val BASELINE_RESTRICTIONS = listOf(
        UserManager.DISALLOW_SAFE_BOOT,
        UserManager.DISALLOW_FACTORY_RESET,
        UserManager.DISALLOW_ADD_USER,
        UserManager.DISALLOW_REMOVE_USER,
        UserManager.DISALLOW_INSTALL_APPS,
        UserManager.DISALLOW_UNINSTALL_APPS,
        UserManager.DISALLOW_APPS_CONTROL,
        UserManager.DISALLOW_MODIFY_ACCOUNTS,
        UserManager.DISALLOW_INSTALL_UNKNOWN_SOURCES,
        UserManager.DISALLOW_CONFIG_DATE_TIME,
        UserManager.DISALLOW_MOUNT_PHYSICAL_MEDIA
    )
    
    /**
     * Required runtime permissions for FamilyEye agent.
     */
    val REQUIRED_PERMISSIONS = listOf(
        android.Manifest.permission.ACCESS_FINE_LOCATION,
        android.Manifest.permission.ACCESS_COARSE_LOCATION,
        android.Manifest.permission.CAMERA,
        android.Manifest.permission.READ_CONTACTS,
        android.Manifest.permission.READ_CALL_LOG,
        android.Manifest.permission.READ_SMS
    )
}

/**
 * Helper class for managing individual restrictions.
 * Provides a clean API for restriction operations.
 */
class RestrictionManager(
    private val context: Context,
    private val dpm: DevicePolicyManager,
    private val admin: ComponentName
) {
    
    /**
     * Set a specific restriction by name.
     * @return true if successful
     */
    fun setRestriction(restrictionName: String, enabled: Boolean): Boolean {
        val restriction = DeviceRestrictions.RESTRICTION_MAP[restrictionName]
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
     * Remove a specific restriction by name.
     */
    fun removeRestriction(restrictionName: String): Boolean {
        return setRestriction(restrictionName, false)
    }
    
    /**
     * Get list of currently active restrictions.
     */
    fun getActiveRestrictions(): List<String> {
        val userManager = context.getSystemService(Context.USER_SERVICE) as UserManager
        val activeRestrictions = mutableListOf<String>()
        
        DeviceRestrictions.RESTRICTION_MAP.forEach { (name, restriction) ->
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
     * Apply multiple restrictions from a map.
     */
    fun applyRestrictions(restrictions: Map<String, Boolean>): Boolean {
        var allSuccess = true
        restrictions.forEach { (name, enabled) ->
            if (!setRestriction(name, enabled)) {
                allSuccess = false
            }
        }
        return allSuccess
    }
    
    /**
     * Apply all baseline restrictions.
     */
    fun applyBaselineRestrictions() {
        DeviceRestrictions.BASELINE_RESTRICTIONS.forEach { restriction ->
            try {
                dpm.addUserRestriction(admin, restriction)
            } catch (e: Exception) {
                Timber.w("Failed to add restriction: $restriction")
            }
        }
    }
    
    /**
     * Clear all baseline restrictions.
     */
    fun clearBaselineRestrictions() {
        DeviceRestrictions.BASELINE_RESTRICTIONS.forEach { restriction ->
            try {
                dpm.clearUserRestriction(admin, restriction)
            } catch (e: Exception) {
                Timber.w("Failed to clear restriction: $restriction")
            }
        }
    }
}

/**
 * Helper class for managing runtime permissions.
 */
class PermissionManager(
    private val context: Context,
    private val dpm: DevicePolicyManager,
    private val admin: ComponentName
) {
    
    /**
     * Grant a runtime permission to a package.
     */
    fun grantPermission(packageName: String, permission: String): Boolean {
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
     * Grant all required permissions to FamilyEye.
     */
    fun grantAllRequiredPermissions(): Boolean {
        var allGranted = true
        DeviceRestrictions.REQUIRED_PERMISSIONS.forEach { permission ->
            if (!grantPermission(context.packageName, permission)) {
                allGranted = false
            }
        }
        return allGranted
    }
}
