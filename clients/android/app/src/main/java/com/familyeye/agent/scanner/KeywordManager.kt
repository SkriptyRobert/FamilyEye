package com.familyeye.agent.scanner

import com.familyeye.agent.data.api.FamilyEyeApi
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.familyeye.agent.data.api.dto.ShieldKeyword
import kotlinx.coroutines.flow.firstOrNull
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class KeywordManager @Inject constructor(
    private val api: FamilyEyeApi,
    private val configRepository: AgentConfigRepository
) {
    private var cachedKeywords: List<ShieldKeyword> = emptyList()

    // Default hardcoded keywords until sync
    init {
        cachedKeywords = listOf(
            ShieldKeyword(0, 0, "sebevražda", "danger", "high", true),
            ShieldKeyword(0, 0, "zabiju", "danger", "high", true),
            ShieldKeyword(0, 0, "drogy", "danger", "high", true)
        )
    }

    fun getKeywords(): List<ShieldKeyword> {
        return cachedKeywords
    }

    suspend fun syncKeywords() {
        try {
            val deviceId = configRepository.deviceId.firstOrNull()
            val apiKey = configRepository.apiKey.firstOrNull()
            if (deviceId.isNullOrEmpty() || apiKey.isNullOrEmpty()) return

            val request = com.familyeye.agent.data.api.dto.AgentAuthRequest(deviceId, apiKey)
            val response = api.getShieldKeywords(request)
            
            if (response.isSuccessful && response.body() != null) {
                val newKeywords = response.body()!!
                cachedKeywords = newKeywords
                Timber.d("Keywords synced: ${newKeywords.size} active")
            } else {
                Timber.e("Failed to sync keywords: ${response.code()}")
            }
            
        } catch (e: Exception) {
            Timber.e(e, "Failed to sync keywords")
        }
    }
}
