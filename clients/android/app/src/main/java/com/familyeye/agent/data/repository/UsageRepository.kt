package com.familyeye.agent.data.repository

/**
 * Repository for managing usage statistics baseline.
 * 
 * This repository bridges the gap between local usage logs and the backend's 
 * global usage view. It persists the "External Usage" snapshot received 
 * during rule sync, allowing the agent to enforce limits even if local logs 
 * are lost (e.g. after fresh install or crash).
 */
interface UsageRepository {
    /**
     * Save the usage snapshot received from the backend.
     * 
     * @param usageByApp Map of App Name -> Duration in Seconds
     * @param dailyUsage Total device usage today (seconds)
     */
    suspend fun saveRemoteUsage(usageByApp: Map<String, Int>, dailyUsage: Int)

    /**
     * Get the remote baseline usage for a specific app.
     * 
     * @param appName The display name of the app (as known by backend)
     * @return Usage in seconds calculated by backend
     */
    suspend fun getRemoteAppUsage(appName: String): Int

    /**
     * Get the remote baseline for total device usage.
     * 
     * @return Total usage in seconds calculated by backend
     */
    suspend fun getRemoteDailyUsage(): Int
}
