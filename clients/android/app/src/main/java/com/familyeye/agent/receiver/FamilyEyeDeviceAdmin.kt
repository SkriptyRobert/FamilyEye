package com.familyeye.agent.receiver

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast
import com.familyeye.agent.device.DeviceOwnerPolicyEnforcer
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
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

    /**
     * Called when Device Owner provisioning is complete.
     * This is triggered after successful `dpm set-device-owner` command.
     */
    override fun onProfileProvisioningComplete(context: Context, intent: Intent) {
        super.onProfileProvisioningComplete(context, intent)
        Timber.i("Device Owner provisioning complete!")
        
        // Activate full Device Owner protections
        // Note: Using factory method since DeviceAdminReceiver doesn't support Hilt DI
        val enforcer = DeviceOwnerPolicyEnforcer.create(context)
        enforcer.onDeviceOwnerActivated()
        
        // Notify backend
        notifyBackendDeviceOwnerActivated(context)
        
        // Show UI for account restoration (if needed)
        showAccountRestoreUI(context)
    }

    /**
     * Notify backend that Device Owner has been activated.
     * Note: Backend endpoint will be created in Phase 4.
     */
    private fun notifyBackendDeviceOwnerActivated(context: Context) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Get device ID from SharedPreferences (same storage as AgentConfigRepository)
                val prefs = context.getSharedPreferences("encrypted_prefs", Context.MODE_PRIVATE)
                val deviceId = prefs.getString("device_id", null)
                
                if (deviceId != null) {
                    // Note: Backend endpoint will be created in Phase 4
                    // For now, just log - actual API call will be implemented in Phase 4
                    Timber.i("Device Owner activated - deviceId: $deviceId")
                    Timber.i("Backend notification will be implemented in Phase 4")
                } else {
                    Timber.w("Cannot notify backend - device not paired yet")
                }
            } catch (e: Exception) {
                Timber.e(e, "Failed to notify backend of Device Owner activation")
            }
        }
    }

    /**
     * Show UI to guide user to restore accounts after Device Owner provisioning.
     */
    private fun showAccountRestoreUI(context: Context) {
        // Launch main activity with flag to show account restoration message
        try {
            val intent = Intent(context, com.familyeye.agent.ui.MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("device_owner_activated", true)
            }
            context.startActivity(intent)
            
            Toast.makeText(
                context,
                "Device Owner aktivován! Nyní můžete přidat účty zpět.",
                Toast.LENGTH_LONG
            ).show()
        } catch (e: Exception) {
            Timber.e(e, "Failed to show account restore UI")
        }
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
