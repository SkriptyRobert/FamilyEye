package com.familyeye.agent.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import timber.log.Timber

/**
 * Broadcast Receiver for screen state changes.
 * 
 * When screen turns ON after being off (e.g., user picks up phone after hours),
 * this triggers an immediate sync and WebSocket reconnection to ensure
 * the device reports its status to the backend ASAP.
 */
class ScreenStateReceiver : BroadcastReceiver() {

    companion object {
        private var listener: ScreenStateListener? = null
        
        fun register(context: Context, listener: ScreenStateListener) {
            this.listener = listener
            val filter = IntentFilter().apply {
                addAction(Intent.ACTION_SCREEN_ON)
                addAction(Intent.ACTION_SCREEN_OFF)
            }
            context.registerReceiver(ScreenStateReceiver(), filter)
            Timber.d("ScreenStateReceiver registered")
        }
    }
    
    override fun onReceive(context: Context?, intent: Intent?) {
        when (intent?.action) {
            Intent.ACTION_SCREEN_ON -> {
                Timber.i("Screen turned ON - triggering immediate sync")
                listener?.onScreenOn()
            }
            Intent.ACTION_SCREEN_OFF -> {
                Timber.d("Screen turned OFF")
                listener?.onScreenOff()
            }
        }
    }
}

/**
 * Interface for screen state callbacks.
 */
interface ScreenStateListener {
    fun onScreenOn()
    fun onScreenOff()
}
