package com.familyeye.agent.ui

import android.app.Activity
import android.content.Intent
import android.os.Bundle
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
 * IMPROVED: Now waits briefly to verify service health and logs recovery source.
 */
class KeepAliveActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val source = intent.getStringExtra("source") ?: "unknown"
        Timber.d("KeepAliveActivity: Recovery triggered from '$source'")

        // 1. Ensure Service is running first
        try {
            FamilyEyeService.start(this)
            Timber.i("FamilyEyeService.start() called")
        } catch (e: Exception) {
            Timber.e(e, "Failed to start service from KeepAlive")
        }

        // 2. Wait and verify service health before closing
        CoroutineScope(Dispatchers.Main).launch {
            verifyAndFinish()
        }
    }

    /**
     * Simplified recovery: Start service and finish immediately.
     * Service will handle Accessibility binding verification internally.
     */
    private suspend fun verifyAndFinish() {
        // Brief delay to allow service to start
        delay(500)
        
        // Finish immediately without animation
        finish()
        overridePendingTransition(0, 0)
    }

}
