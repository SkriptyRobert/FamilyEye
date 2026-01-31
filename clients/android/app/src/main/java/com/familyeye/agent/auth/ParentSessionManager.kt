package com.familyeye.agent.auth

import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Manages parent authentication sessions.
 * 
 * When a parent successfully authenticates via PIN in the app,
 * a temporary session is started that allows Settings access.
 * This enables parents to manage device admin permissions, 
 * accessibility settings, etc. without being blocked.
 * 
 * Session automatically expires after [SESSION_TIMEOUT_MS].
 */
@Singleton
class ParentSessionManager @Inject constructor() {
    
    companion object {
        /** Session timeout in milliseconds (5 minutes) */
        const val SESSION_TIMEOUT_MS = 5 * 60 * 1000L
    }
    
    @Volatile
    private var sessionStartTime: Long = 0L
    
    /**
     * Start a new parent session.
     * Call this after successful PIN verification.
     */
    fun startSession() {
        sessionStartTime = System.currentTimeMillis()
        Timber.i("Parent session started, expires in ${SESSION_TIMEOUT_MS / 1000}s")
    }
    
    /**
     * Check if the parent session is currently active.
     * @return true if parent is authenticated and session hasn't expired
     */
    fun isSessionActive(): Boolean {
        if (sessionStartTime == 0L) return false
        val elapsed = System.currentTimeMillis() - sessionStartTime
        val active = elapsed < SESSION_TIMEOUT_MS
        
        if (!active && sessionStartTime != 0L) {
            // Session just expired
            Timber.i("Parent session expired")
            sessionStartTime = 0L
        }
        
        return active
    }
    
    /**
     * Get remaining session time in seconds.
     * @return remaining seconds, or 0 if no active session
     */
    fun getRemainingSeconds(): Int {
        if (!isSessionActive()) return 0
        val elapsed = System.currentTimeMillis() - sessionStartTime
        return ((SESSION_TIMEOUT_MS - elapsed) / 1000).toInt().coerceAtLeast(0)
    }
    
    /**
     * End the parent session immediately.
     * Call this when parent logs out or when leaving admin screens.
     */
    fun endSession() {
        if (sessionStartTime != 0L) {
            Timber.i("Parent session ended manually")
            sessionStartTime = 0L
        }
    }
}
