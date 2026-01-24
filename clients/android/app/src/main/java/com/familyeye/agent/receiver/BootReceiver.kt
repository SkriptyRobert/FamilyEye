package com.familyeye.agent.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.familyeye.agent.service.FamilyEyeService
import timber.log.Timber

/**
 * Receives various system broadcasts to ensure service is always running:
 * - BOOT_COMPLETED: Device restart
 * - QUICKBOOT_POWERON: Quick boot (some OEMs)
 * - MY_PACKAGE_REPLACED: App update
 * - USER_PRESENT: Screen unlock
 * - ACTION_POWER_CONNECTED: Charger connected
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action
        Timber.i("BootReceiver triggered: $action")
        
        when (action) {
            Intent.ACTION_BOOT_COMPLETED,
            "android.intent.action.QUICKBOOT_POWERON",
            Intent.ACTION_MY_PACKAGE_REPLACED,
            Intent.ACTION_USER_PRESENT,
            Intent.ACTION_POWER_CONNECTED -> {
                Timber.i("Starting FamilyEye Service from: $action")
                try {
                    FamilyEyeService.start(context)
                } catch (e: Exception) {
                    Timber.e(e, "Failed to start service from BootReceiver")
                }
            }
        }
    }
}
