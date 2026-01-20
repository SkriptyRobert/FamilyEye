package com.familyeye.agent.data.repository

import android.content.Context
import android.content.SharedPreferences
import android.provider.Settings
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.familyeye.agent.config.AgentConstants
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import timber.log.Timber
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import javax.inject.Inject

/**
 * Repository implementation for agent configuration.
 * 
 * Security improvements:
 * - Sensitive data (API Key, Device ID, PIN) stored in EncryptedSharedPreferences
 * - PIN uses PBKDF2 with device-specific salt
 * - Seamless migration from DataStore to EncryptedSharedPreferences
 */
class AgentConfigRepositoryImpl @Inject constructor(
    private val dataStore: DataStore<Preferences>,
    private val encryptedPrefs: SharedPreferences, // Injected EncryptedSharedPreferences
    @ApplicationContext private val context: Context
) : AgentConfigRepository {

    // Keys for DataStore (Non-sensitive settings)
    private object DsKeys {
        val BACKEND_URL = stringPreferencesKey("backend_url")
        val DATA_SAVER_ENABLED = stringPreferencesKey("data_saver_enabled")
        
        // Legacy keys for migration
        val LEGACY_DEVICE_ID = stringPreferencesKey("device_id")
        val LEGACY_API_KEY = stringPreferencesKey("api_key")
        val LEGACY_PIN_HASH = stringPreferencesKey("pin_hash")
        val LEGACY_PIN_SALT = stringPreferencesKey("pin_salt")
    }

    // Keys for SharedPreferences (All pairing data now in same storage for consistency)
    private object EncKeys {
        const val DEVICE_ID = "device_id"
        const val API_KEY = "api_key"
        const val BACKEND_URL = "backend_url"  // Moved here for consistency
        const val PIN_HASH = "pin_hash"
        const val PIN_SALT = "pin_salt"
        const val SETTINGS_PROTECTION = "settings_protection"
        const val SETTINGS_EXCEPTIONS = "settings_exceptions"
    }

    init {
        // Trigger migration from DataStore to EncryptedSharedPreferences
        CoroutineScope(Dispatchers.IO).launch {
            migrateSensitiveData()
        }
    }

    private suspend fun migrateSensitiveData() {
        val prefs = dataStore.data.first()
        
        // Migration helper
        suspend fun migrateKey(dsKey: Preferences.Key<String>, encKey: String) {
            val value = prefs[dsKey]
            if (value != null) {
                Timber.i("Migrating $encKey to EncryptedStorage")
                encryptedPrefs.edit().putString(encKey, value).apply()
                dataStore.edit { it.remove(dsKey) }
            }
        }

        migrateKey(DsKeys.LEGACY_DEVICE_ID, EncKeys.DEVICE_ID)
        migrateKey(DsKeys.LEGACY_API_KEY, EncKeys.API_KEY)
        migrateKey(DsKeys.LEGACY_PIN_HASH, EncKeys.PIN_HASH)
        migrateKey(DsKeys.LEGACY_PIN_SALT, EncKeys.PIN_SALT)
    }

    // Helper to generic Flow from SharedPreferences
    private fun getEncryptedStringFlow(key: String): Flow<String?> = callbackFlow {
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { prefs, changedKey ->
            if (key == changedKey) {
                trySend(prefs.getString(key, null))
            }
        }
        encryptedPrefs.registerOnSharedPreferenceChangeListener(listener)
        
        // Initial value
        trySend(encryptedPrefs.getString(key, null))
        
        awaitClose {
            encryptedPrefs.unregisterOnSharedPreferenceChangeListener(listener)
        }
    }.distinctUntilChanged()

    override val deviceId: Flow<String?> = getEncryptedStringFlow(EncKeys.DEVICE_ID)

    override val apiKey: Flow<String?> = getEncryptedStringFlow(EncKeys.API_KEY)

    // Backend URL now stored in SharedPreferences for consistency
    override val backendUrl: Flow<String?> = getEncryptedStringFlow(EncKeys.BACKEND_URL)

    override val isPaired: Flow<Boolean> = combine(deviceId, apiKey, backendUrl) { dId, key, url ->
        val paired = !dId.isNullOrEmpty() && !key.isNullOrEmpty() && !url.isNullOrEmpty()
        Timber.d("isPaired check: deviceId=${dId?.take(8)}... apiKey=${key?.take(8)}... url=${url?.take(20)}... => $paired")
        paired
    }

    override val dataSaverEnabled: Flow<Boolean> = dataStore.data.map { prefs ->
        prefs[DsKeys.DATA_SAVER_ENABLED]?.toBoolean() ?: false
    }

    override suspend fun savePairingData(deviceId: String, apiKey: String) {
        Timber.i("Saving pairing data: deviceId=${deviceId.take(8)}... apiKey=${apiKey.take(8)}...")
        // Use commit() to ensure data is written to disk immediately and synchronously.
        val success = encryptedPrefs.edit()
            .putString(EncKeys.DEVICE_ID, deviceId)
            .putString(EncKeys.API_KEY, apiKey)
            .commit()
        Timber.i("Pairing data save result: $success")
            
        // Ensure legacy keys are removed just in case
        dataStore.edit { prefs ->
            prefs.remove(DsKeys.LEGACY_DEVICE_ID)
            prefs.remove(DsKeys.LEGACY_API_KEY)
        }
    }

    override suspend fun saveBackendUrl(url: String) {
        Timber.i("Saving backend URL: ${url.take(30)}...")
        // Store in SharedPreferences for consistency with other pairing data
        val success = encryptedPrefs.edit()
            .putString(EncKeys.BACKEND_URL, url)
            .commit()
        Timber.i("Backend URL save result: $success")
    }

    override suspend fun clearPairingData() {
        Timber.i("Clearing all pairing data")
        encryptedPrefs.edit()
            .remove(EncKeys.DEVICE_ID)
            .remove(EncKeys.API_KEY)
            .remove(EncKeys.BACKEND_URL)
            .commit()
    }
    
    override suspend fun setDataSaverEnabled(enabled: Boolean) {
        dataStore.edit { prefs ->
            prefs[DsKeys.DATA_SAVER_ENABLED] = enabled.toString()
        }
    }
    
    override suspend fun getDeviceId(): String? {
        return encryptedPrefs.getString(EncKeys.DEVICE_ID, null)
    }
    
    override suspend fun getApiKey(): String? {
        return encryptedPrefs.getString(EncKeys.API_KEY, null)
    }

    override suspend fun getBackendUrl(): String? {
        return encryptedPrefs.getString(EncKeys.BACKEND_URL, null)
    }

    // ==================== PIN Security with PBKDF2 ====================

    override suspend fun savePin(pin: String) {
        val salt = generateSalt()
        val hash = hashPinPBKDF2(pin, salt)
        
        encryptedPrefs.edit()
            .putString(EncKeys.PIN_HASH, hash)
            .putString(EncKeys.PIN_SALT, salt.toHexString())
            .apply()
            
        // Clean up legacy
        dataStore.edit { prefs ->
            prefs.remove(DsKeys.LEGACY_PIN_HASH)
            prefs.remove(DsKeys.LEGACY_PIN_SALT)
        }
        
        Timber.i("PIN saved with PBKDF2 hashing in EncryptedStorage")
    }

    override suspend fun verifyPin(pin: String): Boolean {
        // Try encrypted prefs first
        var storedHash = encryptedPrefs.getString(EncKeys.PIN_HASH, null)
        var storedSaltHex = encryptedPrefs.getString(EncKeys.PIN_SALT, null)
        
        // Fallback to DataStore if not found (and migration pending/failed)
        if (storedHash == null) {
            val prefs = dataStore.data.first()
            storedHash = prefs[DsKeys.LEGACY_PIN_HASH]
            storedSaltHex = prefs[DsKeys.LEGACY_PIN_SALT]
        }
        
        if (storedHash == null) return false
        val storedSalt = storedSaltHex?.hexToByteArray() ?: return false
        
        val computedHash = hashPinPBKDF2(pin, storedSalt)
        return storedHash == computedHash
    }

    override suspend fun hasPin(): Boolean {
        return encryptedPrefs.contains(EncKeys.PIN_HASH) || 
               dataStore.data.first()[DsKeys.LEGACY_PIN_HASH] != null
    }

    /**
     * Generate a cryptographically secure salt.
     * Combines device-specific Android ID with random bytes.
     */
    private fun generateSalt(): ByteArray {
        // Device-specific component from Android ID
        val androidId = Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ANDROID_ID
        ) ?: "default_fallback"
        
        // Random component for additional entropy
        val random = ByteArray(16)
        SecureRandom().nextBytes(random)
        
        // Combine device ID and random bytes
        val combined = androidId.toByteArray() + random
        
        // Return first 32 bytes (256 bits) of combined salt
        return combined.copyOf(32)
    }

    /**
     * Hash a PIN using PBKDF2 with SHA-256.
     */
    private fun hashPinPBKDF2(pin: String, salt: ByteArray): String {
        try {
            val spec = PBEKeySpec(
                pin.toCharArray(),
                salt,
                AgentConstants.PIN_HASH_ITERATIONS,
                AgentConstants.PIN_HASH_KEY_LENGTH
            )
            
            val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
            val hash = factory.generateSecret(spec).encoded
            
            return hash.toHexString()
        } catch (e: Exception) {
            Timber.e(e, "PBKDF2 hashing failed, falling back to SHA-256")
            return fallbackHash(pin, salt)
        }
    }

    private fun fallbackHash(pin: String, salt: ByteArray): String {
        val combined = pin.toByteArray() + salt
        val bytes = java.security.MessageDigest.getInstance("SHA-256").digest(combined)
        return bytes.toHexString()
    }

    // ==================== Extension Functions ====================

    private fun ByteArray.toHexString(): String {
        return joinToString("") { "%02x".format(it) }
    }

    private fun String.hexToByteArray(): ByteArray {
        return chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    }
    
    // ==================== Settings Protection ====================
    
    override suspend fun saveSettingsProtection(level: String, exceptions: String?) {
        encryptedPrefs.edit()
            .putString(EncKeys.SETTINGS_PROTECTION, level)
            .apply {
                if (exceptions != null) {
                    putString(EncKeys.SETTINGS_EXCEPTIONS, exceptions)
                } else {
                    remove(EncKeys.SETTINGS_EXCEPTIONS)
                }
            }
            .apply()
        Timber.i("Settings protection saved: level=$level, exceptions=$exceptions")
    }
    
    override fun getSettingsProtection(): String {
        return encryptedPrefs.getString(EncKeys.SETTINGS_PROTECTION, "full") ?: "full"
    }
    
    override fun getSettingsExceptions(): String? {
        return encryptedPrefs.getString(EncKeys.SETTINGS_EXCEPTIONS, null)
    }
}
