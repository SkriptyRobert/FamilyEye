package com.familyeye.agent.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.view.accessibility.AccessibilityEvent
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber
import javax.inject.Inject

/**
 * Service to detect foreground app changes using Accessibility API.
 * This is faster and more reliable than UsageStatsManager for instant blocking.
 */
@AndroidEntryPoint // Helper not directly usable in Service without manual injection or HiltService
class AppDetectorService : AccessibilityService() {

    companion object {
        @Volatile
        var currentPackage: String? = null
    }

    @Inject
    lateinit var ruleEnforcer: RuleEnforcer

    override fun onCreate() {
        super.onCreate()
        Timber.d("AppDetectorService created")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        val info = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
            notificationTimeout = 100
        }
        serviceInfo = info
        Timber.d("AppDetectorService connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val packageName = event.packageName?.toString() ?: return
            val className = event.className?.toString() ?: ""
            
            // Update global state for UsageTracker
            currentPackage = packageName

            // Skip our own app
            if (packageName == this.packageName) return 

            // 1. SELF-PROTECTION: Block Device Admin Deactivation
            // Check if "Unlock Settings" is active (admin bypass)
            val isUnlocked = try {
                 ::ruleEnforcer.isInitialized && ruleEnforcer.isUnlockSettingsActive()
            } catch (e: Exception) {
                false
            }

            if (!isUnlocked && 
                packageName == "com.android.settings" && 
                className.contains("DeviceAdminAdd")) {
                
                Timber.w("BLOCKED attempt to deactivate Device Admin!")
                performGlobalAction(GLOBAL_ACTION_HOME)
                
                // Optional: Show Toast
                // Toast.makeText(this, "Tato akce je blokována rodičem.", Toast.LENGTH_LONG).show()
                return
            }
            // Basic blocking check
            // Note: In real production code, we need to handle injection properly (EntryPoints) checking 
            // if 'ruleEnforcer' is initialized. For now, assuming Hilt works.
            
            // Determining blocking (Commented out until UI is ready)
            /*
            if (ruleEnforcer.isAppBlocked(packageName)) {
                performGlobalAction(GLOBAL_ACTION_HOME)
                // TODO: Launch Overlay Activity
                Timber.w("BLOCKED: $packageName")
            }
            */
            Timber.v("Window detected: $packageName / $className")
        }
    }

    override fun onInterrupt() {
        Timber.w("AppDetectorService interrupted")
    }
}
