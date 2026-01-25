package com.familyeye.agent.data.repository

import android.content.Context
import android.content.SharedPreferences
import dagger.hilt.android.qualifiers.ApplicationContext
import org.json.JSONObject
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class UsageRepositoryImpl @Inject constructor(
    @ApplicationContext private val context: Context
) : UsageRepository {

    companion object {
        private const val PREFS_NAME = "usage_baseline_prefs"
        private const val KEY_USAGE_MAP = "usage_map_json"
        private const val KEY_DAILY_TOTAL = "daily_total"
        private const val KEY_TIMESTAMP = "last_update_timestamp"
    }

    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    override suspend fun saveRemoteUsage(usageByApp: Map<String, Int>, dailyUsage: Int) {
        try {
            val jsonObject = JSONObject()
            usageByApp.forEach { (app, duration) ->
                jsonObject.put(app, duration)
            }
            
            prefs.edit()
                .putString(KEY_USAGE_MAP, jsonObject.toString())
                .putInt(KEY_DAILY_TOTAL, dailyUsage)
                .putLong(KEY_TIMESTAMP, System.currentTimeMillis())
                .apply()
                
            Timber.v("Saved remote usage baseline: ${usageByApp.size} apps, total=$dailyUsage")
        } catch (e: Exception) {
            Timber.e(e, "Failed to save remote usage")
        }
    }

    override suspend fun getRemoteAppUsage(appName: String): Int {
        // Reset if data is stale (older than 24h)? No, let UsageTracker decide logic.
        // But preventing stale usage from blocking mostly harmless if it resets at midnight.
        // For simplicity, we trust the backend's snapshot until overwritten.
        
        try {
            val jsonString = prefs.getString(KEY_USAGE_MAP, "{}")
            val jsonObject = JSONObject(jsonString)
            return jsonObject.optInt(appName, 0)
        } catch (e: Exception) {
            Timber.e(e, "Failed to read remote app usage")
            return 0
        }
    }

    override suspend fun getRemoteDailyUsage(): Int {
        return prefs.getInt(KEY_DAILY_TOTAL, 0)
    }
}
