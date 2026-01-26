package com.familyeye.agent.receiver

import android.content.Context
import android.content.Intent
import android.os.Build
import com.familyeye.agent.service.FamilyEyeService
import io.mockk.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [Build.VERSION_CODES.P])
class BootReceiverTest {

    private lateinit var context: Context
    private lateinit var receiver: BootReceiver

    @Before
    fun setup() {
        context = RuntimeEnvironment.getApplication()
        receiver = BootReceiver()
        mockkObject(FamilyEyeService.Companion)
    }

    @Test
    fun testRebootStartsService() {
        val intent = Intent(Intent.ACTION_BOOT_COMPLETED)
        receiver.onReceive(context, intent)
        verify { FamilyEyeService.start(any()) }
    }

    @Test
    fun testDirectBootStartsService() {
        // Test Intent.ACTION_LOCKED_BOOT_COMPLETED (Direct Boot)
        val intent = Intent(Intent.ACTION_LOCKED_BOOT_COMPLETED)
        receiver.onReceive(context, intent)
        verify { FamilyEyeService.start(any()) }
    }

    @Test
    fun testUserPresentStartsService() {
        val intent = Intent(Intent.ACTION_USER_PRESENT)
        receiver.onReceive(context, intent)
        verify { FamilyEyeService.start(any()) }
    }
}
