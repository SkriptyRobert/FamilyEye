package com.familyeye.agent.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.view.accessibility.AccessibilityEvent
import com.familyeye.agent.ui.screens.BlockType
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
                    
                    // A. Device Lock (Highest Priority - Blocks EVERYTHING including Launcher)
                    // We check this BEFORE whitelist (except critical SystemUI) to ensure "Brick" mode works.
                    // A. Device Lock (Highest Priority - Blocks EVERYTHING)
                    if (ruleEnforcer.isDeviceLocked()) {
                         // Security: If SystemUI (Notification Shade) is pulled down during Lock, close it!
                         if (packageName == "com.android.systemui") {
                             Timber.w("Device Locked: Closing Notification Shade")
                             performGlobalAction(GLOBAL_ACTION_BACK)
                             // Also try closing status bar directly if API allows (usually BACK works)
                             return
                         }

                         // If on launcher, just show overlay (don't go home loop)
                         if (isLauncher(packageName)) {
                             blockOverlayManager.show(packageName, BlockType.DEVICE_LOCK)
                         } else {
                             blockApp(packageName, BlockType.DEVICE_LOCK)
                         }
                         return
                    }

                    // B. Whitelist Check (for normal app blocking)
                    if (isWhitelisted(packageName)) {
                         blockOverlayManager.hide()
                         return
                    }

                    // C. Normal Rules (App Block, Schedule, Limits)
                    // Check 1: Explicit Sync Checks
                    if (ruleEnforcer.isAppBlocked(packageName)) {
                         blockApp(packageName, BlockType.APP_FORBIDDEN)
     } else if (ruleEnforcer.isDeviceScheduleBlocked()) {
                         // Global Schedule (e.g. Bedtime) -> Blocks EVERYTHING
                         val rule = ruleEnforcer.getActiveDeviceScheduleRule()
                         val timeStr = if (rule != null) "${rule.scheduleStartTime} - ${rule.scheduleEndTime}" else null

                         if (packageName != "com.android.systemui") {
                             if (isLauncher(packageName)) {
                                 blockOverlayManager.show(packageName, BlockType.DEVICE_SCHEDULE, timeStr)
                             } else {
                                 blockApp(packageName, BlockType.DEVICE_SCHEDULE, timeStr)
                             }
                             return
                         }
                    } else if (ruleEnforcer.isAppScheduleBlocked(packageName)) {
                         // App Specific Schedule
                         val rule = ruleEnforcer.getActiveAppScheduleRule(packageName)
                         val timeStr = if (rule != null) "${rule.scheduleStartTime} - ${rule.scheduleEndTime}" else null

                         blockApp(packageName, BlockType.APP_SCHEDULE, timeStr)
                    } else {
                        // Check 2: Async Checks (Daily Limit, App Time Limit)
                        serviceScope.launch {
                            val totalUsage = usageTracker.getTotalUsageToday()
                            val appUsage = usageTracker.getUsageToday(packageName)
                            
                            if (ruleEnforcer.isDailyLimitExceeded(totalUsage)) {
                                 blockApp(packageName, BlockType.DEVICE_LIMIT)
                            } else if (ruleEnforcer.isAppTimeLimitExceeded(packageName, appUsage)) {
                                 blockApp(packageName, BlockType.APP_LIMIT)
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

    private fun isLauncher(packageName: String): Boolean {
        if (packageName.contains("launcher", ignoreCase = true)) return true
        if (packageName.contains("home", ignoreCase = true)) return true 
        if (packageName == "com.google.android.apps.nexuslauncher" || 
            packageName == "com.sec.android.app.launcher") return true
        return false
    }

    private fun isWhitelisted(packageName: String): Boolean {
        // 1. Self allowed
        if (packageName == this.packageName) return true
        
        // 2. System UI allowed?
        // CAUTION: If we block SystemUI, we might crash.
        // But if we are LOCKED, we handle SystemUI in the main loop (by closing it).
        // Here we just return true for SystemUI to avoid "Blocked" overlayloop on the shade itself?
        // Actually, if we return true here, valid block logic loop won't run.
        // We should allow SystemUI here BUT handle "Lock Mode" check before whitelist.
        if (packageName == "com.android.systemui") return true
        
        // 3. Settings - BLOCKED UNLESS UNLOCKED
        if (packageName == "com.android.settings") {
             if (::ruleEnforcer.isInitialized && ruleEnforcer.isUnlockSettingsActive()) {
                 Timber.w("Settings Allowed (Admin Unlock Active)")
                 return true
             }
             return false // Block settings by default!
        }
        
        // 4. Launcher allowed (Infinite loop protection)
        if (isLauncher(packageName)) {
             Timber.v("Whitelist match (launcher): $packageName")
             return true
        }

        return false
    }

    private fun blockApp(packageName: String, blockType: BlockType = BlockType.GENERIC, scheduleInfo: String? = null) {
        Timber.w("BLOCKED: $packageName ($blockType)")
        performGlobalAction(GLOBAL_ACTION_HOME)
        blockOverlayManager.show(packageName, blockType, scheduleInfo)
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
