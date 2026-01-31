package com.familyeye.agent.service

import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.view.Gravity
import android.view.WindowManager
import androidx.compose.ui.platform.ComposeView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import androidx.savedstate.SavedStateRegistry
import androidx.savedstate.SavedStateRegistryController
import androidx.savedstate.SavedStateRegistryOwner
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.lifecycle.setViewTreeViewModelStoreOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.familyeye.agent.ui.screens.BlockOverlayScreen
import com.familyeye.agent.ui.screens.BlockType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Manages the full-screen overlay when an app is blocked.
 * 
 * Improvements:
 * - Debouncing to prevent flickering (tracks current state)
 * - FLAG_NOT_FOCUSABLE to avoid keyboard/focus issues
 * - Stable overlay that doesn't minimize/maximize
 */
@Singleton
class BlockOverlayManager @Inject constructor(
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: Context
) : LifecycleOwner, ViewModelStoreOwner, SavedStateRegistryOwner {

    private val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var overlayView: ComposeView? = null

    // Debouncing state - track what's currently shown
    private var currentBlockedPackage: String? = null
    internal var currentBlockType: BlockType? = null // Internal for Smart Pulse access

    // Lifecycle requirements for ComposeView in Service
    private val lifecycleRegistry = LifecycleRegistry(this)
    private val _viewModelStore = ViewModelStore()
    private val savedStateRegistryController = SavedStateRegistryController.create(this)

    override val lifecycle: Lifecycle = lifecycleRegistry
    override val viewModelStore: ViewModelStore = _viewModelStore
    override val savedStateRegistry: SavedStateRegistry = savedStateRegistryController.savedStateRegistry

    init {
        savedStateRegistryController.performRestore(null)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
    }

    /**
     * Show the blocking overlay. Debounced - won't recreate if already showing same block.
     */
    /**
     * Show the blocking overlay. Debounced - won't recreate if already showing same block.
     */
    fun show(appName: String, blockType: BlockType = BlockType.GENERIC, scheduleInfo: String? = null) {
        // Debounce: If already showing overlay for this app+type, skip
        if (overlayView != null && isShowing()) {
             if (currentBlockedPackage == appName && currentBlockType == blockType) {
                 Timber.v("Overlay already showing for $appName ($blockType), skipping")
                 return
             }
             // If different app/type, update text in place instead of recreating view could be smoother,
             // but for now, we'll recreate to be safe.
        }

        // If showing for a different app (or null), proceed
        
        // Hide existing first to be clean
        if (overlayView != null) {
            hideInternal()
        }

        Timber.i("Showing block overlay for $appName ($blockType) Info: $scheduleInfo")
        
        currentBlockedPackage = appName
        currentBlockType = blockType
        
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) 
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY 
            else 
                WindowManager.LayoutParams.TYPE_PHONE,
            // Key flags for BLOCKING overlay:
            // - NO FLAG_NOT_FOCUSABLE: Overlay captures all input
            // - FLAG_LAYOUT_IN_SCREEN: Draw under status bar
            // - FLAG_LAYOUT_NO_LIMITS: Cover entire screen including nav bar
            // - FLAG_WATCH_OUTSIDE_TOUCH: Detect touches outside (for logging)
            // Result: User CANNOT interact with anything behind the overlay
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
            WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.CENTER
            // Ensure screen stays on so child sees the block message
            screenBrightness = -1f 
        }

        // Create view
        val newOverlay = ComposeView(context).apply {
            setContent {
                BlockOverlayScreen(appName = appName, blockType = blockType, scheduleInfo = scheduleInfo) {
                    // onDismiss callback - User acted on the "Close/Unlock" button
                    Timber.i("User tapped overlay dismiss - hiding overlay")
                    hide() // Allow closing the overlay (e.g. going back to home)
                }
            }
            this.setViewTreeLifecycleOwner(this@BlockOverlayManager)
            this.setViewTreeViewModelStoreOwner(this@BlockOverlayManager)
            this.setViewTreeSavedStateRegistryOwner(this@BlockOverlayManager)
        }

        // Add to WindowManager
        try {
            windowManager.addView(newOverlay, params)
            lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_START)
            lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
            overlayView = newOverlay
            
            // Start zombie detection - hide overlay if service dies
            startZombieDetection()
        } catch (e: Exception) {
            Timber.e(e, "Failed to show overlay")
            overlayView = null
            currentBlockedPackage = null
            currentBlockType = null
        }
    }

    private var zombieDetectionJob: Job? = null

    /**
     * Monitor if the backing service (AppDetectorService) is still alive.
     * If it dies, we should hide the overlay to avoid zombie state where
     * overlay is visible but nothing is actually being enforced.
     */
    private fun startZombieDetection() {
        zombieDetectionJob?.cancel()
        zombieDetectionJob = CoroutineScope(Dispatchers.Main).launch {
            while (overlayView != null) {
                delay(5_000) // Check every 5 seconds
                
                if (AppDetectorService.instance == null) {
                    Timber.w("ZOMBIE DETECTION: Overlay showing but AppDetectorService is DEAD! Hiding zombie overlay.")
                    hide()
                    break
                }
            }
        }
    }

    /**
     * Hide the overlay. Public method with debounce check.
     */
    fun hide() {
        if (overlayView == null) return
        hideInternal()
    }

    /**
     * Internal hide without null check (for use in show() when switching).
     */
    private fun hideInternal() {
        Timber.i("Hiding block overlay")
        
        // Safety check if view is actually attached
        if (overlayView == null) return

        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_PAUSE)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_STOP)
        
        try {
            windowManager.removeView(overlayView)
        } catch (e: Exception) {
            Timber.e(e, "Failed to remove overlay")
        }
        overlayView = null
        currentBlockedPackage = null
        currentBlockType = null
    }

    /**
     * Check if the overlay is currently being shown.
     */
    fun isShowing(): Boolean = overlayView != null && overlayView?.isAttachedToWindow == true

    /**
     * Get currently blocked package name (for debugging/logging).
     */
    fun getCurrentBlockedPackage(): String? = currentBlockedPackage
}

