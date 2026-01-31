package com.familyeye.agent.ui

import android.app.Activity
import android.os.Bundle
import com.familyeye.agent.receiver.RestartReceiver
import com.familyeye.agent.service.FamilyEyeService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import timber.log.Timber

/**
 * Transparent Activity used to "kick" the application process back to life
 * with high priority after a "Clear All" or crash.
 * 
 * Starting an Activity forces the Android system to recognize the app as 
 * "Foreground" / User-Interactive for a moment, which dramatically increases
 * the chance that the System will re-bind the Accessibility Service (AppDetector).
 * 
 * Includes debounce mechanism to prevent concurrent restart attempts.
 */
class KeepAliveActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val source = intent.getStringExtra("source") ?: "unknown"
        
        // Debounce check - skip if restart was triggered recently
        if (!RestartReceiver.shouldProceedWithRestart(this, "KeepAlive:$source")) {
            Timber.d("KeepAliveActivity: Skipped (debounced) from '$source'")
            finish()
            return
        }
        
        Timber.i("KeepAliveActivity: Recovery triggered from '$source'")

        // 1. Ensure Service is running first
        try {
            FamilyEyeService.start(this)
            Timber.i("FamilyEyeService.start() called from KeepAlive")
        } catch (e: Exception) {
            Timber.e(e, "Failed to start service from KeepAlive")
        }

        // 2. Wait to allow service to stabilize before closing
        CoroutineScope(Dispatchers.Main).launch {
            verifyAndFinish()
        }
    }

    /**
     * Wait for service to stabilize then finish.
     * Increased delay to 1000ms to allow Accessibility Service rebinding.
     */
    private suspend fun verifyAndFinish() {
        // Increased delay to allow service and Accessibility rebinding
        delay(1000)
        
        // Finish immediately without animation
        finish()
        @Suppress("DEPRECATION")
        overridePendingTransition(0, 0)
    }
}
