package com.familyeye.agent.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.view.accessibility.AccessibilityEvent
import com.familyeye.agent.enforcement.EnforcementResult
import com.familyeye.agent.enforcement.EnforcementService
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
 * 
 * Refactored to delegate logic to:
 * - EnforcementService: For blocking decisions
 * - ContentScanner: For Smart Shield
 * - ScreenshotHandler: For capturing evidence (moved to private method for now)
 */
@AndroidEntryPoint
class AppDetectorService : AccessibilityService() {

    companion object {
        @Volatile
        var currentPackage: String? = null
        
        @Volatile
        var instance: AppDetectorService? = null
    }

    @Inject
    lateinit var enforcementService: EnforcementService

    @Inject
    lateinit var blockOverlayManager: BlockOverlayManager

    @Inject
    lateinit var usageTracker: UsageTracker

    @Inject
    lateinit var reporter: Reporter

    @Inject
    lateinit var contentScanner: com.familyeye.agent.scanner.ContentScanner

    @Inject
    lateinit var configRepository: com.familyeye.agent.data.repository.AgentConfigRepository

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var isPaired = false

    // Known browser packages for content scanning
    private val BROWSER_PACKAGES = setOf(
        "com.android.chrome",
        "com.google.android.apps.chrome",
        "com.sec.android.app.sbrowser",
        "org.mozilla.firefox",
        "com.microsoft.emmx",
        "com.opera.browser",
        "com.brave.browser"
    )

    override fun onCreate() {
        super.onCreate()
        Timber.d("AppDetectorService created")
        instance = this
        
        // Monitor Paired State
        serviceScope.launch {
            if (::configRepository.isInitialized) {
                configRepository.isPaired.collect { paired ->
                    isPaired = paired
                    Timber.i("AppDetectorService: Pairing state changed to $paired")
                }
            }
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        val info = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED or
                         AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED or
                         AccessibilityEvent.TYPE_VIEW_SCROLLED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or 
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100
        }
        serviceInfo = info
        Timber.d("AppDetectorService connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (!isPaired) return
        
        val packageName = event?.packageName?.toString() ?: return
        val className = event.className?.toString()

        // 1. Handle Window State Changes (App Switching)
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            currentPackage = packageName
            
            // Delegate blocking logic to EnforcementService
            handleWindowChange(packageName, className)
            
            // Trigger Smart Shield scanning
            if (::contentScanner.isInitialized) {
                contentScanner.processScreen(rootInActiveWindow, packageName)
            }
        }
        
        // 2. Handle Content Changes (Browsers only)
        else if (event.eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED || 
                 event.eventType == AccessibilityEvent.TYPE_VIEW_SCROLLED) {
            
            if (BROWSER_PACKAGES.contains(packageName)) {
                if (::contentScanner.isInitialized) {
                    val root = try { rootInActiveWindow } catch (e: Exception) { null }
                    contentScanner.processScreen(root, packageName)
                }
            }
        }
    }

    private fun handleWindowChange(packageName: String, className: String?) {
        try {
            if (!::enforcementService.isInitialized) return

            // synchronous checks (allow/block decisions that don't need DB)
            when (val result = enforcementService.evaluate(packageName, className)) {
                is EnforcementResult.Allow -> {
                    // Allowed so far, check async time limits
                    checkTimeLimits(packageName)
                }
                is EnforcementResult.Whitelisted -> {
                    // Fix for overlay disappearing on Home:
                    // If we are showing an overlay, and we switch to:
                    // 1. Ourselves (Agent)
                    // 2. The Launcher (Home Screen)
                    // Then we shoud NOT hide the overlay automatically. The user must dismiss it.
                    val isSelf = packageName == this.packageName
                    val isLauncher = enforcementService.isLauncher(packageName)
                    
                    if ((isSelf || isLauncher) && blockOverlayManager.isShowing()) {
                        Timber.d("Ignoring whitelist hide for $packageName (overlay is likely cause/active)")
                    } else {
                        blockOverlayManager.hide()
                    }
                }
                is EnforcementResult.Block -> {
                    // "Brick Mode" logic:
                    // If Device is LOCKED or in SCHEDULE DOWNTIME, block the Notification Shade (SystemUI).
                    // This prevents bypassing the overlay or accessing quick settings.
                    val isStrictLock = result.blockType == BlockType.DEVICE_LOCK || result.blockType == BlockType.DEVICE_SCHEDULE
                    
                    if (isStrictLock && packageName == "com.android.systemui") {
                        Timber.d("Blocking SystemUI (Notification Shade) due to Strict Lock")
                        performGlobalAction(GLOBAL_ACTION_BACK)
                    } else if (enforcementService.isLauncher(packageName)) {
                        // Don't block launcher physically (loop), just overlay
                        blockOverlayManager.show(packageName, result.blockType, result.scheduleInfo)
                    } else {
                        blockApp(packageName, result.blockType, result.scheduleInfo)
                    }
                }
                is EnforcementResult.TamperingDetected -> {
                    // Critical tampering event
                    handleTampering(packageName, className ?: "unknown")
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "Error handling window change")
        }
    }

    fun recheckEnforcement() {
        serviceScope.launch {
            val pkg = currentPackage
            if (pkg != null) {
                handleWindowChange(pkg, null)
            }
        }
    }

    private fun checkTimeLimits(packageName: String) {
        serviceScope.launch {
            if (!::usageTracker.isInitialized) return@launch

            val totalUsage = usageTracker.getTotalUsageToday()
            val appUsage = usageTracker.getUsageToday(packageName)

            when (val result = enforcementService.evaluateTimeLimits(packageName, appUsage, totalUsage)) {
                is EnforcementResult.Block -> {
                    blockApp(packageName, result.blockType)
                }
                is EnforcementResult.Allow -> {
                    // Critical Fix: If we were blocked but now are allowed (e.g. time added, schedule ended),
                    // we MUST hide the overlay if it's showing.
                    if (blockOverlayManager.isShowing()) {
                        Timber.i("Unblocking $packageName - Time limits passed/refreshed")
                        blockOverlayManager.hide()
                    }
                }
                else -> {
                     // Do nothing on allow? Or hide?
                }
            }
        }
    }

    fun blockApp(packageName: String, blockType: BlockType, scheduleInfo: String? = null) {
        Timber.w("BLOCKED: $packageName ($blockType)")
        
        // 1. Force minimize app first
        performGlobalAction(GLOBAL_ACTION_HOME)
        
        // 2. Wait a tiny bit for transition to start, then show overlay
        // This prevents the "flicker" where overlay shows on top of app before it closes
        serviceScope.launch {
            kotlinx.coroutines.delay(150)
            blockOverlayManager.show(packageName, blockType, scheduleInfo)
        }
    }

    private fun handleTampering(packageName: String, className: String) {
        Timber.e("TAMPERING DETECTED: $packageName / $className")
        blockApp(packageName, BlockType.TAMPERING)
        
        // Report critical event
        serviceScope.launch {
            if (::reporter.isInitialized) {
                val tamperingKeyword = ShieldKeyword(0, 0, "TAMPERING", "SECURITY", "CRITICAL", true)
                requestScreenshot { bitmap ->
                    reporter.reportShieldAlert(tamperingKeyword, packageName, "Anti-Tamper: $className", bitmap)
                }
            }
        }
    }

    fun handleSmartShieldDetection(keyword: ShieldKeyword, packageName: String, contextText: String) {
        Timber.w("SMART SHIELD HIT: ${keyword.keyword} in $packageName")
        
        serviceScope.launch {
            kotlinx.coroutines.delay(1000) 
            requestScreenshot { bitmap ->
                if (::reporter.isInitialized) {
                    reporter.reportShieldAlert(keyword, packageName, contextText, bitmap)
                }
            }
        }
    }

    fun requestScreenshot(callback: (android.graphics.Bitmap?) -> Unit) {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
            takeScreenshot(
                android.view.Display.DEFAULT_DISPLAY,
                this.mainExecutor,
                object : TakeScreenshotCallback {
                    override fun onSuccess(result: AccessibilityService.ScreenshotResult) {
                        try {
                            val bitmap = android.graphics.Bitmap.wrapHardwareBuffer(
                                result.hardwareBuffer, result.colorSpace
                            )
                            callback(bitmap)
                        } catch (e: Exception) {
                            Timber.e(e, "Failed to wrap screenshot")
                            callback(null)
                        }
                    }
                    override fun onFailure(errorCode: Int) {
                        callback(null)
                    }
                }
            )
        } else {
            callback(null)
        }
    }

    override fun onInterrupt() {}
    
    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }
}

