package com.familyeye.agent.device

import android.app.admin.DevicePolicyManager
import android.content.Context
import android.os.Build
import io.mockk.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import timber.log.Timber

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [Build.VERSION_CODES.P], manifest = Config.NONE)
class PolicyEnforcerTest {

    private lateinit var context: Context
    private lateinit var dpm: DevicePolicyManager
    private lateinit var enforcer: DeviceOwnerPolicyEnforcer

    @Before
    fun setup() {
        context = spyk(RuntimeEnvironment.getApplication())
        dpm = mockk(relaxed = true)
        
        // Mock getSystemService to return our mock DPM
        every { context.getSystemService(Context.DEVICE_POLICY_SERVICE) } returns dpm
        
        enforcer = DeviceOwnerPolicyEnforcer(context)
        
        // Mock isDeviceOwner to be true for tests
        every { dpm.isDeviceOwnerApp(any()) } returns true
    }

    @Test
    fun testApplyBaselineRestrictionsHandlesSecurityException() {
        // Force a SecurityException when adding a restriction (e.g. permission revoked)
        every { dpm.addUserRestriction(any(), any()) } throws SecurityException("Permission removed by user")

        // This should NOT crash the app because of the try-catch block in DeviceOwnerPolicyEnforcer
        enforcer.applyBaselineRestrictions()
        
        // Verify that it reached the loop at least once
        verify(atLeast = 1) { dpm.addUserRestriction(any(), any()) }
    }

    @Test
    fun testSetUninstallBlockedHandlesException() {
        every { dpm.setUninstallBlocked(any(), any(), any()) } throws SecurityException("Not DO anymore")
        
        // Should not crash
        enforcer.setUninstallBlocked(true)
        
        verify { dpm.setUninstallBlocked(any(), any(), any()) }
    }
}
