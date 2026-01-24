package com.familyeye.agent.enforcement

import android.content.Context
import com.familyeye.agent.service.BlockOverlayManager
import com.familyeye.agent.service.RuleEnforcer
import com.familyeye.agent.service.UsageTracker
import com.familyeye.agent.ui.screens.BlockType
import com.familyeye.agent.utils.PackageMatcher
import dagger.hilt.android.qualifiers.ApplicationContext
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Result of an enforcement evaluation.
 */
sealed class EnforcementResult {
    /**
     * App is allowed to run.
     */
    object Allow : EnforcementResult()

    /**
     * App should be blocked.
     */
    data class Block(
        val blockType: BlockType,
        val scheduleInfo: String? = null
    ) : EnforcementResult()

    /**
     * App is whitelisted and should always be allowed.
     */
    object Whitelisted : EnforcementResult()

    /**
     * Tampering attempt detected.
     */
    data class TamperingDetected(
        val reason: String
    ) : EnforcementResult()
}

/**
 * Central enforcement orchestrator that evaluates all blocking policies.
 * 
 * This service delegates to specialized handlers for different types of checks:
 * - SelfProtectionHandler: Anti-tampering detection
 * - WhitelistManager: System app whitelist
 * - RuleEnforcer: Policy rules (blocks, schedules, limits)
 * 
 * The enforcement follows a priority order:
 * 1. Self-protection (tampering attempts)
 * 2. Device Lock (highest priority rule)
 * 3. Whitelist check
 * 4. App blocking rules
 * 5. Device schedules
 * 6. App schedules
 * 7. Device daily limit
 * 8. App time limits
 */
@Singleton
class EnforcementService @Inject constructor(
    @ApplicationContext private val context: Context,
    private val ruleEnforcer: RuleEnforcer,
    private val selfProtectionHandler: SelfProtectionHandler,
    private val whitelistManager: WhitelistManager
) {
    private val ownPackageName = context.packageName

    /**
     * Evaluate whether an app should be allowed or blocked.
     * 
     * @param packageName The package name of the app to evaluate
     * @param className Optional class name for more specific checks
     * @return EnforcementResult indicating whether to allow, block, or escalate
     */
    fun evaluate(packageName: String, className: String? = null): EnforcementResult {
        // Skip our own app
        if (packageName == ownPackageName) {
            return EnforcementResult.Whitelisted
        }

        // 1. Self-protection check (highest priority)
        if (selfProtectionHandler.isTamperingAttempt(packageName, className)) {
            return EnforcementResult.TamperingDetected(
                "Attempt to access protected settings: $packageName/$className"
            )
        }

        // 1.5. CRITICAL: Block SystemUI (Recents/Clear All) when Settings protection is active
        // This MUST be before Device Lock check to prevent access to Clear All
        if (PackageMatcher.isSystemUI(packageName)) {
            val protectionLevel = ruleEnforcer.getSettingsProtectionLevel()
            val unlockActive = ruleEnforcer.isUnlockSettingsActive()
            val shouldBlockSystemUI = com.familyeye.agent.policy.SettingsProtectionPolicy.shouldBlockSettings(
                protectionLevel, unlockActive
            )
            if (shouldBlockSystemUI) {
                Timber.w("CRITICAL: SystemUI blocked (prevents Clear All access)")
                return EnforcementResult.Block(BlockType.TAMPERING)
            }
        }

        // 2. Device Lock check (blocks everything except SystemUI)
        if (ruleEnforcer.isDeviceLocked()) {
            // Allow SystemUI to prevent crash but will be handled specially
            if (PackageMatcher.isSystemUI(packageName)) {
                return EnforcementResult.Block(BlockType.DEVICE_LOCK)
            }
            return EnforcementResult.Block(BlockType.DEVICE_LOCK)
        }

        // 2b. Device Schedule check for SystemUI (Brick Mode for Schedule)
        // SystemUI is normally whitelisted, so we must check this BEFORE the whitelist check.
        // This ensures the Notification Shade is blocked during schedules too.
        if (ruleEnforcer.isDeviceScheduleBlocked() && PackageMatcher.isSystemUI(packageName)) {
             val rule = ruleEnforcer.getActiveDeviceScheduleRule()
             val scheduleInfo = rule?.let { "${it.scheduleStartTime} - ${it.scheduleEndTime}" }
             return EnforcementResult.Block(BlockType.DEVICE_SCHEDULE, scheduleInfo)
        }

        // 3. Whitelist check
        if (whitelistManager.isWhitelisted(packageName)) {
            return EnforcementResult.Whitelisted
        }

        // 4. App blocking rules
        if (ruleEnforcer.isAppBlocked(packageName)) {
            return EnforcementResult.Block(BlockType.APP_FORBIDDEN)
        }

        // 5. Device schedule
        if (ruleEnforcer.isDeviceScheduleBlocked()) {
            val rule = ruleEnforcer.getActiveDeviceScheduleRule()
            val scheduleInfo = rule?.let { "${it.scheduleStartTime} - ${it.scheduleEndTime}" }
            return EnforcementResult.Block(BlockType.DEVICE_SCHEDULE, scheduleInfo)
        }

        // 6. App schedule
        if (ruleEnforcer.isAppScheduleBlocked(packageName)) {
            val rule = ruleEnforcer.getActiveAppScheduleRule(packageName)
            val scheduleInfo = rule?.let { "${it.scheduleStartTime} - ${it.scheduleEndTime}" }
            return EnforcementResult.Block(BlockType.APP_SCHEDULE, scheduleInfo)
        }

        // Time-based checks require async data - handled separately
        return EnforcementResult.Allow
    }

    /**
     * Evaluate time-based limits (requires suspend for database access).
     * Call this after the synchronous evaluate() returns Allow.
     * 
     * @param packageName The package name of the app
     * @param appUsageSeconds Usage time for this specific app today
     * @param totalUsageSeconds Total device usage time today
     * @return EnforcementResult for time-based limits
     */
    fun evaluateTimeLimits(
        packageName: String,
        appUsageSeconds: Int,
        totalUsageSeconds: Int
    ): EnforcementResult {
        // 7. Device daily limit
        if (ruleEnforcer.isDailyLimitExceeded(totalUsageSeconds)) {
            return EnforcementResult.Block(BlockType.DEVICE_LIMIT)
        }

        // 8. App time limit
        if (ruleEnforcer.isAppTimeLimitExceeded(packageName, appUsageSeconds)) {
            return EnforcementResult.Block(BlockType.APP_LIMIT)
        }

        return EnforcementResult.Allow
    }

    /**
     * Check if this is a launcher app (needs special handling).
     */
    fun isLauncher(packageName: String): Boolean {
        return PackageMatcher.isLauncher(packageName)
    }

    /**
     * Check if unlock settings is active (parent unlocked device temporarily).
     */
    fun isUnlockSettingsActive(): Boolean {
        return ruleEnforcer.isUnlockSettingsActive()
    }
}
