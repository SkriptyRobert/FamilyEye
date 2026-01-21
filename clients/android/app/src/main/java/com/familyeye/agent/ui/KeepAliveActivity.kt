package com.familyeye.agent.ui

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import com.familyeye.agent.service.FamilyEyeService
import timber.log.Timber

/**
 * Transparent Activity used to "kick" the application process back to life
 * with high priority after a "Clear All" or crash.
 * 
 * Starting an Activity forces the Android system to recognize the app as 
 * "Foreground" / User-Interactive for a moment, which dramatically increases
 * the chance that the System will re-bind the Accessibility Service (AppDetector).
 */
class KeepAliveActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Timber.d("KeepAliveActivity: Kicking process...")

        // 1. Ensure Service is running
        try {
            FamilyEyeService.start(this)
        } catch (e: Exception) {
            Timber.e(e, "Failed to start service from KeepAlive")
        }

        // 2. Finish immediately - we don't need to show UI
        finish()
        overridePendingTransition(0, 0) // No animation
    }
}
