package com.familyeye.agent.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.view.accessibility.AccessibilityEvent
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.cancel
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

    @Inject
    lateinit var blockOverlayManager: BlockOverlayManager

    @Inject
    lateinit var usageTracker: UsageTracker

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())

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
            /* DISABLED FOR DEV/TESTING as per user request
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
                return
            }
            */

            // 2. APP BLOCKING ENFORCEMENT
            try {
                if (::ruleEnforcer.isInitialized && ::blockOverlayManager.isInitialized && ::usageTracker.isInitialized) {
                    
                    if (isWhitelisted(packageName)) {
                        // Ensure overlay is hidden if we are in a safe app
                         blockOverlayManager.hide()
                         return
                    }

                    // Check 1: Explicit Sync Checks (App Block, Device Lock, Schedule)
                    if (ruleEnforcer.isAppBlocked(packageName) || 
                        ruleEnforcer.isDeviceLocked() || 
                        ruleEnforcer.isScheduleBlocked()) {
                        
                        blockApp(packageName)
                    } else {
                        // Check 2: Async Checks (Daily Limit, App Time Limit)
                        serviceScope.launch {
                            val totalUsage = usageTracker.getTotalUsageToday()
                            val appUsage = usageTracker.getUsageToday(packageName)
                            
                            if (ruleEnforcer.isDailyLimitExceeded(totalUsage) || 
                                ruleEnforcer.isAppTimeLimitExceeded(packageName, appUsage)) {
                                blockApp(packageName)
                            } else {
                                // If allowed, hide.
                                blockOverlayManager.hide()
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                Timber.e(e, "Error during blocking check")
            }
            
            Timber.v("Window detected: $packageName / $className")
        }
    }

    private fun isWhitelisted(packageName: String): Boolean {
        // 1. Self allowed
        if (packageName == this.packageName) return true
        
        // 2. System UI allowed (Notification shade, etc)
        if (packageName == "com.android.systemui") return true
        
        // 3. Settings allowed (for now, to allow admin/uninstall unless specifically blocked)
        // If we want strict mode, we block settings too. But keeping it open is safer for now.
        if (packageName == "com.android.settings") return true
        
        // 4. Launcher allowed (Infinite loop protection)
        // Simple heuristic: if it contains 'launcher', assume it's home.
        // Better: Check intent. For performance, we assume standard search or cache.
        if (packageName.contains("launcher", ignoreCase = true)) return true
        if (packageName.contains("home", ignoreCase = true)) return true // e.g. com.sec.android.app.home (?)
        
        // TODO: Implement robust Launcher detection caching
        
        return false
    }

    private fun blockApp(packageName: String) {
        Timber.w("BLOCKED: $packageName")
        performGlobalAction(GLOBAL_ACTION_HOME)
        blockOverlayManager.show(packageName)
    }

    override fun onInterrupt() {
        Timber.w("AppDetectorService interrupted")
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
        Timber.d("AppDetectorService destroyed")
    }
}
