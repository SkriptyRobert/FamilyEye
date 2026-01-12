package com.familyeye.agent.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.familyeye.agent.service.FamilyEyeService
import timber.log.Timber

/**
 * Receives BOOT_COMPLETED broadcast to restart the service when device powers on.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || 
            intent.action == "android.intent.action.QUICKBOOT_POWERON") {
            Timber.i("Boot completed, starting FamilyEye Service...")
            FamilyEyeService.start(context)
        }
    }
}
