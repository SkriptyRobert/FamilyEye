package com.familyeye.agent.receiver

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast
import timber.log.Timber

/**
 * Device Admin Receiver for MDM functionalities.
 * Handles events: enabled, disabled, password changed, etc.
 * Provides anti-tampering protection.
 */
class FamilyEyeDeviceAdmin : DeviceAdminReceiver() {
    
    override fun onEnabled(context: Context, intent: Intent) {
        super.onEnabled(context, intent)
        Timber.i("Device Admin Enabled - Protection active")
        Toast.makeText(context, "FamilyEye: Ochrana aktivována", Toast.LENGTH_SHORT).show()
    }

    override fun onDisabled(context: Context, intent: Intent) {
        super.onDisabled(context, intent)
        Timber.w("Device Admin Disabled - TAMPERING DETECTED!")
        // Log this event for later sync to backend
        logTamperingAttempt(context, "DEVICE_ADMIN_DISABLED")
    }

    override fun onDisableRequested(context: Context, intent: Intent): CharSequence {
        Timber.w("Device Admin disable requested - POTENTIAL TAMPERING")
        logTamperingAttempt(context, "DEVICE_ADMIN_DISABLE_REQUESTED")
        
        // Return a warning message that will be shown to the user
        return "UPOZORNĚNÍ: Deaktivace správce zařízení umožní dítěti odinstalovat FamilyEye. " +
               "Tato akce bude zaznamenána a nahlášena rodiči."
    }
    
    override fun onLockTaskModeEntering(context: Context, intent: Intent, pkg: String) {
        super.onLockTaskModeEntering(context, intent, pkg)
        Timber.i("Entering Lock Task Mode (Kiosk)")
    }

    override fun onLockTaskModeExiting(context: Context, intent: Intent) {
        super.onLockTaskModeExiting(context, intent)
        Timber.i("Exiting Lock Task Mode (Kiosk)")
    }

    private fun logTamperingAttempt(context: Context, eventType: String) {
        try {
            // Store in SharedPreferences for later sync
            val prefs = context.getSharedPreferences("tampering_log", Context.MODE_PRIVATE)
            val timestamp = System.currentTimeMillis()
            val existingLog = prefs.getString("events", "") ?: ""
            val newEntry = "$timestamp:$eventType"
            val updatedLog = if (existingLog.isEmpty()) newEntry else "$existingLog,$newEntry"
            prefs.edit().putString("events", updatedLog).apply()
            
            Timber.w("Tampering event logged: $eventType")
        } catch (e: Exception) {
            Timber.e(e, "Failed to log tampering event")
        }
    }
}
