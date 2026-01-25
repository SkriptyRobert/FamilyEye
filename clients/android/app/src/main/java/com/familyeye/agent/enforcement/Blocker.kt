package com.familyeye.agent.enforcement

import android.content.Context
import android.content.Intent
import com.familyeye.agent.service.BlockOverlayManager
import com.familyeye.agent.ui.screens.BlockType
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Centralized executor for blocking actions.
 * 
 * Provides a single "How to Block" implementation used by both:
 * 1. AppDetectorService (Fast Path - Accessibility)
 * 2. UsageTracker (Slow Path - UsageStats)
 */
@Singleton
class Blocker @Inject constructor(
    @ApplicationContext private val context: Context,
    private val blockOverlayManager: BlockOverlayManager
) {

    /**
     * Execute a block action against a specific package.
     * 
     * Actions taken:
     * 1. Launch HOME intent (to close the app)
     * 2. Show the Blocking Overlay (to explain why)
     */
    fun block(
        packageName: String, 
        blockType: BlockType, 
        scheduleInfo: String? = null
    ) {
        Timber.i("BLOCKING $packageName ($blockType)")
        
        // 1. Force Home Screen (The "Kick")
        performHomeAction()
        
        // 2. Show Overlay (The "Shield")
        // We use the main thread for UI operations
        CoroutineScope(Dispatchers.Main).launch {
            blockOverlayManager.show(packageName, blockType, scheduleInfo)
        }
    }

    private fun performHomeAction() {
        try {
            val startMain = Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_HOME)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(startMain)
        } catch (e: Exception) {
            Timber.e(e, "Failed to perform Home action")
        }
    }
}
