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
import com.familyeye.agent.data.api.dto.ShieldKeyword

/**
 * Service to detect foreground app changes using Accessibility API.
 * This is faster and more reliable than UsageStatsManager for instant blocking.
 */
@AndroidEntryPoint // Helper not directly usable in Service without manual injection or HiltService
class AppDetectorService : AccessibilityService() {

    companion object {
        @Volatile
        var currentPackage: String? = null
        
        @Volatile
        var instance: AppDetectorService? = null
    }

    @Inject
    lateinit var ruleEnforcer: RuleEnforcer

    @Inject
    lateinit var blockOverlayManager: BlockOverlayManager

    @Inject
    lateinit var usageTracker: UsageTracker

    @Inject
    lateinit var reporter: Reporter

    @Inject
    lateinit var contentScanner: com.familyeye.agent.scanner.ContentScanner

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    override fun onCreate() {
        super.onCreate()
        Timber.d("AppDetectorService created")
        instance = this
    }
    
    fun requestScreenshot(callback: (android.graphics.Bitmap?) -> Unit) {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
            // API 30+: Use takeScreenshot with integer ID.
            // DO NOT access 'this.display' or 'windowManager.defaultDisplay' from Service context on Android 11+
            // as it throws UnsupportedOperationException.
            
            takeScreenshot(
                android.view.Display.DEFAULT_DISPLAY,
                this.mainExecutor,
                object : TakeScreenshotCallback {
                    override fun onSuccess(screenshot: AccessibilityService.ScreenshotResult) {
                        val bitmap = try {
                            val colorSpace = screenshot.colorSpace
                            val hardwareBuffer = screenshot.hardwareBuffer
                            android.graphics.Bitmap.wrapHardwareBuffer(hardwareBuffer, colorSpace)
                        } catch (e: Exception) {
                            Timber.e(e, "Failed to wrap hardware buffer")
                            null
                        }
                        callback(bitmap)
                    }

                    override fun onFailure(errorCode: Int) {
                        Timber.e("Screenshot failed with error code: $errorCode")
                        callback(null)
                    }
                }
            )
        } else {
            Timber.w("Screenshot not supported on this Android version (<30)")
            callback(null)
        }
    }

    private val BROWSER_PACKAGES = setOf(
        "com.android.chrome",
        "com.google.android.apps.chrome",
        "com.sec.android.app.sbrowser", // Samsung Internet
        "org.mozilla.firefox",
        "com.microsoft.emmx" // Edge
    )

    override fun onServiceConnected() {
        super.onServiceConnected()
        // Use existing info from XML to preserve capabilities (like canTakeScreenshot)
        val info = serviceInfo ?: AccessibilityServiceInfo()
        info.apply {
            // Listen to Window State (App switching) AND Content Changes (Scrolling/Web loading)
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED or
                         AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED or
                         AccessibilityEvent.TYPE_VIEW_SCROLLED
            
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            // Append flags, don't overwrite if we want to keep XML flags (though here we define them explicitly)
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or 
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100
        }
        serviceInfo = info
        Timber.d("AppDetectorService connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return
        val className = event.className?.toString() ?: ""

        // 1. Handle Window State Changes (App Switching) - Full Logic
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            
            // Update global state for UsageTracker
            currentPackage = packageName

            // Skip our own app
            if (packageName == this.packageName) return 

            // ... (Core Blocking Logic - Keep as is)
            // 1. SELF-PROTECTION: Block Device Admin Deactivation
            // (Disabled for now as per user request/testing)


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
            
            // 3. SMART SHIELD (Trigger on Window Change)
            if (::contentScanner.isInitialized) {
                contentScanner.processScreen(rootInActiveWindow, packageName)
            }
        }
        
        // 2. Handle Content Changes / Scrolling (Only for Browsers to save battery)
        else if (event.eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED || 
                 event.eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED) {
            
            if (BROWSER_PACKAGES.contains(packageName)) {
                // Determine if we should scan based on ContentScanner's internal debounce
                // We pass the root window to it. It will ignore if too soon.
                if (::contentScanner.isInitialized) {
                    // Note: rootInActiveWindow might be null during fast scrolls
                    val root = try { rootInActiveWindow } catch (e: Exception) { null }
                    contentScanner.processScreen(root, packageName)
                }
            }
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

    fun handleSmartShieldDetection(keyword: ShieldKeyword, packageName: String, contextText: String) {
        Timber.w("SMART SHIELD HIT: ${keyword.keyword} in $packageName")
        
        // Wait for UI to render (especially for web pages loading)
        serviceScope.launch {
            kotlinx.coroutines.delay(1000) 
            
            requestScreenshot { bitmap ->
                if (bitmap != null) {
                    // Upload alert via Reporter
                    if (::reporter.isInitialized) {
                        reporter.reportShieldAlert(keyword, packageName, contextText, bitmap)
                    }
                } else {
                    // Report without screenshot
                     if (::reporter.isInitialized) {
                        reporter.reportShieldAlert(keyword, packageName, contextText, null)
                    }
                }
            }
        }
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
