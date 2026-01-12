package com.familyeye.agent.receiver

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import timber.log.Timber

/**
 * Device Admin Receiver for MDM functionalities.
 * Handled events: enabled, disabled, password changed, etc.
 */
class FamilyEyeDeviceAdmin : DeviceAdminReceiver() {
    
    override fun onEnabled(context: Context, intent: Intent) {
        super.onEnabled(context, intent)
        Timber.i("Device Admin Enabled")
    }

    override fun onDisabled(context: Context, intent: Intent) {
        super.onDisabled(context, intent)
        Timber.i("Device Admin Disabled")
    }
    
    override fun onLockTaskModeEntering(context: Context, intent: Intent, pkg: String) {
        super.onLockTaskModeEntering(context, intent, pkg)
        Timber.i("Entering Lock Task Mode (Kiosk)")
    }

    override fun onLockTaskModeExiting(context: Context, intent: Intent) {
        super.onLockTaskModeExiting(context, intent)
        Timber.i("Exiting Lock Task Mode (Kiosk)")
    }
}
