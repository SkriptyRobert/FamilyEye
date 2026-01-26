package com.familyeye.agent.receiver

import android.content.Context
import android.content.Intent
import android.os.Build
import com.familyeye.agent.service.FamilyEyeService
import io.mockk.*
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [Build.VERSION_CODES.P], manifest = Config.NONE)
class RestartReceiverTest {

    private lateinit var context: Context
    private lateinit var receiver: RestartReceiver

    @Before
    fun setup() {
        context = spyk(RuntimeEnvironment.getApplication())
        receiver = RestartReceiver()
        
        // Mock the static FamilyEyeService class
        mockkObject(FamilyEyeService)
    }

    @After
    fun tearDown() {
        unmockkAll()
    }

    @Test
    fun testRestartActionStartsService() {
        val intent = Intent(RestartReceiver.ACTION_RESTART).apply {
            putExtra("source", "test")
        }
        
        // Ensure debounce doesn't block us (last restart was long ago)
        val prefs = context.getSharedPreferences("restart_debounce", Context.MODE_PRIVATE)
        prefs.edit().putLong("last_restart_time", 0L).apply()

        receiver.onReceive(context, intent)

        // Verify that FamilyEyeService.start(context) was called
        verify { FamilyEyeService.start(any()) }
    }

    @Test
    fun testDebounceMechanism() {
        val intent = Intent(RestartReceiver.ACTION_RESTART).apply {
            putExtra("source", "test")
        }
        
        // Set last restart to NOW
        val prefs = context.getSharedPreferences("restart_debounce", Context.MODE_PRIVATE)
        prefs.edit().putLong("last_restart_time", System.currentTimeMillis()).apply()

        receiver.onReceive(context, intent)

        // Should NOT call start because of debounce
        verify(exactly = 0) { FamilyEyeService.start(any()) }
    }
}
