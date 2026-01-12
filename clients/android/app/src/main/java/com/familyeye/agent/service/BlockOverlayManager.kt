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
// import dagger.hilt.android.EntryPointAccessors // Unused
import timber.log.Timber

/**
 * Manages the full-screen overlay when an app is blocked.
 */
class BlockOverlayManager(private val context: Context) : LifecycleOwner, ViewModelStoreOwner, SavedStateRegistryOwner {

    private val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var overlayView: ComposeView? = null

    // Lifecycle requirements for ComposeView in Service
    private val lifecycleRegistry = LifecycleRegistry(this)
    private val _viewModelStore = ViewModelStore() // renamed to avoid conflict
    private val savedStateRegistryController = SavedStateRegistryController.create(this)

    override val lifecycle: Lifecycle = lifecycleRegistry
    override val viewModelStore: ViewModelStore = _viewModelStore // correct override
    override val savedStateRegistry: SavedStateRegistry = savedStateRegistryController.savedStateRegistry

    init {
        savedStateRegistryController.performRestore(null)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
    }

    fun show(appName: String) {
        if (overlayView != null) return

        Timber.i("Showing block overlay for $appName")
        
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) 
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY 
            else 
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or 
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.CENTER
        }

        overlayView = ComposeView(context).apply {
            setContent {
                BlockOverlayScreen(appName = appName) {
                    hide()
                }
            }
            // Set owners for Compose using extension methods
            this.setViewTreeLifecycleOwner(this@BlockOverlayManager)
            this.setViewTreeViewModelStoreOwner(this@BlockOverlayManager)
            this.setViewTreeSavedStateRegistryOwner(this@BlockOverlayManager)
        }

        try {
            windowManager.addView(overlayView, params)
            lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_START)
            lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
        } catch (e: Exception) {
            Timber.e(e, "Failed to show overlay")
        }
    }

    fun hide() {
        if (overlayView == null) return
        
        Timber.i("Hiding block overlay")
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_PAUSE)
        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_STOP)
        
        try {
            windowManager.removeView(overlayView)
        } catch (e: Exception) {
            Timber.e(e, "Failed to remove overlay")
        }
        overlayView = null
    }
}
