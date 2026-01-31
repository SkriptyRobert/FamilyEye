package com.familyeye.agent.config

/**
 * Centralized constants for the FamilyEye agent.
 * 
 * This file replaces all magic numbers scattered throughout the codebase
 * with named constants for better maintainability and configuration.
 */
object AgentConstants {

    // ==================== TIMING INTERVALS ====================
    
    /**
     * Interval for fetching rules from backend (milliseconds).
     * Rules are cached locally and refreshed at this interval.
     */
    const val RULE_FETCH_INTERVAL_MS = 30_000L  // 30 seconds

    /**
     * Interval for tracking app usage (milliseconds).
     * Lower values = more accurate tracking, higher battery usage.
     */
    const val USAGE_TRACK_INTERVAL_MS = 5_000L  // 5 seconds

    /**
     * Interval when screen is off; longer to avoid waking the process often (battery-friendly).
     */
    const val USAGE_TRACK_INTERVAL_SCREEN_OFF_MS = 60_000L  // 60 seconds

    /**
     * Interval for flushing in-memory usage buffer to DB (milliseconds).
     * Reduces disk writes while screen is on.
     */
    const val USAGE_FLUSH_INTERVAL_MS = 60_000L  // 60 seconds

    /**
     * Interval for syncing usage logs to backend (milliseconds).
     * Also serves as heartbeat interval.
     */
    const val SYNC_INTERVAL_MS = 30_000L  // 30 seconds

    /**
     * Interval for syncing when battery is low (milliseconds).
     * Longer interval to conserve battery.
     */
    const val SYNC_INTERVAL_BATTERY_LOW_MS = 60_000L  // 60 seconds

    /**
     * Battery level threshold for low-battery mode (percentage 0-100).
     * Below this level, sync interval is extended to conserve battery.
     */
    const val BATTERY_LOW_THRESHOLD = 20

    /**
     * Maximum number of logs to send via WebSocket.
     * Larger batches go via HTTP for reliability.
     */
    const val WEBSOCKET_LOG_BATCH_THRESHOLD = 20

    /**
     * Delay before taking screenshots (milliseconds).
     * Allows UI to fully render before capture.
     */
    const val SCREENSHOT_DELAY_MS = 1_000L  // 1 second

    /**
     * Interval for WebSocket reconnection attempts (milliseconds).
     */
    const val WEBSOCKET_RETRY_INTERVAL_MS = 5_000L  // 5 seconds



    /**
     * Notification timeout for accessibility service (milliseconds).
     */
    const val ACCESSIBILITY_NOTIFICATION_TIMEOUT_MS = 100L

    // ==================== RECOVERY & WATCHDOG ====================

    /**
     * Interval for security/health monitoring watchdog (milliseconds).
     * Faster = quicker recovery from zombie state, but more CPU usage.
     */
    const val SECURITY_CHECK_INTERVAL_MS = 10_000L  // 10 seconds (was 60s)

    /**
     * Interval for content scanner (Smart Shield) between scans (milliseconds).
     * Set to 1000L for responsiveness.
     */
    const val CONTENT_SCAN_INTERVAL_MS = 1_000L


    /**
     * Interval for WorkManager guardian worker (minutes).
     * This is the minimum allowed by WorkManager.
     */
    const val GUARDIAN_WORKER_INTERVAL_MIN = 15L  // 15 minutes

    /**
     * Delay before escalating to nuclear restart (milliseconds).
     * If self-repair doesn't work within this time, force full restart.
     */
    const val SELF_REPAIR_TIMEOUT_MS = 5_000L  // 5 seconds

    // ==================== SYNC LIMITS ====================

    /**
     * Maximum number of unsynced logs to fetch per sync batch.
     */
    const val MAX_UNSYNCED_LOGS_PER_BATCH = 100

    /**
     * Maximum age of synced logs to retain locally (milliseconds).
     * Older synced logs are deleted to save storage.
     */
    const val SYNCED_LOG_RETENTION_MS = 24 * 60 * 60 * 1000L  // 24 hours

    /**
     * Maximum number of sync retry attempts before giving up.
     */
    const val MAX_SYNC_RETRIES = 5

    // ==================== CACHE LIMITS ====================

    /**
     * Maximum number of app names to cache in memory.
     */
    const val APP_NAME_CACHE_SIZE = 200

    /**
     * Maximum context text length for shield alerts (characters).
     */
    const val MAX_CONTEXT_TEXT_LENGTH = 200

    // ==================== IMAGE QUALITY ====================

    /**
     * JPEG compression quality for screenshots (0-100).
     * Lower = smaller file, lower quality.
     */
    const val SCREENSHOT_JPEG_QUALITY = 70

    // ==================== NOTIFICATION IDS ====================

    /**
     * Notification ID for the monitoring foreground service.
     */
    const val MONITORING_NOTIFICATION_ID = 1001

    /**
     * Notification channel ID for monitoring service.
     */
    const val MONITORING_CHANNEL_ID = "familyeye_monitor_channel"

    // ==================== PIN SECURITY ====================

    /**
     * Number of PBKDF2 iterations for PIN hashing.
     * Higher = more secure but slower.
     */
    const val PIN_HASH_ITERATIONS = 10_000

    /**
     * Length of derived key for PIN hashing (bytes).
     */
    const val PIN_HASH_KEY_LENGTH = 256

    // ==================== DATA FORMATS ====================

    /**
     * ISO 8601 date format for API communication.
     */
    const val ISO_DATE_FORMAT = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"

    /**
     * Time format used in schedule rules.
     */
    const val SCHEDULE_TIME_FORMAT = "HH:mm"
    
    /**
     * Shared Preferences file name.
     */
    const val PREFS_NAME = "family_eye_prefs"
}
