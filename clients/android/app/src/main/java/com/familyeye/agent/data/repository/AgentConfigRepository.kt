package com.familyeye.agent.data.repository

import kotlinx.coroutines.flow.Flow

interface AgentConfigRepository {
    val deviceId: Flow<String?>
    val apiKey: Flow<String?>
    val backendUrl: Flow<String?>
    val isPaired: Flow<Boolean>
    val dataSaverEnabled: Flow<Boolean>
    
    suspend fun savePairingData(deviceId: String, apiKey: String)
    suspend fun saveBackendUrl(url: String)
    suspend fun clearPairingData()
    
    suspend fun setDataSaverEnabled(enabled: Boolean)
    
    suspend fun getDeviceId(): String?
    suspend fun getApiKey(): String?
    suspend fun getBackendUrl(): String?
    
    // PIN Protection
    suspend fun savePin(pin: String)
    suspend fun verifyPin(pin: String): Boolean
    suspend fun hasPin(): Boolean
    
    // Settings Protection
    suspend fun saveSettingsProtection(level: String, exceptions: String?)
    fun getSettingsProtection(): String  // Synchronous - SharedPreferences read
    fun getSettingsExceptions(): String?  // Synchronous - SharedPreferences read
}
