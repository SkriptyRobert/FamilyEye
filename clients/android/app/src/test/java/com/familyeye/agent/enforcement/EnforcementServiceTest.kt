package com.familyeye.agent.enforcement

import android.content.Context
import com.familyeye.agent.service.RuleEnforcer
import com.familyeye.agent.ui.screens.BlockType
import com.familyeye.agent.utils.PackageMatcher
import io.mockk.*
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [28])
class EnforcementServiceTest {

    private lateinit var context: Context
    private lateinit var ruleEnforcer: RuleEnforcer
    private lateinit var selfProtectionHandler: SelfProtectionHandler
    private lateinit var whitelistManager: WhitelistManager
    private lateinit var enforcementService: EnforcementService

    @Before
    fun setup() {
        context = RuntimeEnvironment.getApplication()
        ruleEnforcer = mockk(relaxed = true)
        selfProtectionHandler = mockk(relaxed = true)
        whitelistManager = mockk(relaxed = true)

        every { context.packageName } returns "com.familyeye.agent"

        enforcementService = EnforcementService(
            context,
            ruleEnforcer,
            selfProtectionHandler,
            whitelistManager
        )
    }

    @Test
    fun testOwnPackageIsWhitelisted() {
        val result = enforcementService.evaluate("com.familyeye.agent")

        assertTrue("Own package should always be whitelisted", result is EnforcementResult.Whitelisted)
    }

    @Test
    fun testTamperingAttemptIsDetected() {
        every { selfProtectionHandler.isTamperingAttempt(any(), any()) } returns true

        val result = enforcementService.evaluate("com.android.settings")

        assertTrue("Tampering attempts should be detected", result is EnforcementResult.TamperingDetected)
    }

    @Test
    fun testDeviceLockBlocksAllApps() {
        every { selfProtectionHandler.isTamperingAttempt(any(), any()) } returns false
        every { ruleEnforcer.isDeviceLocked() } returns true
        every { PackageMatcher.isSystemUI(any()) } returns false

        val result = enforcementService.evaluate("com.example.app")

        assertTrue("Device lock should block all apps", result is EnforcementResult.Block)
        assertEquals(BlockType.DEVICE_LOCK, (result as EnforcementResult.Block).blockType)
    }

    @Test
    fun testWhitelistedAppIsAllowed() {
        every { selfProtectionHandler.isTamperingAttempt(any(), any()) } returns false
        every { ruleEnforcer.isDeviceLocked() } returns false
        every { whitelistManager.isWhitelisted("com.system.app") } returns true

        val result = enforcementService.evaluate("com.system.app")

        assertTrue("Whitelisted apps should be allowed", result is EnforcementResult.Whitelisted)
    }

    @Test
    fun testBlockedAppIsBlocked() {
        every { selfProtectionHandler.isTamperingAttempt(any(), any()) } returns false
        every { ruleEnforcer.isDeviceLocked() } returns false
        every { whitelistManager.isWhitelisted(any()) } returns false
        every { ruleEnforcer.isAppBlocked("com.blocked.app") } returns true

        val result = enforcementService.evaluate("com.blocked.app")

        assertTrue("Blocked apps should be blocked", result is EnforcementResult.Block)
        assertEquals(BlockType.APP_FORBIDDEN, (result as EnforcementResult.Block).blockType)
    }

    @Test
    fun testDeviceScheduleBlocksApp() {
        every { selfProtectionHandler.isTamperingAttempt(any(), any()) } returns false
        every { ruleEnforcer.isDeviceLocked() } returns false
        every { whitelistManager.isWhitelisted(any()) } returns false
        every { ruleEnforcer.isAppBlocked(any()) } returns false
        every { ruleEnforcer.isDeviceScheduleBlocked() } returns true
        every { ruleEnforcer.getActiveDeviceScheduleRule() } returns mockk {
            every { scheduleStartTime } returns "08:00"
            every { scheduleEndTime } returns "20:00"
        }

        val result = enforcementService.evaluate("com.example.app")

        assertTrue("Device schedule should block apps", result is EnforcementResult.Block)
        assertEquals(BlockType.DEVICE_SCHEDULE, (result as EnforcementResult.Block).blockType)
    }

    @Test
    fun testAllowedAppReturnsAllow() {
        every { selfProtectionHandler.isTamperingAttempt(any(), any()) } returns false
        every { ruleEnforcer.isDeviceLocked() } returns false
        every { whitelistManager.isWhitelisted(any()) } returns false
        every { ruleEnforcer.isAppBlocked(any()) } returns false
        every { ruleEnforcer.isDeviceScheduleBlocked() } returns false
        every { ruleEnforcer.isAppScheduleBlocked(any()) } returns false
        every { enforcementService.evaluateTimeLimits(any(), any(), any()) } returns EnforcementResult.Allow

        val result = enforcementService.evaluate("com.allowed.app")

        assertTrue("Apps that pass all checks should be allowed", result is EnforcementResult.Allow)
    }
}
