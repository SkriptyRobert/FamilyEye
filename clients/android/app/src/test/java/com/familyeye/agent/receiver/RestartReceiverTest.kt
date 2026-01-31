package com.familyeye.agent.receiver

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.PowerManager
import com.familyeye.agent.service.AlarmWatchdog
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
    private lateinit var powerManager: PowerManager
    private lateinit var receiver: RestartReceiver

    @Before
    fun setup() {
        context = spyk(RuntimeEnvironment.getApplication())
        powerManager = mockk(relaxed = true)
        every { context.getSystemService(Context.POWER_SERVICE) } returns powerManager
        receiver = RestartReceiver()
        mockkObject(FamilyEyeService)
        mockkObject(AlarmWatchdog)
    }

    @After
    fun tearDown() {
        unmockkAll()
    }

    @Test
    fun testRestartActionStartsService() {
        every { powerManager.isInteractive } returns true
        val intent = Intent(RestartReceiver.ACTION_RESTART).apply {
            putExtra("source", "test")
        }
        val prefs = context.getSharedPreferences("restart_debounce", Context.MODE_PRIVATE)
        prefs.edit().putLong("last_restart_time", 0L).apply()

        receiver.onReceive(context, intent)

        verify { FamilyEyeService.start(any()) }
        verify { AlarmWatchdog.scheduleHeartbeat(any()) }
    }

    @Test
    fun testScreenOffDoesNotScheduleHeartbeat() {
        every { powerManager.isInteractive } returns false
        val intent = Intent(RestartReceiver.ACTION_RESTART).apply {
            putExtra("source", "test")
        }
        val prefs = context.getSharedPreferences("restart_debounce", Context.MODE_PRIVATE)
        prefs.edit().putLong("last_restart_time", 0L).apply()

        receiver.onReceive(context, intent)

        verify { FamilyEyeService.start(any()) }
        verify(exactly = 0) { AlarmWatchdog.scheduleHeartbeat(any()) }
    }

    @Test
    fun testDebounceMechanism() {
        every { powerManager.isInteractive } returns true
        val intent = Intent(RestartReceiver.ACTION_RESTART).apply {
            putExtra("source", "test")
        }
        val prefs = context.getSharedPreferences("restart_debounce", Context.MODE_PRIVATE)
        prefs.edit().putLong("last_restart_time", System.currentTimeMillis()).apply()

        receiver.onReceive(context, intent)

        verify(exactly = 0) { FamilyEyeService.start(any()) }
        verify(exactly = 0) { AlarmWatchdog.scheduleHeartbeat(any()) }
    }
}
