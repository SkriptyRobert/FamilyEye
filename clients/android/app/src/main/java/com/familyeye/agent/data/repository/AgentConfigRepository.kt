package com.familyeye.agent.data.repository

import kotlinx.coroutines.flow.Flow

interface AgentConfigRepository {
    val deviceId: Flow<String?>
    val apiKey: Flow<String?>
    val isPaired: Flow<Boolean>
    
    suspend fun savePairingData(deviceId: String, apiKey: String)
    suspend fun clearPairingData()
    
    suspend fun getDeviceId(): String?
    suspend fun getApiKey(): String?
}
