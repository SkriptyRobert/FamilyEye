package com.familyeye.agent.data.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import java.security.MessageDigest
import javax.inject.Inject

class AgentConfigRepositoryImpl @Inject constructor(
    private val dataStore: DataStore<Preferences>
) : AgentConfigRepository {

    private object Keys {
        val DEVICE_ID = stringPreferencesKey("device_id")
        val API_KEY = stringPreferencesKey("api_key")
        val BACKEND_URL = stringPreferencesKey("backend_url")
        val DATA_SAVER_ENABLED = stringPreferencesKey("data_saver_enabled")
        val PIN_HASH = stringPreferencesKey("pin_hash")
    }

    override val deviceId: Flow<String?> = dataStore.data.map { prefs ->
        prefs[Keys.DEVICE_ID]
    }

    override val apiKey: Flow<String?> = dataStore.data.map { prefs ->
        prefs[Keys.API_KEY]
    }

    override val backendUrl: Flow<String?> = dataStore.data.map { prefs ->
        prefs[Keys.BACKEND_URL]
    }

    override val isPaired: Flow<Boolean> = dataStore.data.map { prefs ->
        prefs[Keys.DEVICE_ID] != null && prefs[Keys.API_KEY] != null && prefs[Keys.BACKEND_URL] != null
    }

    override val dataSaverEnabled: Flow<Boolean> = dataStore.data.map { prefs ->
        prefs[Keys.DATA_SAVER_ENABLED]?.toBoolean() ?: false
    }

    override suspend fun savePairingData(deviceId: String, apiKey: String) {
        dataStore.edit { prefs ->
            prefs[Keys.DEVICE_ID] = deviceId
            prefs[Keys.API_KEY] = apiKey
        }
    }

    override suspend fun saveBackendUrl(url: String) {
        dataStore.edit { prefs ->
            prefs[Keys.BACKEND_URL] = url
        }
    }

    override suspend fun clearPairingData() {
        dataStore.edit { prefs ->
            prefs.remove(Keys.DEVICE_ID)
            prefs.remove(Keys.API_KEY)
            prefs.remove(Keys.BACKEND_URL)
        }
    }
    
    override suspend fun setDataSaverEnabled(enabled: Boolean) {
        dataStore.edit { prefs ->
            prefs[Keys.DATA_SAVER_ENABLED] = enabled.toString()
        }
    }
    
    override suspend fun getDeviceId(): String? {
        return dataStore.data.first()[Keys.DEVICE_ID]
    }
    
    override suspend fun getApiKey(): String? {
        return dataStore.data.first()[Keys.API_KEY]
    }

    override suspend fun getBackendUrl(): String? {
        return dataStore.data.first()[Keys.BACKEND_URL]
    }

    // PIN Protection
    override suspend fun savePin(pin: String) {
        val hash = hashPin(pin)
        dataStore.edit { prefs ->
            prefs[Keys.PIN_HASH] = hash
        }
    }

    override suspend fun verifyPin(pin: String): Boolean {
        val storedHash = dataStore.data.first()[Keys.PIN_HASH] ?: return false
        return hashPin(pin) == storedHash
    }

    override suspend fun hasPin(): Boolean {
        return dataStore.data.first()[Keys.PIN_HASH] != null
    }

    private fun hashPin(pin: String): String {
        val bytes = MessageDigest.getInstance("SHA-256").digest(pin.toByteArray())
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
