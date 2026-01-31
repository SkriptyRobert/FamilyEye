package com.familyeye.agent.service

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.familyeye.agent.data.api.WebSocketClient
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.familyeye.agent.ui.KeepAliveActivity
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.firstOrNull
import timber.log.Timber

/**
 * Guardian Worker that runs periodically via WorkManager to ensure
 * the agent is healthy. This is a backup recovery mechanism for when
 * AlarmManager or onTaskRemoved fail due to aggressive OEM battery management.
 * 
 * Runs every 15 minutes (WorkManager minimum interval).
 */
@HiltWorker
class ProcessGuardianWorker @AssistedInject constructor(
    @Assisted private val context: Context,
    @Assisted params: WorkerParameters,
    private val configRepository: AgentConfigRepository,
    private val webSocketClient: WebSocketClient
) : CoroutineWorker(context, params) {

    companion object {
        const val WORK_NAME = "FamilyEyeGuardian"
        private const val MAX_WEBSOCKET_SILENCE_MS = 120_000L // 2 minutes
    }

    override suspend fun doWork(): Result {
        Timber.d("ProcessGuardianWorker: Running health check...")
        
        // Only run if device is paired
        val isPaired = configRepository.isPaired.firstOrNull() ?: false
        if (!isPaired) {
            Timber.d("Device not paired, skipping guardian check")
            return Result.success()
        }

        val isHealthy = checkServiceHealth()
        
        if (!isHealthy) {
            Timber.w("ProcessGuardianWorker: Agent unhealthy! Triggering recovery...")
            triggerRecovery()
        } else {
            Timber.d("ProcessGuardianWorker: Agent healthy")
        }
        
        return Result.success()
    }

    /**
     * Check if all critical agent components are running properly.
     * Also checks Device Owner status if available.
     */
    private fun checkServiceHealth(): Boolean {
        // 1. Check FamilyEyeService is running
        val isServiceRunning = isServiceRunning(FamilyEyeService::class.java)
        if (!isServiceRunning) {
            Timber.e("Guardian: FamilyEyeService NOT running!")
            return false
        }

        // 2. Check AppDetectorService (Accessibility) is bound
        val isAccessibilityActive = AppDetectorService.instance != null
        if (!isAccessibilityActive) {
            Timber.e("Guardian: AppDetectorService NOT bound!")
            return false
        }

        // 3. Check Device Owner status (if applicable)
        try {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
            val isDeviceOwner = dpm.isDeviceOwnerApp(context.packageName)
            if (isDeviceOwner) {
                Timber.d("Guardian: Device Owner mode active - enhanced protection")
            }
        } catch (e: Exception) {
            Timber.d("Guardian: Could not check Device Owner status (normal if not provisioned)")
        }

        // 4. Check WebSocket connection (allow 2 min silent period)
        val isWebSocketConnected = webSocketClient.isConnected.value
        if (!isWebSocketConnected) {
            Timber.w("Guardian: WebSocket not connected (may be temporary)")
            // Not a hard failure - network could be temporarily unavailable
        }

        return true
    }

    /**
     * Check if a service is currently running.
     */
    private fun isServiceRunning(serviceClass: Class<*>): Boolean {
        val manager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        @Suppress("DEPRECATION")
        for (service in manager.getRunningServices(Int.MAX_VALUE)) {
            if (serviceClass.name == service.service.className) {
                return true
            }
        }
        return false
    }

    /**
     * Trigger full recovery by launching KeepAliveActivity.
     * This kicks the process into foreground priority and restarts services.
     */
    private fun triggerRecovery() {
        try {
            val intent = Intent(context, KeepAliveActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                putExtra("source", "guardian_worker")
            }
            context.startActivity(intent)
            Timber.i("ProcessGuardianWorker: Recovery triggered via KeepAliveActivity")
        } catch (e: Exception) {
            Timber.e(e, "Failed to trigger recovery")
            // Fallback: try to start service directly
            try {
                FamilyEyeService.start(context)
            } catch (e2: Exception) {
                Timber.e(e2, "Fallback service start also failed")
            }
        }
    }
}
