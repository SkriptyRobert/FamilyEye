package com.familyeye.agent.time

import android.content.Context
import android.content.SharedPreferences
import android.os.SystemClock
import com.familyeye.agent.utils.TimeUtils
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber
import java.util.Calendar
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Provides secure, tamper-resistant time for usage tracking and rule enforcement.
 * 
 * ### Problem Solved:
 * Children can manipulate device time to bypass parental controls:
 * - Setting time backwards to reset daily limits
 * - Setting time forward to escape schedule blocks
 * 
 * ### Solution:
 * Uses Android's `SystemClock.elapsedRealtime()` which:
 * - Is monotonic (always increases)
 * - Is unaffected by device time changes
 * - Resets on device reboot (handled by persistence)
 * 
 * ### How It Works:
 * 1. On first initialization, records a reference point:
 *    - `referenceWallTime`: Current wall clock time (System.currentTimeMillis)
 *    - `referenceElapsedTime`: Current monotonic time (elapsedRealtime)
 * 2. For subsequent time requests:
 *    - Calculates elapsed monotonic time since reference
 *    - Adds elapsed time to reference wall time
 *    - This gives "secure" time that's resistant to manipulation
 * 3. On device reboot (detected by lower elapsedRealtime):
 *    - Re-syncs reference point
 *    - Optional: Sync with server time if available
 * 
 * ### Limitations:
 * - Cannot prevent time manipulation if device is rebooted
 * - Server time sync improves accuracy but requires network
 * - Initial reference uses wall clock (can be set before agent install)
 */
@Singleton
class SecureTimeProvider @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        private const val PREFS_NAME = "secure_time_prefs"
        private const val KEY_REFERENCE_WALL_TIME = "reference_wall_time"
        private const val KEY_REFERENCE_ELAPSED_TIME = "reference_elapsed_time"
        private const val KEY_LAST_KNOWN_ELAPSED = "last_known_elapsed"
        private const val KEY_SERVER_TIME_OFFSET = "server_time_offset"
        
        // Tolerance for detecting device reboot (5 seconds)
        private const val REBOOT_DETECTION_THRESHOLD_MS = 5_000L
    }

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    // Cached values for performance
    @Volatile private var referenceWallTime: Long = 0
    @Volatile private var referenceElapsedTime: Long = 0
    @Volatile private var serverTimeOffset: Long = 0  // Offset from local to server time

    init {
        initialize()
    }

    /**
     * Initialize or restore the time reference.
     */
    private fun initialize() {
        val savedReferenceWall = prefs.getLong(KEY_REFERENCE_WALL_TIME, 0)
        val savedReferenceElapsed = prefs.getLong(KEY_REFERENCE_ELAPSED_TIME, 0)
        val lastKnownElapsed = prefs.getLong(KEY_LAST_KNOWN_ELAPSED, 0)
        serverTimeOffset = prefs.getLong(KEY_SERVER_TIME_OFFSET, 0)

        val currentElapsed = SystemClock.elapsedRealtime()

        // Check if we have a saved reference
        if (savedReferenceWall > 0 && savedReferenceElapsed > 0) {
            // Check for device reboot (current elapsed < last known elapsed)
            if (currentElapsed < lastKnownElapsed - REBOOT_DETECTION_THRESHOLD_MS) {
                Timber.w("Device reboot detected - re-syncing time reference")
                createNewReference()
            } else {
                // Restore saved reference
                referenceWallTime = savedReferenceWall
                referenceElapsedTime = savedReferenceElapsed
                Timber.d("Time reference restored: wall=$savedReferenceWall, elapsed=$savedReferenceElapsed")
            }
        } else {
            // First time initialization
            Timber.i("Initializing secure time reference for first time")
            createNewReference()
        }

        // Update last known elapsed time
        saveLastKnownElapsed(currentElapsed)
    }

    /**
     * Create a new time reference point.
     * Uses current wall time and elapsed time as the reference.
     */
    private fun createNewReference() {
        referenceWallTime = System.currentTimeMillis()
        referenceElapsedTime = SystemClock.elapsedRealtime()

        prefs.edit()
            .putLong(KEY_REFERENCE_WALL_TIME, referenceWallTime)
            .putLong(KEY_REFERENCE_ELAPSED_TIME, referenceElapsedTime)
            .apply()

        Timber.i("New time reference created: wall=$referenceWallTime, elapsed=$referenceElapsedTime")
    }

    /**
     * Save the last known elapsed time for reboot detection.
     */
    private fun saveLastKnownElapsed(elapsed: Long) {
        prefs.edit()
            .putLong(KEY_LAST_KNOWN_ELAPSED, elapsed)
            .apply()
    }

    /**
     * Get the secure current time in milliseconds (epoch time).
     * 
     * This time is resistant to device time manipulation.
     * 
     * @return Current time in milliseconds since Unix epoch
     */
    fun getSecureCurrentTimeMillis(): Long {
        val currentElapsed = SystemClock.elapsedRealtime()
        val elapsedSinceReference = currentElapsed - referenceElapsedTime

        // Update last known elapsed periodically
        saveLastKnownElapsed(currentElapsed)

        // Calculate secure time: reference wall time + elapsed since reference
        val secureTime = referenceWallTime + elapsedSinceReference

        // Apply server time offset if we have one
        return secureTime + serverTimeOffset
    }

    /**
     * Get the start of the current day using secure time.
     * 
     * @return Epoch milliseconds for 00:00:00.000 of the current day (secure)
     */
    fun getSecureStartOfDay(): Long {
        return TimeUtils.getStartOfDay(getSecureCurrentTimeMillis())
    }

    /**
     * Synchronize with server time to improve accuracy.
     * 
     * Call this when receiving a response from the backend that contains
     * a server timestamp. This helps correct any drift in local time.
     * 
     * @param serverTimeMillis The server's current time in milliseconds
     */
    fun syncWithServerTime(serverTimeMillis: Long) {
        val localSecureTime = getSecureCurrentTimeMillis()
        val newOffset = serverTimeMillis - localSecureTime

        // Only update if significant difference (> 1 second)
        if (kotlin.math.abs(newOffset - serverTimeOffset) > 1000) {
            serverTimeOffset = newOffset
            prefs.edit()
                .putLong(KEY_SERVER_TIME_OFFSET, serverTimeOffset)
                .apply()
            Timber.i("Server time sync: offset updated to ${serverTimeOffset}ms")
        }
    }

    /**
     * Check if time appears to have been manipulated.
     * 
     * Compares the secure time against the device time. A large discrepancy
     * may indicate time manipulation.
     * 
     * @return true if potential manipulation detected
     */
    fun isTimeManipulationDetected(): Boolean {
        val secureTime = getSecureCurrentTimeMillis()
        val deviceTime = System.currentTimeMillis()
        val difference = kotlin.math.abs(secureTime - deviceTime)

        // If difference is more than 5 minutes, likely manipulation
        val isManipulated = difference > 5 * 60 * 1000L

        if (isManipulated) {
            Timber.w("Potential time manipulation detected: secure=$secureTime, device=$deviceTime, diff=${difference}ms")
        }

        return isManipulated
    }

    /**
     * Get the elapsed time since the device booted (monotonic).
     * 
     * @return Milliseconds since device boot
     */
    fun getElapsedRealtime(): Long {
        return SystemClock.elapsedRealtime()
    }

    /**
     * Force a resync of the time reference.
     * Use this if the user explicitly corrects device time via settings.
     */
    fun forceResync() {
        Timber.i("Forcing time reference resync")
        createNewReference()
    }

    /**
     * Get diagnostic information about the time provider state.
     * Useful for debugging time-related issues.
     */
    fun getDiagnostics(): Map<String, Any> {
        val currentElapsed = SystemClock.elapsedRealtime()
        return mapOf(
            "referenceWallTime" to referenceWallTime,
            "referenceElapsedTime" to referenceElapsedTime,
            "currentElapsedTime" to currentElapsed,
            "serverTimeOffset" to serverTimeOffset,
            "secureTime" to getSecureCurrentTimeMillis(),
            "deviceTime" to System.currentTimeMillis(),
            "timeManipulationDetected" to isTimeManipulationDetected()
        )
    }
}
