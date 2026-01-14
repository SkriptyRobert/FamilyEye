package com.familyeye.agent.service

import com.familyeye.agent.data.api.FamilyEyeApi
import com.familyeye.agent.data.api.dto.AgentReportRequest
import com.familyeye.agent.data.api.dto.AgentUsageLogCreate
import com.familyeye.agent.data.local.UsageLogDao
import com.familyeye.agent.data.repository.AgentConfigRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import timber.log.Timber
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Syncs local usage logs to the backend.
 */
@Singleton
class Reporter @Inject constructor(
    private val api: FamilyEyeApi,
    private val usageLogDao: UsageLogDao,
    private val configRepository: AgentConfigRepository,
    @dagger.hilt.android.qualifiers.ApplicationContext private val context: android.content.Context
) {
    private val reporterScope = CoroutineScope(Dispatchers.IO)
    private val isoFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    fun start() {
        reporterScope.launch {
            while (isActive) {
                try {
                    doSync()
                } catch (e: Exception) {
                    Timber.e(e, "Error in Reporter")
                }
                delay(30000) // Sync every 30 seconds
            }
        }
    }

    fun forceSync() {
        reporterScope.launch {
             try {
                doSync()
             } catch (e: Exception) {
                Timber.e(e, "Error in Force Sync")
             }
        }
    }

    private suspend fun doSync() {
        if (configRepository.isPaired.first()) {
            val isDataSaver = configRepository.dataSaverEnabled.first()
            
            if (isDataSaver && !isWifiConnected()) {
                Timber.d("Data Saver active & NO Wi-Fi - skipping sync")
            } else {
                syncLogs()
            }
        }
    }

    private suspend fun syncLogs() {
        val deviceId = configRepository.getDeviceId() ?: return
        val apiKey = configRepository.getApiKey() ?: return
        
        val unsyncedLogs = usageLogDao.getUnsyncedLogs(limit = 100)
        
        // Even if no logs, send heartbeat to keep device "Online"
        Timber.d("Syncing ${unsyncedLogs.size} logs to backend (Heartbeat)...")

        val reportItems = unsyncedLogs.map { log ->
            AgentUsageLogCreate(
                appName = log.appName,
                duration = log.durationSeconds,
                isFocused = true,
                timestamp = isoFormat.format(Date(log.timestamp))
            )
        }

        val request = AgentReportRequest(
            deviceId = deviceId,
            apiKey = apiKey,
            usageLogs = reportItems,
            clientTimestamp = isoFormat.format(Date())
        )

        try {
            val response = api.reportUsage(request)
            if (response.isSuccessful) {
                if (unsyncedLogs.isNotEmpty()) {
                    Timber.i("Successfully synced ${unsyncedLogs.size} logs")
                    usageLogDao.markAsSynced(unsyncedLogs.map { it.id })
                    
                    // Cleanup old logs
                    val oneDayAgo = System.currentTimeMillis() - (24 * 60 * 60 * 1000)
                    usageLogDao.deleteSyncedLogsOlderThan(oneDayAgo)
                } else {
                    Timber.i("Heartbeat sent successfully")
                }
            } else {
                Timber.e("Failed to sync logs/heartbeat: ${response.code()}")
            }
        } catch (e: Exception) {
             Timber.e(e, "Network error during sync")
        }
    }

    private fun isWifiConnected(): Boolean {
        val connectivityManager = context.getSystemService(android.content.Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        return capabilities.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI)
    }
}
